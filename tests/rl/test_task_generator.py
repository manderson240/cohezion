"""Tests for TaskGenerator — generates TaskSpec from PRIME skill archetypes.

The TaskGenerator converts PRIME skill definitions into RL-compatible TaskSpecs,
each with TRIUNE dominance weights, exotic vacuum conditions, interruption points,
and test oracle validation functions.

Test archetypes:
1. HIHO Basin Navigation
2. TRIUNE Balance
3. Interruption Recovery
4. Exotic Charge Tolerance
5. Kordylewski Orbit

Each archetype x 4 difficulty levels = 20 TaskSpecs total.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


class TestTaskSpec:
    """Tests for TaskSpec dataclass."""

    @pytest.fixture
    def spec_cls(self):
        try:
            from cohezion.rl.task_generator import TaskSpec

            return TaskSpec
        except ImportError:
            pytest.skip("TaskGenerator not yet implemented")

    def test_taskspec_has_required_fields(self, spec_cls):
        """TaskSpec has all required fields for RL task definition."""
        spec = spec_cls(archetype="test", horizon=100)
        assert spec.archetype == "test"
        assert spec.horizon == 100

    def test_taskspec_defaults(self, spec_cls):
        """TaskSpec has sensible defaults for all optional fields."""
        spec = spec_cls(archetype="test")
        assert spec.interruption_points == []
        assert spec.context_injection is False
        assert spec.noise_level == 0.05
        assert spec.doer_dominance == pytest.approx(1.0 / 3.0, abs=0.01)
        assert spec.thinker_dominance == pytest.approx(1.0 / 3.0, abs=0.01)
        assert spec.knower_dominance == pytest.approx(1.0 / 3.0, abs=0.01)
        assert spec.exotic_charge_amplitude == 0.0
        assert spec.kordylewski_gravity == 0.0

    def test_taskspec_triune_weights_sum_to_one(self, spec_cls):
        """TRIUNE dominance weights sum to 1.0."""
        spec = spec_cls(archetype="test")
        total = spec.doer_dominance + spec.thinker_dominance + spec.knower_dominance
        assert abs(total - 1.0) < 1e-6

    def test_taskspec_validate_returns_tuple(self, spec_cls):
        """validate() returns (bool, float) for oracle."""
        spec = spec_cls(archetype="test")

        class MockEVO:
            coherence_amplitude = 0.8
            # mutable default avoided
            journey_id = "test-001"

        evo = MockEVO()
        valid, score = spec.validate(evo)
        assert isinstance(valid, bool)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_taskspec_archetype_in_list(self, spec_cls):
        """TaskSpec archetype must be in known archetypes."""
        valid_archetypes = [
            "hiho_basin",
            "triune_balance",
            "interruption_recovery",
            "exotic_charge_tolerance",
            "kordylewski_orbit",
        ]
        for arch in valid_archetypes:
            spec = spec_cls(archetype=arch)
            assert spec.archetype == arch


class TestTaskGenerator:
    """Tests for TaskGenerator class."""

    @pytest.fixture
    def gen_cls(self):
        try:
            from cohezion.rl.task_generator import TaskGenerator

            return TaskGenerator
        except ImportError:
            pytest.skip("TaskGenerator not yet implemented")

    @pytest.fixture
    def spec_cls(self):
        try:
            from cohezion.rl.task_generator import TaskSpec

            return TaskSpec
        except ImportError:
            pytest.skip("TaskGenerator not yet implemented")

    def test_generator_creates_hiho_basin_spec(self, gen_cls, spec_cls):
        """Generator can create a HIHO Basin Navigation task."""
        gen = gen_cls()
        spec = gen.generate("hiho_basin", difficulty=1)
        assert spec.archetype == "hiho_basin"
        assert spec.horizon > 0
        assert spec.stability_well == "HIHO_Origin"

    def test_generator_creates_triune_balance_spec(self, gen_cls, spec_cls):
        """Generator can create a TRIUNE Balance task."""
        gen = gen_cls()
        spec = gen.generate("triune_balance", difficulty=2)
        assert spec.archetype == "triune_balance"
        assert spec.doer_dominance > 0.2
        assert spec.thinker_dominance > 0.2
        assert spec.knower_dominance > 0.2

    def test_generator_creates_interruption_recovery_spec(self, gen_cls, spec_cls):
        """Generator creates interruption recovery tasks with interruption_points."""
        gen = gen_cls()
        spec = gen.generate("interruption_recovery", difficulty=2)
        assert spec.archetype == "interruption_recovery"
        assert len(spec.interruption_points) > 0
        assert spec.interruption_points[0] > 0

    def test_generator_creates_exotic_charge_tolerance_spec(self, gen_cls, spec_cls):
        """Generator creates exotic charge tolerance tasks with high exotic_charge_amplitude."""
        gen = gen_cls()
        spec = gen.generate("exotic_charge_tolerance", difficulty=3)
        assert spec.archetype == "exotic_charge_tolerance"
        assert spec.exotic_charge_amplitude > 0.0

    def test_generator_creates_kordylewski_orbit_spec(self, gen_cls, spec_cls):
        """Generator creates Kordylewski orbit tasks with swarm gravity."""
        gen = gen_cls()
        spec = gen.generate("kordylewski_orbit", difficulty=2)
        assert spec.archetype == "kordylewski_orbit"
        assert spec.kordylewski_gravity > 0.0

    def test_generator_difficulty_affects_horizon(self, gen_cls, spec_cls):
        """Higher difficulty = longer horizon."""
        gen = gen_cls()
        easy = gen.generate("hiho_basin", difficulty=1)
        hard = gen.generate("hiho_basin", difficulty=4)
        assert hard.horizon > easy.horizon

    def test_generator_difficulty_affects_noise(self, gen_cls, spec_cls):
        """Higher difficulty = more action noise."""
        gen = gen_cls()
        easy = gen.generate("hiho_basin", difficulty=1)
        hard = gen.generate("hiho_basin", difficulty=4)
        assert hard.noise_level >= easy.noise_level

    def test_generator_produces_20_task_specs(self, gen_cls, spec_cls):
        """Generator produces 5 archetypes x 4 difficulty levels = 20 specs."""
        gen = gen_cls()
        specs = gen.generate_all()
        assert len(specs) == 20

    def test_generator_all_archetypes_covered(self, gen_cls, spec_cls):
        """All 5 archetypes are represented in generate_all()."""
        gen = gen_cls()
        specs = gen.generate_all()
        archetypes = {s.archetype for s in specs}
        expected = {
            "hiho_basin",
            "triune_balance",
            "interruption_recovery",
            "exotic_charge_tolerance",
            "kordylewski_orbit",
        }
        assert archetypes == expected

    def test_generator_validate_oracle(self, gen_cls, spec_cls):
        """Oracle validation correctly identifies success/failure."""
        gen = gen_cls()

        class MockEVO:
            def __init__(self, coherence_amplitude):
                self.coherence_amplitude = coherence_amplitude
                self.coherence_history = [coherence_amplitude] * 10

        spec = gen.generate("hiho_basin", difficulty=1)
        good_evo = MockEVO(coherence_amplitude=0.85)
        valid, score = spec.validate(good_evo)
        assert valid is True
        assert score > 0.7

        bad_evo = MockEVO(coherence_amplitude=0.2)
        valid, score = spec.validate(bad_evo)
        assert valid is False
        assert score < 0.5

    def test_generator_saves_and_loads_registry(self, gen_cls, spec_cls):
        """Generator can save/load task spec registry."""
        gen = gen_cls()
        specs = gen.generate_all()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "registry.json"
            gen.save_registry(specs, path)
            loaded = gen_cls.load_registry(path)
            assert len(loaded) == len(specs)
            for s, loaded_i in zip(specs, loaded, strict=True):
                assert s.archetype == loaded_i.archetype


class TestTaskArchetypes:
    """Tests for specific archetype behaviors."""

    @pytest.fixture
    def gen_cls(self):
        try:
            from cohezion.rl.task_generator import TaskGenerator

            return TaskGenerator
        except ImportError:
            pytest.skip("TaskGenerator not yet implemented")

    def test_hiho_basin_has_hiho_origin_well(self, gen_cls):
        """HIHO Basin tasks target HIHO_Origin stability well."""
        gen = gen_cls()
        for difficulty in range(1, 5):
            spec = gen.generate("hiho_basin", difficulty=difficulty)
            assert spec.stability_well == "HIHO_Origin"

    def test_triune_balance_equal_weights(self, gen_cls):
        """TRIUNE Balance tasks have roughly equal dominance weights."""
        gen = gen_cls()
        spec = gen.generate("triune_balance", difficulty=2)
        weights = sorted([spec.doer_dominance, spec.thinker_dominance, spec.knower_dominance])
        assert weights[-1] - weights[0] < 0.2

    def test_interruption_recovery_has_mid_horizon_interrupt(self, gen_cls):
        """Interruption recovery interrupts at 40-60% of horizon."""
        gen = gen_cls()
        spec = gen.generate("interruption_recovery", difficulty=2)
        mid_point = spec.horizon * 0.5
        assert any(abs(ip - mid_point) / spec.horizon < 0.2 for ip in spec.interruption_points)

    def test_exotic_charge_tolerance_difficulty_scales_charge(self, gen_cls):
        """Exotic charge tolerance: higher difficulty = higher charge amplitude."""
        gen = gen_cls()
        amps = [
            gen.generate("exotic_charge_tolerance", difficulty=d).exotic_charge_amplitude
            for d in range(1, 5)
        ]
        assert amps[3] >= amps[0]

    def test_kordylewski_orbit_has_l4_or_l5_cloud(self, gen_cls):
        """Kordylewski orbit tasks assign L4 or L5 cloud targets."""
        gen = gen_cls()
        spec = gen.generate("kordylewski_orbit", difficulty=2)
        assert spec.kordylewski_cloud_id in ["L4", "L5"]
