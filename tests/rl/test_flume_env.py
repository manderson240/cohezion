"""Tests for FlumeNavEnv Phase 3 integrations.

Tests cover:
- TaskSpec configuration at reset()
- Interruption injection via pause()/resume()
- Context injection via inject_drift()
- Open-ended mode (max_steps=None)
- EVO emission after episode
- TRIUNE-weighted coherence computation
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest


class TestTaskSpecIntegration:
    """Tests for TaskSpec configuring env at reset()."""

    @pytest.fixture
    def env_cls(self):
        from cohezion.rl.environment import FlumeNavEnv

        return FlumeNavEnv

    @pytest.fixture
    def task_spec_cls(self):
        from cohezion.rl.task_generator import TaskSpec

        return TaskSpec

    def test_reset_with_task_spec_sets_horizon(self, env_cls, task_spec_cls):
        """TaskSpec horizon overrides env max_steps."""
        env = env_cls(max_steps=200)
        task_spec = task_spec_cls(archetype="hiho_basin", horizon=100)
        env.reset(task_spec=task_spec)
        assert env.max_steps == 100

    def test_reset_with_task_spec_sets_interruption_points(self, env_cls, task_spec_cls):
        """TaskSpec interruption_points are stored."""
        env = env_cls()
        task_spec = task_spec_cls(
            archetype="interruption_recovery",
            horizon=200,
            interruption_points=[50, 100, 150],
        )
        env.reset(task_spec=task_spec)
        assert env.interruption_points == [50, 100, 150]

    def test_reset_with_task_spec_sets_noise_level(self, env_cls, task_spec_cls):
        """TaskSpec noise_level is stored."""
        env = env_cls()
        task_spec = task_spec_cls(archetype="hiho_basin", noise_level=0.15)
        env.reset(task_spec=task_spec)
        assert env._noise_level == 0.15

    def test_reset_with_task_spec_sets_triune_weights(self, env_cls, task_spec_cls):
        """TaskSpec TRIUNE dominance weights are stored."""
        env = env_cls()
        task_spec = task_spec_cls(
            archetype="triune_balance",
            doer_dominance=0.6,
            thinker_dominance=0.3,
            knower_dominance=0.1,
        )
        env.reset(task_spec=task_spec)
        assert env._triune_weights["doer"] == 0.6
        assert env._triune_weights["thinker"] == 0.3
        assert env._triune_weights["knower"] == 0.1

    def test_reset_without_task_spec_uses_defaults(self, env_cls):
        """Without TaskSpec, env uses default TRIUNE weights."""
        env = env_cls()
        env.reset()
        assert env._triune_weights["doer"] == pytest.approx(1.0 / 3.0)
        assert env._triune_weights["thinker"] == pytest.approx(1.0 / 3.0)
        assert env._triune_weights["knower"] == pytest.approx(1.0 / 3.0)
        assert env._noise_level == 0.05

    def test_current_task_spec_property(self, env_cls, task_spec_cls):
        """current_task_spec property returns the configured TaskSpec."""
        env = env_cls()
        task_spec = task_spec_cls(archetype="hiho_basin", horizon=150)
        env.reset(task_spec=task_spec)
        assert env.current_task_spec is task_spec


class TestInterruptionHandling:
    """Tests for pause()/resume() interruption injection."""

    @pytest.fixture
    def env_cls(self):
        from cohezion.rl.environment import FlumeNavEnv

        return FlumeNavEnv

    def test_pause_sets_is_paused_true(self, env_cls):
        """pause() sets is_paused to True."""
        env = env_cls()
        env.reset()
        assert not env.is_paused
        env.pause()
        assert env.is_paused

    def test_resume_sets_is_paused_false(self, env_cls):
        """resume() sets is_paused to False."""
        env = env_cls()
        env.reset()
        env.pause()
        assert env.is_paused
        env.resume()
        assert not env.is_paused

    def test_step_returns_zero_reward_when_paused(self, env_cls):
        """step() returns 0 reward when paused."""
        env = env_cls()
        env.reset()
        env.pause()
        action = np.zeros(env.action_space.shape)
        _, reward, terminated, truncated, info = env.step(action)
        assert reward == 0.0
        assert info["paused"] is True
        assert terminated is False
        assert truncated is False

    def test_state_unchanged_when_paused(self, env_cls):
        """step() does not apply physics when paused."""
        env = env_cls()
        env.reset()
        state_before = env._state.copy() if env._state is not None else None
        env.pause()
        action = np.ones(env.action_space.shape) * 0.5
        env.step(action)
        state_after = env._state.copy() if env._state is not None else None
        if state_before is not None:
            np.testing.assert_array_equal(state_before, state_after)


class TestContextInjection:
    """Tests for inject_drift() context injection."""

    @pytest.fixture
    def env_cls(self):
        from cohezion.rl.environment import FlumeNavEnv

        return FlumeNavEnv

    def test_inject_drift_into_doer_layer(self, env_cls):
        """inject_drift() modifies doer layer (first 12 dims)."""
        env = env_cls()
        env.reset()
        original_doer = env._state[:12].copy()
        drift = np.ones(12, dtype=np.float32) * 0.1
        env.inject_drift(drift, "doer")
        assert not np.allclose(env._state[:12], original_doer)
        assert env._drift_injected["doer"] is True

    def test_inject_drift_into_thinker_layer(self, env_cls):
        """inject_drift() modifies thinker layer (dims 12-524)."""
        env = env_cls(z_dim=600)
        env.reset()
        original_thinker = env._state[12:524].copy()
        drift = np.ones(512, dtype=np.float32) * 0.1
        env.inject_drift(drift, "thinker")
        assert not np.allclose(env._state[12:524], original_thinker)
        assert env._drift_injected["thinker"] is True

    def test_inject_drift_invalid_layer_raises(self, env_cls):
        """inject_drift() raises ValueError for invalid layer."""
        env = env_cls()
        env.reset()
        with pytest.raises(ValueError, match="Invalid layer"):
            env.inject_drift(np.ones(12), "invalid_layer")

    def test_inject_drift_scales_by_noise_level(self, env_cls):
        """inject_drift() scales drift by noise_level."""
        env = env_cls()
        env.reset(
            task_spec=type(
                "TaskSpec",
                (),
                {
                    "noise_level": 0.1,
                    "horizon": 200,
                    "interruption_points": [],
                    "doer_dominance": 0.33,
                    "thinker_dominance": 0.33,
                    "knower_dominance": 0.33,
                    "stability_well": "HIHO_Origin",
                    "kordylewski_cloud_id": "none",
                },
            )()
        )
        env._noise_level = 0.1
        original_state = env._state[:12].copy()
        drift = np.ones(12, dtype=np.float32)
        env.inject_drift(drift, "doer")
        change = env._state[:12] - original_state
        np.testing.assert_allclose(change, drift * 0.1, atol=1e-5)

    def test_inject_drift_clamps_state(self, env_cls):
        """inject_drift() clamps state to [-2, 2] bounds."""
        env = env_cls()
        env.reset()
        large_drift = np.ones(12, dtype=np.float32) * 10.0
        env.inject_drift(large_drift, "doer")
        assert np.all(env._state[:12] <= 2.0)
        assert np.all(env._state[:12] >= -2.0)


class TestOpenEndedMode:
    """Tests for open-ended mode (max_steps=None)."""

    @pytest.fixture
    def env_cls(self):
        from cohezion.rl.environment import FlumeNavEnv

        return FlumeNavEnv

    def test_open_ended_mode_no_truncation(self, env_cls):
        """Open-ended mode (max_steps=None) does not truncate."""
        env = env_cls(max_steps=None)
        env.reset()
        action = np.zeros(env.action_space.shape)
        for _ in range(300):
            _, _, terminated, truncated, _ = env.step(action)
            if terminated or truncated:
                break
        assert not truncated
        assert env.max_steps is None

    def test_open_ended_terminates_on_exotic_charge_density(self, env_cls):
        """Open-ended mode terminates when exotic_charge_density > 0.95."""
        env = env_cls(max_steps=None, use_hamiltonian=False, temperature=0.5)
        env.reset()
        env._state = env.np_random.uniform(-1.8, 1.8, env.z_dim).astype(np.float32)
        action = np.ones(env.action_space.shape) * 0.8
        terminated = False
        steps = 0
        while not terminated and steps < 200:
            _, _, terminated, _, info = env.step(action)
            steps += 1
            if terminated:
                assert info["exotic_charge_density"] > 0.95
        assert terminated

    def test_open_ended_returns_exotic_charge_in_info(self, env_cls):
        """step() returns exotic_charge_density in info dict."""
        env = env_cls(max_steps=None)
        env.reset()
        action = np.zeros(env.action_space.shape)
        _, _, _, _, info = env.step(action)
        assert "exotic_charge_density" in info


class TestEVOMission:
    """Tests for EVO emission after episode."""

    @pytest.fixture
    def env_cls(self):
        from cohezion.rl.environment import FlumeNavEnv

        return FlumeNavEnv

    @pytest.fixture
    def tracker_cls(self):
        from cohezion.rl.evo import EVOTracker

        return EVOTracker

    @pytest.fixture
    def evo_cls(self):
        from cohezion.rl.evo import EthericVariantOscillator

        return EthericVariantOscillator

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_env_with_evo_tracker_creates_evo_on_reset(self, env_cls, tracker_cls, temp_dir):
        """Environment with EVOTracker creates EVO on reset()."""
        tracker = tracker_cls(storage_dir=temp_dir)
        env = env_cls(evo_tracker=tracker)
        env.reset()
        assert env.current_evo is not None

    def test_emit_evo_returns_current_evo(self, env_cls, tracker_cls, evo_cls, temp_dir):
        """emit_evo() returns the current EVO with trajectory."""
        tracker = tracker_cls(storage_dir=temp_dir)
        env = env_cls(evo_tracker=tracker)
        env.reset()
        for _ in range(10):
            action = np.zeros(env.action_space.shape)
            env.step(action)
        evo = env.emit_evo()
        assert evo is not None
        assert len(evo.trajectory) == 10
        assert env.current_evo is None

    def test_emit_evo_returns_none_when_no_evo(self, env_cls):
        """emit_evo() returns None when no EVO exists."""
        env = env_cls()
        env.reset()
        evo = env.emit_evo()
        assert evo is None

    def test_evo_has_task_stability_well(self, env_cls, tracker_cls, evo_cls, temp_dir):
        """EVO inherits stability_well from TaskSpec."""
        tracker = tracker_cls(storage_dir=temp_dir)
        env = env_cls(evo_tracker=tracker)
        from cohezion.rl.task_generator import TaskSpec

        task_spec = TaskSpec(archetype="kordylewski_orbit", stability_well="L4")
        env.reset(task_spec=task_spec)
        evo = env.current_evo
        assert evo is not None
        assert evo.stability_well == "L4"

    def test_evo_has_kordylewski_cloud_id(self, env_cls, tracker_cls, evo_cls, temp_dir):
        """EVO has kordylewski_cloud_id from TaskSpec."""
        tracker = tracker_cls(storage_dir=temp_dir)
        env = env_cls(evo_tracker=tracker)
        from cohezion.rl.task_generator import TaskSpec

        task_spec = TaskSpec(archetype="kordylewski_orbit", kordylewski_cloud_id="L5")
        env.reset(task_spec=task_spec)
        evo = env.current_evo
        assert evo is not None
        assert evo.kordylewski_cloud_id == "L5"

    def test_emit_evo_unregisters_from_tracker(self, env_cls, tracker_cls, evo_cls, temp_dir):
        """emit_evo() unregisters EVO from tracker."""
        tracker = tracker_cls(storage_dir=temp_dir)
        env = env_cls(evo_tracker=tracker)
        env.reset()
        evo = env.current_evo
        journey_id = evo.journey_id
        tracker.register(evo)
        env.emit_evo()
        assert journey_id not in tracker.active_evos


class TestTRIUNEWeightedCoherence:
    """Tests for TRIUNE-weighted coherence computation."""

    @pytest.fixture
    def env_cls(self):
        from cohezion.rl.environment import FlumeNavEnv

        return FlumeNavEnv

    def test_coherence_uses_triune_weights(self, env_cls):
        """_compute_coherence() uses TRIUNE weights for doer/thinker/knower."""
        env = env_cls(z_dim=2560)
        env.reset()
        env._triune_weights = {"doer": 1.0, "thinker": 0.0, "knower": 0.0}
        env._state[:] = 0.5
        env._state[12:524] = 0.0
        env._state[524:] = 0.0
        coherence = env._compute_coherence(env._state)
        assert coherence > 0.5

    def test_doer_dominance_affects_coherence(self, env_cls):
        """High doer_dominance means doer chunk variance affects coherence more."""
        env = env_cls(z_dim=2560)
        env.reset()
        env._triune_weights = {"doer": 1.0, "thinker": 0.0, "knower": 0.0}
        env._state[:12] = 0.6
        env._state[12:524] = 0.3
        env._state[524:] = 0.3
        coherence_doer_dominant = env._compute_coherence(env._state)
        env._triune_weights = {"doer": 0.0, "thinker": 1.0, "knower": 0.0}
        env._state[:12] = 0.6
        env._state[12:524] = 0.3
        env._state[524:] = 0.3
        coherence_thinker_dominant = env._compute_coherence(env._state)
        assert coherence_doer_dominant != coherence_thinker_dominant


class TestExoticChargeDensity:
    """Tests for exotic charge density computation."""

    @pytest.fixture
    def env_cls(self):
        from cohezion.rl.environment import FlumeNavEnv

        return FlumeNavEnv

    def test_exotic_charge_density_from_variance(self, env_cls):
        """_compute_exotic_charge_density() returns variance-based density."""
        env = env_cls()
        env.reset()
        env._state[:] = 0.5
        density1 = env._compute_exotic_charge_density(env._state)
        env._state[:] = np.random.randn(256).astype(np.float32) * 2.0
        density2 = env._compute_exotic_charge_density(env._state)
        assert density1 < density2

    def test_exotic_charge_density_clamped_to_one(self, env_cls):
        """_compute_exotic_charge_density() returns value in [0, 1]."""
        env = env_cls()
        env.reset()
        env._state[:] = np.random.randn(256).astype(np.float32) * 10.0
        density = env._compute_exotic_charge_density(env._state)
        assert 0.0 <= density <= 1.0
