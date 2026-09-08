"""The categorical fast path: route provably-categorical work to the 1B NPU tier.

`make_local_execute_fn` used `build_reasoning_orchestrator` for everything --
deepseek-r1 8B on the NPU. That was a deliberate workaround for
`build_triune_omni_orchestrator`'s `min_chars=500` gate, which guaranteed 100%
escalation on short answers. The per-task `gate_chars` override added later
neutralises that gate, making the workaround stale.

Measured 2026-08-29 on the production path, same three categorical prompts:

    before (deepseek-r1 8B):  15.4s / 16.5s / 12.0s, CoT leakage + markdown
    after  (llama3.2-1b):      1.1s /  0.4s /  0.4s, clean 'Yes'/'Positive'/'Paris'

These tests lock the SELECTION rule, not the latency -- latency is measured in
the report. The rule matters because routing a reasoning task to a 1B model
would quietly destroy answer quality.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import cohezion.compound.local_inference as li


def _reset_singletons() -> None:
    li._orchestrator = None
    li._categorical_orchestrator = None


def _run(prompt: str):
    """Run execute_fn with both orchestrators mocked; return the one used."""
    _reset_singletons()
    reasoning, categorical = MagicMock(name="reasoning"), MagicMock(name="categorical")

    async def _fake_run(*_a, **_kw):
        result = MagicMock()
        result.text = "ok"
        result.final_model = "m"
        result.escalation_count = 0
        result.cost_usd = 0.0
        result.error = None
        return result

    reasoning.run = _fake_run
    categorical.run = _fake_run

    # Set the module SINGLETON rather than patching `_get_orchestrator`.
    # The fast path only engages when `orch is _orchestrator` (the mock guard
    # that keeps a patched getter authoritative), so a test that patches the
    # getter would make the fast path stand down and measure nothing. Assigning
    # the singleton is also closer to production, where `_get_orchestrator()`
    # returns exactly that object.
    li._orchestrator = reasoning

    with patch.object(li, "_get_categorical_orchestrator", return_value=categorical) as cat_get:
        fn = li.make_local_execute_fn()
        assert fn is not None
        fn(prompt)
        return "categorical" if cat_get.called else "reasoning"


def test_t2_categorical_prompt_uses_the_fast_1b_path() -> None:
    """DISCRIMINATING: before the change every prompt used the 8B reasoning path."""
    assert _run("Answer with one word only. Is Python a programming language?") == "categorical"


def test_t2_reasoning_prompt_keeps_the_8b_path() -> None:
    """DISCRIMINATING: an impl routing everything to the 1B destroys reasoning quality.

    This is the guard that makes the optimisation safe -- only provably
    categorical work moves.
    """
    prompt = (
        "Analyse the trade-offs between optimistic and pessimistic concurrency "
        "control in a distributed database, covering failure modes, latency "
        "under contention, and when each is preferable. Explain your reasoning."
    )
    assert _run(prompt) == "reasoning"


def test_t2_short_answer_is_not_fast_pathed() -> None:
    """short_answer can legitimately be a sentence, so it keeps the larger model."""
    assert _run("In one sentence, what does the HIHO stability principle optimize for?") == (
        "reasoning"
    )


def test_t2_explicit_orchestrator_injection_still_wins() -> None:
    """A caller-supplied orchestrator must not be silently replaced."""
    _reset_singletons()
    injected = MagicMock(name="injected")

    async def _fake_run(*_a, **_kw):
        r = MagicMock()
        r.text, r.final_model, r.escalation_count, r.cost_usd, r.error = "ok", "m", 0, 0.0, None
        return r

    injected.run = _fake_run

    with patch.object(li, "_get_categorical_orchestrator") as cat_get:
        fn = li.make_local_execute_fn(orchestrator=injected)
        assert fn is not None
        fn("Answer with one word only. Is Python a programming language?")
        assert not cat_get.called, "explicit orchestrator must take precedence"


def test_t2_patching_get_orchestrator_still_controls_routing() -> None:
    """REGRESSION (CI, 2026-08-29): the fast path bypassed the documented mock seam.

    Callers and tests control routing by patching `_get_orchestrator`. The first
    version of the fast path resolved its orchestrator through a DIFFERENT
    function, so a patched `_get_orchestrator` was ignored and a suite that
    believed itself fully mocked issued REAL inference calls --
    tests/unit/compound/test_local_inference.py went red on main with a live
    model's answer where the mock's string belonged.

    DISCRIMINATING: removing the `orch is _orchestrator` guard makes this fail.
    """
    _reset_singletons()

    async def _fake_run(*_a, **_kw):
        r = MagicMock()
        r.text, r.final_model, r.escalation_count, r.cost_usd, r.error = (
            "MOCKED",
            "m",
            0,
            0.0,
            None,
        )
        return r

    mocked = MagicMock(name="patched-get_orchestrator")
    mocked.run = _fake_run

    with (
        patch.object(li, "_get_orchestrator", return_value=mocked),
        patch.object(li, "_get_categorical_orchestrator") as cat_get,
    ):
        fn = li.make_local_execute_fn()
        assert fn is not None
        out = fn("Answer with one word only. Is Python a programming language?")

    text = out[0] if isinstance(out, tuple) else out
    assert text == "MOCKED", "a patched _get_orchestrator must win"
    assert not cat_get.called, "the fast path must stand down when the seam is patched"


def test_t1_categorical_orchestrator_is_a_separate_singleton() -> None:
    _reset_singletons()
    assert li._categorical_orchestrator is None
    assert hasattr(li, "_get_categorical_orchestrator")


# ---------------- KNOWN LIMITATION, pinned deliberately ----------------


def test_known_limitation_arithmetic_in_categorical_clothing() -> None:
    """Arithmetic phrased with a one-word instruction takes the FAST path.

    MEASURED 2026-08-29: "Respond with one word: yes or no. Is 7 a prime
    number?" returned 'No' on the 1B fast path (wrong -- 7 is prime). The 8B
    reasoning path answered correctly. Accuracy over one 8-prompt cycle was
    7/8 fast vs 8/8 slow, at 0.4s vs 19.1s median.

    WHY: `task_classifier` routes on FORM. An explicit one-word instruction
    fires the categorical override, which by design "always overrides ANY GPU
    signals" so that "reply with one word" beats "implement this:...". A
    question needing computation therefore bypasses `math_reasoning` routing.

    This test PINS the behaviour rather than asserting it is correct. It is an
    acceptable trade for tier-0 routing/classification (the fast path's actual
    job) and a real hazard for factual QA that requires computation. If the
    routing is ever narrowed to exclude arithmetic, this test should flip and
    the docstring should be rewritten -- not deleted.
    """
    assert _run("Respond with one word: yes or no. Is 7 a prime number?") == "categorical"
