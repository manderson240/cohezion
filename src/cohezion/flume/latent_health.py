"""SVD-based latent basis health monitor for detecting posterior collapse in FLUME VAE.

Implements the effective rank metric from Roy & Vetterli (2007):
    effective_rank = exp(H(σ / ‖σ‖₁))
where H is the Shannon entropy (in nats) of the normalised singular value distribution.

This is an empirical complement to harness invariant A3 (kl_weight ≤ 0.01 guard):
- A3 prevents posterior collapse by constraining the KL regularisation strength.
- LatentBasisMonitor detects collapse empirically by measuring how much of the latent
  space is actually used — a low rank_ratio means all inputs map to the same subspace.

Usage::

    from cohezion.flume.latent_health import LatentBasisMonitor

    monitor = LatentBasisMonitor(expected_rank_ratio=0.5)
    monitor.update(z_batch)            # z_batch: [batch, latent_dim]
    health = monitor.compute_health()  # {"effective_rank": ..., "is_healthy": ...}
    monitor.reset()                    # clear for next evaluation window
"""

import torch


class LatentBasisMonitor:
    """Accumulates latent codes and measures effective rank via SVD.

    Effective rank (Roy & Vetterli 2007): ``exp(H(σ/‖σ‖₁))`` where σ are the singular
    values of the accumulated, mean-centred latent code matrix. A ratio of
    ``effective_rank / latent_dim`` below ``expected_rank_ratio`` signals posterior
    collapse — the encoder maps all inputs to a low-dimensional subspace.

    Complement to A3 harness invariant (kl_weight ≤ 0.01): A3 prevents collapse via
    regularisation; this monitor detects it from the geometry of the latent subspace.
    """

    def __init__(self, expected_rank_ratio: float = 0.5) -> None:
        """
        Args:
            expected_rank_ratio: Minimum healthy ratio of ``effective_rank / latent_dim``.
                Default 0.5 means ≥ 50 % of latent dimensions should be effectively used.
                For small sample sizes (< 512 in 256-D), the rank is bounded by
                ``min(n_samples - 1, latent_dim)``; use a lower threshold (e.g. 0.01–0.05)
                when evaluating with few batches.
        """
        self.expected_rank_ratio = expected_rank_ratio
        self._samples: list[torch.Tensor] = []

    @property
    def has_samples(self) -> bool:
        """True iff at least one batch has been passed to update()."""
        return bool(self._samples)

    def update(self, z: torch.Tensor) -> None:
        """Accumulate a batch of latent codes.

        Args:
            z: Latent codes, shape ``[batch, latent_dim]``.  Detached and moved to CPU.
        """
        self._samples.append(z.detach().cpu())

    def compute_health(self) -> dict:
        """Compute SVD-based health metrics from accumulated samples.

        Uses ``torch.linalg.svd`` (not the deprecated ``torch.svd``).

        Returns:
            dict with keys:

            * ``effective_rank`` *(float)* – ``exp(H(σ/‖σ‖₁))``.
            * ``rank_ratio`` *(float)* – ``effective_rank / latent_dim``.
            * ``is_healthy`` *(bool)* – ``rank_ratio >= expected_rank_ratio``.
            * ``top_singular_values`` *(list[float])* – top-5 (or fewer) singular values.

        Raises:
            ValueError: If no samples have been accumulated yet.
        """
        if not self._samples:
            raise ValueError("No samples accumulated. Call update() first.")

        z_matrix = torch.cat(self._samples, dim=0)  # [N, D]
        latent_dim = z_matrix.shape[1]

        # Centre the matrix so SVD captures variance, not mean offset.
        z_centred = z_matrix - z_matrix.mean(dim=0, keepdim=True)

        # SVD — torch.linalg.svd, NOT deprecated torch.svd.
        # full_matrices=False: S has shape (min(N, D),).
        _, S, _ = torch.linalg.svd(z_centred, full_matrices=False)

        s_sum = S.sum()
        if s_sum < 1e-10:
            # All singular values are effectively zero → complete collapse → rank = 1.
            effective_rank = 1.0
        else:
            s_norm = S / s_sum
            # Shannon entropy of the normalised singular-value distribution (nats).
            entropy = -(s_norm * torch.log(s_norm.clamp(min=1e-10))).sum()
            effective_rank = float(entropy.exp().item())

        rank_ratio = effective_rank / latent_dim
        is_healthy = rank_ratio >= self.expected_rank_ratio

        top_k = min(5, S.shape[0])
        top_singular_values: list[float] = S[:top_k].tolist()

        return {
            "effective_rank": effective_rank,
            "rank_ratio": rank_ratio,
            "is_healthy": is_healthy,
            "top_singular_values": top_singular_values,
        }

    def reset(self) -> None:
        """Clear all accumulated samples."""
        self._samples = []
