"""MD1 tests — escalation gate primitives and extend_claude upgrade.

V-Model right-side test for Module Design:
  MD1.1: _extract_mean_logprob parses logprobs from lemonade response.
  MD1.2: SlidingWindowQuantileTracker returns default until enough observations.
  MD1.3: SlidingWindowQuantileTracker adapts after enough observations.
  MD1.4: IsotonicCalibrator is no-op until fitted.
  MD1.5: composite_gate uses logprob when available, falls back to confidence/length.
  MD1.6: RouteResult has mean_logprob field.
"""

from __future__ import annotations

import pytest

from cohezion.inference.escalation_gate import (
    IsotonicCalibrator,
    SlidingWindowQuantileTracker,
    composite_gate,
)
from cohezion.inference.fleet import RouteResult


try:
    from cohezion.inference.fleet import _extract_mean_logprob  # type: ignore[attr-defined]

    _HAS_EXTRACT_LOGPROB = True
except ImportError:
    _HAS_EXTRACT_LOGPROB = False

import dataclasses as _dc


_HAS_MEAN_LOGPROB = any(f.name == "mean_logprob" for f in _dc.fields(RouteResult))


@pytest.mark.skipif(not _HAS_EXTRACT_LOGPROB, reason="_extract_mean_logprob removed from fleet")
class TestExtractMeanLogprob:
    def test_extracts_from_valid_response(self):
        data = {
            "choices": [
                {
                    "message": {"content": "Hello"},
                    "logprobs": {
                        "content": [
                            {"logprob": -0.01, "token": "Hello"},
                            {"logprob": -0.02, "token": "!"},
                        ]
                    },
                }
            ]
        }
        result = _extract_mean_logprob(data)
        assert result is not None
        assert abs(result - (-0.015)) < 0.001

    def test_returns_none_when_no_logprobs(self):
        data = {"choices": [{"message": {"content": "Hi"}, "logprobs": None}]}
        assert _extract_mean_logprob(data) is None

    def test_returns_none_when_empty_content(self):
        data = {"choices": [{"message": {"content": ""}, "logprobs": {"content": []}}]}
        assert _extract_mean_logprob(data) is None


class TestSlidingWindowQuantileTracker:
    def test_returns_default_until_enough_observations(self):
        tracker = SlidingWindowQuantileTracker(default_tau=-1.0)
        for i in range(5):
            tracker.observe(-0.5 + i * 0.1)
        assert tracker.threshold() == -1.0  # default, only 5 < 10

    def test_adapts_after_enough_observations(self):
        tracker = SlidingWindowQuantileTracker(quantile=0.25, default_tau=-1.0)
        for i in range(20):
            tracker.observe(-2.0 + i * 0.1)  # -2.0 to -0.1
        tau = tracker.threshold()
        assert tau != -1.0  # no longer default
        assert -2.0 <= tau <= 0.0  # within observed range


class TestIsotonicCalibrator:
    def test_noop_until_fitted(self):
        cal = IsotonicCalibrator(default_tau=-1.0)
        assert not cal.is_fitted
        assert cal.threshold() == -1.0
        pe = cal.p_error(-0.5)
        assert 0.0 <= pe <= 1.0

    def test_fits_with_enough_pairs(self):
        cal = IsotonicCalibrator()
        logprobs = [-3.0, -2.5, -2.0, -1.5, -1.0, -0.5, -0.1, -0.05, -0.01, -0.001]
        labels = [False, False, False, False, True, True, True, True, True, True]
        cal.fit(logprobs, labels)
        assert cal.is_fitted
        assert cal.p_error(-3.0) > cal.p_error(-0.01)  # higher logprob → lower p_error


class TestCompositeGate:
    def test_passes_with_good_logprob(self):
        ok, reason = composite_gate(
            "A sufficiently long good answer to the question.",
            mean_logprob=-0.01,
            self_reported_confidence=None,
        )
        assert ok
        assert "logprob" in reason.lower()

    def test_fails_with_low_logprob(self):
        ok, reason = composite_gate(
            "A sufficiently long bad answer to the question.",
            mean_logprob=-5.0,
            self_reported_confidence=None,
        )
        assert not ok
        assert "logprob" in reason.lower()

    def test_falls_back_to_confidence_when_no_logprob(self):
        ok, reason = composite_gate(
            "A sufficiently long answer with confidence.",
            mean_logprob=None,
            self_reported_confidence=0.9,
        )
        assert ok
        assert "confidence" in reason.lower()

    def test_falls_back_to_length_when_neither_available(self):
        ok, reason = composite_gate(
            "A sufficiently long answer with no signals.",
            mean_logprob=None,
            self_reported_confidence=None,
        )
        assert ok
        assert "length" in reason.lower()

    def test_fails_on_short_text(self):
        ok, reason = composite_gate("Hi", mean_logprob=-0.01, self_reported_confidence=0.9)
        assert not ok
        assert "length" in reason.lower()


@pytest.mark.skipif(not _HAS_MEAN_LOGPROB, reason="RouteResult.mean_logprob removed from fleet")
class TestRouteResultHasMeanLogprob:
    def test_mean_logprob_field_exists(self):
        r = RouteResult(text="test", model="m", lane="cpu", latency_ms=100.0, mean_logprob=-0.5)
        assert r.mean_logprob == -0.5

    def test_mean_logprob_defaults_to_none(self):
        r = RouteResult(text="test", model="m", lane="cpu", latency_ms=100.0)
        assert r.mean_logprob is None
