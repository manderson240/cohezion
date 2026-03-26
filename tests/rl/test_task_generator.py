"""Tests for TaskGenerator — Phase 2.

TaskGenerator produces TaskSpecs from 5 archetypes x 4 difficulty levels.
Each TaskSpec configures FlumeNavEnv with TRIUNE weights, interruption points,
exotic vacuum conditions, and a validate(evo) oracle.

Test archetypes:
1. HIHO Basin Navigation — navigate to HIHO stability
2. TRIUNE Balance — maintain equal Doer/Thinker/Knower activation
3. Interruption Recovery — resume after pause + drift injection
4. Exotic Charge Tolerance — survive exotic_charge_density > 0.9
5. Kordylewski Orbit — maintain stable orbit around L4/L5 point

Difficulty levels: 1 (easy) → 4 (extreme)
Each archetype × difficulty = 20 TaskSpecs total.
"""

from __future__ import annotations

import json
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
            pytest.skip("TaskSpec not yet implemented")

    def test_creation_all_fields(self, spec_cls):
        """TaskSpec accepts all required fields."""
        spec = spec_cls(
            name="test_task",
            archetype="HIHO_BASIN",
            difficulty=2,
            horizon=100,
            noise_level=0.05,
            doer_dominance=0.6,
            thinker_dominance=0.3,
            knower_dominance=0.1,
            interruption_points=[10, 50],
            validate_fn=None,
        )
        assert spec.name == "test_task"
        assert spec.archetype == "HIHO_BASIN"
        assert spec.difficulty == 2
        assert spec.horizon == 100
        assert spec.noise_level == 0.05

    def test_weights_sum_to_one(self, spec_cls):
        """TRIUNE weights normalize to 1.0."""
        spec = spec_cls(
            name="normalize_test",
            archetype="TRIUNE_BALANCE",
            difficulty=1,
            doer_dominance=0.5,
            thinker_dominance=0.5,
            knower_dominance=0.5,
        )
        total = spec.doer_dominance + spec.thinker_dominance + spec.knower_dominance
        assert abs(total - 1.0) < 1e-6

    def test_negative_weights_become_zero(self, spec_cls):
        """Negative weights are clipped to 0."""
        spec = spec_cls(
            name="clip_test",
            archetype="HIHO_BASIN",
            difficulty=1,
            doer_dominance=-0.5,
            thinker_dominance=1.0,
            knower_dominance=0.5,
        )
        assert spec.doer_dominance == 0.0
        assert spec.thinker_dominance + spec.knower_dominance == 1.0

    def test_validate_returns_bool_and_score(self, spec_cls):
        """validate() returns (True/False, score 0-1)."""
        spec = spec_cls(name="oracle_test", archetype="HIHO_BASIN", difficulty=1)
        valid, score = spec.validate(None)
        assert isinstance(valid, bool)
        assert 0.0 <= score <= 1.0


class TestTaskGenerator:
    """Tests for TaskGenerator registry."""

    @pytest.fixture
    def gen_cls(self):
        try:
            from cohezion.rl.task_generator import TaskGenerator

            return TaskGenerator
        except ImportError:
            pytest.skip("TaskGenerator not yet implemented")

    def test_all_20_task_specs_generated(self, gen_cls):
        """5 archetypes × 4 difficulties = 20 TaskSpecs."""
        gen = gen_cls()
        specs = gen.all_specs()
        assert len(specs) == 20

    def test_each_archetype_has_4_difficulties(self, gen_cls):
        """Each archetype appears with difficulties 1, 2, 3, 4."""
        gen = gen_cls()
        for archetype in [
            "HIHO_BASIN",
            "TRIUNE_BALANCE",
            "INTERRUPTION_RECOVERY",
            "EXOTIC_CHARGE",
            "KORDYLEWSKI_ORBIT",
        ]:
            difficulties = [s.difficulty for s in gen.all_specs() if s.archetype == archetype]
            assert sorted(difficulties) == [1, 2, 3, 4]

    def test_sample_returns_valid_spec(self, gen_cls):
        """sample() returns a TaskSpec from the registry."""
        gen = gen_cls()
        for _ in range(10):
            spec = gen.sample()
            assert spec is not None
            assert 1 <= spec.difficulty <= 4

    def test_sample_difficulty_filter(self, gen_cls):
        """sample(difficulty=3) only returns difficulty=3 specs."""
        gen = gen_cls()
        for _ in range(20):
            spec = gen.sample(difficulty=3)
            assert spec.difficulty == 3

    def test_sample_archetype_filter(self, gen_cls):
        """sample(archetype='HIHO_BASIN') only returns HIHO_BASIN specs."""
        gen = gen_cls()
        for _ in range(20):
            spec = gen.sample(archetype="HIHO_BASIN")
            assert spec.archetype == "HIHO_BASIN"

    def test_get_returns_named_spec(self, gen_cls):
        """get(name) returns the matching spec or None."""
        gen = gen_cls()
        spec = gen.get("HIHO_BASIN-d2")
        assert spec is not None
        assert spec.name == "HIHO_BASIN-d2"

    def test_get_returns_none_for_missing(self, gen_cls):
        """get(missing_name) returns None."""
        gen = gen_cls()
        assert gen.get("NONEXISTENT") is None


class TestTaskArchetypes:
    """Tests for archetype-specific behavior."""

    @pytest.fixture
    def gen_cls(self):
        try:
            from cohezion.rl.task_generator import TaskGenerator

            return TaskGenerator
        except ImportError:
            pytest.skip("TaskGenerator not yet implemented")

    def test_hiho_basin_low_noise(self, gen_cls):
        """HIHO_BASIN difficulty 1 has low noise (0.01-0.03)."""
        gen = gen_cls()
        spec = gen.get("HIHO_BASIN-d1")
        assert spec.noise_level <= 0.03

    def test_exotic_charge_high_horizon(self, gen_cls):
        """EXOTIC_CHARGE difficulty 4 has horizon >= 200."""
        gen = gen_cls()
        spec = gen.get("EXOTIC_CHARGE-d4")
        assert spec.horizon >= 200

    def test_interruption_recovery_has_interruptions(self, gen_cls):
        """INTERRUPTION_RECOVERY specs have interruption_points."""
        gen = gen_cls()
        for diff in [1, 2, 3, 4]:
            spec = gen.get(f"INTERRUPTION_RECOVERY-d{diff}")
            assert len(spec.interruption_points) > 0

    def test_triune_balance_equal_weights(self, gen_cls):
        """TRIUNE_BALANCE difficulty 1 has near-equal weights."""
        gen = gen_cls()
        spec = gen.get("TRIUNE_BALANCE-d1")
        assert abs(spec.doer_dominance - 0.333) < 0.05
        assert abs(spec.thinker_dominance - 0.333) < 0.05
        assert abs(spec.knower_dominance - 0.333) < 0.05

    def test_kordylewski_orbit_has_kordylewski_params(self, gen_cls):
        """KORDYLEWSKI specs have orbit-specific params."""
        gen = gen_cls()
        spec = gen.get("KORDYLEWSKI_ORBIT-d1")
        assert spec.kordylewski_cloud in ("L4", "L5")


class TestTaskGeneratorPersistence:
    """Tests for TaskSpec save/load."""

    @pytest.fixture
    def gen_cls(self):
        try:
            from cohezion.rl.task_generator import TaskGenerator

            return TaskGenerator
        except ImportError:
            pytest.skip("TaskGenerator not yet implemented")

    def test_save_and_load(self, gen_cls, tmp_path):
        """save() and load() roundtrip the registry."""
        gen = gen_cls()
        save_path = Path("data/rl/test_tasks.json")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        gen.save(save_path)
        loaded = gen_cls.load(save_path)
        assert len(loaded.all_specs()) == len(gen.all_specs())

    def test_save_readable_json(self, gen_cls):
        """Saved registry is valid JSON."""
        gen = gen_cls()
        path = Path("data/rl/test_tasks_readable.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        gen.save(path)
        with open(path) as f:
            data = json.load(f)
        assert "tasks" in data
        assert len(data["tasks"]) == 20

    def test_load_rejects_path_traversal(self, gen_cls, tmp_path):
        """Loading a path with ../ is rejected (security)."""
        import json

        # Create the file BEFORE it gets resolved away
        target = Path("data/../../../evade.json")
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps({"tasks": [], "version": "1.0"}))
        # Now the file exists at a path with literal ".." in it
        gen = gen_cls()
        with pytest.raises(ValueError, match="must be within"):
            gen.load(target)

    def test_save_accepts_path_outside_data_dir(self, gen_cls, tmp_path):
        """Saving to arbitrary path is allowed (no path restriction on save)."""
        gen = gen_cls()
        path = tmp_path / "tasks.json"
        gen.save(path)
        assert path.exists()
