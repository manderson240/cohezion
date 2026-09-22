"""The "no thinking" intent must emit the family's real control, not only a "/no_think" prefix.

Measured 2026-09-21 on :13305: Qwen3.6-35B-A3B-MTP-GGUF ignores the "/no_think" soft switch
(300/300 tokens of reasoning, empty content); ``chat_template_kwargs.enable_thinking=false``
makes it answer directly. Non-Qwen families get nothing (no verified toggle).
"""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime

import pytest

from cohezion.inference import direct_tier
from cohezion.inference.capability_profile import CapabilityProfile
from cohezion.inference.model_card_harness import ModelCardHarness, thinking_off_extras
from cohezion.inference.registry import KVQuant, Lane, ModelEntry, Task, WeightQuant
from cohezion.inference.route_by_capability import _build_aligned_params


_OFF = {"chat_template_kwargs": {"enable_thinking": False}}
_QWEN36 = "Qwen3.6-35B-A3B-MTP-GGUF"


def _entry(model_id: str, task: Task) -> ModelEntry:
    profile = CapabilityProfile(
        model_id=model_id,
        family="qwen",
        supported_modes=frozenset({"chat"}),
        optimal_ctx=8192,
        min_ctx=512,
        strengths=frozenset({"code"}),
        weaknesses=frozenset(),
        sampling_sweet_spot={"temperature": 0.6, "top_p": 0.95},
        prompt_template_fingerprint="chatml",
        thinking_mode="never",
        known_failure_modes=(),
        source_url=f"https://huggingface.co/{model_id}",
        read_at=datetime(2026, 9, 21, tzinfo=UTC),
    )
    return ModelEntry(
        model_id=model_id,
        lane=Lane.IGPU_UNIFIED,
        endpoint="http://localhost:9999/v1",
        runtime_backend="llamacpp_hip",
        task_affinity=frozenset({task}),
        weight_quant=WeightQuant.Q4_K_M,
        context_window=32768,
        kv_quant=KVQuant(),
        profile=profile,
    )


@pytest.mark.parametrize("model_id", [_QWEN36, "Qwen3.5-9B-GGUF", "Qwen3-8B-GGUF", "qwen3-coder-30b"])
def test_qwen3_families_get_the_template_kwarg(model_id: str) -> None:
    assert thinking_off_extras(model_id) == _OFF


@pytest.mark.parametrize(
    "model_id",
    ["Gemma-4-26B-A4B-it-GGUF", "DeepSeek-Qwen3-8B-GGUF", "Bonsai-8B-gguf", "llama3.2-1b-FLM"],
)
def test_other_families_get_nothing(model_id: str) -> None:
    assert thinking_off_extras(model_id) == {}


def test_harness_request_body_for_qwen36_disables_thinking() -> None:
    prompt, body = ModelCardHarness([]).get_params("code", _QWEN36).apply("fix it")
    assert prompt.startswith("/no_think")  # prefix kept as a harmless fallback
    assert body["chat_template_kwargs"] == {"enable_thinking": False}


def test_harness_request_body_for_non_qwen_has_no_template_kwarg() -> None:
    _, body = ModelCardHarness([]).get_params("code", "Gemma-4-26B-A4B-it-GGUF").apply("x")
    assert "chat_template_kwargs" not in body


def test_harness_long_generation_leaves_qwen_thinking_on() -> None:
    _, body = ModelCardHarness([]).get_params("long_generation", "Qwen3-8B-GGUF").apply("x")
    assert "chat_template_kwargs" not in body


def test_route_by_capability_aligned_params_disable_qwen_thinking() -> None:
    params = _build_aligned_params(_entry(_QWEN36, Task.CODE_GEN), Task.CODE_GEN)
    assert params.extra_body["chat_template_kwargs"] == {"enable_thinking": False}
    assert params.extra_body["temperature"] == 0.6  # card sweet spot preserved


def test_route_by_capability_reasoning_task_keeps_thinking() -> None:
    params = _build_aligned_params(_entry(_QWEN36, Task.REASONING), Task.REASONING)
    assert "chat_template_kwargs" not in params.extra_body


def _capture_direct_payload(monkeypatch: pytest.MonkeyPatch, model_id: str) -> dict:
    sent: list[dict] = []

    def fake_urlopen(req, timeout=None):  # noqa: ARG001
        sent.append(json.loads(req.data))
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode())

    monkeypatch.setattr(direct_tier.urllib.request, "urlopen", fake_urlopen)
    direct_tier.DirectLemonadeTier(model_id=model_id).call("hi")
    return sent[0]


def test_direct_tier_qwen_payload_disables_thinking(monkeypatch: pytest.MonkeyPatch) -> None:
    body = _capture_direct_payload(monkeypatch, "Qwen3-8B-GGUF")
    assert body["chat_template_kwargs"] == {"enable_thinking": False}


def test_direct_tier_non_qwen_payload_has_no_template_kwarg(monkeypatch: pytest.MonkeyPatch) -> None:
    body = _capture_direct_payload(monkeypatch, "Bonsai-8B-gguf")
    assert "chat_template_kwargs" not in body
