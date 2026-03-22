#!/usr/bin/env python3
"""CLI driver for FLUME VAE training.

Usage:
    uv run python scripts/train_vae.py
    uv run python scripts/train_vae.py --epochs 100 --lr 5e-4
    uv run python scripts/train_vae.py --resume data/flume/checkpoints/flume_vae_ep50.pt
"""

from __future__ import annotations

import argparse
import logging
import sys


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train FLUME VAE autoencoder")
    parser.add_argument(
        "--data-dir",
        default="data/mass_sim/artifacts",
        help="Directory containing training data (default: data/mass_sim/artifacts)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="Number of training epochs (default: 100)",
    )
    parser.add_argument(
        "--checkpoint-dir",
        default="data/flume/checkpoints",
        help="Directory for checkpoints (default: data/flume/checkpoints)",
    )
    parser.add_argument(
        "--log-interval",
        type=int,
        default=10,
        help="Log metrics every N epochs (default: 10)",
    )
    parser.add_argument("--batch-size", type=int, default=64, help="Training batch size (default: 64)")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate (default: 1e-3)")
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to checkpoint to resume training from",
    )

    args = parser.parse_args()

    from cohezion.flume.training import FlumeVAETrainer, TrainConfig

    config = TrainConfig(
        batch_size=args.batch_size,
        epochs=args.epochs,
        lr=args.lr,
        checkpoint_dir=args.checkpoint_dir,
        log_interval=args.log_interval,
        data_dir=args.data_dir,
    )

    if args.resume:
        logger.info(f"Resuming from checkpoint: {args.resume}")
        trainer = FlumeVAETrainer.from_checkpoint(args.resume, config=config)
    else:
        trainer = FlumeVAETrainer(config)

    metrics = trainer.train()

    if not metrics:
        logger.warning("No training metrics produced (empty dataset?)")
        return 1

    final = metrics[-1]
    print(f"\nTraining complete after {len(metrics)} epochs.")
    print(f"  MSE:       {final['mse']:.6f}")
    print(f"  KL:        {final['kl']:.6f}")
    print(f"  Coherence: {final['coherence_loss']:.6f}")
    print(f"  Total:     {final['total']:.6f}")
    print(f"  Metrics:   {trainer.metrics_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
