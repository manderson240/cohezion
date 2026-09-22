"""extend_claude_aligned must SEND the card params it is given, not a default request.

Before the fix the local leg called ``_dispatch_one(model, prompt, None, timeout)``: the
``/no_think`` prefix, ``extra_body`` (incl. ``chat_template_kwargs``) and ``max_tokens``
were validated by RecipeGuard and then dropped, so a Qwen3.x card that disables thinking
still produced a thinking request with the 512-token default. The HTTP client is faked:
no request leaves the process.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.inference.fleet import extend_claude_aligned, get_registry
from cohezion.inference.model_card_harness import InferenceParams


_LONG = "a response comfortably longer than the forty character length gate"
_TARGET = "Gemma-4-E4B-it-GGUF"


def _fake_client(sent: list[dict]) -> AsyncMock:
    resp = AsyncMock()
    resp.raise_for_status = lambda: None
    resp.json = lambda: {"choices": [{"message": {"content": _LONG}}], "usage": {}}

    async def post(url, json):
        sent.append({"url": url, "body": json})
        return resp

    client = AsyncMock()
    client.post = post
    return client


def _params() -> InferenceParams:
    return InferenceParams(
        model_id=_TARGET,
        max_tokens=1234,
        prompt_prefix="/no_think\n",
        extra_body={"chat_template_kwargs": {"enable_thinking": False}, "temperature": 0.6},
    )


@pytest.mark.asyncio
async def test_local_request_body_carries_card_params() -> None:
    assert not get_registry().models[_TARGET].endpoint.endswith(":11434")
    sent: list[dict] = []
    with patch("cohezion.inference.fleet._get_shared_client", return_value=_fake_client(sent)):
        result = await extend_claude_aligned("fix it", params=_params())

    assert result.escalated_to_cloud is False
    assert len(sent) == 1
    body = sent[0]["body"]
    assert body["model"] == _TARGET
    assert body["max_tokens"] == 1234  # not the 512 default
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert body["temperature"] == 0.6
    assert body["messages"][0]["content"] == "/no_think\nfix it"


@pytest.mark.asyncio
async def test_extra_body_cannot_override_core_fields() -> None:
    params = InferenceParams(
        model_id=_TARGET,
        max_tokens=77,
        extra_body={"model": "evil", "max_tokens": 9, "stream": True, "top_p": 0.9},
    )
    sent: list[dict] = []
    with patch("cohezion.inference.fleet._get_shared_client", return_value=_fake_client(sent)):
        await extend_claude_aligned("hi", params=params)
    body = sent[0]["body"]
    assert (body["model"], body["max_tokens"], body["stream"]) == (_TARGET, 77, False)
    assert body["top_p"] == 0.9


@pytest.mark.asyncio
async def test_cloud_escalation_does_not_receive_local_card_params() -> None:
    calls: list[tuple] = []

    async def fake_dispatch(model, prompt, coherence, timeout, *a, **kw):
        calls.append((model.model_id, prompt, kw))
        return ("no", 0.0, None, None) if len(calls) == 1 else (_LONG, 0.01, None, None)

    with patch("cohezion.inference.fleet._dispatch_one", fake_dispatch):
        result = await extend_claude_aligned("fix it", params=_params(), max_local_attempts=1)
    assert result.escalated_to_cloud is True
    local, cloud = calls
    assert local[2]["extra_body"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert cloud[1] == "fix it" and "extra_body" not in cloud[2]
