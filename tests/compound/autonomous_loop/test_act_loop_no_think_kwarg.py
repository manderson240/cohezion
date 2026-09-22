"""make_chat_fn must disable thinking via chat_template_kwargs, not only the /no_think prefix.

Qwen3.6-35B-A3B-MTP ignores "/no_think" (measured 2026-09-21: every ACT call spent the full
3072-token budget reasoning and returned empty content -> FORMAT_ERROR, blamed on the model).
"""

from __future__ import annotations

import io
import json
import urllib.request

import pytest

from cohezion.compound.autonomous_loop import act_loop


def test_qwen3_request_disables_thinking_via_template_kwarg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[dict] = []

    def fake_urlopen(req, timeout=None):  # noqa: ARG001
        sent.append(json.loads(req.data))
        body = {"choices": [{"message": {"content": "```python\nx = 1\n```"}}], "usage": {}}
        return io.BytesIO(json.dumps(body).encode())

    model = "Qwen3.6-35B-A3B-MTP-GGUF"
    monkeypatch.setattr(act_loop, "resident_llms", lambda *_a, **_k: [model])
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    chat = act_loop.make_chat_fn([model], max_tokens=64, timeout=5)
    assert "x = 1" in chat("fix it")["text"]
    assert sent[0].get("chat_template_kwargs") == {"enable_thinking": False}
