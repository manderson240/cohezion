"""TDD RED phase — Task #17: Long2Short quality score in _record_result().

Long2Short formula: quality_score = success * (1.0 / tokens_used)
- success=True,  tokens>0  → 1.0 / tokens  (shorter = higher quality)
- success=False, tokens>0  → 0.0            (failed tasks score zero)
- success=False, tokens=0  → 0.0            (failed, no tokens)
- success=True,  tokens=0  → None           (undefined; follow sparse-metrics contract)

quality_score is:
  1. Appended to report.results as a "quality_score" key
  2. Fed to DegradationDetector as sparse metric when not None
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from cohezion.compound.autonomous_loop.coordinator import (
    LoopConfig,
    LoopCoordinator,
    RunReport,
    SprintResult,
)
from cohezion.compound.degradation_detector import DegradationDetector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class _Task:
    id: str = "t1"
    category: str = "test"


def _make_result(
    *,
    success: bool,
    tokens_used: int,
    elapsed_ms: float | None = 100.0,
    token_surprisal: float | None = None,
) -> dict:
    return {
        "success": success,
        "tokens_used": tokens_used,
        "model": "test-model",
        "node": "igpu",
        "elapsed_ms": elapsed_ms,
        "token_surprisal": token_surprisal,
        "tried_models": ["test-model"],
    }


def _call_record_result(
    coordinator: LoopCoordinator,
    result: dict,
    tokens: int,
    task: _Task | None = None,
) -> RunReport:
    report = RunReport()
    fail_counts: dict[str, int] = {}
    category_stats: dict[str, dict[str, int]] = {}
    sprint = SprintResult()
    task = task or _Task()
    coordinator._record_result(
        result, task, False, tokens, report, fail_counts, category_stats, sprint
    )
    return report


# ---------------------------------------------------------------------------
# Class 1: quality_score arithmetic
# ---------------------------------------------------------------------------

class TestLong2ShortArithmetic:
    """quality_score follows success * (1/tokens) with zero-division protection."""

    def test_success_positive_tokens(self):
        coord = LoopCoordinator(LoopConfig())
        result = _make_result(success=True, tokens_used=200)
        report = _call_record_result(coord, result, tokens=200)
        qs = report.results[0]["quality_score"]
        assert qs == pytest.approx(1.0 / 200)

    def test_failure_positive_tokens(self):
        coord = LoopCoordinator(LoopConfig())
        result = _make_result(success=False, tokens_used=300)
        report = _call_record_result(coord, result, tokens=300)
        qs = report.results[0]["quality_score"]
        assert qs == pytest.approx(0.0)

    def test_failure_zero_tokens(self):
        """Failures with 0 tokens score 0.0 (not None) — failure is definite."""
        coord = LoopCoordinator(LoopConfig())
        result = _make_result(success=False, tokens_used=0)
        report = _call_record_result(coord, result, tokens=0)
        qs = report.results[0]["quality_score"]
        assert qs == pytest.approx(0.0)

    def test_success_zero_tokens_returns_none(self):
        """success=True but tokens=0 → undefined; return None (sparse-metrics contract)."""
        coord = LoopCoordinator(LoopConfig())
        result = _make_result(success=True, tokens_used=0)
        report = _call_record_result(coord, result, tokens=0)
        qs = report.results[0]["quality_score"]
        assert qs is None

    def test_shorter_response_scores_higher(self):
        """Discriminating: 50-token success beats 400-token success."""
        coord = LoopCoordinator(LoopConfig())
        r_short = _make_result(success=True, tokens_used=50)
        r_long  = _make_result(success=True, tokens_used=400)
        rep_s = _call_record_result(coord, r_short, tokens=50, task=_Task(id="s"))
        rep_l = _call_record_result(coord, r_long,  tokens=400, task=_Task(id="l"))
        assert rep_s.results[0]["quality_score"] > rep_l.results[0]["quality_score"]

    def test_single_token_success_is_max(self):
        """1-token success → quality_score = 1.0 (maximum possible)."""
        coord = LoopCoordinator(LoopConfig())
        result = _make_result(success=True, tokens_used=1)
        report = _call_record_result(coord, result, tokens=1)
        assert report.results[0]["quality_score"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Class 2: quality_score key is always present in report.results
# ---------------------------------------------------------------------------

class TestQualityScoreInReport:
    """quality_score is always written to report.results (may be None)."""

    def test_key_present_on_success(self):
        coord = LoopCoordinator(LoopConfig())
        result = _make_result(success=True, tokens_used=100)
        report = _call_record_result(coord, result, tokens=100)
        assert "quality_score" in report.results[0]

    def test_key_present_on_failure(self):
        coord = LoopCoordinator(LoopConfig())
        result = _make_result(success=False, tokens_used=100)
        report = _call_record_result(coord, result, tokens=100)
        assert "quality_score" in report.results[0]

    def test_key_present_zero_tokens_success(self):
        coord = LoopCoordinator(LoopConfig())
        result = _make_result(success=True, tokens_used=0)
        report = _call_record_result(coord, result, tokens=0)
        assert "quality_score" in report.results[0]


# ---------------------------------------------------------------------------
# Class 3: quality_score fed to DegradationDetector as sparse metric
# ---------------------------------------------------------------------------

class TestQualityScoreFedToDetector:
    """quality_score (when not None) is included in the sparse metrics dict
    passed to DegradationDetector.check_degradation()."""

    def test_quality_score_passed_to_detector_on_success(self):
        detector = MagicMock(spec=DegradationDetector)
        coord = LoopCoordinator(LoopConfig(), degradation_detector=detector)
        result = _make_result(success=True, tokens_used=100)
        _call_record_result(coord, result, tokens=100)
        call_kwargs = detector.check_degradation.call_args[0][0]
        assert "quality_score" in call_kwargs
        assert call_kwargs["quality_score"] == pytest.approx(1.0 / 100)

    def test_quality_score_passed_to_detector_on_failure(self):
        detector = MagicMock(spec=DegradationDetector)
        coord = LoopCoordinator(LoopConfig(), degradation_detector=detector)
        result = _make_result(success=False, tokens_used=200)
        _call_record_result(coord, result, tokens=200)
        call_kwargs = detector.check_degradation.call_args[0][0]
        assert "quality_score" in call_kwargs
        assert call_kwargs["quality_score"] == pytest.approx(0.0)

    def test_quality_score_omitted_from_detector_when_none(self):
        """success=True, tokens=0 → quality_score=None → NOT passed to detector
        (sparse-metrics contract: never pass None values as sentinel defaults)."""
        detector = MagicMock(spec=DegradationDetector)
        coord = LoopCoordinator(LoopConfig(), degradation_detector=detector)
        result = _make_result(success=True, tokens_used=0)
        _call_record_result(coord, result, tokens=0)
        call_kwargs = detector.check_degradation.call_args[0][0]
        assert "quality_score" not in call_kwargs

    def test_coexists_with_slp_in_sparse_metrics(self):
        """quality_score and token_surprisal both appear in the same sparse dict."""
        detector = MagicMock(spec=DegradationDetector)
        coord = LoopCoordinator(LoopConfig(), degradation_detector=detector)
        result = _make_result(success=True, tokens_used=150, token_surprisal=2.3)
        _call_record_result(coord, result, tokens=150)
        call_kwargs = detector.check_degradation.call_args[0][0]
        assert "quality_score" in call_kwargs
        assert "token_surprisal" in call_kwargs


# ---------------------------------------------------------------------------
# Class 4: DegradationDetector actually tracks quality_score baseline
#   (discriminating — MagicMock in Class 3 only proves the dict was passed;
#    these use a real detector to prove the baseline accumulates)
# ---------------------------------------------------------------------------

class TestQualityScoreTrackedByDetector:
    """Real DegradationDetector (no mock) accumulates quality_score samples."""

    def test_baseline_accumulates_after_n_samples(self):
        """After min_samples successes, quality_score baseline is established."""
        detector = DegradationDetector()
        coord = LoopCoordinator(LoopConfig(), degradation_detector=detector)

        min_samples = detector._baselines["quality_score"].min_samples
        for i in range(min_samples):
            result = _make_result(success=True, tokens_used=100 + i)
            _call_record_result(coord, result, tokens=100 + i, task=_Task(id=f"t{i}"))

        assert detector._baselines["quality_score"].is_established
        assert len(detector._baselines["quality_score"].samples) == min_samples

    def test_none_quality_score_not_sampled(self):
        """success=True, tokens=0 → quality_score=None → baseline NOT sampled."""
        detector = DegradationDetector()
        coord = LoopCoordinator(LoopConfig(), degradation_detector=detector)

        result = _make_result(success=True, tokens_used=0)
        _call_record_result(coord, result, tokens=0)

        assert len(detector._baselines["quality_score"].samples) == 0

    def test_degradation_alert_fired_when_quality_drops(self):
        """After baseline established, a large quality drop raises an alert."""
        detector = DegradationDetector()
        coord = LoopCoordinator(LoopConfig(), degradation_detector=detector)

        # Establish baseline with fast (high quality) completions: 1/100 = 0.01
        for i in range(detector._baselines["quality_score"].min_samples):
            result = _make_result(success=True, tokens_used=100)
            _call_record_result(coord, result, tokens=100, task=_Task(id=f"base{i}"))

        assert detector._baselines["quality_score"].is_established

        # Now submit a very slow completion: 1/2000 = 0.0005 — well below 80% of baseline
        result = _make_result(success=True, tokens_used=2000)
        _call_record_result(coord, result, tokens=2000, task=_Task(id="slow"))

        alert_metrics = [a.metric for a in detector._alert_history]
        assert "quality_score" in alert_metrics, (
            "Expected quality_score degradation alert when efficiency dropped >20%"
        )
