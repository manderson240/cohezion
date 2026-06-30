"""Behavioral regression gate (FAPO R3) — defends the compound self-improvement loop from QUIET
prompt regression (a skill edit that fixes one case while silently breaking others). run_fn mocked.
"""
from __future__ import annotations

from cohezion.compound.prompt_version_registry import _validate, evaluate_regression


class TestValidator:
    def test_contains_default(self):
        assert _validate("the answer is NEGATIVE", "negative") is True
        assert _validate("POSITIVE", "negative") is False

    def test_exact(self):
        assert _validate(" B ", "B", "exact") is True
        assert _validate("B.", "B", "exact") is False

    def test_regex_and_malformed(self):
        assert _validate("score: 0.95", r"score:\s*\d\.\d+", "regex") is True
        assert _validate("no score", r"score:\s*\d", "regex") is False
        assert _validate("x", "(unclosed", "regex") is True  # malformed → don't block


def _fixtures():
    return [
        {"input": "is 2+2=5?", "expected_output": "no", "critical": True},
        {"input": "say hi", "expected_output": "hi", "critical": True},
    ]


class TestEvaluateRegression:
    def test_all_pass_promotes(self):
        ans = {"is 2+2=5?": "no, that's wrong", "say hi": "hi there"}
        assert evaluate_regression(_fixtures(), "cand", lambda c, i: ans[i]) is True

    def test_critical_regression_blocks(self):
        """Discriminating: a candidate that breaks a CRITICAL fixture is blocked. A no-eval impl
        (always promote → True) fails this."""
        ans = {"is 2+2=5?": "yes!", "say hi": "hi there"}  # first critical fixture regressed
        assert evaluate_regression(_fixtures(), "cand", lambda c, i: ans[i]) is False

    def test_noncritical_failure_allowed(self):
        fx = [{"input": "x", "expected_output": "y", "critical": False}]
        assert evaluate_regression(fx, "cand", lambda c, i: "wrong") is True

    def test_noncritical_error_does_not_block(self):
        """A flaky NON-critical fixture fails OPEN — the passing critical fixture still gates."""
        fx = [
            {"input": "a", "expected_output": "x", "critical": False},  # errors, non-critical
            {"input": "b", "expected_output": "ok", "critical": True},  # passes, critical
        ]

        def run(c, inp):
            if inp == "a":
                raise RuntimeError("flaky")
            return "ok here"

        assert evaluate_regression(fx, "cand", run) is True

    def test_critical_error_fails_closed(self):
        """review #1: a CRITICAL fixture that can't be evaluated → fail-CLOSED even though a
        non-critical one passes (the #8 fix only covered the all-unevaluable case)."""
        fx = [
            {"input": "a", "expected_output": "x", "critical": True},   # errors, CRITICAL
            {"input": "b", "expected_output": "ok", "critical": False},  # passes, non-critical
        ]

        def run(c, inp):
            if inp == "a":
                raise RuntimeError("flaky")
            return "ok"

        assert evaluate_regression(fx, "cand", run) is False

    def test_all_fixtures_unevaluable_fails_closed(self):
        """bughunt #8: well-formed fixtures exist but NONE evaluate (inference down) → fail-CLOSED.
        The old code swallowed all per-fixture errors and returned True (promotion allowed)."""
        def boom(c, i):
            raise RuntimeError("inference down")

        assert evaluate_regression(_fixtures(), "cand", boom) is False

    def test_false_improvement_detected(self):
        """The article's failure mode: aggregate looks OK (1/2 pass) but a CRITICAL category broke."""
        ans = {"is 2+2=5?": "yes", "say hi": "hi"}  # 1 pass, 1 critical fail
        assert evaluate_regression(_fixtures(), "cand", lambda c, i: ans[i]) is False


def test_factory_wires_regression_gate_live():
    """M1: the FAPO R3 gate was DORMANT — _regression_run_fn defaulted None AND was added to the
    wrong class (EnvironmentResponsePredictor), so refine()'s guard would AttributeError if reached.
    Now SkillRefiner owns it and SkillRefinerFactory.create wires a live runner. A dormant gate gives
    the self-improvement loop ZERO behavioral-regression protection."""
    from cohezion.compound.skill_refiner import SkillRefiner, SkillRefinerFactory

    assert hasattr(SkillRefiner(), "_regression_run_fn")          # on the RIGHT class
    assert SkillRefinerFactory.create()._regression_run_fn is not None  # wired LIVE, not dormant


def test_blocked_promotion_recorded_for_review(tmp_path, monkeypatch):
    """HITL/observability surface (2026 Agent Confidence Index #1+#2 levers): a blocked self-mutation
    becomes a visible pending-approval with a 'why', not a silent no-op."""
    from cohezion.compound.skill_refiner import SkillRefiner

    monkeypatch.setattr(SkillRefiner, "_APPROVALS_PATH", tmp_path / "approvals.jsonl")

    class Sig:
        key_insight = "increase cache TTL to 300s"

    sr = SkillRefiner()
    rec = sr._record_blocked_promotion("cache_skill", Sig(), "regression_gate")
    assert rec["reason"] == "regression_gate" and rec["status"] == "pending_review"

    pending = SkillRefiner.get_pending_approvals()
    assert len(pending) == 1
    assert pending[0]["skill"] == "cache_skill" and "cache TTL" in pending[0]["proposed_insight"]


def test_generate_fixture_candidates_parses_local_output():
    """Golden-fixture bootstrap: parse a local model's JSON test cases (Autodata, $0). Robust to
    surrounding prose."""
    from cohezion.compound.prompt_version_registry import generate_fixture_candidates

    def fake_chat(_prompt):
        return ('cases: [{"input":"sort [3,1,2]","expected_output":"[1, 2, 3]","critical":true},'
                '{"input":"x","expected_output":"y","critical":false}] done')

    fx = generate_fixture_candidates("sort_skill", "sorts a list", fake_chat, n=2)
    assert len(fx) == 2
    assert fx[0]["input"] == "sort [3,1,2]" and fx[0]["critical"] is True
    assert fx[0]["validator_type"] == "contains"


def test_generate_fixture_candidates_failsafe():
    from cohezion.compound.prompt_version_registry import generate_fixture_candidates

    def boom(_p):
        raise RuntimeError("lemonade down")

    assert generate_fixture_candidates("s", "p", lambda _p: "no json") == []
    assert generate_fixture_candidates("s", "p", boom) == []
