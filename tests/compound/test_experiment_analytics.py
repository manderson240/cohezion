"""Tests for experiment analytics module."""
import json

from cohezion.compound.experiment_analytics import (
    compute_experiment_stats,
    compute_hiho_balance,
    find_retirement_candidates,
    load_experiment_records,
)


def _make_records(exp, n_keep, n_discard, metric_val=0.15):
    records = []
    for _i in range(n_keep):
        records.append({"metric": metric_val, "status": "keep", "asi": {"experiment": exp}})
    for _i in range(n_discard):
        records.append({"metric": 0.0, "status": "discard", "asi": {"experiment": exp}})
    return records


class TestExperimentStats:

    def test_empty_records_returns_empty(self):
        assert compute_experiment_stats([]) == {}

    def test_single_experiment_stats(self):
        records = _make_records("E63", 10, 2)
        stats = compute_experiment_stats(records)
        assert "E63" in stats
        assert stats["E63"]["total"] == 12
        assert stats["E63"]["n_keeps"] == 10
        assert abs(stats["E63"]["keep_rate"] - 10/12) < 0.001

    def test_constant_metric_has_zero_cv(self):
        records = _make_records("E50", 20, 0, metric_val=0.125)
        stats = compute_experiment_stats(records)
        assert stats["E50"]["cv"] == 0.0

    def test_varied_metric_has_nonzero_cv(self):
        records = (
            _make_records("E63", 10, 0, 0.15) +
            _make_records("E63", 10, 0, 0.125)  # different metric values
        )
        stats = compute_experiment_stats(records)
        assert stats["E63"]["cv"] > 0


class TestRetirementCandidates:

    def test_constant_high_metric_retires(self):
        records = _make_records("E50", 15, 0, 0.125)
        stats = compute_experiment_stats(records)
        candidates = find_retirement_candidates(stats, min_keeps=10)
        assert "E50" in candidates

    def test_insufficient_keeps_not_retired(self):
        records = _make_records("E63", 5, 0, 0.15)  # Only 5 keeps
        stats = compute_experiment_stats(records)
        candidates = find_retirement_candidates(stats, min_keeps=10)
        assert "E63" not in candidates

    def test_high_cv_not_retired(self):
        import random
        random.seed(42)
        records = []
        for _ in range(15):
            m = random.uniform(0.05, 0.25)  # High variance
            records.append({"metric": m, "status": "keep", "asi": {"experiment": "E63"}})
        stats = compute_experiment_stats(records)
        candidates = find_retirement_candidates(stats, min_keeps=10, cv_threshold=0.05)
        assert "E63" not in candidates


class TestHIHOBalance:

    def test_all_keeps_hiho_is_one(self):
        records = [{"status": "keep"} for _ in range(10)]
        assert compute_hiho_balance(records) == 1.0

    def test_all_discards_hiho_is_zero(self):
        records = [{"status": "discard"} for _ in range(10)]
        assert compute_hiho_balance(records) == 0.0

    def test_empty_records_hiho_is_neutral(self):
        assert compute_hiho_balance([]) == 0.5

    def test_half_keeps_hiho_is_half(self):
        records = (
            [{"status": "keep"} for _ in range(5)] +
            [{"status": "discard"} for _ in range(5)]
        )
        assert compute_hiho_balance(records) == 0.5


class TestLoadExperimentRecords:

    def test_load_from_file(self, tmp_path):
        f = tmp_path / "test.jsonl"
        records = [{"run": i, "metric": 0.1, "status": "keep", "asi": {"experiment": "E1"}} for i in range(5)]
        f.write_text("\n".join(json.dumps(r) for r in records))
        loaded = load_experiment_records(n=10, jsonl_path=f)
        assert len(loaded) == 5

    def test_load_respects_n_limit(self, tmp_path):
        f = tmp_path / "test.jsonl"
        records = [{"run": i} for i in range(100)]
        f.write_text("\n".join(json.dumps(r) for r in records))
        loaded = load_experiment_records(n=10, jsonl_path=f)
        assert len(loaded) == 10



class TestExperimentVelocity:

    def test_no_recent_records_returns_zero(self):
        from cohezion.compound.experiment_analytics import compute_experiment_velocity
        # Records with old timestamps
        records = [{"metric": 0.15, "status": "keep", "asi": {"experiment": "E63"}, "timestamp": 0}]
        velocity = compute_experiment_velocity(records, "E63", time_window_ms=60000)
        assert velocity == 0.0  # cutoff > any timestamp

    def test_velocity_positive_for_recent_keeps(self):
        from cohezion.compound.experiment_analytics import compute_experiment_velocity
        import time
        now_ms = int(time.time() * 1000)
        records = [
            {"metric": 0.15, "status": "keep", "asi": {"experiment": "E63"}, "timestamp": now_ms - 1000}
            for _ in range(5)
        ]
        velocity = compute_experiment_velocity(records, "E63", time_window_ms=60000)
        assert velocity > 0.0

    def test_discard_records_not_counted(self):
        from cohezion.compound.experiment_analytics import compute_experiment_velocity
        import time
        now_ms = int(time.time() * 1000)
        records = [
            {"metric": 0.15, "status": "discard", "asi": {"experiment": "E63"}, "timestamp": now_ms - 1000}
        ]
        velocity = compute_experiment_velocity(records, "E63", time_window_ms=60000)
        assert velocity == 0.0  # Discards don't count

