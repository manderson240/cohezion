"""Tests for UniverseAgentEnv — the text-in/text-out LLM agentic environment."""

import numpy as np
import pytest

from cohezion.environments.universe_agent_env import UniverseAgentEnv
from cohezion.worldviews import get_traditions


def _final_deviation(action: str, seed: int, n_steps: int = 10) -> float:
    env = UniverseAgentEnv(max_steps=100, seed=seed)
    env.reset(seed=seed)
    deviation = 0.0
    for _ in range(n_steps):
        _, _, _, _, info = env.step(action)
        deviation = float(info["hiho_deviation"])
    return deviation


class TestTextInterface:
    def test_reset_returns_text(self):
        env = UniverseAgentEnv(max_steps=20, seed=42)
        obs, info = env.reset()
        assert isinstance(obs, str)
        assert not isinstance(obs, np.ndarray)
        assert isinstance(info, dict)
        assert "equilibrium" in obs.lower()

    def test_step_returns_text_and_float_reward(self):
        env = UniverseAgentEnv(max_steps=20, seed=42)
        env.reset()
        obs, reward, terminated, truncated, _info = env.step("push toward equilibrium")
        assert isinstance(obs, str)
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)

    def test_observation_contains_worldview(self):
        env = UniverseAgentEnv(max_steps=20, seed=42)
        obs, info = env.reset()
        assert info["tradition"] in obs
        # Step observations keep the framing too
        obs, _, _, _, _ = env.step("hold")
        assert info["tradition"] in obs

    def test_step_accepts_any_text(self):
        env = UniverseAgentEnv(max_steps=20, seed=42)
        env.reset()
        long_text = "frobnicate the quantum flux capacitor " * 14  # >500 chars
        assert len(long_text) >= 500
        obs, reward, _terminated, _truncated, _info = env.step(long_text)
        assert isinstance(obs, str)
        assert isinstance(reward, float)


class TestActionParsing:
    def test_text_action_parsed_correctly(self):
        env = UniverseAgentEnv(max_steps=20, seed=42)
        env.reset()
        pos = env._last_position.copy()
        vel = env.parse_action("push toward equilibrium")
        expected = np.clip((0.5 - pos) * 3.0, -0.5, 0.5)
        np.testing.assert_allclose(vel, expected, atol=1e-6)

        hold = env.parse_action("hold")
        np.testing.assert_array_equal(hold, np.zeros(12, dtype=np.float32))

    def test_dimension_action_parsed(self):
        env = UniverseAgentEnv(max_steps=20, seed=42)
        env.reset()
        up = env.parse_action("push dimension 3 up")
        assert up[3] == pytest.approx(0.3)
        assert np.count_nonzero(up) == 1
        down = env.parse_action("push dimension 11 down")
        assert down[11] == pytest.approx(-0.3)
        # Out-of-range dimension is a safe no-op
        oob = env.parse_action("push dimension 99 up")
        np.testing.assert_array_equal(oob, np.zeros(12, dtype=np.float32))

    def test_unknown_action_is_failsafe(self):
        env = UniverseAgentEnv(max_steps=20, seed=42)
        env.reset()
        vel = env.parse_action("xyzzy frobnicator")
        np.testing.assert_array_equal(vel, np.zeros(12, dtype=np.float32))
        # And stepping with it does not crash
        obs, _reward, _, _, _ = env.step("xyzzy frobnicator")
        assert isinstance(obs, str)

    def test_explore_action_is_random_perturbation(self):
        env = UniverseAgentEnv(max_steps=20, seed=42)
        env.reset()
        vel = env.parse_action("explore")
        assert vel.shape == (12,)
        assert np.any(vel != 0.0)
        assert np.all(np.abs(vel) <= 0.5)


class TestDynamics:
    def test_step_with_equilibrium_action_reduces_deviation(self):
        # Discriminating: pushing toward equilibrium must beat holding still
        # from the same seed over 10 steps.
        for seed in (0, 42):
            eq_dev = _final_deviation("push toward equilibrium", seed)
            hold_dev = _final_deviation("hold", seed)
            assert eq_dev < hold_dev, (
                f"seed={seed}: equilibrium push ({eq_dev:.4f}) did not beat hold ({hold_dev:.4f})"
            )

    def test_episode_terminates(self):
        env = UniverseAgentEnv(max_steps=5, seed=42)
        env.reset()
        terminated = False
        truncated = False
        for _ in range(5):
            _, _, terminated, truncated, _ = env.step("hold")
            if terminated or truncated:
                break
        assert truncated or terminated
        # A fresh reset works cleanly after episode end
        obs, _ = env.reset()
        assert isinstance(obs, str)


class TestWorldviewCycling:
    def test_tradition_cycles_across_episodes(self):
        env = UniverseAgentEnv(max_steps=5, seed=42)
        n = len(get_traditions())
        seen = set()
        for _ in range(n):
            _, info = env.reset()
            seen.add(info["tradition"])
        assert len(seen) == n

    def test_tradition_cycle_is_deterministic(self):
        names_a = [UniverseAgentEnv(seed=1).reset()[1]["tradition"]]
        env = UniverseAgentEnv(seed=1)
        names_b = [env.reset()[1]["tradition"]]
        assert names_a == names_b


class TestFailOpenIntegrations:
    def test_journey_tracker_recorded_and_failures_swallowed(self):
        class Recorder:
            def __init__(self):
                self.calls = []

            def record_env_state(self, env_type, step, obs, reward):
                self.calls.append((env_type, step, float(reward)))

        rec = Recorder()
        env = UniverseAgentEnv(max_steps=10, seed=42, journey_tracker=rec)
        env.reset()
        env.step("hold")
        assert rec.calls and rec.calls[0][0] == "universe_agent"

        class Exploder:
            def record_env_state(self, *a, **k):
                raise RuntimeError("boom")

        env2 = UniverseAgentEnv(max_steps=10, seed=42, journey_tracker=Exploder())
        env2.reset()
        obs, _, _, _, _ = env2.step("hold")  # must not raise
        assert isinstance(obs, str)

    def test_broken_jepa_gate_is_fail_open(self):
        class BrokenGate:
            def check(self, state_text):
                raise RuntimeError("gate down")

        env = UniverseAgentEnv(max_steps=10, seed=42, jepa_gate=BrokenGate())
        env.reset()
        obs, _, _, _, _ = env.step("push toward equilibrium")
        assert isinstance(obs, str)
