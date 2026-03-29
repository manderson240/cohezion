#!/usr/bin/env python3
"""CLI driver for REINFORCE training on FlumeNav-v0.

Usage:
    uv run python scripts/train_rl.py --episodes 500 --lr 3e-4
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
from dataclasses import asdict
from pathlib import Path


# Global flag for graceful interruption
_interrupted = False


def _handle_sigint(signum: int, frame: object) -> None:
    global _interrupted
    if _interrupted:
        # Second SIGINT — hard exit
        sys.exit(1)
    _interrupted = True
    logging.getLogger(__name__).warning("SIGINT received — finishing current episode then stopping")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a REINFORCE policy on FlumeNav-v0")
    parser.add_argument("--episodes", type=int, default=500, help="Number of episodes")
    parser.add_argument("--max-steps", type=int, default=200, help="Max steps per episode")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    parser.add_argument("--gamma", type=float, default=0.99, help="Discount factor")
    parser.add_argument("--hidden-dim", type=int, default=128, help="Policy hidden layer size")
    parser.add_argument("--z-dim", type=int, default=256, help="FLUME latent dimension")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/rl/checkpoints",
        help="Directory for checkpoints and metrics",
    )
    parser.add_argument("--log-interval", type=int, default=10, help="Episodes between log messages")
    parser.add_argument(
        "--save-interval",
        type=int,
        default=25,
        help="Episodes between checkpoint saves",
    )
    parser.add_argument(
        "--reward-type",
        type=str,
        default="default",
        choices=["default", "composite"],
        help="Reward function type (composite reserved for future use)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log = logging.getLogger("train_rl")

    signal.signal(signal.SIGINT, _handle_sigint)

    from cohezion.rl.trainer import TrainingConfig, train

    config = TrainingConfig(
        n_episodes=args.episodes,
        max_steps=args.max_steps,
        lr=args.lr,
        gamma=args.gamma,
        z_dim=args.z_dim,
        hidden_dim=args.hidden_dim,
        save_interval=args.save_interval,
        output_dir=args.output_dir,
        log_interval=args.log_interval,
    )

    log.info("Starting RL training with config: %s", config)
    if args.reward_type != "default":
        log.warning("Reward type '%s' selected but not yet implemented", args.reward_type)

    results = train(config)

    # Write per-episode metrics to JSONL
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "training_metrics.jsonl"
    with open(metrics_path, "w") as f:
        for r in results:
            f.write(json.dumps(asdict(r)) + "\n")
    log.info("Metrics written to %s", metrics_path)

    # Print summary
    total = len(results)
    if total == 0:
        log.warning("No episodes completed")
        return

    tail = results[-min(50, total) :]
    avg_reward = sum(r.total_reward for r in tail) / len(tail)
    avg_coherence = sum(r.mean_coherence for r in tail) / len(tail)

    log.info(
        "Training complete: %d episodes | Last-%d avg reward: %.3f | Last-%d avg coherence: %.4f",
        total,
        len(tail),
        avg_reward,
        len(tail),
        avg_coherence,
    )


if __name__ == "__main__":
    main()
