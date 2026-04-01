"""Evaluation framework for FLUME VAE v2.

Metrics for all red flags:
  1. KL health (collapse detection, active units)
  2. Reconstruction fidelity (cosine similarity)
  3. Paraphrase discrimination (Precision@1)
  4. Similarity preservation (Spearman rho)
"""

from __future__ import annotations

import logging

import numpy as np
import torch
from scipy import stats

from cohezion.flume.train_vae import count_active_units
from cohezion.flume.vae import FlumeVAE, flume_vae_loss


logger = logging.getLogger(__name__)


def reconstruction_cosine_similarity(original: np.ndarray, reconstructed: np.ndarray) -> float:
    """Mean cosine similarity between original and reconstructed embeddings."""
    # Normalize
    orig_norm = original / (np.linalg.norm(original, axis=1, keepdims=True) + 1e-8)
    recon_norm = reconstructed / (np.linalg.norm(reconstructed, axis=1, keepdims=True) + 1e-8)
    # Per-sample cosine similarity
    cos_sims = (orig_norm * recon_norm).sum(axis=1)
    return float(cos_sims.mean())


def paraphrase_precision_at_1(embeddings: np.ndarray, pairs: list[tuple[int, int]]) -> float:
    """Precision@1: for each anchor, is the paraphrase the nearest neighbor?"""
    if not pairs:
        return 0.0

    # Normalize embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8
    normed = embeddings / norms

    # Cosine similarity matrix
    sim_matrix = normed @ normed.T
    # Zero out self-similarity
    np.fill_diagonal(sim_matrix, -np.inf)

    hits = 0
    total = 0
    for anchor, positive in pairs:
        nn = int(np.argmax(sim_matrix[anchor]))
        if nn == positive:
            hits += 1
        total += 1

    return float(hits / total) if total > 0 else 0.0


def kl_health_check(
    kl_value: float,
    active_units: int,
    total_units: int,
    kl_threshold: float = 0.1,
    active_threshold: int = 128,
) -> dict:
    """Check KL divergence health (Red Flag 1)."""
    reasons = []
    if kl_value < kl_threshold:
        reasons.append(f"KL too low: {kl_value:.4f} < {kl_threshold}")
    if active_units < active_threshold:
        reasons.append(f"Active units too low: {active_units}/{total_units} < {active_threshold}")

    return {
        "healthy": len(reasons) == 0,
        "kl_value": kl_value,
        "active_units": active_units,
        "total_units": total_units,
        "reason": "; ".join(reasons) if reasons else "OK",
    }


def similarity_preservation_spearman(original: np.ndarray, latent: np.ndarray) -> float:
    """Spearman rank correlation between pairwise similarities in original and latent space."""
    n = original.shape[0]
    if n < 3:
        return 0.0

    # Normalize
    orig_norm = original / (np.linalg.norm(original, axis=1, keepdims=True) + 1e-8)
    lat_norm = latent / (np.linalg.norm(latent, axis=1, keepdims=True) + 1e-8)

    # Pairwise cosine similarities (upper triangle)
    orig_sims = orig_norm @ orig_norm.T
    lat_sims = lat_norm @ lat_norm.T

    # Extract upper triangle
    triu_idx = np.triu_indices(n, k=1)
    orig_flat = orig_sims[triu_idx]
    lat_flat = lat_sims[triu_idx]

    rho, _ = stats.spearmanr(orig_flat, lat_flat)
    return float(rho)


class VAEEvaluator:
    """Run full evaluation suite on trained FLUME VAE."""

    def __init__(self, model: FlumeVAE) -> None:
        self.model = model

    @torch.no_grad()
    def evaluate(
        self,
        data: torch.Tensor,
        pairs: list[tuple[int, int]],
    ) -> dict:
        """Run all red-flag evaluations. Returns metrics dict."""
        self.model.eval()

        # Forward pass
        recon, mu, logvar, _z = self.model(data)

        # Reconstruction fidelity (Red Flag 2)
        orig_np = data.cpu().numpy()
        recon_np = recon.cpu().numpy()
        recon_sim = reconstruction_cosine_similarity(orig_np, recon_np)

        # KL health (Red Flag 1)
        losses = flume_vae_loss(data, recon, mu, logvar, beta=1.0, free_bits=0.0)
        kl_value = losses["kl_loss"].item()
        active = count_active_units(mu)
        kl_check = kl_health_check(kl_value, active, mu.shape[1])

        # Paraphrase discrimination (Red Flag 3)
        # Use mu (latent mean) as embedding
        mu_np = mu.cpu().numpy()
        p_at_1 = paraphrase_precision_at_1(mu_np, pairs)

        # Similarity preservation (Red Flag 4)
        spearman = similarity_preservation_spearman(orig_np, mu_np)

        results = {
            "reconstruction_cosine_sim": recon_sim,
            "kl_health": kl_check,
            "kl_value": kl_value,
            "active_units": active,
            "paraphrase_p_at_1": p_at_1,
            "similarity_spearman": spearman,
        }

        logger.info(
            "Evaluation results: %s", {k: v for k, v in results.items() if k != "kl_health"}
        )

        return results
