"""BMAD qa_gate P0 — risk-weighted 4-state ADVISORY gate tests (falsification-first).

Written BEFORE the implementation (watched RED) per verification-depth.md. Every behavioral
test is DISCRIMINATING: it FAILS for the most plausible wrong implementation (a no-op evaluate
that always returns PASS, an impl that ignores the risk band, a consumer that is never called).
"""

from __future__ import annotations

from types import SimpleNamespace


# ── ported BMAD risk model (risk-governance.md: probability×impact = 1-9) ──────────────────────


class TestRiskScorePort:
    def test_score_is_probability_times_impact(self):
        from cohezion.compound.qa_gate import RiskScore

        assert RiskScore(3, 3).score == 9
        assert RiskScore(1, 1).score == 1
        assert RiskScore(2, 3).score == 6

    def test_band_thresholds_match_classifyRiskLevel(self):
        from cohezion.compound.qa_gate import RiskScore

        assert RiskScore(3, 3).band == "CRITICAL"  # 9
        assert RiskScore(2, 3).band == "HIGH"  # 6
        assert RiskScore(2, 2).band == "MEDIUM"  # 4
        assert RiskScore(1, 2).band == "LOW"  # 2

    def test_requires_mitigation_at_six(self):
        from cohezion.compound.qa_gate import RiskScore

        assert RiskScore(2, 3).requires_mitigation is True  # 6
        assert RiskScore(2, 2).requires_mitigation is False  # 4


# ── 4-state decision mapping (gate-decision-engine.ts evaluateGate) ────────────────────────────

_CRIT = {
    "input": "what does it do",
    "expected_output": "cache",
    "validator_type": "contains",
    "critical": True,
}
_NONCRIT = {
    "input": "what does it do",
    "expected_output": "cache",
    "validator_type": "contains",
    "critical": False,
}


class TestEvaluateDecision:
    def test_clean_low_risk_is_pass(self):
        from cohezion.compound import qa_gate

        rec = qa_gate.evaluate(
            "s", "cand", lambda c, i: "this is the cache layer", fixtures=[_CRIT]
        )
        assert rec.decision == "PASS"
        assert rec.fixtures_total == 1 and rec.fixtures_passed == 1

    def test_gate_record_fail_matches_binary_block(self):
        """#2 NAMED: a candidate regressing a CRITICAL fixture → decision=='FAIL' AND legacy
        evaluate_regression(...)==False. A no-op evaluate (always PASS) FAILS this test."""
        from cohezion.compound import qa_gate
        from cohezion.compound.prompt_version_registry import evaluate_regression

        run_fn = lambda c, i: "totally unrelated output"  # noqa: E731
        legacy = evaluate_regression([_CRIT], "cand", run_fn)
        rec = qa_gate.evaluate("s", "cand", run_fn, fixtures=[_CRIT])
        assert legacy is False  # the binary gate blocks
        assert rec.decision == "FAIL"  # the advisory gate agrees

    def test_noncritical_only_issue_is_concerns(self):
        from cohezion.compound import qa_gate
        from cohezion.compound.prompt_version_registry import evaluate_regression

        run_fn = lambda c, i: "totally unrelated output"  # noqa: E731
        # non-critical failure does NOT block the binary gate, but IS a CONCERN.
        assert evaluate_regression([_NONCRIT], "cand", run_fn) is True
        rec = qa_gate.evaluate("s", "cand", run_fn, fixtures=[_NONCRIT])
        assert rec.decision == "CONCERNS"

    def test_score_nine_mandates_fail_even_when_clean(self):
        """risk-governance.md: 'Scores = 9 mandate gate failure.' Even a clean run FAILs at score 9."""
        from cohezion.compound import qa_gate
        from cohezion.compound.qa_gate import RiskScore

        rec = qa_gate.evaluate(
            "s", "cand", lambda c, i: "cache", fixtures=[_CRIT], risk=RiskScore(3, 3)
        )
        assert rec.decision == "FAIL"

    def test_clean_high_risk_band_is_concerns_discriminating(self):
        """DISCRIMINATING: a clean run at risk score 6 (HIGH, demands mitigation) → CONCERNS, NOT
        PASS. A wrong impl that ignores the risk band returns PASS here and FAILS this test."""
        from cohezion.compound import qa_gate
        from cohezion.compound.qa_gate import RiskScore

        rec = qa_gate.evaluate(
            "s", "cand", lambda c, i: "cache", fixtures=[_CRIT], risk=RiskScore(2, 3)
        )
        assert rec.decision == "CONCERNS"

    def test_clean_with_authorized_waiver_is_waived(self):
        from cohezion.compound import qa_gate

        rec = qa_gate.evaluate(
            "s", "cand", lambda c, i: "cache", fixtures=[_CRIT], waiver="qa-lead"
        )
        assert rec.decision == "WAIVED"
        assert rec.waiver == "qa-lead"

    def test_critical_regress_outranks_waiver(self):
        """gate-decision-engine.ts orders FAIL before WAIVED — a waiver cannot rescue a critical regress."""
        from cohezion.compound import qa_gate

        rec = qa_gate.evaluate("s", "cand", lambda c, i: "nope", fixtures=[_CRIT], waiver="qa-lead")
        assert rec.decision == "FAIL"


# ── ADVISORY fail-open: no SurrealDB / table absent must never raise ───────────────────────────


class TestAdvisoryFailOpen:
    def test_evaluate_returns_record_when_db_absent(self, monkeypatch):
        import httpx

        from cohezion.compound import qa_gate

        def boom(*a, **k):
            raise RuntimeError("qa_gate table absent / SurrealDB down")

        monkeypatch.setattr(httpx, "post", boom)  # both load + log paths blow up
        rec = qa_gate.evaluate("s", "cand", lambda c, i: "cache", fixtures=[_CRIT])
        assert rec.decision in {"PASS", "CONCERNS", "FAIL", "WAIVED"}  # never raised


# ── #3 PARAMETERIZED WRITE: the qa_gate writer routes through the reused safe builder ───────────


class TestWriterInert:
    def test_log_gate_renders_payload_inert(self, monkeypatch):
        import json

        import httpx

        from cohezion.compound.qa_gate import GateRecord, RiskScore, _log_gate

        captured: dict[str, str] = {}

        def fake_post(url, **kwargs):
            captured["q"] = kwargs.get("content", "")
            raise RuntimeError("stop after capture")

        monkeypatch.setattr(httpx, "post", fake_post)
        rec = GateRecord(
            decision="FAIL",
            risk=RiskScore(3, 3),
            fixtures_total=2,
            fixtures_passed=1,
            rationale="x'); DROP TABLE qa_gate; --",
        )
        _log_gate("bad skill'; DROP", rec)  # fail-open: swallows the RuntimeError, query captured

        q = captured["q"]
        assert q.startswith("CREATE qa_gate SET ")
        assert "='" not in q, f"no single-quote-wrapped interpolation: {q!r}"
        assert 'skill_name="' in q  # slug is an inert double-quoted literal
        assert json.dumps(rec.rationale) in q  # adversarial rationale rendered inert
        # time::now() must remain a RAW expression, not a quoted string.
        assert "created_at=time::now()" in q and '"time::now()"' not in q


# ── #1 CONSUMPTION: refine() must CALL qa_gate.evaluate (real production consumer) ──────────────


def _drive_refine_to_qa_gate(monkeypatch, tmp_path, run_fn):
    """Drive SkillRefiner.refine() down the success path to the qa_gate advisory seam, with the
    behavioral gate stubbed so we isolate the qa_gate call."""
    import cohezion.compound.prompt_version_registry as pvr
    from cohezion.compound.skill_refiner import LearningSignal, SkillRefiner

    class _Reg:
        def check_drift(self, skill, insight):
            return True

        def _load_behavioral_fixtures(self, skill):
            return []

        def bootstrap_fixtures(self, *a, **k):
            return 0

        def regression_check(self, skill, candidate, rf):
            return True

    monkeypatch.setattr(pvr, "PromptVersionRegistry", _Reg)

    signal = LearningSignal(
        skill_name="s",
        operation_type="generate",
        key_insight="increase cache TTL",
        metric_change="quality +0.1",
        recommendation="raise TTL",
        confidence=0.8,
    )
    prime = tmp_path / "S_PRIME.md"
    prime.write_text("# s skill\nDoes a thing.\n## Version: 1.0.0\n## Keywords: thing\n")

    sr = SkillRefiner()
    sr._regression_run_fn = run_fn
    monkeypatch.setattr(sr, "_find_prime_file", lambda name: prime)
    monkeypatch.setattr(sr, "_extract_metrics", lambda res: SimpleNamespace(success=True))
    monkeypatch.setattr(sr, "_generate_learning_signal", lambda s, o, m: signal)
    monkeypatch.setattr(sr, "_persist_refinement_to_vault", lambda *a, **k: None)
    monkeypatch.setattr(sr, "_ensure_golden_fixtures", lambda *a, **k: None)
    return sr.refine("s", "generate", {"success": True})


def test_refine_consumes_qa_gate_evaluate(monkeypatch, tmp_path):
    """#1 DISCRIMINATING CONSUMPTION: refine() must call qa_gate.evaluate. Neutralizing the call
    (deleting the seam in refine) makes spy.called False → this test FAILS."""
    from unittest.mock import MagicMock

    import cohezion.compound.qa_gate as qa_gate
    from cohezion.compound.qa_gate import GateRecord, RiskScore

    spy = MagicMock(return_value=GateRecord("PASS", RiskScore(2, 2), 0, 0, "ok"))
    monkeypatch.setattr(qa_gate, "evaluate", spy)

    _drive_refine_to_qa_gate(monkeypatch, tmp_path, run_fn=lambda c, i: "out")

    assert spy.called, "refine() must call qa_gate.evaluate (the ADVISORY consumption seam)"
    assert spy.call_args.args[0] == "s"  # called with the real skill_name refine constructed


def test_refine_qa_gate_failure_does_not_break_refine(monkeypatch, tmp_path):
    """ADVISORY guarantee: a raising qa_gate.evaluate must NOT break refine() (still promotes)."""
    import cohezion.compound.qa_gate as qa_gate

    def boom(*a, **k):
        raise RuntimeError("advisory failure")

    monkeypatch.setattr(qa_gate, "evaluate", boom)
    result = _drive_refine_to_qa_gate(monkeypatch, tmp_path, run_fn=lambda c, i: "out")
    assert result is not None  # refine still promoted despite advisory failure
