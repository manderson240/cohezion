"""
Model card harness — maps output_types to optimal models based on live model cards.

Key principle: configure inference parameters FROM model card facts, not guesswork.
- Thinking models: lemonade 'reasoning' label is the primary detection signal
  (Qwen3 family excluded — they use /no_think prefix instead)
- Fallback for FLM/NPU models not in the 13305 catalog: prefix heuristic
- Qwen3 models: support /no_think prefix for direct output
- Coding labels: route code tasks to dedicated coding models
- FLM models: no thinking mode; fast direct responses

Usage:
    from cohezion.inference.model_card_harness import ModelCardHarness
    harness = ModelCardHarness.from_live_api(port=13305)
    params = harness.get_params("code", model_id="DeepSeek-Qwen3-8B-GGUF")
    # params.prompt_prefix, params.max_tokens, params.extra_body
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from typing import Any


# ── Model capability facts (from model card + empirical measurement) ─────────

# Fallback prefix heuristic for thinking models NOT served through port 13305.
# Only used when model_id is absent from the live catalog (e.g. Gemma-4-FLM on NPU XDNA2).
# When the model IS in the lemonade catalog, the 'reasoning' label is authoritative.
_THINKING_MODEL_PREFIXES = ("Gemma-4-", "gemma4-")

# Labels that indicate Qwen3-family /no_think support
_QWEN3_THINKING_PREFIXES = ("Qwen3", "DeepSeek-Qwen3", "qwen3")

# Thinking overhead observed empirically (tokens needed before first output).
# Gemma-4 entries apply to FLM/NPU path (prefix fallback) — llamacpp serving ignores
# budget_tokens silently, so including extra_body is safe but a no-op for llamacpp.
_THINKING_OVERHEAD_TOKENS = {
    "Gemma-4-E4B-it-GGUF": 2260,  # measured: code task on NPU/FLM path
    "Gemma-4-E2B-it-GGUF": 1800,  # estimate
    "default_thinking": 500,  # conservative default for unknown thinking models
}

# Per-output-type optimal max_tokens (thinking budget + output headroom)
_OUTPUT_TYPE_MAX_TOKENS: dict[str, int] = {
    "short_categorical": 50,
    "short_answer": 150,
    "medium_generation": 400,
    "long_generation": 800,
    "code": 600,  # with /no_think: just code; without: needs 2500+
    "math_reasoning": 800,
}

# GPU port default thinking budget (leaves room for output)
_DEFAULT_THINKING_BUDGET = 200


@dataclass(frozen=True)
class InferenceParams:
    model_id: str
    max_tokens: int
    prompt_prefix: str = ""  # prepend to prompt (e.g. "/no_think\n")
    extra_body: dict[str, Any] = field(default_factory=dict)

    def apply(self, prompt: str) -> tuple[str, dict[str, Any]]:
        """Return (final_prompt, extra_api_body)."""
        return self.prompt_prefix + prompt, self.extra_body


class ModelCardHarness:
    """Live model card → inference parameter resolver."""

    def __init__(self, models: list[dict]) -> None:
        self._by_id: dict[str, dict] = {m["id"]: m for m in models}

    @classmethod
    def from_live_api(cls, port: int = 13305) -> ModelCardHarness:
        """Build from the Lemonade /v1/models endpoint."""
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=3) as r:
                data = json.loads(r.read())
            return cls(data.get("data", []))
        except Exception:
            return cls([])  # empty harness — callers must handle gracefully

    def get_labels(self, model_id: str) -> list[str]:
        return self._by_id.get(model_id, {}).get("labels", [])

    def get_ctx_size(self, model_id: str) -> int | None:
        ctx = self._by_id.get(model_id, {}).get("recipe_options", {}).get("ctx_size")
        return int(ctx) if ctx else None

    def is_thinking_model(self, model_id: str) -> bool:
        """True when model always operates in thinking/CoT mode (produces reasoning_content).

        Primary: when model is in the live catalog, the lemonade 'reasoning' label is
        authoritative. Qwen3 family excluded — they use /no_think prefix instead.
        Fallback: prefix heuristic for FLM/NPU variants not in the 13305 catalog.
        """
        if model_id in self._by_id:
            return "reasoning" in self.get_labels(model_id) and not self.is_qwen3_family(model_id)
        # Model not in live catalog (e.g. FLM/NPU variant) — fall back to prefix
        return any(model_id.startswith(p) for p in _THINKING_MODEL_PREFIXES)

    def is_qwen3_family(self, model_id: str) -> bool:
        return any(model_id.startswith(p) for p in _QWEN3_THINKING_PREFIXES)

    def best_model_for_output_type(self, output_type: str) -> str | None:
        """Return the model_id from the catalog best suited to the output type."""
        if output_type == "code":
            # Prefer models with 'coding' label
            for m in self._by_id.values():
                if "coding" in m.get("labels", []) and m.get("downloaded"):
                    return m["id"]
            # Fallback: Qwen3 with /no_think
            for m in self._by_id.values():
                if "reasoning" in m.get("labels", []) and m.get("downloaded"):
                    if self.is_qwen3_family(m["id"]):
                        return m["id"]

        if output_type in ("math_reasoning", "long_generation"):
            for m in self._by_id.values():
                if "reasoning" in m.get("labels", []) and m.get("downloaded"):
                    return m["id"]

        return None

    def get_params(self, output_type: str, model_id: str) -> InferenceParams:
        """Return inference params for this model + output_type combination."""
        max_tokens = _OUTPUT_TYPE_MAX_TOKENS.get(output_type, 400)
        prompt_prefix = ""
        extra_body: dict[str, Any] = {}

        if self.is_qwen3_family(model_id) and output_type in (
            "code",
            "short_categorical",
            "short_answer",
            "medium_generation",
        ):
            # Qwen3 /no_think: disable thinking mode via prompt prefix
            # (model card capability — cheaper than thinking budget API)
            prompt_prefix = "/no_think\n"

        elif self.is_thinking_model(model_id):
            # Thinking models: bound reasoning via budget_tokens API
            overhead = _THINKING_OVERHEAD_TOKENS.get(
                model_id, _THINKING_OVERHEAD_TOKENS["default_thinking"]
            )
            budget = min(_DEFAULT_THINKING_BUDGET, max(50, max_tokens - 100))

            if output_type == "code":
                # Code needs significantly more headroom; prefer /no_think-capable model
                max_tokens = overhead + 400  # thinking + actual code
                budget = min(400, overhead)
            extra_body["thinking"] = {"type": "enabled", "budget_tokens": budget}

        return InferenceParams(
            model_id=model_id,
            max_tokens=max_tokens,
            prompt_prefix=prompt_prefix,
            extra_body=extra_body,
        )
