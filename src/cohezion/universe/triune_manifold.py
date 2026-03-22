from typing import Any

import torch
from pydantic import BaseModel, ConfigDict, field_validator


class TriuneState(BaseModel):
    """
    Data model representing the triune manifold state.

    Attributes:
        doer (torch.Tensor): 12D observable state (physical variables).
            Conceptual mapping: The active Doer (Percival's Triune Self).
        thinker (torch.Tensor): 512D reasoning and interpolation space.
            Conceptual mapping: The reasoning Thinker (Percival's Triune Self).
        knower (torch.Tensor): 2048D deep semantic intent.
            Conceptual mapping: The omniscient Knower (Percival's Triune Self).
    """

    doer: torch.Tensor
    thinker: torch.Tensor
    knower: torch.Tensor

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("doer")
    @classmethod
    def validate_doer(cls, v: Any) -> torch.Tensor:
        if not isinstance(v, torch.Tensor):
            raise ValueError("doer must be a torch.Tensor")
        if v.shape != (12,):
            raise ValueError(f"doer must be 12D, got shape {v.shape}")
        return v

    @field_validator("thinker")
    @classmethod
    def validate_thinker(cls, v: Any) -> torch.Tensor:
        if not isinstance(v, torch.Tensor):
            raise ValueError("thinker must be a torch.Tensor")
        if v.shape != (512,):
            raise ValueError(f"thinker must be 512D, got shape {v.shape}")
        return v

    @field_validator("knower")
    @classmethod
    def validate_knower(cls, v: Any) -> torch.Tensor:
        if not isinstance(v, torch.Tensor):
            raise ValueError("knower must be a torch.Tensor")
        if v.shape != (2048,):
            raise ValueError(f"knower must be 2048D, got shape {v.shape}")
        return v


def calculate_hiho_coherence(intent: torch.Tensor, environment: torch.Tensor) -> float:
    """
    Calculates the coherence between internal intent and external environment.

    Uses cosine similarity normalized to the [0, 1] range.

    Args:
        intent: The intent vector.
        environment: The environment state vector.

    Returns:
        float: Coherence score in [0, 1].
    """
    # Flatten to handle arbitrary (but matching) shapes
    i_flat = intent.flatten()
    e_flat = environment.flatten()

    if i_flat.shape[0] == 0:
        return 0.5

    cos_sim = torch.nn.functional.cosine_similarity(i_flat, e_flat, dim=0)
    return float((cos_sim + 1.0) / 2.0)


def compute_restoring_force(
    current_coherence: float, target: float = 0.5, stiffness: float = 0.1
) -> float:
    """
    Computes the force required to drive coherence back toward the stability point.

    Based on the 0.5 Coherence Rule (HIHO Stability).

    Args:
        current_coherence: The current coherence score.
        target: The target stability point (default 0.5).
        stiffness: The "restoring strength" of the manifold fabric.

    Returns:
        float: The directional force toward the target.
    """
    return (target - current_coherence) * stiffness
