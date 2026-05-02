import torch
import torch.nn.functional as F


def lerp(z1: torch.Tensor, z2: torch.Tensor, alpha: float) -> torch.Tensor:
    """
    Linear interpolation between two vectors.

    Args:
        z1: Start vector.
        z2: End vector.
        alpha: Interpolation factor in [0, 1].

    Returns:
        torch.Tensor: Interpolated vector.
    """
    return (1.0 - alpha) * z1 + alpha * z2


def slerp(z1: torch.Tensor, z2: torch.Tensor, alpha: float, eps: float = 1e-7) -> torch.Tensor:
    """
    Spherical linear interpolation between two vectors.

    Args:
        z1: Start vector.
        z2: End vector.
        alpha: Interpolation factor in [0, 1].
        eps: Small epsilon for numerical stability.

    Returns:
        torch.Tensor: Interpolated vector on the hypersphere.
    """
    # Normalize to unit sphere
    z1_norm = z1 / (z1.norm(dim=-1, keepdim=True) + eps)
    z2_norm = z2 / (z2.norm(dim=-1, keepdim=True) + eps)

    # Calculate cosine of the angle between vectors
    dot = torch.sum(z1_norm * z2_norm, dim=-1, keepdim=True)
    dot = torch.clamp(dot, -1.0, 1.0)

    theta = torch.acos(dot)

    if theta < eps:
        return lerp(z1, z2, alpha)

    sin_theta = torch.sin(theta)

    res = (torch.sin((1.0 - alpha) * theta) * z1_norm + torch.sin(alpha * theta) * z2_norm) / sin_theta

    # Scale back to original average norm if needed?
    # For FLUME, we usually operate on unit-sphere or normalized latents.
    return res.squeeze()


def similarity_score(z1: torch.Tensor, z2: torch.Tensor) -> float:
    """
    Computes conceptual similarity based on cosine distance.
    Normalized to [0, 1] range.

    Args:
        z1: First thought vector.
        z2: Second thought vector.

    Returns:
        float: Similarity score.
    """
    # Use existing manifold utility if possible, but for primitives:
    cos_sim = F.cosine_similarity(z1.flatten(), z2.flatten(), dim=0)
    return float((cos_sim + 1.0) / 2.0)
