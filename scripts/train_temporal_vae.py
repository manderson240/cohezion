"""Train the FLUME Phase 2 TemporalVAE on overnight trajectory sequences.

Usage:
    uv run python scripts/train_temporal_vae.py
    uv run python scripts/train_temporal_vae.py --epochs 50 --batch-size 64

Saves checkpoint to: data/flume/checkpoints_v2/temporal_vae_best.pt
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from cohezion.flume.temporal_encoder import TemporalDecoder, TemporalEncoder
from cohezion.flume.trajectory_dataset import (
    TrajectorySequenceDataset,
    collate_sequences,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path("data/flume/checkpoints_v2")
DEFAULT_DATA = Path("data/overnight/journeys.jsonl")


def temporal_vae_loss(
    recon: torch.Tensor,
    target: torch.Tensor,
    mu: torch.Tensor,
    logvar: torch.Tensor,
    beta: float = 1.0,
    padding_mask: torch.Tensor | None = None,
) -> dict[str, torch.Tensor]:
    """Compute VAE loss components.

    Parameters
    ----------
    recon : [B, T, step_dim]  Reconstructed sequence
    target : [B, T, step_dim] Ground truth
    mu : [B, latent_dim]
    logvar : [B, latent_dim]
    beta : KL weight (annealed from 0 → max_beta during training)
    padding_mask : [B, T] bool, True = padding position

    Returns dict with 'total', 'recon', 'kl' keys.
    """
    if padding_mask is not None:
        # Only compute reconstruction loss on valid (non-padded) positions
        valid = ~padding_mask  # [B, T]
        recon_loss = F.mse_loss(
            recon[valid.unsqueeze(-1).expand_as(recon)],
            target[valid.unsqueeze(-1).expand_as(target)],
        )
    else:
        recon_loss = F.mse_loss(recon, target)

    kl_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
    total = recon_loss + beta * kl_loss
    return {"total": total, "recon": recon_loss, "kl": kl_loss}


def train(
    data_path: Path = DEFAULT_DATA,
    epochs: int = 30,
    batch_size: int = 32,
    lr: float = 3e-4,
    max_seq_len: int = 64,
    max_beta: float = 0.1,
    device_name: str = "cpu",
    checkpoint_dir: Path = CHECKPOINT_DIR,
    max_sessions: int | None = None,
) -> dict:
    """Train TemporalVAE and return final metrics."""
    device = torch.device(device_name)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # ── Data ──────────────────────────────────────────────────────────────────
    logger.info("Loading trajectory data from %s", data_path)
    ds = TrajectorySequenceDataset(data_path, max_seq_len=max_seq_len)
    if max_sessions is not None:
        # Subsample for fast runs / smoke tests
        indices = list(range(min(max_sessions, len(ds))))
        from torch.utils.data import Subset

        ds = Subset(ds, indices)

    loader = DataLoader(
        ds,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=collate_sequences,
        num_workers=0,
    )
    logger.info("Dataset: %d sessions, %d batches/epoch", len(ds), len(loader))

    # ── Model ─────────────────────────────────────────────────────────────────
    encoder = TemporalEncoder().to(device)
    decoder = TemporalDecoder().to(device)

    params = list(encoder.parameters()) + list(decoder.parameters())
    optimizer = torch.optim.AdamW(params, lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    total_steps = epochs * max(len(loader), 1)
    warmup_steps = int(total_steps * 0.3)  # KL annealing over first 30%

    # ── Training loop ─────────────────────────────────────────────────────────
    best_loss = float("inf")
    history: list[dict] = []
    step = 0

    for epoch in range(1, epochs + 1):
        encoder.train()
        decoder.train()

        epoch_recon, epoch_kl, epoch_total = 0.0, 0.0, 0.0
        n_batches = 0

        for sequences, padding_mask in loader:
            sequences = sequences.to(device)
            padding_mask = padding_mask.to(device)

            # KL annealing: linearly ramp beta from 0 → max_beta
            beta = min(max_beta, max_beta * step / max(warmup_steps, 1))

            # Forward
            mu, logvar = encoder.encode(sequences, padding_mask=padding_mask)
            z = encoder.reparameterize(mu, logvar)
            recon = decoder.decode(z, sequences)

            losses = temporal_vae_loss(recon, sequences, mu, logvar, beta=beta, padding_mask=padding_mask)

            optimizer.zero_grad()
            losses["total"].backward()
            torch.nn.utils.clip_grad_norm_(params, max_norm=1.0)
            optimizer.step()

            epoch_recon += losses["recon"].item()
            epoch_kl += losses["kl"].item()
            epoch_total += losses["total"].item()
            n_batches += 1
            step += 1

        scheduler.step()

        avg_recon = epoch_recon / max(n_batches, 1)
        avg_kl = epoch_kl / max(n_batches, 1)
        avg_total = epoch_total / max(n_batches, 1)
        current_beta = min(max_beta, max_beta * step / max(warmup_steps, 1))

        logger.info(
            "Epoch %3d/%d | total=%.4f recon=%.4f kl=%.4f beta=%.4f",
            epoch,
            epochs,
            avg_total,
            avg_recon,
            avg_kl,
            current_beta,
        )
        history.append({"epoch": epoch, "total": avg_total, "recon": avg_recon, "kl": avg_kl, "beta": current_beta})

        # Save best checkpoint
        if avg_total < best_loss:
            best_loss = avg_total
            checkpoint = {
                "encoder_state_dict": encoder.state_dict(),
                "decoder_state_dict": decoder.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "epoch": epoch,
                "metrics": {"total": avg_total, "recon": avg_recon, "kl": avg_kl},
                "config": {
                    "step_dim": 29,
                    "d_model": 128,
                    "latent_dim": 256,
                    "n_heads": 4,
                    "n_layers": 2,
                    "max_seq_len": max_seq_len,
                },
            }
            path = checkpoint_dir / "temporal_vae_best.pt"
            torch.save(checkpoint, path)
            logger.info("  → New best checkpoint saved (loss=%.4f)", best_loss)

    final_metrics = history[-1] if history else {}
    logger.info("Training complete. Best loss: %.4f", best_loss)

    # Save training history
    history_path = checkpoint_dir / "temporal_vae_history.json"
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    return final_metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train FLUME TemporalVAE")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--max-seq-len", type=int, default=64)
    parser.add_argument("--max-beta", type=float, default=0.1)
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--max-sessions", type=int, default=None, help="Limit number of sessions (for smoke testing)")
    args = parser.parse_args()

    train(
        data_path=args.data,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        max_seq_len=args.max_seq_len,
        max_beta=args.max_beta,
        device_name=args.device,
        max_sessions=args.max_sessions,
    )


if __name__ == "__main__":
    main()
