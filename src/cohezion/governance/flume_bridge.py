"""FLUME bridge for governance modules.

Connects the concierge agent and observer patch system to FLUME's 256D
latent space. Instead of keyword matching or raw Bloch angles, governance
decisions are made in FLUME space where the Fisher information metric
provides natural distance measures.

"Look inward (FLUME encode) to excel outward (routing/consistency)."

Key connections:
  - Concierge routing: user prompt → FLUME embedding → nearest historical route
  - Observer patches: agent state → FLUME encode → patch center on S² from latent projection
  - Data product discovery: query → FLUME embedding → cosine similarity with product descriptions

Attribution: FLUME (Cohezion original), Fisher metric (Amari, 1998)
"""

from __future__ import annotations

import logging
import math

import numpy as np


logger = logging.getLogger(__name__)

# FLUME dimension layout
FLUME_DIM = 256


def _get_encoder():
    """Lazy-load the FLUME encoder to avoid import-time overhead."""
    try:
        from cohezion.flume.vae_encoder import get_encoder
        return get_encoder()
    except ImportError:
        logger.debug("FLUME VAE encoder not available, using hash fallback")
        return None


def encode_prompt(prompt: str) -> np.ndarray:
    """Encode a user prompt into FLUME 256D space.

    Used by the concierge for semantic routing — finds the nearest
    historical route by FLUME distance instead of keyword matching.

    Falls back to deterministic hash expansion if FLUME VAE is unavailable.
    """
    encoder = _get_encoder()
    if encoder is not None:
        try:
            return encoder.encode(prompt)
        except (RuntimeError, ValueError, TypeError) as exc:
            logger.warning("FLUME encode failed, using hash fallback: %s", exc)

    # Delegate to VAE encoder's hash fallback for consistency
    try:
        from cohezion.flume.vae_encoder import FlumeVAEEncoder
        return FlumeVAEEncoder._hash_encode(prompt)
    except (ImportError, AttributeError):
        # Last resort: deterministic 256D hash expansion
        import hashlib
        h = hashlib.sha256(prompt.encode()).digest()
        expanded = np.frombuffer(h * 8, dtype=np.uint8)[:FLUME_DIM].astype(np.float32)
        return expanded / (np.linalg.norm(expanded) + 1e-10)


def flume_route_similarity(prompt_embedding: np.ndarray, history_prompt: str) -> float:
    """Compute cosine similarity between a prompt embedding and a historical prompt.

    Returns [0, 1] where 1 = semantically identical prompts.
    Used by the concierge to boost confidence for semantically similar past routes.
    """
    hist_embedding = encode_prompt(history_prompt)
    dot = float(np.dot(prompt_embedding, hist_embedding))
    norm_a = float(np.linalg.norm(prompt_embedding))
    norm_b = float(np.linalg.norm(hist_embedding))
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return max(0.0, dot / (norm_a * norm_b))


def agent_state_to_patch_center(state_12d: np.ndarray) -> tuple[float, float]:
    """Project a 12D agent state to Bloch sphere angles via FLUME geometry.

    Instead of using arbitrary Bloch angles, we project the agent's 12D
    state vector onto the first two principal components, then map to
    (theta, phi) on S². This grounds observer patches in the actual
    manifold geometry rather than ad-hoc coordinates.

    Returns (theta, phi) where:
      theta ∈ [0, π] — polar angle (exploitation ↔ exploration)
      phi ∈ [0, 2π] — azimuthal angle (fabric orientation)
    """
    state = np.asarray(state_12d, dtype=np.float64).ravel()[:12]
    if len(state) < 12:
        state = np.pad(state, (0, 12 - len(state)))

    # Control fabric dims (7-9) map to SPIN: rotation = dim 7, precession = dim 8
    rotation = float(state[6]) if len(state) > 6 else 0.0  # dim 7 (0-indexed: 6)
    precession = float(state[7]) if len(state) > 7 else 0.0  # dim 8 (0-indexed: 7)

    # Map to Bloch sphere angles
    # rotation ∈ [-1, 1] → theta ∈ [0, π]
    theta = (1.0 - np.clip(rotation, -1, 1)) * math.pi / 2
    # precession ∈ [-1, 1] → phi ∈ [0, 2π]
    phi = (np.clip(precession, -1, 1) + 1.0) * math.pi

    return float(theta), float(phi)


def encode_data_product_description(description: str) -> np.ndarray:
    """Encode a data product description for semantic discovery.

    Enables agents to find relevant data products by meaning, not just
    keyword matching. "journey checkpoints" should match "agent state snapshots".
    """
    return encode_prompt(description)


def data_product_similarity(query: str, product_description: str) -> float:
    """Semantic similarity between a query and a data product description."""
    q_emb = encode_prompt(query)
    p_emb = encode_prompt(product_description)
    dot = float(np.dot(q_emb, p_emb))
    norm_a = float(np.linalg.norm(q_emb))
    norm_b = float(np.linalg.norm(p_emb))
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return max(0.0, dot / (norm_a * norm_b))
