"""Unit tests for AutoDQA — Automated Design Quality Assurance."""

from __future__ import annotations

from unittest.mock import patch

from cohezion.compound.autodqa import AutoDQA, DQAResult


class TestDQAResult:
    def test_hiho_coherent_in_band(self):
        from cohezion.inference.quality_eval import QualityVerdict

        r = DQAResult("id1", "desc", "categorical", QualityVerdict(True, 0.5, "ok"), "npu")
        assert r.hiho_coherent is True

    def test_hiho_coherent_below_band(self):
        from cohezion.inference.quality_eval import QualityVerdict

        r = DQAResult("id2", "desc", "code", QualityVerdict(False, 0.2, "fail"), "igpu")
        assert r.hiho_coherent is False

    def test_quality_band_below(self):
        from cohezion.inference.quality_eval import QualityVerdict

        r = DQAResult("id3", "desc", "code", QualityVerdict(False, 0.1, "fail"), "igpu")
        assert r.quality_band == "BELOW_HIHO"

    def test_quality_band_equilibrium(self):
        from cohezion.inference.quality_eval import QualityVerdict

        r = DQAResult("id4", "desc", "categorical", QualityVerdict(True, 0.5, "ok"), "npu")
        assert r.quality_band == "HIHO_EQUILIBRIUM"

    def test_quality_band_above(self):
        from cohezion.inference.quality_eval import QualityVerdict

        r = DQAResult("id5", "desc", "categorical", QualityVerdict(True, 0.9, "ok"), "npu")
        assert r.quality_band == "ABOVE_HIHO"


class TestAutoDQA:
    def test_evaluate_code_output(self):
        dqa = AutoDQA(persist=False, notify_on_reject=False)
        result = dqa.evaluate("def add(a, b): return a + b", "write a Python function")
        assert isinstance(result, DQAResult)
        assert result.verdict.accept is True
        assert result.output_type in ("code", "medium_generation", "unknown")

    def test_evaluate_categorical_output(self):
        dqa = AutoDQA(persist=False, notify_on_reject=False)
        result = dqa.evaluate("yes", "Is this a test? Reply yes or no.")
        assert isinstance(result, DQAResult)
        assert result.verdict.accept is True

    def test_evaluate_empty_output_rejected(self):
        dqa = AutoDQA(persist=False, notify_on_reject=False)
        result = dqa.evaluate("", "classify this text")
        assert result.verdict.accept is False

    def test_batch_evaluate_returns_list(self):
        dqa = AutoDQA(persist=False, notify_on_reject=False)
        pairs = [
            ("def f(): pass", "write a function"),
            ("yes", "is this a test?"),
        ]
        results = dqa.batch_evaluate(pairs)
        assert len(results) == 2
        assert all(isinstance(r, DQAResult) for r in results)

    def test_session_summary_empty(self):
        dqa = AutoDQA(persist=False, notify_on_reject=False)
        s = dqa.session_summary()
        assert s["total"] == 0

    def test_session_summary_with_results(self):
        dqa = AutoDQA(persist=False, notify_on_reject=False)
        dqa.evaluate("def f(): pass", "write a function")
        dqa.evaluate("yes", "reply yes or no")
        s = dqa.session_summary()
        assert s["total"] == 2
        assert 0.0 <= s["avg_score"] <= 1.0

    def test_daily_digest_noop_without_creds(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        dqa = AutoDQA(persist=False, notify_on_reject=False)
        dqa.evaluate("def f(): pass", "write a function")
        dqa.daily_digest()  # must not raise

    def test_alert_sent_on_reject(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "99")
        calls = []

        with patch("cohezion.compound.telegram_notify.httpx") as mock_httpx:
            mock_httpx.post.side_effect = lambda *a, **kw: calls.append(kw)
            dqa = AutoDQA(persist=False, notify_on_reject=True)
            dqa.evaluate("", "classify this")  # empty → reject

        assert len(calls) >= 1  # notification fired

    def test_persist_failure_is_noop(self):
        dqa = AutoDQA(persist=True, notify_on_reject=False)
        with patch(
            "cohezion.compound.autodqa.AutoDQA._persist_result",
            side_effect=RuntimeError("db down"),
        ):
            result = dqa.evaluate("def f(): pass", "write a function")
        # persist failure must not prevent evaluation
        assert isinstance(result, DQAResult)

    def test_i5_structural_invariant(self):
        """I5: AutoDQA must evaluate code correctly."""
        dqa = AutoDQA(persist=False, notify_on_reject=False)
        r = dqa.evaluate("def add(a, b): return a + b", "write a Python function")
        assert r.verdict.accept is True, f"Expected accept, got {r.verdict}"
