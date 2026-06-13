#!/usr/bin/env python3
"""CLI driver: train the FLUME VAE on real agentic experiences.

Usage:
    uv run python scripts/drivers/train_experience_vae.py --epochs 5 --min-real 1
    uv run python scripts/drivers/train_experience_vae.py --no-synthetic --min-real 50
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train FLUME VAE on collected execution experiences."
    )
    parser.add_argument(
        "--min-real",
        type=int,
        default=10,
        help="Minimum real experience records required (default: 10)",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=10_000,
        help="Maximum total training samples (default: 10000)",
    )
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs (default: 50)")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=128,
        help="Batch size (default: 128; was 64 — autoresearch 2026-05-15: bs=128 gives +0.8% reconstruction improvement)",
    )
    parser.add_argument(
        "--kl-weight",
        type=float,
        default=0.01,
        help="KL divergence weight (default: 0.01; was 0.1 — β≥0.1 causes posterior collapse)",
    )
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate (default: 0.001)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--session",
        type=str,
        default="",
        help="Session tag for checkpoint naming (optional)",
    )
    parser.add_argument(
        "--no-synthetic",
        action="store_true",
        help="Disable synthetic data fallback — fail if insufficient real data",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="data/flume/checkpoints",
        help="Checkpoint output directory (default: data/flume/checkpoints)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from cohezion.flume.experience_pipeline import ExperienceTrainingPipeline

    pipeline = ExperienceTrainingPipeline()
    try:
        checkpoint = asyncio.run(
            pipeline.run(
                min_real=args.min_real,
                max_samples=args.max_samples,
                epochs=args.epochs,
                batch_size=args.batch_size,
                lr=args.lr,
                seed=args.seed,
                synthetic_fallback=not args.no_synthetic,
                checkpoint_dir=args.checkpoint_dir,
            )
        )
        print(f"\nCheckpoint saved: {checkpoint}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
