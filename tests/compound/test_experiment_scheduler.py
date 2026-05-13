"""Tests for ExperimentScheduler."""
import json
from pathlib import Path

from cohezion.compound.experiment_scheduler import ExperimentScheduler


def _make_jsonl(path: Path, records: list) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records))


class TestExperimentScheduler:

    def test_default_params(self):
        sched = ExperimentScheduler()
        assert sched.min_keeps == 10
        assert sched.cv_threshold == 0.05

    def test_check_retirements_finds_constant_experiment(self, tmp_path):
        f = tmp_path / "test.jsonl"
        records = [
            {"metric": 0.125, "status": "keep", "asi": {"experiment": "E50"}}
            for _ in range(15)
        ]
        _make_jsonl(f, records)
        sched = ExperimentScheduler(min_keeps=10)
        retired = sched.check_retirements(jsonl_path=f)
        assert "E50" in retired

    def test_check_retirements_skips_variable_experiment(self, tmp_path):
        f = tmp_path / "test.jsonl"
        records = [
            {"metric": 0.15 if i % 2 else 0.125, "status": "keep", "asi": {"experiment": "E63"}}
            for i in range(15)
        ]
        _make_jsonl(f, records)
        sched = ExperimentScheduler(min_keeps=10, cv_threshold=0.05)
        retired = sched.check_retirements(jsonl_path=f)
        assert "E63" not in retired

    def test_already_retired_not_returned_again(self, tmp_path):
        f = tmp_path / "test.jsonl"
        records = [{"metric": 0.125, "status": "keep", "asi": {"experiment": "E50"}} for _ in range(15)]
        _make_jsonl(f, records)
        sched = ExperimentScheduler(min_keeps=10)
        # First call finds E50
        first = sched.check_retirements(jsonl_path=f)
        assert "E50" in first
        # Second call should NOT return E50 again (already retired)
        second = sched.check_retirements(jsonl_path=f)
        assert "E50" not in second

    def test_propose_replacements_returns_list(self, tmp_path):
        f = tmp_path / "test.jsonl"
        records = [{"metric": 0.8, "status": "keep", "asi": {"experiment": "E1"}} for _ in range(5)]
        _make_jsonl(f, records)
        sched = ExperimentScheduler()
        proposals = sched.propose_replacements(["E50"], n=2)
        assert len(proposals) == 2
        assert all("hypothesis" in p for p in proposals)

    def test_propose_replacements_empty_retired_returns_empty(self):
        sched = ExperimentScheduler()
        proposals = sched.propose_replacements([])
        assert proposals == []

    def test_get_schedule_summary(self):
        sched = ExperimentScheduler(min_keeps=5, cv_threshold=0.03)
        sched._retired.add("E50")
        summary = sched.get_schedule_summary()
        assert summary["total_retired"] == 1
        assert "E50" in summary["retired_labels"]
        assert summary["min_keeps"] == 5
        assert summary["cv_threshold"] == 0.03

