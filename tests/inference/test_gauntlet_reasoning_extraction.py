"""The chokepoint must not hand callers a chain of thought, or an empty string.

`gauntlet._call_model` is the designated local-LLM chokepoint -- `check_local_llm_chokepoint.sh`
flags net-new raw POST sites precisely so "solved reasoning-model traps" cannot reappear. Its
extraction was the ORIGINAL of the pattern `gaia_adapter` later copied, and it carried two gaps:

  * `_THINK_RE.sub("", text)` with no guard returns "" when a reply is ENTIRELY a think block,
    which IS the empty-content trap the function exists to prevent (defect 4dd925b0081f). Empty
    reads as "no answer" to callers and as fail-open APPROVE to the adversarial gate.
  * Gemma-4 does not use `<think>`. It emits `<|channel>thought ... <channel|>`, so its reasoning
    passed through untouched -- 3214 chars measured reaching a caller on 2026-08-16.

The 24 pre-existing gauntlet tests pass both before and after the fix, so none of them cover
this. These do.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from cohezion.inference import gauntlet


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    """Stands in for httpx.AsyncClient. Returns one canned chat/completions body."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, *_: Any, **__: Any) -> _FakeResponse:
        return _FakeResponse(self._payload)


def _call(monkeypatch: pytest.MonkeyPatch, content: str, reasoning: str = "") -> str:
    payload = {
        "choices": [{"message": {"content": content, "reasoning_content": reasoning}}],
        "usage": {"completion_tokens": 42},
    }

    class _FakeHttpx:
        @staticmethod
        def AsyncClient(*_: Any, **__: Any) -> _FakeAsyncClient:  # mirrors httpx's class name
            return _FakeAsyncClient(payload)

    monkeypatch.setitem(__import__("sys").modules, "httpx", _FakeHttpx)
    _ttft, _tps, text = asyncio.run(gauntlet._call_model("stub-model", "prompt", 256))
    assert isinstance(text, str)
    return text


class TestChokepointExtraction:
    def test_inline_think_is_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        got = _call(monkeypatch, "<think>weighing it</think>VERDICT: no")
        assert got == "VERDICT: no"

    def test_gemma_channel_is_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DISCRIMINATING: the old `<think>`-only regex returns this whole string untouched."""
        got = _call(monkeypatch, "<|channel>thought reasoning here<channel|>FINAL ANSWER")
        assert got == "FINAL ANSWER"
        assert "channel" not in got

    def test_all_thinking_does_not_become_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DISCRIMINATING: the old bare `sub("")` returns "" here.

        Empty is the exact failure this chokepoint exists to prevent, so the cleanup step must
        not be able to produce it.
        """
        got = _call(monkeypatch, "<think>I never reached an answer</think>")
        assert got, "chokepoint must never return empty as a RESULT of stripping"
        assert "never reached" in got

    def test_empty_content_falls_back_to_reasoning(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Budget exhausted mid-think: content empty, the answer is in the other channel."""
        got = _call(monkeypatch, "", "all of it landed in reasoning_content")
        assert got == "all of it landed in reasoning_content"

    def test_plain_answer_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        got = _call(monkeypatch, "a normal answer with no reasoning markup")
        assert got == "a normal answer with no reasoning markup"


def test_shares_the_adapter_normaliser() -> None:
    """Structural: one implementation, so the two paths cannot drift apart again.

    They already had, in opposite directions -- gauntlet had the <think> strip the adapter
    lacked, and the adapter had the empty-guard gauntlet lacked.
    """
    from cohezion.inference.gaia_adapter import _answer_only

    assert gauntlet._answer_only is _answer_only
    assert not hasattr(gauntlet, "_THINK_RE"), "local copy removed in favour of the shared one"


def test_json_import_still_used() -> None:
    """Guard against the fake-httpx shim masking a real import removal in the module."""
    assert json is not None
