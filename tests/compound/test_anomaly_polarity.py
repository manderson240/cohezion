"""Discriminating tests for the anomaly_score polarity fix (2026-07-12).

``metrics["anomaly_score"]`` is a HEALTH score (high=good) — populated as
``metrics["anomaly_score"] = anomaly.score`` where ``AnomalyDetection.score``
starts at 1.0 and is penalized DOWN. It must be used DIRECTLY as a quality/
coherence signal, never inverted via ``1.0 - anomaly_score``.

Three consumers were fixed here (each was inverting the health score):
  1. skill_refiner.py     — ``SkillRefiner._extract_metrics``
  2. failure_attributor.py — ``FailureAttributor.classify``
  3. post_execution.py    — ``PostExecutionOrchestrator._compute_coherence``

Reference (already-correct, untouched) implementation used for cross-consumer
agreement: ``coherence_v1`` in coherence_v3.py, a byte-for-byte reproduction of
executor.py Step 5.8.

Each test below is written to FAIL against the pre-fix (``1.0 - anomaly_score``)
implementation — verified by running this file against a `git stash` of the
source changes (see PR/review notes). These call the REAL production functions;
none of them reimplement the polarity formula locally.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cohezion.compound.coherence_v3 import coherence_v1
from cohezion.compound.executor import ExecutionResult
from cohezion.compound.failure_attributor import FailureAttributor
from cohezion.compound.post_execution import PostExecutionOrchestrator
from cohezion.compound.skill_refiner import SkillRefiner
from cohezion.core.compound.retrospection import RetrospectionEngine


# A "healthy" run: anomaly.score has NOT been penalized down (stays near its 1.0 start).
_HEALTHY_ANOMALY_SCORE = 0.9
# An "unhealthy" run: anomaly.score has been penalized down toward 0.
_UNHEALTHY_ANOMALY_SCORE = 0.1


def _healthy_execution_result() -> dict:
    """Minimal real ExecutionResult-shaped dict for SkillRefiner._extract_metrics."""
    return {
        "success": True,
        "output": "Sample output",
        "metrics": {
            "duration_seconds": 1.0,
            "anomaly_score": _HEALTHY_ANOMALY_SCORE,
        },
        "duration_seconds": 1.0,
        "token_metrics": {"tokens_used": 100, "cache_hits": 0},
    }


def _unhealthy_execution_result() -> dict:
    result = _healthy_execution_result()
    result["metrics"]["anomaly_score"] = _UNHEALTHY_ANOMALY_SCORE
    return result


# ---------------------------------------------------------------------------
# Site 1: skill_refiner.py — SkillRefiner._extract_metrics
# ---------------------------------------------------------------------------


class TestSkillRefinerAnomalyPolarity:
    def test_healthy_anomaly_score_yields_high_quality_score(self):
        """anomaly_score=0.9 (healthy) must produce quality_score > 0.6.

        Under the old `1.0 - anomaly_score` bug this would be 0.1 (< 0.6) — FAILS.
        """
        refiner = SkillRefiner()
        metrics = refiner._extract_metrics(_healthy_execution_result())
        assert metrics.quality_score > 0.6
        assert metrics.quality_score == pytest.approx(_HEALTHY_ANOMALY_SCORE)

    def test_unhealthy_anomaly_score_yields_low_quality_score(self):
        """anomaly_score=0.1 (unhealthy) must produce a LOW quality_score.

        Under the old bug this would be 0.9 (high) — FAILS.
        """
        refiner = SkillRefiner()
        metrics = refiner._extract_metrics(_unhealthy_execution_result())
        assert metrics.quality_score < 0.6
        assert metrics.quality_score == pytest.approx(_UNHEALTHY_ANOMALY_SCORE)


# ---------------------------------------------------------------------------
# Site 2: failure_attributor.py — FailureAttributor.classify
# ---------------------------------------------------------------------------


class TestFailureAttributorAnomalyPolarity:
    def test_healthy_anomaly_score_returns_no_attribution(self):
        """A healthy run (anomaly_score=0.9) must NOT be attributed to any failure category.

        classify() short-circuits to None only when quality_score > 0.7. Under the old
        `1.0 - anomaly_score` bug, 0.9 would compute quality_score=0.1 (<=0.7), causing
        classify() to fall through into a bogus failure attribution — FAILS.
        """
        fa = FailureAttributor()
        metrics = {"anomaly_score": _HEALTHY_ANOMALY_SCORE}
        result = fa.classify("a healthy, substantial output", metrics, decision_paths=["v/x"])
        assert result is None

    def test_unhealthy_anomaly_score_gets_attributed(self):
        """An unhealthy run (anomaly_score=0.1) must be attributed to a failure category.

        Under the old bug, 0.1 would compute quality_score=0.9 (>0.7), causing classify()
        to wrongly short-circuit to None (silently swallowing a genuine failure) — FAILS.
        """
        fa = FailureAttributor()
        metrics = {"anomaly_score": _UNHEALTHY_ANOMALY_SCORE}
        result = fa.classify(
            "a substantial but low-quality output here", metrics, decision_paths=["v/x"]
        )
        assert result is not None


# ---------------------------------------------------------------------------
# Site 3: post_execution.py — PostExecutionOrchestrator._compute_coherence
# ---------------------------------------------------------------------------


class TestPostExecutionAnomalyPolarity:
    def test_healthy_anomaly_score_yields_high_coherence(self):
        """anomaly_score=0.9 (healthy, success=True) must produce coherence > 0.6.

        Under the old `1.0 - anomaly_score` bug this would be (0.7 + 0.1) / 2 = 0.4
        (< 0.6) — FAILS.
        """
        orchestrator = PostExecutionOrchestrator(executor=MagicMock())
        metrics: dict = {"success": True, "anomaly_score": _HEALTHY_ANOMALY_SCORE}
        orchestrator._compute_coherence(metrics)
        assert metrics["coherence"] > 0.6
        assert metrics["coherence"] == pytest.approx((0.7 + _HEALTHY_ANOMALY_SCORE) / 2)

    def test_unhealthy_anomaly_score_yields_low_coherence(self):
        """anomaly_score=0.1 (unhealthy, success=True) must produce a LOW coherence.

        Under the old bug this would be (0.7 + 0.9) / 2 = 0.8 (high) — FAILS.
        """
        orchestrator = PostExecutionOrchestrator(executor=MagicMock())
        metrics: dict = {"success": True, "anomaly_score": _UNHEALTHY_ANOMALY_SCORE}
        orchestrator._compute_coherence(metrics)
        assert metrics["coherence"] < 0.6

    def test_missing_key_default_matches_healthy_assumption(self):
        """Default (missing anomaly_score) must assume healthy (1.0), matching executor.py:1296.

        Under the old bug the default was 0.0 and got inverted to 1.0 — same net effect
        for the missing-key case, but this pins the NEW default explicitly (1.0, used
        directly) so a future refactor can't silently reintroduce the 0.0-then-invert path.
        """
        orchestrator = PostExecutionOrchestrator(executor=MagicMock())
        metrics: dict = {"success": True}
        orchestrator._compute_coherence(metrics)
        assert metrics["coherence"] == pytest.approx((0.7 + 1.0) / 2)


# ---------------------------------------------------------------------------
# Cross-consumer direction-agreement (the split-brain catcher)
# ---------------------------------------------------------------------------


class TestCrossConsumerDirectionAgreement:
    """One healthy dict fed through all four consumers must trend the SAME direction.

    If any one consumer still inverts, it will diverge from the other three even though
    they all received identical input — this is the test that catches a half-migrated fix.
    """

    def test_all_consumers_agree_on_healthy_input(self):
        healthy_metrics = {"success": True, "anomaly_score": _HEALTHY_ANOMALY_SCORE}

        # Site 1: skill_refiner
        refiner_quality = SkillRefiner()._extract_metrics(_healthy_execution_result()).quality_score

        # Site 2: failure_attributor (proxy: None result = healthy/no-attribution = high quality)
        fa_result = FailureAttributor().classify(
            "a healthy, substantial output", dict(healthy_metrics), decision_paths=["v/x"]
        )
        fa_is_healthy = fa_result is None

        # Site 3: post_execution
        po_metrics = dict(healthy_metrics)
        PostExecutionOrchestrator(executor=MagicMock())._compute_coherence(po_metrics)
        post_execution_coherence = po_metrics["coherence"]

        # Reference: already-correct executor.py Step 5.8 reproduction (untouched)
        reference_coherence = coherence_v1(success=True, metrics=healthy_metrics)

        # All four must trend HIGH together for the same healthy input.
        assert refiner_quality > 0.6
        assert fa_is_healthy is True
        assert post_execution_coherence > 0.6
        assert reference_coherence > 0.6

        # And post_execution's fixed formula must numerically AGREE with the reference
        # implementation (both use anomaly_score directly, same component weighting).
        assert post_execution_coherence == pytest.approx(reference_coherence)

    def test_all_consumers_agree_on_unhealthy_input(self):
        unhealthy_metrics = {"success": True, "anomaly_score": _UNHEALTHY_ANOMALY_SCORE}

        refiner_quality = (
            SkillRefiner()._extract_metrics(_unhealthy_execution_result()).quality_score
        )

        fa_result = FailureAttributor().classify(
            "a substantial but low-quality output here",
            dict(unhealthy_metrics),
            decision_paths=["v/x"],
        )
        fa_is_unhealthy = fa_result is not None

        po_metrics = dict(unhealthy_metrics)
        PostExecutionOrchestrator(executor=MagicMock())._compute_coherence(po_metrics)
        post_execution_coherence = po_metrics["coherence"]

        reference_coherence = coherence_v1(success=True, metrics=unhealthy_metrics)

        assert refiner_quality < 0.6
        assert fa_is_unhealthy is True
        assert post_execution_coherence < 0.6
        assert reference_coherence < 0.6
        assert post_execution_coherence == pytest.approx(reference_coherence)


# ---------------------------------------------------------------------------
# Site 4: retrospection.py — RetrospectionEngine.analyze_execution_result
# ---------------------------------------------------------------------------


class TestRetrospectionEngineAnomalyPolarity:
    """Discriminating tests for the 4th (live-wired) polarity site.

    ``RetrospectionEngine.analyze_execution_result`` is wired into production via
    ``executor_factory.py`` (lines 70/267). Two inversions were fixed:
      - the "low health, investigate" insight now fires on LOW anomaly_score
      - ``compound_score`` now ADDS ``anomaly_score`` directly (was ``1.0 - anomaly_score``)

    Neither test reimplements the formula locally — both call the real method.
    """

    def _healthy_result(self) -> ExecutionResult:
        return ExecutionResult(
            success=True,
            output="Sample output",
            metrics={"coherence": 0.75, "anomaly_score": _HEALTHY_ANOMALY_SCORE},
            duration_seconds=1.0,
        )

    def _unhealthy_result(self) -> ExecutionResult:
        return ExecutionResult(
            success=True,
            output="Sample output",
            metrics={"coherence": 0.75, "anomaly_score": _UNHEALTHY_ANOMALY_SCORE},
            duration_seconds=1.0,
        )

    def test_healthy_anomaly_score_yields_high_compound_score_no_investigate_insight(self):
        """anomaly_score=0.9 (healthy) -> HIGH compound_score, no 'investigate' insight.

        Under the old ``1.0 - anomaly_score`` bug, compound_score would be computed
        with a penalized (0.1) health contribution instead of the healthy (0.9) one,
        pulling compound_score DOWN — FAILS the `> 0.6` assertion below.
        """
        engine = RetrospectionEngine()
        analysis = engine.analyze_execution_result(self._healthy_result(), "test_skill")

        assert analysis["compound_score"] > 0.6
        assert not any(
            "investigate" in insight.lower() or "low health" in insight.lower()
            for insight in analysis["insights"]
        )

    def test_unhealthy_anomaly_score_yields_lower_compound_score_and_investigate_insight(self):
        """anomaly_score=0.1 (unhealthy) -> LOWER compound_score than healthy, plus the
        'Low health score ... investigate' insight.

        Under the old bug the "> 0.7" trigger condition would fire on the HEALTHY score
        (0.9 > 0.7) instead of the unhealthy one (0.1), and the unhealthy compound_score
        would be numerically HIGHER than the healthy one (since 1.0 - 0.1 = 0.9 beats
        1.0 - 0.9 = 0.1) — inverting the expected ordering below.
        """
        engine = RetrospectionEngine()
        healthy_analysis = engine.analyze_execution_result(self._healthy_result(), "test_skill")
        unhealthy_analysis = engine.analyze_execution_result(self._unhealthy_result(), "test_skill")

        assert unhealthy_analysis["compound_score"] < healthy_analysis["compound_score"]
        assert any(
            "low health" in insight.lower() and "investigate" in insight.lower()
            for insight in unhealthy_analysis["insights"]
        )

    def test_cross_consumer_all_four_sites_agree_on_healthy_input(self):
        """The SAME healthy metrics dict trends HIGH through all 4 fixed consumers.

        Catches a half-migrated fix: if retrospection.py were reverted while the other
        three sites stayed fixed, this test diverges (retrospection LOW, others HIGH).
        """
        healthy_metrics = {
            "success": True,
            "coherence": 0.75,
            "anomaly_score": _HEALTHY_ANOMALY_SCORE,
        }

        retrospection_score = RetrospectionEngine().analyze_execution_result(
            self._healthy_result(), "test_skill"
        )["compound_score"]

        refiner_quality = SkillRefiner()._extract_metrics(_healthy_execution_result()).quality_score

        po_metrics = dict(healthy_metrics)
        PostExecutionOrchestrator(executor=MagicMock())._compute_coherence(po_metrics)
        post_execution_coherence = po_metrics["coherence"]

        reference_coherence = coherence_v1(success=True, metrics=healthy_metrics)

        assert retrospection_score > 0.6
        assert refiner_quality > 0.6
        assert post_execution_coherence > 0.6
        assert reference_coherence > 0.6

    def test_cross_consumer_all_four_sites_agree_on_unhealthy_input(self):
        """The SAME unhealthy metrics dict trends LOW through all 4 fixed consumers."""
        unhealthy_metrics = {
            "success": True,
            "coherence": 0.75,
            "anomaly_score": _UNHEALTHY_ANOMALY_SCORE,
        }

        retrospection_score = RetrospectionEngine().analyze_execution_result(
            self._unhealthy_result(), "test_skill"
        )["compound_score"]

        refiner_quality = (
            SkillRefiner()._extract_metrics(_unhealthy_execution_result()).quality_score
        )

        po_metrics = dict(unhealthy_metrics)
        PostExecutionOrchestrator(executor=MagicMock())._compute_coherence(po_metrics)
        post_execution_coherence = po_metrics["coherence"]

        reference_coherence = coherence_v1(success=True, metrics=unhealthy_metrics)

        assert retrospection_score < 0.6
        assert refiner_quality < 0.6
        assert post_execution_coherence < 0.6
        assert reference_coherence < 0.6
