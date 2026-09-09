"""The adapter must report TRUE generation cost, not the length of what survived stripping.

Guards the fix for the 2026-08-16 measurement failure: `lane_termination_benchmark.py` ranked
lanes by `len(text)`, but for a thinking model outside `_THINKING_MODEL_MARKERS` the adapter
discards `reasoning_content`, so `text` is post-strip. gpt-oss-20b and Nemotron were measured
that way while qwen3/gemma lanes were measured complete, and the resulting cost ranking INVERTED
when re-measured on `usage.completion_tokens`.

Every test here is written to FAIL against the pre-fix adapter, which returned a bare string and
had no notion of either quantity.
"""

from __future__ import annotations

import asyncio

import pytest

from cohezion.inference.gaia_adapter import GaiaAgentTier, _GaiaLLMClientShim
from cohezion.inference.orchestrator import OrchestrationResult


class _FakeClient:
    """Minimal OpenAI-compatible stub. `usage` is the point: it is the provider's own count."""

    def __init__(self, content: str, reasoning: str, completion_tokens: int):
        self._content = content
        self._reasoning = reasoning
        self._tokens = completion_tokens

    def chat_completions(self, **_: object) -> dict:
        return {
            "choices": [
                {"message": {"content": self._content, "reasoning_content": self._reasoning}}
            ],
            "usage": {"completion_tokens": self._tokens},
        }


def _agent(content: str, reasoning: str, tokens: int) -> _GaiaLLMClientShim:
    return _GaiaLLMClientShim(
        client=_FakeClient(content, reasoning, tokens),
        model_id="stub-model",
        max_tokens=4000,
        temperature=0.3,
    )


class TestGenTokenTelemetry:
    def test_zero_before_any_call(self) -> None:
        """A reader before the first prompt() sees 0, not AttributeError."""
        a = _agent("x", "", 1)
        assert a.last_gen_tokens == 0
        assert a.last_dropped_reasoning_chars == 0

    def test_reports_provider_token_count_not_text_length(self) -> None:
        """THE discriminating case: 12 visible chars, 900 generated tokens.

        Any implementation deriving cost from the returned string reports ~12/4 = 3 tokens and
        calls this lane cheap. Only reading usage.completion_tokens gets it right.
        """
        a = _agent(content="VERDICT: no", reasoning="w" * 3000, tokens=900)
        text = a.prompt("q")
        assert text == "VERDICT: no"
        assert a.last_gen_tokens == 900, "must come from usage, not from len(text)"
        assert len(text) < 20 < a.last_gen_tokens

    def test_dropped_reasoning_measured_when_content_present(self) -> None:
        """Reasoning is discarded only when content is non-empty -- that is the strip."""
        a = _agent(content="answer", reasoning="r" * 512, tokens=200)
        a.prompt("q")
        assert a.last_dropped_reasoning_chars == 512

    def test_nothing_dropped_when_reasoning_is_the_answer(self) -> None:
        """Empty content triggers the line-269 fallback: reasoning IS returned, so 0 dropped.

        Discriminating against a naive `len(reasoning)` implementation, which would report 512
        here and double-count text the caller actually received.
        """
        a = _agent(content="", reasoning="r" * 512, tokens=200)
        text = a.prompt("q")
        assert text == "r" * 512
        assert a.last_dropped_reasoning_chars == 0

    def test_inline_stripped_reasoning_is_counted(self) -> None:
        """DISCRIMINATING: counting only the CHANNEL reports 0 here, while ~30 chars were cut.

        A guarded lane returns its reasoning inside `content`, so nothing is dropped from
        `reasoning_content` — but the normaliser still removes it from the returned string. A
        field that reports zero while its own subject is happening is worse than no field: it
        made the benchmark print "no lane had reasoning stripped" for a run in which Qwen3-8B
        had ~2240 chars stripped inline.
        """
        a = _agent(content="<think>a long chain of thought</think>answer", reasoning="", tokens=300)
        text = a.prompt("q")
        assert text == "answer"
        assert a.last_dropped_reasoning_chars == len("<think>a long chain of thought</think>")
        assert a.last_gen_tokens == 300

    def test_nothing_dropped_when_there_is_no_reasoning(self) -> None:
        """The true-zero case, so the field is not merely always-positive."""
        a = _agent(content="a plain answer", reasoning="", tokens=50)
        a.prompt("q")
        assert a.last_dropped_reasoning_chars == 0

    def test_channel_and_inline_are_summed(self) -> None:
        """Both mechanisms at once: reasoning_content dropped AND a think block stripped."""
        a = _agent(content="<think>12345</think>answer", reasoning="r" * 100, tokens=400)
        a.prompt("q")
        assert a.last_dropped_reasoning_chars == 100 + len("<think>12345</think>")


class TestOrchestrationResultPropagation:
    def test_tier_run_propagates_both_fields(self) -> None:
        a = _agent(content="short", reasoning="z" * 700, tokens=850)
        res = asyncio.run(GaiaAgentTier(agent=a, label="stub").run("q"))
        assert isinstance(res, OrchestrationResult)
        assert res.gen_tokens == 850
        assert res.dropped_reasoning_chars == 700

    def test_agent_without_telemetry_reports_zero_not_crash(self) -> None:
        """A real gaia.Agent exposes neither attribute. Duck-typed read must degrade to 0."""

        class _Bare:
            def prompt(self, _: str) -> str:
                return "hello"

        res = asyncio.run(GaiaAgentTier(agent=_Bare(), label="bare").run("q"))
        assert res.text == "hello"
        assert res.gen_tokens == 0
        assert res.dropped_reasoning_chars == 0

    def test_defaults_keep_existing_construction_sites_working(self) -> None:
        """CB16 safe-default: every field added is trailing and optional."""
        res = OrchestrationResult(text="t", primary_model="m", final_model="m", escalation_count=0)
        assert res.gen_tokens == 0
        assert res.dropped_reasoning_chars == 0


@pytest.mark.parametrize("tokens", [0, 1, 12345])
def test_token_count_passes_through_unmodified(tokens: int) -> None:
    a = _agent(content="a", reasoning="", tokens=tokens)
    a.prompt("q")
    assert a.last_gen_tokens == tokens
