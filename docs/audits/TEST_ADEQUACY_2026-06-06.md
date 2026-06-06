---
title: "Test-adequacy spot-check — non-discriminating tests (report-only)"
created: 2026-06-06
owner: "/loop self-improvement (item 5)"
verdict: "2 non-discriminating tests CONFIRMED (1 mutation-proven, 1 structurally proven). Report-only — flagged for STRENGTHENING, never deletion (non-destructive). Candidate list needs per-test mutation-proof before flagging."
policy: "A test is non-discriminating iff, when the source it nominally covers is MUTATED to a wrong-but-plausible impl, the test STILL passes. Grep is a candidate generator; the mutation run is the proof."
---

# Test-adequacy spot-check

## Method
1. **AST scan** — `test_*` functions with zero `assert` / `pytest.raises` / `approx` (a call-only
   test passes unless the call raises).
2. **Weak-value grep** — `assert x is not None` / `isinstance` / `len(...) >= 0` / `.called` only
   (asserts existence/type, not the *right value for the right reason*).
3. **Mutation proof** (the falsifiable gate) — mutate the covered source to a wrong impl, run the
   test; if it still passes it does not discriminate. Grep over-reports (see false positive below),
   so nothing is "flagged" without this step.

## CONFIRMED non-discriminating (2)

### 1. `tests/learning/test_mycelium_registry.py::test_ingest_entry` — MUTATION-PROVEN
Body: `registry.ingest_entry(JournalEntry(...))` + comment `# No crash, internal state updated`.
**Zero asserts.** Proof run (2026-06-06):

| Step | Result |
|---|---|
| baseline | `test_ingest_entry` ✅, `test_audit_synthesizes_from_patterns` ✅ |
| mutate `ingest_entry` → `pass` (drop the entry) | — |
| `test_ingest_entry` under mutation | **✅ STILL PASSES** → does NOT discriminate |
| `test_audit_synthesizes_from_patterns` under mutation | ❌ FAILS → bug IS catchable, by a *different* test |
| revert | clean (git diff empty) |

The suite's real coverage of `ingest_entry` comes from `test_audit…`; `test_ingest_entry` adds zero.
**Strengthen** (additive, not this tick): `assert len(registry._entries) == 1` (or assert the entry
is retrievable). Do NOT delete — it documents intent; give it teeth.

### 2. `tests/cache/test_semantic_embeddings.py::test_semantic_cache_hit_rate_improvement` — STRUCTURALLY PROVEN
Docstring: *"Test that semantic cache achieves better discrimination than hash-based."* Body stores 2
prompts, queries a 3rd, then only `print(...)`s the result + hit counts. **0 asserts, 2 prints, NO skip
decorator (it runs live & green in CI).** A named discrimination test that asserts nothing cannot fail on
any value — it gives false confidence. **Strengthen**: `assert result is not None` AND `assert cache.hits_l2
> 0` (or the expected response), so it actually tests the discrimination its name claims.

## FALSE POSITIVE (why grep alone is insufficient)
`tests/swarm/test_multi_agent_orchestration.py::test_func` — flagged by the AST scan, but `test_func` is a
**nested helper** (`def test_func(x): return x*2`) registered as a tool *inside* a real test that DOES assert
(`assert registry.has_tool("test_func")`, `assert tools[0]["name"] == "test_func"`). Discriminating. The
mutation step is what distinguishes this from a real hollow test.

## Candidate pool (NOT yet flagged — need per-test mutation-proof)
AST no-assert scan surfaced these (some are legitimately assertion-free, e.g. `compile()`-raises tests, or
genuine no-op behaviour tests — each needs the mutation run before flagging):
`test_template_engine::test_generate_all_skills_produce_valid_python` (likely legit — compile raises),
`test_semantic_embeddings::…hit_rate_improvement` (CONFIRMED above), `test_mycelium_registry::test_ingest_entry`
(CONFIRMED above), `graph/test_context_bus::test_record_history_no_history_provider_is_noop` (likely legit —
tests a noop), plus weak-value-assert hot files: `tests/chaos/test_phase_6_chaos.py` (15), `tests/test_swarm.py`
(12), `tests/security/test_agent_auth.py` (12), `tests/compound/test_thermal_predictor.py` (12).

## Recommendation (non-destructive)
Strengthening the 2 confirmed tests is an **additive remediation** (give each a value-assert), tracked as a
follow-on — NOT deletion. The mutation-proof method here is the reusable gate for future test-adequacy ticks.
