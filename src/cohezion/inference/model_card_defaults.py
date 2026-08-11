"""Model-card-aligned sampling defaults.

Returns model-specific sampling parameters (temperature, top_k, top_p, min_p)
based on the model card. Caller-set values take precedence over defaults.
"""

from __future__ import annotations

from typing import Any


# Registry of model-card sampling defaults.
# Keys are model name substrings (matched case-insensitive against the payload model field).
_MODEL_DEFAULTS: dict[str, dict[str, Any]] = {
    "gemma-4": {"temperature": 1.0, "top_k": 64, "top_p": 0.95},
    "gemma4": {"temperature": 1.0, "top_k": 64, "top_p": 0.95},
    # Gemma-3 shares Gemma-4's published sampling recommendation (temp 1.0 / top_k 64 /
    # top_p 0.95). Added 2026-07-28 for gemma3-1b-FLM, which matched nothing -- and FLM's only
    # sampling surface is this request layer, since flm_args rejects sampling flags.
    "gemma-3": {"temperature": 1.0, "top_k": 64, "top_p": 0.95},
    "gemma3": {"temperature": 1.0, "top_k": 64, "top_p": 0.95},
    "qwen3.6-35b-a3b-gguf": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0},
    "qwen3.6-35b-a3b-nothinking": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0},
    "qwen3.6-35b-a3b-thinkingcoder": {"temperature": 0.6, "top_k": 30},
    # DeepSeek-R1 (incl. the FLM/NPU build and the Qwen3-distilled GGUF). MUST stay BEFORE the
    # generic "qwen3" key: the distills contain BOTH substrings, and R1's card omits top_k while
    # the generic Qwen3 entry sets top_k=20. Values grounded in lemonade's own registry, which
    # ships DeepSeek-Qwen3-8B-GGUF with exactly `--temp 0.6 --top-p 0.95` (no top_k).
    # Added 2026-07-28: deepseek-r1-0528-8b-FLM previously matched NOTHING and ran on bare
    # defaults at BOTH layers (FLM rejects sampling in flm_args, so the request layer is the
    # only surface it has). It still scored 81% recall on the review benchmark that way --
    # matching gpt-oss:120b-cloud -- so this is correcting a genuine gap, not chasing a failure.
    "deepseek-r1": {"temperature": 0.6, "top_p": 0.95},
    # Generic Qwen3 family (matches e.g. DeepSeek-Qwen3-8B). MUST stay after the
    # qwen3.6-35b-* keys: _match_model takes the first substring hit in insertion order.
    "qwen3": {"temperature": 0.6, "top_p": 0.95, "top_k": 20},
    "llama3.2-1b-flm": {"temperature": 0.3},
    # Nemotron-3-Nano. Grounded in the unsloth card, which gives TWO regimes:
    #   reasoning    -> temperature 1.0, top_p 1.0
    #   tool calling -> temperature 0.6, top_p 0.95
    # We take the TOOL-CALLING values because that is how lemonade labels this model in our
    # catalog ("tool-calling"), and because they are the conservative pair. Switch to 1.0/1.0
    # if this model is ever used as a reasoning tier. No top_k: the card specifies none, and
    # inventing one would be exactly the guess this registry exists to avoid.
    "nemotron": {"temperature": 0.6, "top_p": 0.95},
    # Bonsai family. Unanimous across the FIVE Bonsai entries lemonade ships
    # (1.7B/4B/8B/27B/27B-Q1_0), every one `--temp 0.7 --top-p 0.9 --top-k 40`. The GGUF builds
    # carry these in llamacpp_args already; this entry covers the request layer so a Bonsai
    # served without recipe args (e.g. Ternary-Bonsai-27B-PQ2_0) is not left on bare defaults.
    "bonsai": {"temperature": 0.7, "top_p": 0.9, "top_k": 40},
}


def _match_model(model_id: str) -> dict[str, Any] | None:
    """Find the matching model-card entry by case-insensitive substring match."""
    model_lower = model_id.lower()
    for key, defaults in _MODEL_DEFAULTS.items():
        if key in model_lower:
            return defaults
    return None


def get_sampling_defaults(model_id: str) -> dict[str, Any]:
    """Return model-card sampling defaults for *model_id*.

    Returns an empty dict for unknown models.
    Returns a copy — mutations do not affect the registry.
    """
    defaults = _match_model(model_id)
    if defaults is None:
        return {}
    return dict(defaults)


def apply_model_card_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    """Merge model-card sampling defaults into *payload*.

    Caller-set values take precedence over model-card defaults.
    Mutates and returns *payload* for convenience.
    """
    model = payload.get("model", "")
    defaults = get_sampling_defaults(model)
    for key, value in defaults.items():
        if key not in payload:
            payload[key] = value
    return payload
