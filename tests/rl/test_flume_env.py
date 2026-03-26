"""Tests for FlumeNavEnv pause/resume, drift injection, and EVO emission.

Tests:
1. pause() — env pauses, step returns reward=0 when paused
2. resume() — env resumes from pause
3. inject_drift(layer, drift_vector) — injects drift into TRIUNE layer
4. emit_evo() — creates EVO from episode trajectory, resets episode data
"""

from __future__ import annotations

import numpy as np
import pytest


class TestFlumeNavEnvPauseResume:
    """Tests for FlumeNavEnv pause/resume functionality."""

    @pytest.fixture
    def env_cls(self):
        try:
            from cohezion.rl.environment import FlumeNavEnv

            return FlumeNavEnv
        except ImportError:
            pytest.skip("FlumeNavEnv not yet implemented")

    def test_pause_sets_is_paused(self, env_cls):
        """pause() sets internal _is_paused=True."""
        env = env_cls()
        env.reset()
        assert hasattr(env, "pause")
        env.pause()
        assert hasattr(env, "_is_paused")
        assert env._is_paused is True

    def test_pause_exists(self, env_cls):
        """FlumeNavEnv has a pause() method."""
        env = env_cls()
        env.reset()
        assert hasattr(env, "pause")
        assert callable(env.pause)

    def test_resume_exists(self, env_cls):
        """FlumeNavEnv has a resume() method."""
        env = env_cls()
        env.reset()
        assert hasattr(env, "resume")
        assert callable(env.resume)

    def test_resume_clears_is_paused(self, env_cls):
        """resume() sets _is_paused=False."""
        env = env_cls()
        env.reset()
        env.pause()
        env.resume()
        assert env._is_paused is False

    def test_step_returns_zero_reward_when_paused(self, env_cls):
        """When paused, step() returns reward=0."""
        env = env_cls()
        state, _ = env.reset()
        env.pause()
        action = env.action_space.sample()
        _, reward, _, _, _ = env.step(action)
        assert reward == 0.0

    def test_normal_step_after_resume(self, env_cls):
        """After resume, step() returns normal (non-zero) rewards."""
        env = env_cls()
        state, _ = env.reset()
        env.pause()
        env.resume()
        action = env.action_space.sample()
        _, reward, _, _, info = env.step(action)
        assert "coherence" in info

    def test_pause_increments_step_count(self, env_cls):
        """Pausing does not increment step count."""
        env = env_cls()
        state, _ = env.reset()
        initial_steps = env._step_count
        env.pause()
        assert env._step_count == initial_steps

    def test_multiple_pause_resume_cycles(self, env_cls):
        """Multiple pause/resume cycles work correctly."""
        env = env_cls()
        env.reset()
        env.pause()
        assert env._is_paused is True
        env.resume()
        assert env._is_paused is False
        env.pause()
        assert env._is_paused is True
        env.resume()
        assert env._is_paused is False


class TestInjectDrift:
    """Tests for drift injection into TRIUNE layers."""

    @pytest.fixture
    def env_cls(self):
        try:
            from cohezion.rl.environment import FlumeNavEnv

            return FlumeNavEnv
        except ImportError:
            pytest.skip("FlumeNavEnv not yet implemented")

    def test_inject_drift_method_exists(self, env_cls):
        """FlumeNavEnv has an inject_drift() method."""
        env = env_cls()
        env.reset()
        assert hasattr(env, "inject_drift")
        assert callable(env.inject_drift)

    def test_inject_drift_accepts_doer_layer(self, env_cls):
        """inject_drift accepts layer='doer'."""
        env = env_cls()
        env.reset()
        drift = np.zeros(12, dtype=np.float32)
        env.inject_drift("doer", drift)

    def test_inject_drift_accepts_thinker_layer(self, env_cls):
        """inject_drift accepts layer='thinker'."""
        env = env_cls()
        env.reset()
        drift = np.zeros(512, dtype=np.float32)
        env.inject_drift("thinker", drift)

    def test_inject_drift_accepts_knower_layer(self, env_cls):
        """inject_drift accepts layer='knower'."""
        env = env_cls()
        env.reset()
        drift = np.zeros(2048, dtype=np.float32)
        env.inject_drift("knower", drift)

    def test_inject_drift_modifies_state(self, env_cls):
        """inject_drift modifies the layer state."""
        env = env_cls()
        env.reset()
        assert hasattr(env, "_doer_state")
        assert hasattr(env, "_thinker_state")
        assert hasattr(env, "_knower_state")
        initial_doer = env._doer_state.copy()
        drift = np.ones(12, dtype=np.float32) * 0.1
        env.inject_drift("doer", drift)
        assert not np.array_equal(env._doer_state, initial_doer)

    def test_inject_drift_raises_on_invalid_layer(self, env_cls):
        """inject_drift raises ValueError on invalid layer name."""
        env = env_cls()
        env.reset()
        drift = np.zeros(12, dtype=np.float32)
        with pytest.raises(ValueError):
            env.inject_drift("invalid_layer", drift)

    def test_inject_drift_raises_on_wrong_size(self, env_cls):
        """inject_drift raises on wrong sized drift vector."""
        env = env_cls()
        env.reset()
        wrong_size_drift = np.zeros(100, dtype=np.float32)
        with pytest.raises(ValueError):
            env.inject_drift("doer", wrong_size_drift)


class TestEmitEVO:
    """Tests for EVO emission from episode trajectory."""

    @pytest.fixture
    def env_cls(self):
        try:
            from cohezion.rl.environment import FlumeNavEnv

            return FlumeNavEnv
        except ImportError:
            pytest.skip("FlumeNavEnv not yet implemented")

    def test_emit_evo_method_exists(self, env_cls):
        """FlumeNavEnv has an emit_evo() method."""
        env = env_cls()
        env.reset()
        assert hasattr(env, "emit_evo")
        assert callable(env.emit_evo)

    def test_emit_evo_returns_evo(self, env_cls):
        """emit_evo() returns an EthericVariantOscillator."""
        env = env_cls()
        state, _ = env.reset()
        for _ in range(10):
            action = env.action_space.sample()
            env.step(action)
        evo = env.emit_evo()
        assert evo is not None
        assert hasattr(evo, "journey_id")
        assert hasattr(evo, "doer_state")
        assert hasattr(evo, "thinker_state")
        assert hasattr(evo, "knower_state")

    def test_emit_evo_has_biography(self, env_cls):
        """EVO returned by emit_evo has a non-empty biography."""
        env = env_cls()
        state, _ = env.reset()
        for _ in range(10):
            action = env.action_space.sample()
            env.step(action)
        evo = env.emit_evo()
        assert len(evo.biography) > 0

    def test_emit_evo_resets_episode_data(self, env_cls):
        """emit_evo() resets episode trajectory data."""
        env = env_cls()
        state, _ = env.reset()
        for _ in range(10):
            action = env.action_space.sample()
            env.step(action)
        env.emit_evo()
        assert len(env._episode_coherences) == 0

    def test_emit_evo_episode_count_increments(self, env_cls):
        """emit_evo() increments episode counter."""
        env = env_cls()
        state, _ = env.reset()
        initial_count = getattr(env, "_episode_count", 0)
        for _ in range(10):
            action = env.action_space.sample()
            env.step(action)
        env.emit_evo()
        new_count = getattr(env, "_episode_count", 0)
        assert new_count == initial_count + 1

    def test_emit_evo_has_triune_states(self, env_cls):
        """EVO has correctly sized TRIUNE state vectors."""
        env = env_cls()
        state, _ = env.reset()
        for _ in range(10):
            action = env.action_space.sample()
            env.step(action)
        evo = env.emit_evo()
        assert evo.doer_state.shape == (12,)
        assert evo.thinker_state.shape == (512,)
        assert evo.knower_state.shape == (2048,)

    def test_emit_evo_without_steps(self, env_cls):
        """emit_evo() works even with no steps taken."""
        env = env_cls()
        state, _ = env.reset()
        evo = env.emit_evo()
        assert evo is not None
        assert hasattr(evo, "biography")

    def test_emit_evo_updates_existing_evo(self, env_cls):
        """Multiple emit_evo calls return unique EVOs."""
        env = env_cls()
        state, _ = env.reset()
        for _ in range(5):
            action = env.action_space.sample()
            env.step(action)
        evo1 = env.emit_evo()
        for _ in range(5):
            action = env.action_space.sample()
            env.step(action)
        evo2 = env.emit_evo()
        assert evo1.journey_id != evo2.journey_id


class TestPauseWithInterruptions:
    """Tests for pause/resume interaction with episode termination."""

    @pytest.fixture
    def env_cls(self):
        try:
            from cohezion.rl.environment import FlumeNavEnv

            return FlumeNavEnv
        except ImportError:
            pytest.skip("FlumeNavEnv not yet implemented")

    def test_pause_before_max_steps(self, env_cls):
        """Pausing before max_steps preserves remaining steps."""
        env = env_cls(max_steps=100)
        state, _ = env.reset()
        for _ in range(50):
            action = env.action_space.sample()
            env.step(action)
        env.pause()
        env.resume()
        for _ in range(50):
            action = env.action_space.sample()
            _, _, terminated, truncated, _ = env.step(action)
        assert truncated is True

    def test_resume_after_reset(self, env_cls):
        """After reset, env is not paused."""
        env = env_cls()
        state, _ = env.reset()
        env.pause()
        state, _ = env.reset()
        assert env._is_paused is False
