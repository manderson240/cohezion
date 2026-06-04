"""
Model card harness — maps output_types to optimal models based on live model cards.

Key principle: configure inference parameters FROM model card facts, not guesswork.
- Thinking models (Gemma-4-*): need budget_tokens to bound reasoning overhead
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
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.inference.capability_profile import CapabilityProfile
    from cohezion.inference.registry import Task

# ── Model capability facts (from model card + empirical measurement) ─────────

# Labels that indicate thinking-mode behaviour
_THINKING_MODEL_PREFIXES = ("Gemma-4-", "gemma4-")

# Labels that indicate Qwen3-family /no_think support
_QWEN3_THINKING_PREFIXES = ("Qwen3", "DeepSeek-Qwen3", "qwen3")

# Thinking overhead observed empirically (tokens needed before first output)
_THINKING_OVERHEAD_TOKENS = {
    "Gemma-4-E4B-it-GGUF": 2260,  # measured: code task used 2260 thinking tokens
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

    # ── NEW (WS2A): card-aware accessors ──────────────────────────────────
    #
    # These methods were added in the daily-researcher-agent WS2A build.
    # They look up a model's CapabilityProfile (from the live catalog or
    # the hand-built default_profiles table) and expose the card facts
    # the rest of the system needs.
    #
    # The methods are additive; existing callers (get_params, is_thinking_model,
    # best_model_for_output_type) are unchanged.

    def profile_for(self, model_id: str) -> CapabilityProfile | None:
        """Return the CapabilityProfile for `model_id`.

        Resolution order:
        1. The hand-built default_profiles table (14 default entries).
        2. The live catalog (`self._by_id`); if labels and ctx_size are
           present, we can synthesize a minimal profile on the fly.
        3. None — caller is responsible for fallback.

        The "live catalog" path is a best-effort reconstruction from the
        Lemonade /v1/models response. Full card parsing happens in
        Lane 1 (model_scout) of the daily researcher.
        """
        # Lazy import to avoid a cycle: capability_profile imports from
        # the card parser; we import here so anyone who uses the harness
        # without profiles still works.
        from cohezion.inference.default_profiles import get_profile

        prof = get_profile(model_id)
        if prof is not None:
            return prof

        live = self._by_id.get(model_id)
        if not live:
            return None

        # Synthesize a minimal profile from the live catalog. This is
        # best-effort — many fields (strengths, weaknesses, sampling) are
        # unknown until ScoutLane reads the real card.
        from datetime import UTC, datetime

        from cohezion.inference.capability_profile import CapabilityProfile

        labels = live.get("labels", [])
        is_thinking = "reasoning" in labels
        is_qwen3 = any(model_id.startswith(p) for p in _QWEN3_THINKING_PREFIXES)
        is_coding = "coding" in labels
        modes = frozenset({"chat"})
        if "tool" in str(live).lower() or any("tool" in l for l in labels):
            modes = modes | {"tool_use"}

        strengths: set[str] = set()
        if is_coding:
            strengths.add("code")
            strengths.add("code_completion")
        if is_thinking:
            strengths.add("reasoning")
            strengths.add("math")
        if not strengths:
            strengths.add("general_chat")

        return CapabilityProfile(
            model_id=model_id,
            family=model_id.split("-")[0].lower(),
            supported_modes=modes,
            optimal_ctx=self.get_ctx_size(model_id) or 8192,
            min_ctx=512,
            strengths=frozenset(strengths),
            weaknesses=frozenset(),
            sampling_sweet_spot={},
            prompt_template_fingerprint="chatml" if is_qwen3 else "unknown",
            thinking_mode=("always" if is_thinking and not is_qwen3 else "never"),
            known_failure_modes=(),
            source_url=f"https://huggingface.co/{model_id}",
            read_at=datetime.now(UTC),
        )

    def aligned_params(self, model_id: str, task: Task) -> InferenceParams:
        """Return card-aligned InferenceParams for `model_id` on `task`.

        Convenience wrapper around route_by_capability that always picks
        the registry entry for `model_id` (rather than letting the router
        choose). Use this when the caller has already decided which model
        to dispatch to and only needs the params filled in from the card.
        """
        from cohezion.inference.recipe_guard import RecipeGuard
        from cohezion.inference.registry import get_registry
        from cohezion.inference.route_by_capability import _build_aligned_params

        reg = get_registry()
        entry = reg.models.get(model_id)
        if entry is None:
            raise ValueError(f"unknown model_id {model_id!r}")
        RecipeGuard.assert_card_present(entry)
        return _build_aligned_params(entry, task)
