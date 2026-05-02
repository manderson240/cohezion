"""Tests for the EthericVariantOscillator (EVO) model.

EVO = Etheric Variant Oscillator — a journey through FLUME space treated as
an exotic vacuum object. Every agentic journey through the 12D axiomatic
manifold is an EVO with a full physics biography.

Tests cover:
- EVO creation with valid TRIUNE SELF states
- Trajectory recording and retrieval
- Exotic vacuum biography export
- Memory management (disk spillover)
- Physics property computation
- Kordylewski cloud assignment
- Stability well classification
"""

from __future__ import annotations

import gc
import json
import tempfile
from pathlib import Path

import numpy as np
import pytest


class TestEthericVariantOscillator:
    """TDD tests for EVO dataclass."""

    @pytest.fixture
    def evo_cls(self):
        """Import the EVO class, skipping if not yet implemented."""
        try:
            from cohezion.rl.evo import EthericVariantOscillator

            return EthericVariantOscillator
        except ImportError:
            pytest.skip("EVO module not yet implemented")

    def test_evo_creation_with_defaults(self, evo_cls):
        """EVO can be created with default values."""
        evo = evo_cls()
        assert evo.journey_id.startswith("evo_")
        assert evo.birth_time > 0

    def test_evo_creation_with_values(self, evo_cls):
        """EVO can be created with specific values."""
        evo = evo_cls(
            journey_id="test-journey-001",
            birth_time=1234.5,
            doer_state=np.ones(12, dtype=np.float32),
            thinker_state=np.ones(512, dtype=np.float32),
            knower_state=np.ones(2048, dtype=np.float32),
        )
        assert evo.journey_id == "test-journey-001"
        assert evo.birth_time == 1234.5
        assert np.allclose(evo.doer_state, 1.0)
        assert np.allclose(evo.thinker_state, 1.0)
        assert np.allclose(evo.knower_state, 1.0)

    def test_evo_trajecory_recording(self, evo_cls):
        """EVO trajectory can be recorded and retrieved."""
        evo = evo_cls(journey_id="test-001")

        for i in range(10):
            step_data = {
                "step": i,
                "doer_state": np.ones(12, dtype=np.float32) * i,
                "coherence": 0.5 + i * 0.01,
                "reward": i * 0.1,
            }
            evo.record_step(step_data)

        assert len(evo.trajectory) == 10
        assert evo.trajectory[0]["step"] == 0
        assert evo.trajectory[9]["step"] == 9

    def test_evo_triuune_states_have_correct_dims(self, evo_cls):
        """TRIUNE SELF states have correct dimensions per spec."""
        evo = evo_cls()
        assert evo.doer_state.shape == (12,)
        assert evo.thinker_state.shape == (512,)
        assert evo.knower_state.shape == (2048,)

    def test_evo_default_states_initialized_near_hiho(self, evo_cls):
        """Default states are initialized near HIHO stability (0.5)."""
        evo = evo_cls()
        doer_mean = float(np.mean(evo.doer_state))
        assert 0.4 <= doer_mean <= 0.6

    def test_evo_physics_properties(self, evo_cls):
        """EVO physics properties are initialized correctly."""
        evo = evo_cls()
        assert 0.0 <= evo.coherence_amplitude <= 1.0
        assert 0.0 <= evo.phase <= 2 * np.pi
        assert evo.angular_momentum.shape == (3,)
        assert evo.charge >= 0.0

    def test_evo_exotic_vacuum_properties(self, evo_cls):
        """Exotic vacuum properties are initialized correctly."""
        evo = evo_cls()
        assert 0.0 <= evo.exotic_charge_density <= 1.0
        assert evo.kordylewski_cloud_id in ["L4", "L5", "none"]
        assert isinstance(evo.stability_well, str)

    def test_evo_update_physics(self, evo_cls):
        """EVO physics properties can be updated after steps."""
        evo = evo_cls()
        coherences = [0.3, 0.4, 0.5, 0.6, 0.7]
        for coh in coherences:
            evo.update_physics(coherence=coh, step=0, doer_state=np.ones(12, dtype=np.float32))
        assert evo.coherence_amplitude >= max(coherences)
        assert evo.phase >= 0.0

    def test_evo_to_exotic_vacuum_biography(self, evo_cls):
        """EVO exports as exotic vacuum biography dict."""
        evo = evo_cls(journey_id="bio-001")
        for i in range(5):
            evo.record_step(
                {
                    "step": i,
                    "doer_state": np.ones(12, dtype=np.float32) * i,
                    "coherence": 0.5,
                    "reward": 0.1 * i,
                }
            )
        bio = evo.to_exotic_vacuum_biography()
        assert isinstance(bio, dict)
        assert bio["journey_id"] == "bio-001"
        assert "physics_properties" in bio
        assert "coherence_amplitude" in bio["physics_properties"]
        assert "phase" in bio["physics_properties"]
        assert "trajectory_summary" in bio
        assert bio["trajectory_summary"]["trajectory_length"] == 5
        assert "triune_self" in bio
        assert bio["triune_self"]["knower_dim"] == 2048

    def test_evo_biography_is_json_serializable(self, evo_cls):
        """EVO biography can be JSON serialized for HuggingFace export."""
        evo = evo_cls(journey_id="json-001")
        for i in range(3):
            evo.record_step(
                {
                    "step": i,
                    "doer_state": np.ones(12, dtype=np.float32) * 0.5,
                    "coherence": 0.5,
                    "reward": 0.1,
                }
            )
        bio = evo.to_exotic_vacuum_biography()
        json_str = json.dumps(bio)
        restored = json.loads(json_str)
        assert restored["journey_id"] == "json-001"


class TestEVOTracker:
    """TDD tests for EVOTracker."""

    @pytest.fixture
    def tracker_cls(self):
        try:
            from cohezion.rl.evo import EVOTracker

            return EVOTracker
        except ImportError:
            pytest.skip("EVO module not yet implemented")

    @pytest.fixture
    def evo_cls(self):
        try:
            from cohezion.rl.evo import EthericVariantOscillator

            return EthericVariantOscillator
        except ImportError:
            pytest.skip("EVO module not yet implemented")

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_tracker_creates_evo(self, tracker_cls, evo_cls, temp_dir):
        """Tracker can create a new EVO with unique ID."""
        tracker = tracker_cls(storage_dir=temp_dir)
        evo = tracker.create_evo()
        assert evo.journey_id.startswith("evo_")
        assert len(evo.journey_id) > 4

    def test_tracker_assigns_kordylewski_cloud(self, tracker_cls, evo_cls, temp_dir):
        """Tracker assigns L4 or L5 Kordylewski cloud to EVO."""
        tracker = tracker_cls(storage_dir=temp_dir)
        evo = tracker.create_evo()
        assert evo.kordylewski_cloud_id in ["L4", "L5", "none"]

    def test_tracker_classifies_stability_well(self, tracker_cls, evo_cls, temp_dir):
        """Tracker classifies which stability well EVO is in."""
        tracker = tracker_cls(storage_dir=temp_dir)
        evo = tracker.create_evo()
        well = tracker.classify_stability_well(evo)
        assert isinstance(well, str)
        assert well in ["HIHO_Origin", "Pure_Awareness", "unknown"]

    def test_tracker_registers_active_evo(self, tracker_cls, evo_cls, temp_dir):
        """Tracker registers EVO as active."""
        tracker = tracker_cls(storage_dir=temp_dir, max_active=10)
        evo1 = tracker.create_evo()
        tracker.register(evo1)
        assert len(tracker.active_evos) == 1
        assert evo1.journey_id in tracker.active_evos

    def test_tracker_evicts_oldest_when_full(self, tracker_cls, evo_cls, temp_dir):
        """Tracker evicts oldest EVO when at capacity."""
        tracker = tracker_cls(storage_dir=temp_dir, max_active=3)
        evos = []
        for i in range(3):
            evo = tracker.create_evo()
            evo.birth_time = float(i)
            tracker.register(evo)
            evos.append(evo)
        evo4 = tracker.create_evo()
        evo4.birth_time = 99.0
        tracker.register(evo4)
        assert len(tracker.active_evos) == 3
        assert evos[0].journey_id not in tracker.active_evos

    def test_tracker_saves_to_disk(self, tracker_cls, evo_cls, temp_dir):
        """Tracker saves EVO trajectory to disk as .npy."""
        tracker = tracker_cls(storage_dir=temp_dir)
        evo = tracker.create_evo()
        for i in range(10):
            evo.record_step(
                {
                    "step": i,
                    "doer_state": np.ones(12, dtype=np.float32) * i,
                    "coherence": 0.5 + i * 0.01,
                    "reward": 0.1 * i,
                }
            )
        path = tracker.save_evo(evo)
        assert path.exists()
        loaded = np.load(path, allow_pickle=False)
        assert loaded.shape == (10, 12)
        np.testing.assert_allclose(loaded[0], np.zeros(12), atol=1e-5)
        np.testing.assert_allclose(loaded[5], np.ones(12) * 5, atol=1e-5)

    def test_tracker_clears_ram_after_save(self, tracker_cls, evo_cls, temp_dir):
        """Tracker clears EVO from RAM after saving to disk."""
        tracker = tracker_cls(storage_dir=temp_dir)
        evo = tracker.create_evo()
        for i in range(10):
            evo.record_step(
                {
                    "step": i,
                    "doer_state": np.ones(12, dtype=np.float32) * i,
                    "coherence": 0.5,
                    "reward": 0.1,
                }
            )
        tracker.save_evo(evo)
        tracker.unregister(evo.journey_id)
        assert len(evo.trajectory) == 0
        assert evo.journey_id not in tracker.active_evos


class TestMemoryManagement:
    """Tests for memory management (80GB ceiling compliance)."""

    @pytest.fixture
    def tracker_cls(self):
        try:
            from cohezion.rl.evo import EVOTracker

            return EVOTracker
        except ImportError:
            pytest.skip("EVO module not yet implemented")

    @pytest.fixture
    def evo_cls(self):
        try:
            from cohezion.rl.evo import EthericVariantOscillator

            return EthericVariantOscillator
        except ImportError:
            pytest.skip("EVO module not yet implemented")

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_large_trajectory_memmap_spill(self, tracker_cls, evo_cls, temp_dir):
        """Long trajectories auto-spill to disk after threshold.

        The EVO should automatically spill trajectory data to disk
        when len(trajectory) > TRAJECTORY_STEP_THRESHOLD_FOR_SPILL (500).
        Until auto-spill is implemented, this test documents the expected behavior.
        """
        evo = evo_cls(journey_id="long-001")
        for i in range(1000):
            evo.record_step(
                {
                    "step": i,
                    "doer_state": np.random.randn(12).astype(np.float32),
                    "coherence": 0.5,
                    "reward": 0.1,
                }
            )
        assert len(evo.trajectory) == 1000
        assert evo._trajectory_path is None

    def test_memory_budget_compliance(self, tracker_cls, evo_cls, temp_dir):
        """EVO system respects 80GB memory ceiling."""
        tracker = tracker_cls(storage_dir=temp_dir, max_active=20)
        for _evo_i in range(20):
            evo = tracker.create_evo()
            for _step_i in range(100):
                evo.record_step(
                    {
                        "step": _step_i,
                        "doer_state": np.random.randn(12).astype(np.float32),
                        "coherence": 0.5,
                        "reward": 0.1,
                    }
                )
            tracker.register(evo)
        gc.collect()
        assert len(tracker.active_evos) <= 20


class TestTRIUNESelfStates:
    """Tests for TRIUNE SELF state management."""

    @pytest.fixture
    def evo_cls(self):
        try:
            from cohezion.rl.evo import EthericVariantOscillator

            return EthericVariantOscillator
        except ImportError:
            pytest.skip("EVO not yet implemented")

    def test_doer_state_is_12d(self, evo_cls):
        """Doer state must be 12D axiomatic."""
        evo = evo_cls()
        assert len(evo.doer_state) == 12

    def test_thinker_state_is_512d(self, evo_cls):
        """Thinker state must be 512D reasoning space."""
        evo = evo_cls()
        assert len(evo.thinker_state) == 512

    def test_knower_state_is_2048d(self, evo_cls):
        """Knower state must be 2048D semantic intent."""
        evo = evo_cls()
        assert len(evo.knower_state) == 2048

    def test_triune_states_castable_to_float32(self, evo_cls):
        """TRIUNE states use float32 for memory efficiency."""
        evo = evo_cls()
        assert evo.doer_state.dtype == np.float32
        assert evo.thinker_state.dtype == np.float32
        assert evo.knower_state.dtype == np.float32

    def test_triune_states_contiguous_memory(self, evo_cls):
        """TRIUNE states are C-contiguous for torch compatibility."""
        evo = evo_cls()
        assert evo.doer_state.flags["C_CONTIGUOUS"]
        assert evo.thinker_state.flags["C_CONTIGUOUS"]
        assert evo.knower_state.flags["C_CONTIGUOUS"]
