"""Which Lemonade RECIPE enforces a decoding constraint? — an un-mocked boundary fact.

Lemonade publishes NO per-recipe capability matrix, so "does this lane honor `grammar`?" has
to be re-derived by hand every time it matters. This test makes it an executable, CI-enforced
fact instead (.claude/rules/verification-depth.md corrective #3: this bug class is structurally
INVISIBLE to mocks — a mocked orchestrator passes identically whether the backend honors
`grammar` or discards it).

The split is STRUCTURAL, not a config gap:
  - GBNF is a llama.cpp SAMPLER feature, so the `llamacpp` recipe inherits it from its runtime.
  - The `flm` recipe is FastFlowLM — a separate from-scratch NPU runtime, not llama.cpp. Its
    documented request parameters are model/messages/stream/temperature/top_p/presence_penalty:
    no `grammar`, no `response_format`, no guided decoding.

The HAZARD (what the docs do NOT state, and only a probe can show): FastFlowLM does not reject
unknown request fields — it returns 200 OK and silently ignores them. So sending `grammar=` to
the NPU lane yields UNCONSTRAINED output with NO error. A consumer that assumes the constraint
held is silently wrong. That is the behavior pinned below.

Established against Lemonade 11.5.0 (2026-07-28). The version is RECORDED, not asserted — if
FastFlowLM later gains constraint support this test goes red, which is the correct signal.

Skips gracefully when :13305 is unreachable or a required model is not already resident.
The resident check is SAFETY-CRITICAL, not politeness: this box runs below the 16 GB N3 floor,
so a request that triggers an auto-load is an OOM hazard (root harness.md N3).
"""

from __future__ import annotations

import pytest
import requests


BASE_URL = "http://localhost:13305"

# Discriminating grammar: tokens no model would emit naturally for the prompt below. A
# "True"|"False" grammar would pass on EVERY lane regardless of enforcement and prove nothing.
GRAMMAR = 'root ::= "BANANA" | "PENGUIN"'
GRAMMAR_TOKENS = {"BANANA", "PENGUIN"}
PROMPT = "Is 2 + 2 equal to 5? Answer with one word."

# Generous budget: a frugal cap on a thinking model measures TRUNCATION (finish_reason="length",
# empty content), not enforcement — observed while probing Gemma-4-E4B this session.
MAX_TOKENS = 512
# Sized for QUEUEING, not for inference. These two models answer in 3-9s idle, but the request
# queues behind whatever else holds the lane: `status="in_use"` is normal, lemonade serves ~2
# slots per model (-np 2), and pytest-xdist (installed) can fire both lanes at once. A 609s
# inference was measured on this box during a concurrent 3-model run. A too-tight timeout turns
# a busy fleet into a spurious RED, which trains people to ignore this file — the one outcome
# the anti-retirement canary below exists to prevent.
TIMEOUT_S = 300


def _loaded_model_names() -> set[str] | None:
    """Names of models resident on :13305. **None = unreachable; set() = reachable but EMPTY.**

    Those two states must NOT collapse into one value (found by an adversarial review lane,
    2026-07-28). An earlier version returned `set()` for both, and the caller's `if not resident:
    pytest.skip("lemonade :13305 down")` then fired for a router that was UP and healthy but
    reporting zero loaded models — skipping with a message that is factually false, and silently
    retiring the proof. That is the same skip-vs-fail conflation the canary exists to prevent,
    surviving one level down in the helper.


    PRESENCE-based, deliberately NOT status-whitelisted. An earlier version accepted only
    `status in {"ready", "in_use"}` — the two values observed live. A local QA lane flagged that
    an unenumerated transient (e.g. a mid-load "loading") would be read as NOT resident; probing
    :13305 confirmed only those two values *occur in practice* but did NOT let me enumerate the
    full set, so the whitelist rests on an assumption I cannot discharge.

    Membership in `all_models_loaded` IS the residency signal — the field name says so. Failure
    modes are asymmetric and settle it: wrongly INCLUDING a model costs a queued request whose
    error surfaces loudly through the HTTP/timeout assertions below; wrongly EXCLUDING one costs
    a silent skip, or (since the lane check now fails rather than skips) a spurious RED. Prefer
    the loud, self-correcting failure over the quiet, misleading one.
    """
    try:
        r = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        r.raise_for_status()
        payload = r.json()
    except Exception:
        return None  # genuinely unreachable — the only state that justifies a skip
    # Reached the router. A missing/empty `all_models_loaded` is a DEGRADED fleet, not an
    # absent one, so it returns an empty set and the callers fail rather than skip.
    return {m["model_name"] for m in payload.get("all_models_loaded", []) if m.get("model_name")}


# (model_id, expect_enforced) — parametrized so the FALSIFICATION CHECK is a one-token edit:
# change "llama3.2-1b-FLM" below to True (or point the llamacpp id at the flm model) and the
# ENFORCED assertion MUST go red. If it stays green, this test verifies nothing — see
# scripts/ci/dormancy_scan.py --self-test for the same discipline applied to that gate.
LANES = [
    pytest.param("Gemma-4-E4B-it-GGUF", True, id="llamacpp-igpu"),
    pytest.param("llama3.2-1b-FLM", False, id="flm-npu"),
]


def _chat(model_id: str, *, grammar: str | None) -> tuple[int, str]:
    """POST a completion, with or WITHOUT the grammar. Returns (http_status, content).

    The `grammar=None` arm is the CONTROL: it establishes what the model says unprompted by any
    constraint, so the enforced lane is proven by COMPARISON rather than by trusting that the
    grammar tokens are implausible. Raised by an adversarial review lane (deepseek-v4-pro,
    2026-07-28): `out in GRAMMAR_TOKENS` alone cannot distinguish "the constraint was enforced"
    from "the model happened to emit that token".
    """
    payload: dict[str, object] = {
        "model": model_id,
        "messages": [{"role": "user", "content": PROMPT}],
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
    }
    if grammar is not None:
        payload["grammar"] = grammar
    r = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, timeout=TIMEOUT_S)
    status = r.status_code
    try:
        content = r.json()["choices"][0]["message"]["content"] or ""
    except Exception:
        content = ""
    return status, content


def test_rc1_lanes_are_actually_running() -> None:
    """CANARY: fail LOUDLY when the RC1 proof has silently stopped running.

    Found by a local QA lane (Bonsai-27B, 2026-07-28): "SILENT-RETIREMENT: FAIL — the test uses
    pytest.skip when models are missing, which can cause the suite to report success without
    actually verifying the silent-swallow behavior, effectively retiring the proof." Correct: a
    skip on the negative case is INDISTINGUISHABLE from a pass in the summary line, and naming
    the lost lane in the skip message (the first fix) makes it readable, not *loud*.

    The distinction this draws:
      - lemonade DOWN            -> skip. Legitimately untestable (CI without lemonade).
      - lemonade UP, all resident -> the lane tests run. Nothing to report.
      - lemonade UP, model gone   -> FAIL. The instrument is degrading silently; that is a
                                     defect in the instrument, not an absent boundary.

    Same philosophy as scripts/ci/dormancy_scan.py applied to this test itself: a capability
    that stops being exercised must go RED, never quietly green.
    """
    resident = _loaded_model_names()
    if resident is None:
        pytest.skip("lemonade :13305 unreachable — RC1 legitimately untestable, not degraded")

    missing = [p.values[0] for p in LANES if p.values[0] not in resident]
    assert not missing, (
        f"RC1 PROOF IS NOT RUNNING: lemonade :13305 is UP but {missing} is not resident "
        f"(likely LRU-evicted). The lane test(s) will SKIP, and a skip is indistinguishable "
        f"from a pass in the summary — so the constraint-enforcement fact silently stops being "
        f"verified. Pre-load the model with a BOUNDED ctx_size (N3) to restore the proof; do "
        f"not delete this canary. Resident: {sorted(resident)}"
    )


def test_reachable_but_empty_fleet_fails_rather_than_skips(monkeypatch) -> None:
    """DISCRIMINATING: a router that is UP but reports zero models must FAIL, never skip.

    Found by an adversarial review lane (deepseek-v4-pro, 2026-07-28): `_loaded_model_names`
    previously returned `set()` for BOTH 'unreachable' and 'reachable but empty', so the caller's
    `if not resident: skip("lemonade down")` fired on a healthy router — a factually false skip
    that silently retires the proof. The None/set() split fixes it; this test is what would go
    red if anyone collapses them again.
    """
    monkeypatch.setattr(f"{__name__}._loaded_model_names", lambda: set(), raising=True)
    # BaseException, NOT Exception. pytest.skip raises Skipped, which derives from
    # BaseException — so `pytest.raises(Exception)` lets a skip sail straight through and THIS
    # test then reports as "skipped", indistinguishable from a pass. That is the very defect
    # under test, reproduced inside its own guard (caught by falsification, 2026-07-28).
    with pytest.raises(BaseException) as exc:  # narrowed by the two asserts below
        test_rc1_lanes_are_actually_running()
    assert not isinstance(exc.value, pytest.skip.Exception), (
        "a reachable-but-empty fleet took the SKIP path — a degraded fleet is being reported as "
        "'untestable', which is exactly the silent retirement this file exists to prevent"
    )
    assert "RC1 PROOF IS NOT RUNNING" in str(exc.value)


@pytest.mark.parametrize("model_id,expect_enforced", LANES)
def test_recipe_grammar_enforcement(model_id: str, expect_enforced: bool) -> None:
    """llamacpp CONSTRAINS output to the grammar; flm accepts `grammar` and IGNORES it silently."""
    # Probed HERE, not at import: the full tests/inference/ run takes ~110s and this fleet evicts
    # by LRU, so a module-level snapshot goes stale. A stale snapshot would skip a lane that is
    # actually available — and a skip on the flm (negative) case is INDISTINGUISHABLE from a pass
    # in the summary line, silently retiring the silent-swallow proof. That is the exact dormancy
    # failure this file exists to prevent; do not hoist this back to module scope.
    resident = _loaded_model_names()
    lane = "llamacpp/ENFORCED" if expect_enforced else "flm/SILENT-SWALLOW"

    if resident is None:
        pytest.skip(f"[{lane} lane NOT RUN] lemonade :13305 unreachable — un-mocked boundary test")
    # FAIL, not skip. The canary above closes the common case, but it checks residency at ITS
    # execution time: under pytest-xdist (installed) the canary and this lane run on separate
    # workers, so an eviction BETWEEN them leaves the canary green while this lane skips — and a
    # skip is indistinguishable from a pass. Found by a local QA lane (Qwen3-Coder-30B, F1).
    # Checking at the point of USE closes that window; auto-loading is still refused (N3).
    if model_id not in resident:
        pytest.fail(
            f"[{lane}] RC1 PROOF NOT RUNNING: lemonade :13305 is UP but {model_id} is not "
            f"resident (likely LRU-evicted, possibly after the canary passed). Refusing to "
            f"auto-load — N3 OOM hazard below the 16 GB floor. Pre-load it with a BOUNDED "
            f"ctx_size to restore the proof. Resident: {sorted(resident)}"
        )

    status, content = _chat(model_id, grammar=GRAMMAR)
    out = content.strip()

    assert status == 200, f"{model_id}: HTTP {status} — the lane rejected the request outright"

    if expect_enforced:
        # ENFORCEMENT PROOF. Grammar-constrained llama.cpp output can carry leading/trailing
        # whitespace, hence .strip().
        # PAIRED CONTROL: prove enforcement by COMPARISON, not by trusting that the grammar
        # tokens are implausible. The same prompt WITHOUT the grammar must produce something
        # outside the token set; if the unconstrained model also says "BANANA", the constrained
        # result proves nothing and the whole lane is uninformative.
        ctl_status, control = _chat(model_id, grammar=None)
        # Check the control's status + non-emptiness FIRST: a failed control returns "", and
        # "" is trivially outside the token set, so the comparison below would pass VACUOUSLY
        # and prove nothing (adversarial review lane, 2026-07-28).
        assert ctl_status == 200 and control.strip(), (
            f"CONTROL CALL FAILED for {model_id} (HTTP {ctl_status}, content={control.strip()!r}) "
            f"— cannot establish the unconstrained baseline, so the enforcement comparison below "
            f"would be vacuous. Fix the probe before trusting this lane."
        )
        assert control.strip() not in GRAMMAR_TOKENS, (
            f"CONTROL FAILED for {model_id}: unconstrained output {control.strip()!r} is itself "
            f"in {sorted(GRAMMAR_TOKENS)}, so a constrained result cannot demonstrate "
            f"enforcement. Choose grammar tokens the model would never emit for this prompt."
        )
        assert out in GRAMMAR_TOKENS, (
            f"llamacpp lane ({model_id}) did NOT enforce the GBNF grammar: got {out!r}, "
            f"expected one of {sorted(GRAMMAR_TOKENS)}. Either the recipe lost grammar support "
            f"or this request is no longer reaching a llamacpp backend — do not weaken this "
            f"assertion; find out which."
        )
    else:
        # SILENT-FAILURE PROOF. All three clauses are load-bearing: 200 (above) + NON-EMPTY +
        # outside-the-grammar. Without the non-empty clause an empty reply, a truncation, or a
        # dead endpoint would satisfy "not in GRAMMAR_TOKENS" and this would pass while proving
        # nothing (testing-and-verification.md: "absence of error stands in for success").
        assert out, (
            f"flm lane ({model_id}) returned EMPTY content — cannot distinguish "
            f"'ignored the constraint' from 'never answered'. Fix the probe before trusting it."
        )
        # SILENT vs LOUD. A 200 body carrying "Error: unsupported parameter 'grammar'" would also
        # be non-empty and outside the grammar, so the two assertions around this one would read a
        # LOUD in-body rejection as a SILENT swallow — the opposite conclusion. Raised by a local
        # QA lane (Gemma-4-26B). Empirically the lane answers the prompt ('No'), so this guard is
        # cheap insurance against a future FLM that reports errors in the body instead.
        assert not any(
            k in out.lower() for k in ("error", "unsupported", "invalid", "not supported")
        ), (
            f"flm lane ({model_id}) returned what looks like an in-body ERROR: {out!r}. That is a "
            f"LOUD rejection, not the silent swallow RC1 pins — the invariant's premise no longer "
            f"holds. Re-probe the lane and update structured_npu.py + the RC1 invariant."
        )
        assert out not in GRAMMAR_TOKENS, (
            f"flm lane ({model_id}) now HONORS `grammar` (got {out!r}) — FastFlowLM has gained "
            f"constraint support since Lemonade 11.5.0. This RED is correct and actionable: "
            f"update src/cohezion/inference/structured_npu.py, the RC1 invariant in "
            f".claude/rules/harness.md, and the vault report. Do NOT weaken this assertion."
        )
