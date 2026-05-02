"""
FLUME Geometric Overlap: Measures semantic alignment between latent intent and physical reality.
Used for 'Holographic Record' correlation and Physics-as-a-Policy (PaaP) gating.
"""

from __future__ import annotations

from typing import Any

import torch


def calculate_geometric_overlap(
    latent_state: torch.Tensor, universe_state: torch.Tensor
) -> dict[str, Any]:
    """
    Calculate the geometric overlap (L2 distance) between a down-projected
    latent vector and an axiomatic physical state vector.

    Args:
        latent_state: [12D] vector representing agent intent.
        universe_state: [12D] vector representing physical reality.

    Returns:
        Dictionary containing L2 distance, coherence match, and metadata.
    """
    if latent_state.shape != universe_state.shape:
        raise ValueError(
            f"Shape mismatch: latent {latent_state.shape} vs universe {universe_state.shape}"
        )

    # 1. L2 Distance (Euclidean)
    l2_dist = torch.norm(latent_state - universe_state, p=2).item()

    # 2. Coherence Match (Higher is better, inverse of normalized distance)
    # Range [0, 1] assuming vectors are normalized to [-1, 1]
    # Max possible distance in 12D [-1, 1] cube is sqrt(12 * 2^2) = sqrt(48)
    max_dist = 6.9282  # sqrt(48)
    coherence_match = max(0.0, 1.0 - (l2_dist / max_dist))

    return {
        "l2_distance": l2_dist,
        "coherence_match": coherence_match,
        "is_aligned": coherence_match >= 0.85,  # Alignment threshold from spec
    }
