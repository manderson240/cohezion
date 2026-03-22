#!/usr/bin/env python3
"""CLI for training the FLUME VAE autoencoder.

Usage:
    uv run python scripts/train_flume.py
    uv run python scripts/train_flume.py --epochs 100 --lr 5e-4
    uv run python scripts/train_flume.py --synthetic --epochs 20
"""

from __future__ import annotations

import argparse
import json
import logging
import sys


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train FLUME VAE autoencoder")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--z-dim", type=int, default=256)
    parser.add_argument("--kl-weight", type=float, default=0.1)
    parser.add_argument("--coherence-weight", type=float, default=0.05)
    parser.add_argument("--data-dir", default="data/mass_sim/artifacts")
    parser.add_argument("--checkpoint-dir", default="data/flume/checkpoints")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data")
    parser.add_argument("--n-samples", type=int, default=10000)

    args = parser.parse_args()

    from cohezion.flume.training import FlumeVAETrainer, TrainConfig

    config = TrainConfig(
        z_dim=args.z_dim,
        batch_size=args.batch_size,
        epochs=args.epochs,
        lr=args.lr,
        kl_weight=args.kl_weight,
        coherence_weight=args.coherence_weight,
        checkpoint_dir=args.checkpoint_dir,
        data_dir=args.data_dir,
    )

    trainer = FlumeVAETrainer(config)

    dataset = None
    if args.synthetic:
        from cohezion.flume.dataset import SyntheticFlumeDataset

        dataset = SyntheticFlumeDataset(n_samples=args.n_samples, z_dim=args.z_dim)

    metrics = trainer.train(dataset=dataset)

    # Save metrics summary
    from pathlib import Path

    out = Path(args.checkpoint_dir) / "training_metrics.json"
    with open(out, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"\nTraining complete. Metrics saved to {out}")

    final = metrics[-1]
    print(f"Final MSE: {final['mse']:.4f} | KL: {final['kl']:.4f} | Total: {final['total']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
