"""Tests for MakerCheckerVerifier (lushbinary Maker-Checker split pattern).

Verifies the asymmetric verification design without requiring a live Lemonade
instance. All HTTP calls are mocked at urllib.request.urlopen.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from cohezion.compound.maker_checker import (
    CheckerResult,
    MakerCheckerVerifier,
    build_maker_checker,
)


class TestCheckerResult:
    def test_to_metrics_dict_keys(self):
        r = CheckerResult(
            verdict="pass",
            confidence=0.9,
            reason="looks good",
            latency_seconds=0.5,
            model="test-model",
        )
        d = r.to_metrics_dict()
        assert set(d.keys()) == {
            "checker_verdict",
            "checker_confidence",
            "checker_reason",
            "checker_latency_s",
            "checker_model",
        }
        assert d["checker_verdict"] == "pass"
        assert d["checker_confidence"] == 0.9

    def test_default_verdict_is_skipped(self):
        r = CheckerResult()
        assert r.verdict == "skipped"


class TestMakerCheckerVerifierDisabled:
    def test_disabled_returns_skipped(self):
        verifier = MakerCheckerVerifier(enabled=False)
        result = verifier.verify("do X", "did X")
        assert result.verdict == "skipped"
        assert "disabled" in result.reason

    def test_disabled_verify_async_returns_skipped(self):
        verifier = MakerCheckerVerifier(enabled=False)
        result = verifier.verify_async("do X", "did X")
        assert result.verdict == "skipped"


class TestMakerCheckerVerifierHTTP:
    """Mock HTTP responses to test the full parse path."""

    def _mock_urlopen(self, response_text: str):
        """Return a context-manager mock for urllib.request.urlopen."""
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps(
            {"choices": [{"message": {"content": response_text}}]}
        ).encode()
        return mock_resp

    @patch("cohezion.compound.maker_checker.urllib.request.urlopen")
    def test_pass_verdict_parsed(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen(
            '{"verdict": "pass", "confidence": 0.95, "reason": "output matches task"}'
        )
        v = MakerCheckerVerifier()
        r = v.verify("Write hello world", "print('hello world')")
        assert r.verdict == "pass"
        assert r.confidence == 0.95
        assert "matches" in r.reason

    @patch("cohezion.compound.maker_checker.urllib.request.urlopen")
    def test_fail_verdict_parsed(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen(
            '{"verdict": "fail", "confidence": 0.8, "reason": "output does not address task"}'
        )
        v = MakerCheckerVerifier()
        r = v.verify("Summarize in one sentence", "Here is a long essay...")
        assert r.verdict == "fail"
        assert r.confidence == 0.8

    @patch("cohezion.compound.maker_checker.urllib.request.urlopen")
    def test_partial_verdict_parsed(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen(
            '{"verdict": "partial", "confidence": 0.6, "reason": "partially addressed"}'
        )
        v = MakerCheckerVerifier()
        r = v.verify("task", "output")
        assert r.verdict == "partial"

    @patch("cohezion.compound.maker_checker.urllib.request.urlopen")
    def test_json_wrapped_in_markdown(self, mock_urlopen):
        """Checker model may wrap JSON in markdown code block."""
        mock_urlopen.return_value = self._mock_urlopen(
            '```json\n{"verdict": "pass", "confidence": 0.7, "reason": "ok"}\n```'
        )
        v = MakerCheckerVerifier()
        r = v.verify("task", "output")
        assert r.verdict == "pass"

    @patch("cohezion.compound.maker_checker.urllib.request.urlopen")
    def test_unknown_verdict_becomes_error(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen(
            '{"verdict": "maybe", "confidence": 0.5, "reason": "unsure"}'
        )
        v = MakerCheckerVerifier()
        r = v.verify("task", "output")
        assert r.verdict == "error"

    @patch("cohezion.compound.maker_checker.urllib.request.urlopen")
    def test_confidence_clamped_to_range(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen(
            '{"verdict": "pass", "confidence": 1.5, "reason": "very sure"}'
        )
        v = MakerCheckerVerifier()
        r = v.verify("task", "output")
        assert r.confidence <= 1.0
        assert r.confidence >= 0.0

    def test_network_error_returns_error_verdict(self):
        """HTTP failure must not propagate — returns error verdict instead."""
        import urllib.error

        with patch(
            "cohezion.compound.maker_checker.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            v = MakerCheckerVerifier()
            r = v.verify("task", "output")
        assert r.verdict == "error"
        assert "URLError" in r.reason or "error" in r.verdict

    def test_unparseable_response_returns_error(self):
        with patch(
            "cohezion.compound.maker_checker.urllib.request.urlopen",
        ) as mock_urlopen:
            mock_urlopen.return_value = self._mock_urlopen("not json at all")
            v = MakerCheckerVerifier()
            r = v.verify("task", "output")
        assert r.verdict == "error"
        assert "unparseable" in r.reason


class TestMakerCheckerVerifyAsync:
    @patch("cohezion.compound.maker_checker.urllib.request.urlopen")
    def test_async_returns_result_when_fast(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps(
            {
                "choices": [
                    {"message": {"content": '{"verdict":"pass","confidence":0.9,"reason":"ok"}'}}
                ]
            }
        ).encode()
        mock_urlopen.return_value = mock_resp

        v = MakerCheckerVerifier(timeout_seconds=5.0)
        r = v.verify_async("task", "output", timeout=5.0)
        assert r.verdict == "pass"

    def test_async_returns_skipped_on_timeout(self):
        """A very slow checker must return skipped, not block indefinitely."""
        import time

        def slow_urlopen(*_args, **_kwargs):
            time.sleep(10)

        with patch(
            "cohezion.compound.maker_checker.urllib.request.urlopen",
            side_effect=slow_urlopen,
        ):
            v = MakerCheckerVerifier(timeout_seconds=0.1)
            r = v.verify_async("task", "output", timeout=0.1)
        assert r.verdict in {"skipped", "error"}


class TestBuildMakerChecker:
    def test_build_returns_verifier(self):
        v = build_maker_checker()
        assert isinstance(v, MakerCheckerVerifier)
        assert v.lemonade_url == "http://localhost:13305"
        assert v.enabled is True

    def test_build_disabled(self):
        v = build_maker_checker(enabled=False)
        assert v.enabled is False

    def test_metrics_dict_integrates_cleanly(self):
        """Verify the metrics dict keys don't collide with standard executor metrics."""
        r = CheckerResult(
            verdict="pass", confidence=0.9, reason="ok", latency_seconds=0.5, model="m"
        )
        d = r.to_metrics_dict()
        # These keys are NEW — not used elsewhere in the standard pipeline
        for key in d:
            assert key.startswith("checker_"), f"Unexpected key: {key}"
