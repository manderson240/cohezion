"""TDD tests for scripts/research/adaptive_schedule.py"""

import json
import sys
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
from scripts.research.adaptive_schedule import AdaptiveSchedule, ExperimentStats


class TestExperimentStats:
    def test_keep_frac_zero_runs(self):
        assert ExperimentStats(name="t").keep_frac == 0.0

    def test_keep_frac_partial(self):
        s = ExperimentStats(name="t", n=10, keep_count=3, deltas=[0.1] * 3 + [0.0] * 7)
        assert s.keep_frac == pytest.approx(0.3)

    def test_is_at_ceiling_deterministic(self):
        s = ExperimentStats(name="t", n=8, keep_count=8, deltas=[0.15] * 8)
        assert s.is_at_ceiling

    def test_should_retire_threshold(self):
        s = ExperimentStats(name="E12", n=15, keep_count=0, deltas=[0.0] * 15)
        assert s.should_retire

    def test_should_not_retire_insufficient_samples(self):
        s = ExperimentStats(name="E12", n=5, keep_count=0, deltas=[0.0] * 5)
        assert not s.should_retire


class TestAdaptiveScheduleLoading:
    def _make_jsonl(self, entries):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        for e in entries:
            tmp.write(json.dumps(e) + "\n")
        tmp.close()
        return Path(tmp.name)

    def test_loads_empty_file(self):
        assert AdaptiveSchedule.from_jsonl(self._make_jsonl([])).stats == {}

    def test_loads_missing_file(self):
        assert AdaptiveSchedule.from_jsonl("/nonexistent/path.jsonl").stats == {}

    def test_counts_runs_correctly(self):
        entries = [
            {"experiment": "E63", "delta": 0.15, "keep": "keep"},
            {"experiment": "E63", "delta": 0.15, "keep": "keep"},
            {"experiment": "E63", "delta": 0.0, "keep": "discard"},
        ]
        s = AdaptiveSchedule.from_jsonl(self._make_jsonl(entries))
        assert s.stats["E63"].n == 3
        assert s.stats["E63"].keep_count == 2

    def test_skips_finding_entries(self):
        entries = [
            {"experiment": "FINDING_ceiling", "delta": 0.275, "keep": "keep"},
            {"experiment": "E63", "delta": 0.15, "keep": "keep"},
        ]
        s = AdaptiveSchedule.from_jsonl(self._make_jsonl(entries))
        assert "FINDING_ceiling" not in s.stats


class TestPivotCheck:
    def test_pivot_needed_when_3_at_same_ceiling(self):
        stats = {
            n: ExperimentStats(name=n, n=8, keep_count=8, deltas=[0.15] * 8)
            for n in ("E63", "E50", "E51")
        }
        result = AdaptiveSchedule(stats).pivot_check()
        assert result["pivot_needed"] is True
        assert abs(float(result.get("ceiling_value", 0)) - 0.15) < 0.001
