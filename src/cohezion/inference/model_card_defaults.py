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
    "qwen3.6-35b-a3b-gguf": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0},
    "qwen3.6-35b-a3b-nothinking": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0},
    "qwen3.6-35b-a3b-thinkingcoder": {"temperature": 0.6, "top_k": 30},
    "llama3.2-1b-flm": {"temperature": 0.3},
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