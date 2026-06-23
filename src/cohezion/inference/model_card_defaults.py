"""Model-card-aligned sampling defaults (stub).

Exports consumed by tests/inference/test_model_card_defaults.py.
"""

from __future__ import annotations

from typing import Any


def get_sampling_defaults(model_id: str) -> dict[str, Any]:
    """Return model-card sampling defaults for *model_id*.

    Returns an empty dict for unknown models.
    Returns a copy — mutations do not affect the registry.
    """
    raise NotImplementedError


def apply_model_card_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    """Merge model-card sampling defaults into *payload*.

    Caller-set values take precedence over model-card defaults.
    Mutates and returns *payload* for convenience.
    """
    raise NotImplementedError
