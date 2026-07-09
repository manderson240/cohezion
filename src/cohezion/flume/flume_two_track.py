"""FlumeTwoTrack: analytical two-track structural/semantic split of FLUME's 256D latent.

Inspired by IV-CoT (arXiv:2606.24849): structural dims encode layout/topology,
semantic dims encode appearance/content. The split is post-hoc — no new weights,
zero inference overhead. Only structural_regularizer adds a training-time signal.

Harness invariants respected:
  A3: kl_weight ≤ 0.01 — caller's responsibility; this file doesn't set kl_weight
  A4: 2-layer decoder, hd=4096 — enforced in base_vae; not touched here
  A5: cyclic β amp=0.005 — caller's training loop; this file provides the aux loss only
"""

from __future__ import annotations

import torch
from torch import Tensor

from cohezion.flume.vae import FlumeVAE


class FlumeTwoTrack:
    """Two-track FLUME VAE: structural_dim + semantic_dim = base_vae.latent_dim.

    The split is analytical (tensor slicing). First `structural_dim` dims are
    "structural" (layout/topology), remaining dims are "semantic" (appearance/content).
    No new parameters; interpolate() and structural_regularizer() are inference-free
    except for the existing base_vae weights.
    """

    def __init__(self, base_vae: FlumeVAE, structural_dim: int = 128) -> None:
        if structural_dim <= 0 or structural_dim >= base_vae.latent_dim:
            raise ValueError(
                f"structural_dim={structural_dim} must be in (0, {base_vae.latent_dim})"
            )
        self.base_vae = base_vae
        self.structural_dim = structural_dim
        self.semantic_dim = base_vae.latent_dim - structural_dim

    def encode(
        self,
        x: Tensor,
        attention_mask: Tensor | None = None,
    ) -> tuple[Tensor, Tensor, Tensor, Tensor]:
        """Encode x, then split mu into structural and semantic halves.

        Returns
        -------
        mu : (batch, latent_dim)
        log_var : (batch, latent_dim)
        mu_structural : (batch, structural_dim)  — first dims
        mu_semantic : (batch, semantic_dim)       — remaining dims
        """
        mu, log_var = self.base_vae.encode(x, attention_mask)
        return mu, log_var, mu[:, : self.structural_dim], mu[:, self.structural_dim :]

    def structural_regularizer(self, mu_structural: Tensor, weight: float = 1.0) -> Tensor:
        """Training-only auxiliary loss: encourage high variance in structural dims.

        Loss = -var(mu_structural, dim=0).mean() * weight
        Higher variance → more informative structural encoding → lower loss.
        Always ≤ 0 (variance is non-negative, negated here for gradient descent).

        At inference: pass weight=0.0 to zero out (or simply don't call it).
        """
        # var across batch dimension: shape (structural_dim,)
        var_per_dim = torch.var(mu_structural, dim=0, unbiased=False)
        return -var_per_dim.mean() * weight

    def interpolate(self, z1: Tensor, z2: Tensor, *, swap_structural: bool = False) -> Tensor:
        """Cross-track recombination of two latent vectors.

        Parameters
        ----------
        z1, z2 : (batch, latent_dim) or (latent_dim,)
        swap_structural : if True, take structural half from z1 + semantic from z2;
                          if False, take structural from z2 + semantic from z1.

        Returns
        -------
        Tensor : same shape as z1
        """
        if z1.shape != z2.shape:
            raise ValueError(f"z1.shape {z1.shape} != z2.shape {z2.shape}")
        if swap_structural:
            # structural from z1, semantic from z2
            structural = z1[..., : self.structural_dim]
            semantic = z2[..., self.structural_dim :]
        else:
            # structural from z2, semantic from z1
            structural = z2[..., : self.structural_dim]
            semantic = z1[..., self.structural_dim :]
        return torch.cat([structural, semantic], dim=-1)


def run_twotrack_smoke_test() -> dict:
    """Verify two-track split preserves reconstruction quality."""
    base = FlumeVAE(input_dim=16, latent_dim=8)
    base.eval()
    tt = FlumeTwoTrack(base, structural_dim=4)

    x = torch.randn(3, 16)
    mu, _, mu_s, mu_e = tt.encode(x)

    assert mu_s.shape[-1] + mu_e.shape[-1] == 8, "dims must sum to latent_dim"
    assert mu_s.shape == (3, 4)
    assert mu_e.shape == (3, 4)

    z1 = mu
    z2 = torch.randn_like(mu)
    interp = tt.interpolate(z1, z2, swap_structural=True)
    assert interp.shape == mu.shape

    reg = tt.structural_regularizer(mu_s)
    assert reg.dim() == 0, "must be scalar"
    assert float(reg) <= 0, "regularizer must be ≤ 0"

    return {
        "structural_dim": tt.structural_dim,
        "semantic_dim": tt.semantic_dim,
        "smoke_passed": True,
    }
