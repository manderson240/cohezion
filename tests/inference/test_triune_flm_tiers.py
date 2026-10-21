"""Triune tiers on FLM (NPU) models, used the way their model cards say.

Qwen3.5 card (huggingface.co/Qwen/Qwen3.5-4B, "Using Qwen3.5 via the Chat Completions API"):
  - thinks by default; no /think soft switch; turn it off per request
  - thinking, general:      temperature=1.0, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=1.5
  - non-thinking, general:  temperature=0.7, top_p=0.8,  top_k=20, min_p=0.0, presence_penalty=1.5
FastFlowLM server (fastflowlm.com/docs/instructions/server/reasoning_and_tools/):
  - per-request toggle is the top-level ``think`` field
  - "The setting sticks" on the loaded model, so every request must send it
"""

from __future__ import annotations

import pytest

from cohezion.inference.model_card_defaults import get_sampling_defaults


QWEN35_THINKING = {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.0,
    "presence_penalty": 1.5,
}
QWEN35_NON_THINKING = {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 20,
    "min_p": 0.0,
    "presence_penalty": 1.5,
}


class TestQwen35Card:
    def test_default_is_the_thinking_card(self) -> None:
        # Previously fell through to the generic "qwen3" key (Qwen3's card, 0.6/0.95/20).
        assert get_sampling_defaults("qwen3.5-4b-FLM") == QWEN35_THINKING

    def test_thinking_off_uses_the_instruct_card(self) -> None:
        assert get_sampling_defaults("qwen3.5-4b-FLM", thinking=False) == QWEN35_NON_THINKING
        assert get_sampling_defaults("qwen3.5-4b-FLM", thinking=True) == QWEN35_THINKING

    def test_qwen3_card_unchanged(self) -> None:
        assert get_sampling_defaults("Qwen3-8B-GGUF") == {
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 20,
        }

    def test_mode_is_ignored_for_models_without_a_mode_card(self) -> None:
        assert get_sampling_defaults("llama3.2-1b-FLM", thinking=False) == {"temperature": 0.3}


class _RecordingClient:
    def __init__(self, **_: object) -> None:
        self.calls: list[dict[str, object]] = []

    def chat_completions(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return {"choices": [{"message": {"content": "ok"}}], "usage": {"completion_tokens": 1}}


def _tier(model_id: str, **kw: object):
    from unittest.mock import patch

    from cohezion.inference.gaia_adapter import build_gaia_llm_tier

    pytest.importorskip("gaia")
    holder: dict[str, _RecordingClient] = {}

    def factory(**fkw: object) -> _RecordingClient:
        holder["c"] = _RecordingClient(**fkw)
        return holder["c"]

    with patch("gaia.llm.lemonade_client.LemonadeClient", factory):
        tier = build_gaia_llm_tier(model_id, silent=True, **kw)
    return tier, holder["c"]


class TestThinkingToggleOnTheWire:
    def test_flm_sends_think_on_every_request(self) -> None:
        # Sticky server state: a tier that sent think once and then omitted it would inherit
        # whatever the last caller (another tier or session) set.
        tier, client = _tier("qwen3.5-4b-FLM", thinking=False)
        tier.agent.prompt("a")
        tier.agent.prompt("b")
        assert [c["think"] for c in client.calls] == [False, False]
        assert client.calls[0]["temperature"] == 0.7
        assert client.calls[0]["presence_penalty"] == 1.5
        assert client.calls[0]["top_p"] == 0.8

    def test_flm_thinking_tier_sends_true_and_thinking_card(self) -> None:
        tier, client = _tier("qwen3.5-4b-FLM", thinking=True)
        tier.agent.prompt("a")
        assert client.calls[0]["think"] is True
        assert client.calls[0]["temperature"] == 1.0
        assert client.calls[0]["top_p"] == 0.95

    def test_non_flm_backend_uses_chat_template_kwargs(self) -> None:
        tier, client = _tier("Qwen3.5-4B-GGUF", thinking=False)
        tier.agent.prompt("a")
        assert client.calls[0]["chat_template_kwargs"] == {"enable_thinking": False}
        assert "think" not in client.calls[0]

    def test_no_mode_requested_sends_no_toggle(self) -> None:
        tier, client = _tier("llama3.2-1b-FLM")
        tier.agent.prompt("a")
        assert "think" not in client.calls[0]


class TestTriuneOnFlm:
    def test_tiers_are_flm_with_card_modes(self) -> None:
        pytest.importorskip("gaia")
        from cohezion.inference.triune_orchestrator import build_triune_omni_orchestrator

        agents = [tier[0].agent for tier in build_triune_omni_orchestrator().tiers]
        assert [a._model for a in agents] == [
            "llama3.2-1b-FLM",
            "qwen3.5-4b-FLM",
            "qwen3.5-4b-FLM",
        ]
        assert all(a._model.endswith("-FLM") for a in agents)
        assert "think" not in agents[0]._extra_sampling
        assert agents[1]._extra_sampling["think"] is False
        assert agents[2]._extra_sampling["think"] is True
        # Thinking needs room for the reasoning AND the answer.
        assert agents[2]._max_tokens >= 4096 > agents[1]._max_tokens
