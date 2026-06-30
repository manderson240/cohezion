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
    surrounding prose. WIRING H1 anti-poisoning: ``critical`` is forced False regardless of the
    model's self-claim — an auto-generated fixture must not hard-block a promotion."""
    from cohezion.compound.prompt_version_registry import generate_fixture_candidates

    def fake_chat(_prompt):
        return ('cases: [{"input":"sort [3,1,2]","expected_output":"[1, 2, 3]","critical":true},'
                '{"input":"greet","expected_output":"hello","critical":false}] done')

    fx = generate_fixture_candidates("sort_skill", "sorts a list", fake_chat, n=2)
    assert len(fx) == 2
    assert fx[0]["input"] == "sort [3,1,2]"
    assert fx[0]["validator_type"] == "contains"
    # anti-poisoning: model claimed critical=true, but auto-generated fixtures are never critical
    assert fx[0]["critical"] is False
    assert fx[1]["critical"] is False


def test_generate_fixture_candidates_rejects_degenerate_expected_output():
    """WIRING H1 anti-poisoning (discriminating): a degenerate expected_output (<3 non-space chars)
    ``contains``-matches almost any output, so it would NEVER block — a poisoned fixture that
    auto-promotes anything. Reject it. A naive impl that keeps all parsed items fails this."""
    from cohezion.compound.prompt_version_registry import generate_fixture_candidates

    def fake_chat(_p):
        return (
            '[{"input":"a","expected_output":"x","critical":true},'        # 1 char -> rejected
            '{"input":"b","expected_output":"   ","critical":true},'        # whitespace -> rejected
            '{"input":"c","expected_output":"valid answer","critical":true}]'  # kept (forced non-critical)
        )

    fx = generate_fixture_candidates("s", "p", fake_chat, n=3)
    assert len(fx) == 1
    assert fx[0]["input"] == "c" and fx[0]["expected_output"] == "valid answer"
    assert fx[0]["critical"] is False


def test_generate_fixture_candidates_failsafe():
    from cohezion.compound.prompt_version_registry import generate_fixture_candidates

    def boom(_p):
        raise RuntimeError("lemonade down")

    assert generate_fixture_candidates("s", "p", lambda _p: "no json") == []
    assert generate_fixture_candidates("s", "p", boom) == []


class _FakeRegistry:
    """Stand-in for PromptVersionRegistry with an in-memory golden_fixture store, used to prove
    the WIRING H1 fix: refine() bootstraps fixtures from the CURRENT prime before the regression
    gate runs. ``bootstrap_enabled=False`` simulates lemonade/SurrealDB down (population fails)."""

    store: dict[str, list] = {}
    bootstrap_enabled = True

    def check_drift(self, skill, insight):
        return True  # drift gate always allows — isolate the behavioral gate

    def _load_behavioral_fixtures(self, skill):
        return list(_FakeRegistry.store.get(skill, []))

    def bootstrap_fixtures(self, skill, prime, chat_fn=None, n=3):
        if not _FakeRegistry.bootstrap_enabled:
            return 0  # population failed (infra down) -> fixtures stay empty
        # Faithful to the real anti-poisoning contract: auto-generated fixtures are critical=False.
        _FakeRegistry.store.setdefault(skill, []).append(
            {"input": "is 2+2=5?", "expected_output": "no", "validator_type": "contains", "critical": False}
        )
        return 1

    def regression_check(self, skill, candidate, run_fn):
        from cohezion.compound.prompt_version_registry import evaluate_regression

        fx = _FakeRegistry.store.get(skill, [])
        if not fx:
            return True  # no fixtures -> fail-open skip (the DORMANT path)
        return evaluate_regression(fx, candidate, run_fn)


def _drive_refine(monkeypatch, tmp_path, *, bootstrap_enabled):
    """Drive SkillRefiner.refine() to the behavioral regression gate with a stubbed prime file and
    a run_fn that simulates inference being DOWN (raises). With fixtures present this fail-CLOSES
    (blocks); with none it fail-OPENS (promotes). Returns (result, pending_approvals)."""
    from types import SimpleNamespace

    import cohezion.compound.prompt_version_registry as pvr
    from cohezion.compound.skill_refiner import LearningSignal, SkillRefiner

    signal = LearningSignal(
        skill_name="cache_skill",
        operation_type="generate",
        key_insight="increase cache TTL to 300s",
        metric_change="quality +0.1",
        recommendation="raise TTL",
        confidence=0.8,
    )

    _FakeRegistry.store = {}
    _FakeRegistry.bootstrap_enabled = bootstrap_enabled
    monkeypatch.setattr(pvr, "PromptVersionRegistry", _FakeRegistry)
    monkeypatch.setattr(SkillRefiner, "_APPROVALS_PATH", tmp_path / "approvals.jsonl")

    prime = tmp_path / "CACHE_SKILL_PRIME.md"
    prime.write_text("# Cache skill\nDoes caching.\n## Version: 1.0.0\n## Keywords: cache\n")

    sr = SkillRefiner()
    sr._regression_run_fn = lambda candidate, inp: (_ for _ in ()).throw(RuntimeError("inference down"))
    monkeypatch.setattr(sr, "_find_prime_file", lambda name: prime)
    monkeypatch.setattr(sr, "_extract_metrics", lambda res: SimpleNamespace(success=True))
    monkeypatch.setattr(sr, "_generate_learning_signal", lambda s, o, m: signal)
    monkeypatch.setattr(sr, "_persist_refinement_to_vault", lambda *a, **k: None)

    result = sr.refine("cache_skill", "generate", {"success": True})
    return result, SkillRefiner.get_pending_approvals()


def test_population_makes_regression_gate_non_dormant(tmp_path, monkeypatch):
    """WIRING H1 keystone (discriminating): the gate was DORMANT because nothing populated
    golden_fixture, so regression_check always hit its no-fixtures fail-open path. refine() now
    bootstraps fixtures from the CURRENT prime BEFORE the gate. With fixtures present and inference
    down, evaluate_regression fail-CLOSES → promotion BLOCKED + recorded for review.

    CONTROL (bootstrap disabled = infra down): no fixtures populated → gate fail-opens → PROMOTES.
    The original dormant code (no bootstrap caller) behaves like the control in BOTH cases, so it
    fails the blocked-case assertion below — this test discriminates the fix from the bug."""
    # Population succeeds -> gate bites -> blocked
    result, pending = _drive_refine(monkeypatch, tmp_path, bootstrap_enabled=True)
    assert result is None
    assert len(pending) == 1
    assert pending[0]["skill"] == "cache_skill" and pending[0]["reason"] == "regression_gate"


def test_failed_bootstrap_leaves_gate_failopen(tmp_path, monkeypatch):
    """Fail-safe: when bootstrap can't populate fixtures (lemonade/SurrealDB down), the gate stays
    fail-open (no fixtures -> skip) and refine() PROMOTES — population failure must NOT break or
    hard-block the loop."""
    result, pending = _drive_refine(monkeypatch, tmp_path, bootstrap_enabled=False)
    assert result is not None  # promoted (fail-open), not blocked
    assert pending == []
