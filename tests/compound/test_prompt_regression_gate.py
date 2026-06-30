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

    def bootstrap_fixtures(self, skill, prime, chat_fn=None, n=3, ground_fn=None):
        if not _FakeRegistry.bootstrap_enabled:
            return 0  # population failed (infra down) -> fixtures stay empty
        from cohezion.compound.prompt_version_registry import _ground_fixture

        # candidate keyword "cache" (the prime's keyword); GROUND it against the current skill so a
        # confirmed keyword becomes critical=True (real H1 contract). ground_fn=None -> critical=False.
        fx = {"input": "what does this skill do?", "expected_output": "cache",
              "validator_type": "contains", "critical": False}
        if ground_fn is not None:
            fx = _ground_fixture(fx, ground_fn)
            if fx is None:
                return 0  # un-grounded keyword -> dropped
        _FakeRegistry.store.setdefault(skill, []).append(fx)
        return 1

    def regression_check(self, skill, candidate, run_fn):
        from cohezion.compound.prompt_version_registry import evaluate_regression

        fx = _FakeRegistry.store.get(skill, [])
        if not fx:
            return True  # no fixtures -> fail-open skip (the DORMANT path)
        return evaluate_regression(fx, candidate, run_fn)


_KEYSTONE_PRIME = "# Cache skill\nDoes caching.\n## Version: 1.0.0\n## Keywords: cache\n"


def _drive_refine(monkeypatch, tmp_path, *, bootstrap_enabled, run_fn=None):
    """Drive SkillRefiner.refine() to the behavioral regression gate with a stubbed prime file.
    run_fn defaults to simulating inference DOWN (raises); pass a grounded-regression run_fn to test
    the real catch (grounds the CURRENT prime, regresses the candidate → BLOCK). Returns
    (result, pending_approvals)."""
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
    prime.write_text(_KEYSTONE_PRIME)

    sr = SkillRefiner()
    if run_fn is None:
        run_fn = lambda candidate, inp: (_ for _ in ()).throw(RuntimeError("inference down"))  # noqa: E731
    sr._regression_run_fn = run_fn
    monkeypatch.setattr(sr, "_find_prime_file", lambda name: prime)
    monkeypatch.setattr(sr, "_extract_metrics", lambda res: SimpleNamespace(success=True))
    monkeypatch.setattr(sr, "_generate_learning_signal", lambda s, o, m: signal)
    monkeypatch.setattr(sr, "_persist_refinement_to_vault", lambda *a, **k: None)

    result = sr.refine("cache_skill", "generate", {"success": True})
    return result, SkillRefiner.get_pending_approvals()


def test_population_makes_regression_gate_non_dormant(tmp_path, monkeypatch):
    """WIRING H1 keystone done RIGHT (discriminating): refine() bootstraps GROUNDED fixtures from the
    CURRENT skill (inference UP) — the keyword is confirmed in the current output → critical=True — so
    a regressing candidate is BLOCKED. This is the REAL behavioral-regression catch, not the inference-
    outage path the earlier version mistakenly proved.

    DISCRIMINATING: the pre-grounding code forced auto-fixtures critical=False, and evaluate_regression
    only blocks on critical=True, so this exact scenario (inference UP, candidate regresses) PROMOTED
    the regression. A wrong impl that skips grounding makes `result is None` FAIL (it would promote)."""

    def run_fn(candidate, inp):
        # grounding runs the CURRENT prime (== _KEYSTONE_PRIME) → output contains "cache" (keyword
        # grounded, critical=True); the refined candidate differs → output lacks "cache" → REGRESSION.
        return "this skill manages the cache" if candidate == _KEYSTONE_PRIME else "unrelated behavior now"

    result, pending = _drive_refine(monkeypatch, tmp_path, bootstrap_enabled=True, run_fn=run_fn)
    assert result is None  # BLOCKED — a real regression caught with inference UP
    assert len(pending) == 1
    assert pending[0]["skill"] == "cache_skill" and pending[0]["reason"] == "regression_gate"


def test_failed_bootstrap_leaves_gate_failopen(tmp_path, monkeypatch):
    """Fail-safe: when bootstrap can't populate fixtures (lemonade/SurrealDB down), the gate stays
    fail-open (no fixtures -> skip) and refine() PROMOTES — population failure must NOT break or
    hard-block the loop."""
    result, pending = _drive_refine(monkeypatch, tmp_path, bootstrap_enabled=False)
    assert result is not None  # promoted (fail-open), not blocked
    assert pending == []


def test_grounded_bootstrap_makes_gate_block_a_real_regression():
    """H1 done right (the test that should have existed): GROUNDING the fixture keyword against the
    CURRENT skill's actual output makes it critical=True (verified behaviour, not an LLM guess), so the
    gate BLOCKS a real behavioral regression with inference UP — not merely an outage.

    DISCRIMINATING: the pre-fix code forced every auto-fixture critical=False, and evaluate_regression
    only blocks on critical=True, so this exact scenario PROMOTED the regression. A wrong impl that
    skips grounding (critical stays False) makes the final assertion FAIL."""
    from cohezion.compound.prompt_version_registry import PromptVersionRegistry, evaluate_regression

    def current_skill(inp):  # the CURRENT skill's output contains "done" for this input
        return "Task complete: DONE."

    def fake_chat(_prompt):  # the LLM proposes (input, keyword) — keyword is only a CANDIDATE
        return '[{"input":"do the task","expected_output":"done","critical":false}]'

    reg = PromptVersionRegistry()
    captured: list[dict] = []
    reg._write_fixture = lambda skill, fx: (captured.append(fx) or True)  # capture; no SurrealDB

    n = reg.bootstrap_fixtures("s", "a skill", chat_fn=fake_chat, n=1, ground_fn=current_skill)
    assert n == 1
    assert captured[0]["critical"] is True  # grounded (keyword IS in current output) → can hard-block
    assert captured[0]["expected_output"] == "done"

    def candidate_skill(_cand, inp):  # the candidate REGRESSES — no longer produces "done"
        return "Task complete: FAILED."

    # inference is UP (run_fn returns a real string); the candidate diverges from grounded behaviour
    assert evaluate_regression(captured, "candidate", candidate_skill) is False  # BLOCKED


def test_grounding_drops_ungrounded_keyword():
    """A keyword the LLM guessed but the CURRENT skill does NOT produce is un-grounded → DROPPED, not
    written as a false criterion. This is the anti-poisoning guarantee that lets grounded fixtures be
    critical=True safely: only keywords confirmed in real current behaviour survive."""
    from cohezion.compound.prompt_version_registry import PromptVersionRegistry

    def current_skill(_inp):
        return "the sky is blue"

    def fake_chat(_p):  # "purple" is NOT in the current skill's output → must be dropped
        return '[{"input":"x","expected_output":"purple","critical":true}]'

    reg = PromptVersionRegistry()
    captured: list[dict] = []
    reg._write_fixture = lambda skill, fx: (captured.append(fx) or True)

    n = reg.bootstrap_fixtures("s", "p", chat_fn=fake_chat, n=1, ground_fn=current_skill)
    assert n == 0 and captured == []


class TestSafeIdentSlugifyWarning:
    """Review LOW #2: slugification can collide distinct skill names → shared golden_fixture rows.
    Surface it with a warning so collisions are at least visible."""

    def test_slugified_name_logs_warning(self, caplog):
        import logging

        from cohezion.compound.prompt_version_registry import _safe_ident

        with caplog.at_level(logging.WARNING, logger="cohezion.compound.prompt_version_registry"):
            result = _safe_ident("my skill")
        assert result == "my_skill"
        assert any("slugif" in r.message.lower() or "my_skill" in r.message for r in caplog.records), (
            "expected a warning when the name was slugified"
        )

    def test_clean_name_does_not_warn(self, caplog):
        import logging

        from cohezion.compound.prompt_version_registry import _safe_ident

        with caplog.at_level(logging.WARNING, logger="cohezion.compound.prompt_version_registry"):
            result = _safe_ident("my_skill")
        assert result == "my_skill"
        assert not caplog.records, "a name needing no slugification must not warn"


# ── SurrealQL injection class — STRUCTURAL kill via the central safe builder ───────────────────
#
# Goal: no gate/persistence writer hand-builds an interpolated SurrealQL f-string. Every value goes
# through _surql_lit (json.dumps → escapes BOTH quotes AND backslashes → inert), every field name is
# validated as a bare identifier, and time::now() is the ONLY raw expression (via _RawSurql). These
# tests are written FALSIFICATION-FIRST: they fail against the pre-fix hand-built f-strings.

_INJECTION_PAYLOADS = [
    "x'); DROP TABLE golden_fixture; --",   # classic single-quote breakout
    "back\\slash",                           # embedded backslash
    "evil\\",                                # TRAILING backslash — the journey_tracker hole
    "().__class__",                          # python/expr-looking smuggle
    'a"b',                                    # double-quote (json.dumps target delimiter)
    "time::now()",                           # an expression smuggled as a VALUE must stay inert
]


class TestSurqlBuilderUnit:
    """Unit: the builder renders any value inert and validates field names."""

    def test_surql_lit_escapes_quotes_and_backslashes(self):
        import json

        from cohezion.compound.prompt_version_registry import _surql_lit

        for p in _INJECTION_PAYLOADS:
            rendered = _surql_lit(p)
            # json.dumps wraps in DOUBLE quotes and escapes quotes+backslashes → the literal cannot
            # be broken out of. A raw `'{p}'` impl (the wrong one) would NOT equal json.dumps(p).
            assert rendered == json.dumps(p)
            assert rendered.startswith('"') and rendered.endswith('"')
            # discriminating: a trailing backslash must be DOUBLED so the closing quote isn't escaped.
            if p.endswith("\\"):
                assert rendered.endswith('\\\\"'), "trailing backslash must be escaped, literal stays closed"

    def test_surql_set_validates_field_names(self):
        """A non-identifier field NAME (the one spot json.dumps can't cover) must be rejected, not
        interpolated raw. A naive builder that f-strings the key would silently emit injection."""
        from cohezion.compound.prompt_version_registry import _surql_set

        assert _surql_set({"skill_name": "ok"}) == 'skill_name="ok"'
        for bad in ["a=1; DROP", "a b", "a'b", "", "1abc"]:
            try:
                _surql_set({bad: "v"})
            except ValueError:
                continue
            raise AssertionError(f"unsafe field name {bad!r} must raise, not interpolate")

    def test_raw_surql_is_sole_expression_escape_hatch(self):
        """time::now() must be a _RawSurql (developer constant), and a plain string "time::now()"
        must be rendered INERT (quoted), never executed — proving values can't smuggle expressions."""
        from cohezion.compound.prompt_version_registry import _NOW, _RawSurql, _surql_lit

        assert _surql_lit(_RawSurql("time::now()")) == "time::now()"   # passthrough for constants
        assert _surql_lit(_NOW) == "time::now()"
        assert _surql_lit("time::now()") == '"time::now()"'            # a VALUE stays a quoted string


def _capture_writer_query(monkeypatch, call):
    """Run a writer with httpx.post stubbed to capture the emitted SurrealQL (writers fail-open, so
    raising after capture is fine)."""
    import httpx

    captured: dict[str, str] = {}

    def fake_post(url, **kwargs):
        captured["q"] = kwargs.get("content", "")
        raise RuntimeError("stop after capture")

    monkeypatch.setattr(httpx, "post", fake_post)
    # writers fail-open (swallow); loaders re-raise — catch the sentinel either way, query is captured.
    try:
        call()
    except RuntimeError:
        pass
    return captured["q"]


class TestWriterInjectionInert:
    """The actual gate/persistence writers must render adversarial skill-names AND fixture values
    inert — discriminating vs the pre-fix `skill_name='{...}'` / single-quote-wrapped form."""

    def test_write_fixture_renders_payloads_inert(self, monkeypatch):
        import json

        from cohezion.compound.prompt_version_registry import PromptVersionRegistry

        reg = PromptVersionRegistry()
        for p in _INJECTION_PAYLOADS:
            fx = {"input": p, "expected_output": p, "validator_type": "contains", "critical": False}
            q = _capture_writer_query(monkeypatch, lambda fx=fx: reg._write_fixture("bad skill", fx))
            # the payload appears ONLY as a json-escaped (inert) literal — proves the safe builder ran.
            assert json.dumps(p) in q
            # the wrong impl emitted `input='...'` (single-quote wrapped) or `skill_name='...` — gone.
            assert "='" not in q, f"no single-quote-wrapped interpolation allowed: {q!r}"
            # skill_name slug is itself an inert double-quoted literal, never broken out of.
            assert 'skill_name="' in q

    def test_log_run_renders_payload_inert(self, monkeypatch):
        from cohezion.compound.prompt_version_registry import PromptVersionRegistry

        reg = PromptVersionRegistry()
        q = _capture_writer_query(
            monkeypatch, lambda: reg._log_run("x'); DROP TABLE fixture_run; --", 0.5, passed=False)
        )
        assert "='" not in q
        assert 'skill_name="' in q
        # time::now() must remain a RAW expression (the only non-literal), not a quoted string.
        assert "created_at=time::now()" in q and '"time::now()"' not in q

    def test_loaders_use_safe_where_equality(self, monkeypatch):
        from cohezion.compound.prompt_version_registry import PromptVersionRegistry

        reg = PromptVersionRegistry()
        for loader in (reg._load_fixtures, reg._load_behavioral_fixtures):
            q = _capture_writer_query(monkeypatch, lambda loader=loader: loader("x' OR 1=1 --"))
            assert "='" not in q, f"WHERE must not single-quote-interpolate: {q!r}"
            assert 'skill_name="' in q  # inert double-quoted RHS


class TestNoRawInterpolationStructural:
    """Structural regression guard: every writer/loader MUST route through _surql_set and contain NO
    raw single-quoted f-string interpolation. A future regression that hand-builds is caught HERE,
    before it can reach a live DB — discriminating against the exact pre-fix source."""

    def test_every_surql_building_site_routes_through_builder(self):
        """GENERALIZED (residual fix): instead of listing writer functions BY NAME (which silently
        omits a NEW writer like qa_gate._log_gate), walk the AST of BOTH SurrealQL-touching modules
        and assert that EVERY function whose body builds a query (CREATE/UPDATE/WHERE) routes through
        ``_surql_set`` and hand-builds no single-quoted interpolation. A future writer that bypasses
        the safe builder in either module is auto-caught here, before it can reach a live DB."""
        import ast
        import inspect

        import cohezion.compound.prompt_version_registry as pvr
        import cohezion.compound.qa_gate as qg

        MARKERS = ("CREATE ", "UPDATE ", " WHERE ")  # SurrealQL write / filter sites
        offenders: list[str] = []
        checked = 0
        for module in (pvr, qg):
            src = inspect.getsource(module)
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                fsrc = ast.get_source_segment(src, node) or ""
                # strip the docstring so MARKER prose in a docstring isn't mistaken for a query.
                body_src = fsrc
                doc = ast.get_docstring(node)
                if doc:
                    body_src = body_src.replace(doc, "", 1)
                if not any(m in body_src for m in MARKERS):
                    continue
                checked += 1
                if "_surql_set" not in body_src:
                    offenders.append(f"{module.__name__}.{node.name} builds SurrealQL without _surql_set")
                if "='{" in body_src or "= '{" in body_src:
                    offenders.append(f"{module.__name__}.{node.name} hand-builds single-quoted interpolation")

        # the 4 registry writers/loaders + qa_gate._log_gate = at least 5 covered sites.
        assert checked >= 5, f"expected >=5 SurrealQL-building sites, found {checked}"
        assert not offenders, offenders
