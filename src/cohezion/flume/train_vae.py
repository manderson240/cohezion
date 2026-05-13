"""Training pipeline for FLUME VAE v2.

Features:
  - KL annealing (linear warmup)
  - Free-bits per dimension
  - Gradient clipping
  - Checkpoint save/load
  - Active unit monitoring
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from cohezion.flume.vae import FlumeVAE, flume_vae_loss


if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)


def kl_annealing_beta(step: int, warmup_steps: int, max_beta: float) -> float:
    """Linear KL annealing: 0 → max_beta over warmup_steps."""
    if warmup_steps <= 0:
        return max_beta
    return min(max_beta, max_beta * step / warmup_steps)


def count_active_units(mu: torch.Tensor, threshold: float = 0.01) -> int:
    """Count latent dimensions with variance above threshold across samples."""
    var_per_dim = mu.var(dim=0)
    return int((var_per_dim > threshold).sum().item())


class VAETrainer:
    """Train FLUME VAE with KL annealing and monitoring."""

    def __init__(
        self,
        model: FlumeVAE,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
        max_beta: float = 0.1,
        warmup_fraction: float = 0.3,
        free_bits: float = 0.125,
        lambda_coherence: float = 0.01,
        grad_clip: float = 1.0,
    ) -> None:
        self.model = model
        self.max_beta = max_beta
        self.warmup_fraction = warmup_fraction
        self.free_bits = free_bits
        self.lambda_coherence = lambda_coherence
        self.grad_clip = grad_clip

        self.optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    def train(
        self,
        data: torch.Tensor,
        epochs: int = 50,
        batch_size: int = 64,
        contrastive_pairs: list[tuple[int, int]] | None = None,
        lambda_contrastive: float = 0.0,
        lambda_sim_match: float = 0.0,
    ) -> list[dict[str, float]]:
        """Train VAE on embedded data. Returns per-epoch metrics."""
        n_samples = data.shape[0]
        indices = torch.arange(n_samples)
        dataset = TensorDataset(data, indices)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        # Build pair lookup for fast batch-local pair finding
        pair_map: dict[int, list[int]] = {}
        if contrastive_pairs:
            for a, b in contrastive_pairs:
                pair_map.setdefault(a, []).append(b)
                pair_map.setdefault(b, []).append(a)

        total_steps = epochs * len(loader)
        warmup_steps = int(total_steps * self.warmup_fraction)

        history: list[dict[str, float]] = []
        global_step = 0

        self.model.train()
        for epoch in range(epochs):
            epoch_losses: dict[str, list[float]] = {
                "total_loss": [],
                "recon_loss": [],
                "kl_loss": [],
                "coherence_loss": [],
                "contrastive_loss": [],
                "sim_match_loss": [],
            }
            current_beta = 0.0

            for batch_data, batch_indices in loader:
                current_beta = kl_annealing_beta(global_step, warmup_steps, self.max_beta)

                recon, mu, logvar, z = self.model(batch_data)

                # Find contrastive pairs within this batch
                batch_pairs: list[tuple[int, int]] = []
                if lambda_contrastive > 0 and pair_map:
                    idx_list = batch_indices.tolist()
                    idx_to_local = {global_idx: local for local, global_idx in enumerate(idx_list)}
                    for local_i, global_i in enumerate(idx_list):
                        for partner in pair_map.get(global_i, []):
                            if partner in idx_to_local and partner > global_i:
                                batch_pairs.append((local_i, idx_to_local[partner]))

                losses = flume_vae_loss(
                    batch_data,
                    recon,
                    mu,
                    logvar,
                    beta=current_beta,
                    free_bits=self.free_bits,
                    lambda_coherence=self.lambda_coherence,
                    lambda_contrastive=lambda_contrastive,
                    lambda_sim_match=lambda_sim_match,
                    contrastive_pairs=batch_pairs if batch_pairs else None,
                    z=z,
                )

                self.optimizer.zero_grad()
                losses["total_loss"].backward()

                if self.grad_clip > 0:
                    nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)

                self.optimizer.step()
                global_step += 1

                for k in epoch_losses:
                    epoch_losses[k].append(losses[k].item())

            avg = {k: sum(v) / len(v) for k, v in epoch_losses.items()}
            avg["beta"] = current_beta
            avg["epoch"] = epoch
            history.append(avg)

            if (epoch + 1) % 10 == 0 or epoch == 0:
                logger.info(
                    "Epoch %d: loss=%.4f recon=%.4f kl=%.4f contr=%.4f sim_match=%.4f β=%.4f",
                    epoch,
                    avg["total_loss"],
                    avg["recon_loss"],
                    avg["kl_loss"],
                    avg["contrastive_loss"],
                    avg["sim_match_loss"],
                    current_beta,
                )

        return history

    def save_checkpoint(self, path: Path, epoch: int, metrics: dict | None = None) -> None:
        """Save model + optimizer state."""
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "epoch": epoch,
                "metrics": metrics or {},
                "config": {
                    "input_dim": getattr(self.model, "input_dim", None),
                    "latent_dim": getattr(self.model, "latent_dim", 256),
                    "max_beta": self.max_beta,
                    "free_bits": self.free_bits,
                },
            },
            path,
        )
        logger.info("Saved checkpoint to %s (epoch %d)", path, epoch)

    def load_checkpoint(self, path: Path) -> dict:
        """Load checkpoint into current model/optimizer."""
        ckpt = torch.load(path, map_location="cpu", weights_only=True)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        logger.info("Loaded checkpoint from %s (epoch %d)", path, ckpt["epoch"])
        return {"epoch": ckpt["epoch"], "metrics": ckpt["metrics"], "config": ckpt["config"]}
