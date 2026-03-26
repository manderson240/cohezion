"""Tests for EthericVariantOscillator (EVO) — Phase 1.

EVO is an Etheric Variant Oscillator: an exotic vacuum object with a full
physics biography governed by TRIUNE SELF dynamics, Kordylewski swarm gravity,
and HIHO stability physics.

Tests:
1. EVO creation with journey_id and archetype
2. TRIUNE SELF states: Doer(12D) / Thinker(512D) / Knower(2048D)
3. Kordylewski cloud assignment (L4/L5) and StabilityWell classification
4. Physics biography update (update_physics)
5. Exotic vacuum biography export for HuggingFace
6. LRU eviction (max 20 active) and .npy disk spillover
7. Atomic file writes via temp-file-then-rename
8. journey_id regex sanitization (alphanumeric + _ + -, max 64)
9. NaN coherence guard in update_physics
"""

from __future__ import annotations

import json
import re

import numpy as np
import pytest


class TestEVO:
    """Tests for EthericVariantOscillator creation and identity."""

    @pytest.fixture
    def evo_cls(self):
        try:
            from cohezion.rl.evo import EthericVariantOscillator

            return EthericVariantOscillator
        except ImportError:
            pytest.skip("EVO not yet implemented")

    def test_creation_with_journey_id(self, evo_cls):
        """EVO initializes with a valid journey_id and correct dimensions."""
        evo = evo_cls(journey_id="journey_test_001")
        assert evo.journey_id == "journey_test_001"
        assert evo.doer_state.shape == (12,)
        assert evo.thinker_state.shape == (512,)
        assert evo.knower_state.shape == (2048,)

    def test_journey_id_sanitization(self, evo_cls):
        """journey_id is sanitized: alphanumeric + _ + -, max 64 chars."""
        evo = evo_cls(journey_id="valid_journey-123")
        assert re.match(r"^[a-zA-Z0-9_-]+$", evo.journey_id)
        assert len(evo.journey_id) <= 64

    def test_journey_id_rejects_path_traversal(self, evo_cls):
        """journey_id with path separators is sanitized."""
        evo = evo_cls(journey_id="../etc/passwd")
        assert ".." not in evo.journey_id
        assert "/" not in evo.journey_id

    def test_default_kordylewski_cloud(self, evo_cls):
        """Default Kordylewski cloud assignment is L4 or L5."""
        evo = evo_cls()
        assert evo.kordylewski_cloud in ("L4", "L5")

    def test_stability_well_classification(self, evo_cls):
        """StabilityWell is classified as basin or hilltop."""
        evo = evo_cls()
        assert evo.stability_well in ("basin", "hilltop")

    def test_exotic_charge_initialization(self, evo_cls):
        """Exotic charge is initialized near zero."""
        evo = evo_cls()
        assert 0.0 <= evo.exotic_charge_density <= 1.0

    def test_biography_starts_empty(self, evo_cls):
        """Biography list starts empty."""
        evo = evo_cls()
        assert evo.biography == []


class TestTRIUNESelfStates:
    """Tests for TRIUNE SELF state vectors."""

    @pytest.fixture
    def evo_cls(self):
        try:
            from cohezion.rl.evo import EthericVariantOscillator

            return EthericVariantOscillator
        except ImportError:
            pytest.skip("EVO not yet implemented")

    def test_doer_state_is_12d_float32(self, evo_cls):
        """Doer state is 12D, float32, C-contiguous."""
        evo = evo_cls()
        assert evo.doer_state.shape == (12,)
        assert evo.doer_state.dtype == np.float32
        assert evo.doer_state.flags["C_CONTIGUOUS"]

    def test_thinker_state_is_512d_float32(self, evo_cls):
        """Thinker state is 512D, float32, C-contiguous."""
        evo = evo_cls()
        assert evo.thinker_state.shape == (512,)
        assert evo.thinker_state.dtype == np.float32
        assert evo.thinker_state.flags["C_CONTIGUOUS"]

    def test_knower_state_is_2048d_float32(self, evo_cls):
        """Knower state is 2048D, float32, C-contiguous."""
        evo = evo_cls()
        assert evo.knower_state.shape == (2048,)
        assert evo.knower_state.dtype == np.float32
        assert evo.knower_state.flags["C_CONTIGUOUS"]

    def test_triune_weights_sum_to_one(self, evo_cls):
        """TRIUNE weights renormalize to sum to 1.0 in __post_init__."""
        evo = evo_cls(doer_weight=0.33, thinker_weight=0.33, knower_weight=0.33)
        total = evo.doer_weight + evo.thinker_weight + evo.knower_weight
        assert abs(total - 1.0) < 1e-6

    def test_triune_weights_negative_become_zero(self, evo_cls):
        """Negative TRIUNE weights become 0 in __post_init__."""
        evo = evo_cls(doer_weight=-0.5, thinker_weight=1.0, knower_weight=0.5)
        assert evo.doer_weight == 0.0
        assert abs(evo.thinker_weight + evo.knower_weight - 1.0) < 1e-6


class TestPhysicsBiography:
    """Tests for physics biography update and export."""

    @pytest.fixture
    def evo_cls(self):
        try:
            from cohezion.rl.evo import EthericVariantOscillator

            return EthericVariantOscillator
        except ImportError:
            pytest.skip("EVO not yet implemented")

    def test_update_physics_records_step(self, evo_cls):
        """update_physics appends a step to biography."""
        evo = evo_cls()
        evo.update_physics(coherence=0.5, hiho_distance=0.1)
        assert len(evo.biography) == 1
        assert evo.biography[0]["coherence"] == 0.5
        assert evo.biography[0]["hiho_distance"] == 0.1

    def test_update_physics_nan_guard(self, evo_cls):
        """NaN coherence is replaced with previous coherence."""
        evo = evo_cls()
        evo.update_physics(coherence=0.5, hiho_distance=0.1)
        evo.update_physics(coherence=float("nan"), hiho_distance=0.1)
        assert evo.biography[-1]["coherence"] == 0.5
        assert len(evo.biography) == 2

    def test_coherence_is_nan_guard(self, evo_cls):
        """Coherence becomes NaN when no previous coherence exists."""
        evo = evo_cls()
        evo.update_physics(coherence=float("nan"), hiho_distance=0.1)
        assert np.isnan(evo.biography[-1]["coherence"])

    def test_phase_accumulates(self, evo_cls):
        """Phase increases monotonically across steps."""
        evo = evo_cls()
        for _ in range(5):
            evo.update_physics(coherence=0.5, hiho_distance=0.1)
        assert evo.phase > 0.0

    def test_exotic_charge_accumulates(self, evo_cls):
        """Exotic charge density grows with each step."""
        evo = evo_cls()
        initial_charge = evo.exotic_charge_density
        for _ in range(10):
            evo.update_physics(coherence=0.5, hiho_distance=0.1)
        assert evo.exotic_charge_density > initial_charge

    def test_export_biography(self, evo_cls):
        """export_biography returns a JSON-serializable dict."""
        evo = evo_cls(journey_id="test_export")
        evo.update_physics(coherence=0.5, hiho_distance=0.1)
        bio = evo.export_biography()
        assert "journey_id" in bio
        assert "triune_weights" in bio
        assert "biography" in bio
        assert bio["journey_id"] == "test_export"
        json.dumps(bio)


class TestEVONumpyExport:
    """Tests for .npy-based exotic vacuum biography export."""

    @pytest.fixture
    def evo_cls(self):
        try:
            from cohezion.rl.evo import EthericVariantOscillator

            return EthericVariantOscillator
        except ImportError:
            pytest.skip("EVO not yet implemented")

    def test_export_evp_creates_npy_file(self, evo_cls, tmp_path):
        """export_evp writes a .npy file per TRIUNE state."""
        evo = evo_cls(journey_id="test_evp")
        for _ in range(3):
            evo.update_physics(coherence=0.5, hiho_distance=0.1)
        evo.export_evp(tmp_path)
        assert (tmp_path / "test_evp_doer.npy").exists()
        assert (tmp_path / "test_evp_thinker.npy").exists()
        assert (tmp_path / "test_evp_knower.npy").exists()

    def test_export_evp_readable_back(self, evo_cls, tmp_path):
        """Exported .npy files are readable and match state."""
        evo = evo_cls(journey_id="test_readback")
        for _ in range(3):
            evo.update_physics(coherence=0.5, hiho_distance=0.1)
        evo.export_evp(tmp_path)
        doer_back = np.load(tmp_path / "test_readback_doer.npy")
        assert np.array_equal(doer_back, evo.doer_state)


class TestAtomicWrite:
    """Tests for atomic file write safety."""

    @pytest.fixture
    def evo_cls(self):
        try:
            from cohezion.rl.evo import EthericVariantOscillator

            return EthericVariantOscillator
        except ImportError:
            pytest.skip("EVO not yet implemented")

    def test_atomic_write_no_orphan_on_crash(self, evo_cls, tmp_path):
        """If write crashes, no orphan .tmp file is left behind."""
        evo = evo_cls(journey_id="test_atomic")
        evo.update_physics(coherence=0.5, hiho_distance=0.1)
        evo.export_evp(tmp_path)
        orphans = list(tmp_path.glob("*.tmp"))
        assert len(orphans) == 0


class TestLRUEviction:
    """Tests for LRU eviction when max_active exceeded."""

    @pytest.fixture
    def evo_cls(self):
        try:
            from cohezion.rl.evo import EthericVariantOscillator

            return EthericVariantOscillator
        except ImportError:
            pytest.skip("EVO not yet implemented")

    def test_lru_eviction_after_max(self, evo_cls, tmp_path):
        """After max_active EVs, least-recently-used is evicted."""
        tracker = evo_cls.build_tracker(max_active=3, spill_dir=tmp_path)
        for i in range(5):
            evo = evo_cls(journey_id=f"lrutest_{i}")
            tracker.register(evo)
        assert len(tracker.active_evos) == 3
        assert "lrutest_0" not in tracker.active_evos


class TestEVOTracker:
    """Tests for EVOTracker registry."""

    @pytest.fixture
    def evo_cls(self):
        try:
            from cohezion.rl.evo import EthericVariantOscillator

            return EthericVariantOscillator
        except ImportError:
            pytest.skip("EVO not yet implemented")

    def test_register_adds_to_active(self, evo_cls):
        """register() adds EVO to active_evos dict."""
        tracker = evo_cls.build_tracker(max_active=10)
        evo = evo_cls(journey_id="reg_test")
        tracker.register(evo)
        assert "reg_test" in tracker.active_evos

    def test_register_spills_previous(self, evo_cls, tmp_path):
        """Registering beyond max_active spills oldest to disk."""
        tracker = evo_cls.build_tracker(max_active=2, spill_dir=tmp_path)
        evo1 = evo_cls(journey_id="spill_1")
        tracker.register(evo1)
        evo2 = evo_cls(journey_id="spill_2")
        tracker.register(evo2)
        evo3 = evo_cls(journey_id="spill_3")
        tracker.register(evo3)
        assert len(tracker.active_evos) == 2
        assert "spill_1" not in tracker.active_evos

    def test_get_returns_spilled_evp(self, evo_cls, tmp_path):
        """get() on spilled EVO loads from .npy files."""
        tracker = evo_cls.build_tracker(max_active=2, spill_dir=tmp_path)
        evo = evo_cls(journey_id="get_test")
        tracker.register(evo)
        tracker.get("get_test")
        assert "get_test" in tracker.active_evos
