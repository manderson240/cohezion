"""Production quality signal: measured when there is evidence, UNKNOWN when there is not.

Before 2026-09-22 ``make_local_execute_fn`` published no quality key, so
``SkillRefiner._extract_metrics`` defaulted to 0.5 -- one tenth below
DifficultyEstimator's 0.6 floor -- and every production run looked identical and
sub-par. These tests drive the PRODUCTION path (execute_fn -> metrics dict ->
SkillRefiner.refine -> DifficultyEstimator) with fake orchestrator outcomes; no live
inference is issued (the orchestrator is a double; ``_get_orchestrator`` is patched,
which also keeps the categorical fast path from building a real one).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import cohezion.compound.local_inference as li
from cohezion.compound.difficulty_estimator import DifficultyEstimator
from cohezion.compound.skill_health_tracker import SkillHealthTracker
from cohezion.compound.skill_refiner import SkillRefiner
from cohezion.inference.orchestrator import OrchestrationResult


CODE_TASK = "Write a Python function that reverses a string."
PROSE_TASK = "Summarize the history of the Roman Republic in a few paragraphs."

GOOD_CODE = "```python\ndef reverse(s):\n    return s[::-1]\n```"
# Not code at all: no parseable Python, no code markers -> a measured failure.
BAD_CODE = "Sure! Reversing things is a fascinating idea with a long history."


def _outcome(text: str, *, escalation_count: int = 0) -> OrchestrationResult:
    return OrchestrationResult(
        text=text, primary_model="m", final_model="m", escalation_count=escalation_count
    )


def _run(task: str, text: str, *, min_tier_index: int = 0, escalation_count: int = 0):
    orch = MagicMock()
    orch.run = AsyncMock(return_value=_outcome(text, escalation_count=escalation_count))
    with patch.object(li, "_get_orchestrator", return_value=orch):
        return li.make_local_execute_fn(task)("", min_tier_index=min_tier_index)


def _feed(refiner: SkillRefiner, metrics: dict) -> None:
    """The executor's Step 7 hand-off: refine() on a successful execution."""
    refiner.refine(
        skill_name="S",
        operation_type="op",
        execution_result={
            "success": True,
            "output": "x",
            "metrics": metrics,
            "duration_seconds": 1.0,
            "token_metrics": {},
        },
    )


class TestProducer:
    def test_two_outcomes_produce_different_quality(self):
        """Discriminating: a constant producer (the old behaviour) fails here."""
        _, good = _run(CODE_TASK, GOOD_CODE)
        _, bad = _run(CODE_TASK, BAD_CODE)
        assert good["cascade_quality_score"] == pytest.approx(1.0)
        assert bad["cascade_quality_score"] == pytest.approx(0.0)

    def test_exhausted_cascade_is_measured_zero(self):
        _, m = _run(CODE_TASK, "   ", escalation_count=2)
        assert m["gate_miss"] is True
        assert m["cascade_quality_score"] == 0.0

    def test_uncalibrated_type_is_explicitly_unknown_not_a_number(self):
        """The key is PRESENT with None: the producer spoke and said 'not measured'."""
        _, m = _run(PROSE_TASK, "The Roman Republic " * 40)
        assert "cascade_quality_score" in m
        assert m["cascade_quality_score"] is None
        assert m["cascade_quality_source"].startswith("unmeasured")

    def test_quality_does_not_depend_on_escalation_count(self):
        """escalation_count is RELATIVE (H1/H2) and was falsified as a quality proxy."""
        _, a = _run(CODE_TASK, GOOD_CODE, escalation_count=0)
        _, b = _run(CODE_TASK, GOOD_CODE, escalation_count=2)
        assert a["cascade_quality_score"] == b["cascade_quality_score"]


class TestExtractMetrics:
    def _extract(self, metrics: dict):
        return SkillRefiner()._extract_metrics(
            {"success": True, "metrics": metrics, "duration_seconds": 1.0, "token_metrics": {}}
        )

    def test_producer_value_beats_anomaly_alias(self):
        """The executor always sets anomaly_score (health); the producer's value must win."""
        extracted = self._extract({"anomaly_score": 0.9, "cascade_quality_score": 0.0})
        assert extracted.quality_score == pytest.approx(0.0)

    def test_producer_none_is_unknown_even_with_anomaly_present(self):
        extracted = self._extract({"anomaly_score": 0.9, "cascade_quality_score": None})
        assert extracted.quality_score is None

    def test_absent_everything_is_unknown_not_half(self):
        assert self._extract({}).quality_score is None


class TestConsumers:
    def test_ORACLE_distinction_reproduces_through_the_production_path(self):
        """The 2026-08-30 discriminating measurement, now via execute_fn -> refine().

        Record count and escalation_count are held identical across the two tiers so
        quality is the only differing signal. With the fabricated 0.5 both tiers sit
        below the 0.6 floor and the dominant-tier fallback picks npu (cheapest wins).
        """
        refiner = SkillRefiner()
        for _ in range(5):
            _, m_npu = _run(CODE_TASK, BAD_CODE, min_tier_index=0)
            _, m_igpu = _run(CODE_TASK, GOOD_CODE, min_tier_index=1)
            assert m_npu["tier_used"] == "npu" and m_igpu["tier_used"] == "igpu"
            assert m_npu["escalation_count"] == m_igpu["escalation_count"] == 0
            _feed(refiner, {**m_npu, "anomaly_score": 0.9})
            _feed(refiner, {**m_igpu, "anomaly_score": 0.9})
        assert len(refiner._difficulty_estimator._history[("S", "op")]) == 10
        assert refiner._difficulty_estimator.predict_tier("S", "op") == "igpu"

    def test_unknown_quality_does_not_move_difficulty_stats(self):
        refiner = SkillRefiner()
        _, m = _run(PROSE_TASK, "The Roman Republic " * 40)
        _feed(refiner, {**m, "anomaly_score": 0.9})
        assert ("S", "op") not in refiner._difficulty_estimator._history
        assert refiner._env_predictor.predict("S", "op") is None

    def test_estimator_record_skips_none(self):
        est = DifficultyEstimator()
        est.record("S", "op", "npu", 0, None)
        assert est.predict_tier("S", "op") == "unknown"

    def test_health_tracker_excludes_unknown_from_average(self, tmp_path):
        tracker = SkillHealthTracker(storage_path=tmp_path / "h.json")
        tracker.record_usage("S", success=True, quality_score=0.9)
        tracker.record_usage("S", success=True, quality_score=None)
        rec = tracker._records["S"]
        assert rec.successful_invocations == 2
        assert rec.avg_quality_score == pytest.approx(0.9)
