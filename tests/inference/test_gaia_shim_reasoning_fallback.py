"""Discriminating tests for _GaiaLLMClientShim's reasoning_content fallback (defect 4dd925b0081f).

WHY THESE EXIST. `build_gaia_llm_tier` sets ``reasoning_format="none"`` for thinking models, but
only for ids matching the ``_THINKING_MODEL_MARKERS`` substring list. Any thinking model NOT on
that list returns ``content=""`` with the whole answer in ``reasoning_content`` — and every
caller reads "" as "no answer". `skill_refiner`'s adversarial gate reads it as fail-open APPROVE,
i.e. a gate that cannot fail.

Verified live 2026-07-28: ``Bonsai-27B-gguf`` matches no marker and returned
``finish_reason='length', content=0, reasoning_content=456``. It scored 0/8 on a code-review
benchmark purely as a harness artifact — the model was answering, the shim was discarding it.

The fallback makes the marker list an optimisation rather than a correctness dependency. Both
tests below FAIL against the pre-fix implementation (`return msg.get("content", "") or ""`).
"""

from __future__ import annotations

from cohezion.inference.gaia_adapter import _GaiaLLMClientShim


class _FakeClient:
    """Minimal stand-in for LemonadeClient — returns whatever message body we hand it."""

    def __init__(self, message: dict[str, str]):
        self._message = message
        self.calls: list[dict] = []

    def chat_completions(self, **kwargs):
        self.calls.append(kwargs)
        return {"choices": [{"message": self._message, "finish_reason": "length"}]}


def _shim(message: dict[str, str]) -> _GaiaLLMClientShim:
    return _GaiaLLMClientShim(
        _FakeClient(message), "unlisted-thinking-model", max_tokens=64, temperature=0.3
    )


class TestReasoningFallback:
    def test_falls_back_to_reasoning_content_when_content_empty(self):
        """DISCRIMINATING: the pre-fix shim returns "" here and the caller sees "no answer"."""
        out = _shim({"content": "", "reasoning_content": "mutable default argument"}).prompt("q")
        assert out == "mutable default argument"

    def test_whitespace_only_content_also_falls_back(self):
        """DISCRIMINATING: `or ""` alone does NOT catch "\\n  " — it is truthy.

        A thinking model that emits a stray newline into content before exhausting its budget
        would defeat a naive truthiness check while still having the real answer in reasoning.
        """
        out = _shim({"content": "\n  ", "reasoning_content": "bare except swallows exits"}).prompt(
            "q"
        )
        assert out == "bare except swallows exits"

    def test_real_content_wins_over_reasoning(self):
        """The fallback must not shadow a genuine answer with raw chain-of-thought."""
        out = _shim(
            {"content": "the answer", "reasoning_content": "long rambling thoughts"}
        ).prompt("q")
        assert out == "the answer"

    def test_both_empty_returns_empty_string_not_none(self):
        """Callers do `.strip()` on this; None would raise instead of degrading."""
        assert _shim({"content": "", "reasoning_content": ""}).prompt("q") == ""

    def test_missing_reasoning_key_is_safe(self):
        """Non-thinking backends (e.g. FLM on the NPU) have no reasoning_content channel."""
        assert _shim({"content": "plain answer"}).prompt("q") == "plain answer"
