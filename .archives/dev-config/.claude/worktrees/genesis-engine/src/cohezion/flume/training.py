"""Training pipeline for the FLUME autoencoder (VAE).

Trains the FlumeEncoder to compress and reconstruct latent vectors
with a combined loss: MSE reconstruction + KL divergence + coherence
regularization toward HIHO 0.5 target.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader


logger = logging.getLogger(__name__)


@dataclass
class TrainConfig:
    """FLUME VAE training configuration."""

    z_dim: int = 256
    batch_size: int = 64
    epochs: int = 50
    lr: float = 1e-3
    kl_weight: float = 0.1
    coherence_weight: float = 0.05
    grad_clip: float = 1.0
    lr_schedule: str = "cosine"  # "cosine" or "step"
    checkpoint_dir: str = "data/flume/checkpoints"
    log_interval: int = 10
    data_dir: str = "data/mass_sim/artifacts"
    max_samples: int = 100_000


class FlumeVAETrainer:
    """Train a simple VAE on FLUME latent vectors.

    Since the full FlumeEncoder requires a tokenizer, this trainer
    operates on a simpler encoder/decoder that works directly on
    latent vectors (bypassing text tokenization).

    Architecture:
        Encoder: z_dim -> hidden -> mu, log_var (z_dim each)
        Decoder: z_dim -> hidden -> z_dim (reconstruction)
    """

    def __init__(self, config: TrainConfig | None = None) -> None:
        self.config = config or TrainConfig()
        self.device = torch.device("cpu")  # No CUDA on Strix Halo

        z = self.config.z_dim
        hidden = z * 2

        # Encoder: outputs mu and log_var for VAE
        self.encoder = nn.Sequential(
            nn.Linear(z, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
        ).to(self.device)
        self.mu_head = nn.Linear(hidden, z).to(self.device)
        self.logvar_head = nn.Linear(hidden, z).to(self.device)

        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(z, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, z),
        ).to(self.device)

        self._all_params = (
            list(self.encoder.parameters())
            + list(self.mu_head.parameters())
            + list(self.logvar_head.parameters())
            + list(self.decoder.parameters())
        )

    def _reparameterize(self, mu: torch.Tensor, log_var: torch.Tensor) -> torch.Tensor:
        """VAE reparameterization trick: z = mu + std * eps."""
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + std * eps

    def _forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Full VAE forward pass. Returns (reconstruction, mu, log_var)."""
        h = self.encoder(x)
        mu = self.mu_head(h)
        log_var = self.logvar_head(h)
        z = self._reparameterize(mu, log_var)
        recon = self.decoder(z)
        return recon, mu, log_var

    def _loss(
        self,
        x: torch.Tensor,
        recon: torch.Tensor,
        mu: torch.Tensor,
        log_var: torch.Tensor,
    ) -> tuple[torch.Tensor, dict[str, float]]:
        """Compute VAE loss: MSE + KL + coherence regularization."""
        # Reconstruction loss
        mse = nn.functional.mse_loss(recon, x)

        # KL divergence
        kl = -0.5 * torch.mean(1 + log_var - mu.pow(2) - log_var.exp())

        # Coherence regularization: penalize mu mean deviating from 0.5
        mu_mean = mu.mean(dim=-1)
        coherence_loss = torch.mean((mu_mean - 0.5) ** 2)

        total = mse + self.config.kl_weight * kl + self.config.coherence_weight * coherence_loss

        metrics = {
            "mse": mse.item(),
            "kl": kl.item(),
            "coherence_loss": coherence_loss.item(),
            "total": total.item(),
        }
        return total, metrics

    def train(self, dataset: torch.utils.data.Dataset | None = None) -> list[dict]:
        """Run training loop.

        Parameters
        ----------
        dataset : Dataset, optional
            Training dataset. If None, loads from config.data_dir.

        Returns
        -------
        list[dict]
            Per-epoch training metrics.
        """
        if dataset is None:
            from cohezion.flume.dataset import FlumeTrajectoryDataset

            dataset = FlumeTrajectoryDataset(
                data_dir=self.config.data_dir,
                max_samples=self.config.max_samples,
                z_dim=self.config.z_dim,
            )

        loader = DataLoader(
            dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            drop_last=len(dataset) > self.config.batch_size,
        )

        optimizer = optim.Adam(self._all_params, lr=self.config.lr)

        if self.config.lr_schedule == "cosine":
            scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=self.config.epochs)
        else:
            scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.5)

        checkpoint_dir = Path(self.config.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        epoch_metrics: list[dict] = []
        logger.info(
            f"Starting FLUME VAE training: {self.config.epochs} epochs, "
            f"{len(dataset)} samples, batch_size={self.config.batch_size}"
        )

        for epoch in range(1, self.config.epochs + 1):
            epoch_start = time.perf_counter()
            batch_metrics: list[dict] = []

            for batch in loader:
                x = batch.to(self.device)
                recon, mu, log_var = self._forward(x)
                loss, metrics = self._loss(x, recon, mu, log_var)

                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self._all_params, self.config.grad_clip)
                optimizer.step()

                batch_metrics.append(metrics)

            scheduler.step()

            # Aggregate epoch metrics
            epoch_avg = {k: np.mean([m[k] for m in batch_metrics]) for k in batch_metrics[0]}
            epoch_avg["epoch"] = epoch
            epoch_avg["lr"] = scheduler.get_last_lr()[0]
            epoch_avg["elapsed_s"] = time.perf_counter() - epoch_start
            epoch_metrics.append(epoch_avg)

            if epoch % self.config.log_interval == 0 or epoch == 1:
                logger.info(
                    f"Epoch {epoch}/{self.config.epochs} | "
                    f"MSE: {epoch_avg['mse']:.4f} | "
                    f"KL: {epoch_avg['kl']:.4f} | "
                    f"Coh: {epoch_avg['coherence_loss']:.4f} | "
                    f"Total: {epoch_avg['total']:.4f} | "
                    f"LR: {epoch_avg['lr']:.6f}"
                )

            # Save checkpoint
            if epoch % 25 == 0 or epoch == self.config.epochs:
                ckpt = {
                    "epoch": epoch,
                    "encoder": self.encoder.state_dict(),
                    "mu_head": self.mu_head.state_dict(),
                    "logvar_head": self.logvar_head.state_dict(),
                    "decoder": self.decoder.state_dict(),
                    "optimizer": optimizer.state_dict(),
                    "config": self.config.__dict__,
                }
                path = checkpoint_dir / f"flume_vae_ep{epoch}.pt"
                torch.save(ckpt, path)
                logger.info(f"Checkpoint saved: {path}")

        return epoch_metrics

    def train_from_experiences(
        self,
        collector: Any | None = None,
        max_samples: int = 100_000,
        min_real_samples: int = 10,
    ) -> list[dict]:
        """Train VAE on real experience data from ExperienceCollector.

        Connects ExperienceCollector -> ExperienceEncoder -> ExperienceDataset
        -> VAE training. Falls back to synthetic data if insufficient real samples.

        Parameters
        ----------
        collector : ExperienceCollector, optional
            If None, creates a default collector.
        max_samples : int
            Maximum samples to collect.
        min_real_samples : int
            Minimum real samples required before falling back to synthetic.

        Returns
        -------
        list[dict]
            Per-epoch training metrics.
        """
        from cohezion.flume.dataset import SyntheticFlumeDataset
        from cohezion.flume.experience_collector import ExperienceCollector
        from cohezion.flume.experience_dataset import ExperienceDataset

        if collector is None:
            collector = ExperienceCollector()

        # Collect real experiences
        experiences = collector.collect_all(max_samples=max_samples)

        if len(experiences) >= min_real_samples:
            logger.info("Training VAE on %d real experience samples", len(experiences))
            dataset = ExperienceDataset(experiences, seed=42)
        else:
            logger.warning(
                "Only %d real samples (need %d). Falling back to synthetic data.",
                len(experiences),
                min_real_samples,
            )
            dataset = SyntheticFlumeDataset(
                n_samples=max(1000, self.config.batch_size * 20),
                z_dim=self.config.z_dim,
            )

        return self.train(dataset=dataset)
