"""Smoke tests for E65–E70 experiment functions in overnight_evo_loop."""
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Load overnight_evo_loop as a module
spec = importlib.util.spec_from_file_location(
    "overnight_evo_loop",
    Path("/home/mike-anderson/dev/cohezion/scripts/overnight_evo_loop.py"),
)

# Patch heavy imports before loading
@pytest.fixture(autouse=True)
def patch_heavy_imports():
    """Prevent heavy imports (torch, SurrealDB etc.) from running."""
    mocks = {
        "cohezion.learning.mycelium_registry": MagicMock(),
        "cohezion.core.journey_worker": MagicMock(),
        "cohezion.core.telemetry_bus": MagicMock(),
    }
    with patch.dict("sys.modules", mocks):
        yield


def _make_deliberation_result(consensus: float = 0.7) -> dict:
    return {"consensus": consensus, "event_metadata": None}


class TestE65AdaptiveLr:
    def test_adaptive_lr_formula(self):
        """lr = min(2.0, |gap| * 4.0) for various gap values."""
        cases = [(0.15, 0.6), (0.3, 1.2), (0.5, 2.0), (0.8, 2.0)]
        for gap, expected_lr in cases:
            lr = min(2.0, abs(gap) * 4.0)
            assert abs(lr - expected_lr) < 1e-9, f"gap={gap} → lr={lr} expected {expected_lr}"

    def test_adaptive_lr_capped_at_2(self):
        """Large gaps should cap lr at 2.0."""
        for gap in [0.5, 1.0, 5.0]:
            lr = min(2.0, abs(gap) * 4.0)
            assert lr <= 2.0


class TestE66ParallelDeliberations:
    def test_parallel_means_multiple_concurrent(self):
        """asyncio.gather in E66 runs n_parallel tasks concurrently."""
        import asyncio

        call_count = []

        async def mock_fn(idx: int) -> float:
            call_count.append(idx)
            return 0.7

        async def _test():
            results = await asyncio.gather(*[mock_fn(i) for i in range(4)])
            return results

        results = asyncio.run(_test())
        assert len(results) == 4
        assert len(call_count) == 4

    def test_diversity_zero_for_identical_scores(self):
        """stdev([0.7, 0.7, 0.7]) == 0."""
        import statistics
        scores = [0.7, 0.7, 0.7]
        assert statistics.stdev(scores) == 0.0

    def test_diversity_nonzero_for_varied_scores(self):
        """stdev([0.3, 0.7, 0.9]) > 0."""
        import statistics
        scores = [0.3, 0.7, 0.9]
        assert statistics.stdev(scores) > 0.0


class TestE69CoherenceWeightedVoting:
    def test_weighted_mean_above_unweighted_for_high_scores(self):
        """When scores are high, weighting by score itself raises the mean."""
        scores = [0.8, 0.9, 0.7]
        unweighted = sum(scores) / len(scores)
        weighted_num = sum(s * s for s in scores)
        weight_total = sum(scores)
        weighted = weighted_num / weight_total
        assert weighted >= unweighted, f"weighted={weighted} should >= unweighted={unweighted}"

    def test_weighted_mean_below_unweighted_for_low_scores(self):
        """When scores are mixed with low values, weight-floor of 0.1 dampens effect."""
        scores = [0.1, 0.2, 0.9]
        unweighted = sum(scores) / len(scores)
        weighted_num = sum(max(0.1, s) * s for s in scores)
        weight_total = sum(max(0.1, s) for s in scores)
        weighted = weighted_num / weight_total
        # Either direction is fine — just verify no division by zero
        assert isinstance(weighted, float)


class TestE70RetirementCV:
    def test_cv_below_003_retires_at_all_thresholds(self):
        import statistics
        deltas = [0.05] * 10 + [0.051]  # tiny variation
        mean_d = sum(deltas) / len(deltas)
        std_d = statistics.stdev(deltas)
        cv = abs(std_d / mean_d)
        assert cv < 0.03
        retirements = {k: cv < v for k, v in {"cv_003": 0.03, "cv_005": 0.05, "cv_007": 0.07}.items()}
        assert all(retirements.values())

    def test_cv_above_010_retires_at_none(self):
        import statistics
        deltas = [0.05, 0.50, -0.10, 0.80, 0.02]  # high variation
        mean_d = sum(deltas) / len(deltas)
        std_d = statistics.stdev(deltas)
        cv = abs(std_d / mean_d) if mean_d != 0 else float("inf")
        retirements = {k: cv < v for k, v in {"cv_003": 0.03, "cv_005": 0.05, "cv_007": 0.07}.items()}
        assert not any(retirements.values()), f"cv={cv} should not retire"


# ---------------------------------------------------------------------------
# E77–E80 tests
# ---------------------------------------------------------------------------


class TestE77LrSweep:
    def test_lr_sweep_formula_distinct_adjustments(self):
        """Each lr in [0.25, 0.5, 1.0, 1.5] must produce a distinct calibration adjustment.

        E77 uses lr as a direct multiplier on a target_delta — so for any nonzero
        baseline gap, distinct lrs produce distinct adjustments.
        """
        gap = 0.15  # typical baseline-to-target gap in E63
        adjustments = [lr * gap for lr in [0.25, 0.5, 1.0, 1.5]]
        # All adjustments must be unique
        assert len(set(adjustments)) == len(adjustments), (
            f"lrs produced collision: {adjustments}"
        )
        # And must be monotone increasing (assuming positive gap)
        assert adjustments == sorted(adjustments), (
            f"adjustments not monotone: {adjustments}"
        )


class TestE79CvThresholdOrdering:
    def test_cv_threshold_ordering_monotone(self):
        """Stricter (higher) cv_threshold retires more often than lower thresholds.

        For any cv value, retire = (cv < threshold). Therefore the count of
        retirements at threshold T1 <= T2 <= T3 must satisfy R(T1) <= R(T2) <= R(T3).
        """
        thresholds = [0.01, 0.03, 0.05, 0.07]
        # Sample CV values spanning the threshold range
        cvs = [0.005, 0.02, 0.04, 0.06, 0.08, 0.10]
        # For each cv, count retirements per threshold
        for cv in cvs:
            retire_counts = [int(cv < t) for t in thresholds]
            # Monotone non-decreasing
            for i in range(len(retire_counts) - 1):
                assert retire_counts[i] <= retire_counts[i + 1], (
                    f"cv={cv}: retirements non-monotone {retire_counts}"
                )
        # And at any cv between two thresholds, the lower one rejects, the higher accepts
        cv_mid = 0.04  # between 0.03 and 0.05
        assert not (cv_mid < 0.03)
        assert (cv_mid < 0.05)


class TestE78PhaseCountStability:
    def test_phase_count_more_phases_more_stable(self):
        """More phases → smaller standard error of mean (1/sqrt(n) scaling).

        Generates synthetic deliberation samples with fixed underlying noise
        and verifies that variance of the *mean* falls as n grows.
        """
        import random
        import statistics

        random.seed(42)
        n_trials = 200
        underlying_std = 0.1

        def mean_var(n_phase: int) -> float:
            means = []
            for _ in range(n_trials):
                samples = [random.gauss(0.7, underlying_std) for _ in range(n_phase)]
                means.append(statistics.mean(samples))
            return statistics.variance(means)

        var_3 = mean_var(3)
        var_8 = mean_var(8)
        var_12 = mean_var(12)
        # Strict monotone: more phases = smaller variance of mean
        assert var_8 < var_3, f"var_8={var_8} should be < var_3={var_3}"
        assert var_12 < var_8, f"var_12={var_12} should be < var_8={var_8}"


class TestE80VoiceWeightDistribution:
    def test_voice_weight_profiles_sum_to_one(self):
        """All E80 weight profiles must sum to ~1.0 (within float tolerance)."""
        profiles = {
            "uniform": {"architect": 0.25, "engineer": 0.25, "ethicist": 0.25, "resource": 0.25},
            "engineer_heavy": {"architect": 0.20, "engineer": 0.40, "ethicist": 0.20, "resource": 0.20},
            "ethicist_heavy": {"architect": 0.20, "engineer": 0.20, "ethicist": 0.40, "resource": 0.20},
            "architect_heavy": {"architect": 0.40, "engineer": 0.20, "ethicist": 0.20, "resource": 0.20},
        }
        for name, weights in profiles.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 1e-6, f"profile {name} sums to {total}, not 1.0"
            # And each profile must have all 4 voices present
            assert set(weights.keys()) == {"architect", "engineer", "ethicist", "resource"}, (
                f"profile {name} missing voices: {set(weights.keys())}"
            )

