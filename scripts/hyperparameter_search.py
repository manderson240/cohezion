#!/usr/bin/env python3
"""Iterative hyperparameter search using Democratic Debate.

Runs a loop: train → evaluate → debate → adjust → retrain
for up to max_iterations cycles. Each iteration:
1. Train (or re-train) VAE + RL with current hyperparameters
2. Evaluate coherence metrics
3. Run Democratic Debate with current metrics as context
4. Extract suggested hyperparameter changes
5. Apply and repeat

Usage:
    uv run python scripts/hyperparameter_search.py
    uv run python scripts/hyperparameter_search.py --iterations 3 --skip-debate
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("hyperparam_search")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Iterative hyperparameter search via Democratic Debate")
    parser.add_argument("--iterations", type=int, default=5, help="Max search iterations (default: 5)")
    parser.add_argument(
        "--vae-epochs",
        type=int,
        default=25,
        help="VAE epochs per iteration (default: 25)",
    )
    parser.add_argument(
        "--rl-episodes",
        type=int,
        default=100,
        help="RL episodes per iteration (default: 100)",
    )
    parser.add_argument(
        "--data-dir",
        default="data/mass_sim/artifacts",
        help="Training data directory",
    )
    parser.add_argument(
        "--output-dir",
        default="data/hyperparameter_search",
        help="Output directory for search history",
    )
    parser.add_argument(
        "--skip-debate",
        action="store_true",
        help="Skip Ollama debate (use random perturbation instead)",
    )
    return parser.parse_args()


async def run_debate_for_params(
    baseline_metrics: dict,
) -> dict:
    """Run Democratic Debate to suggest hyperparameters."""
    try:
        from cohezion.pipeline.hyperparameter_debate import HyperparameterDebate

        debate = HyperparameterDebate()
        params = await debate.search_rl_params(
            baseline_metrics=baseline_metrics,
            output_path="data/hyperparameter_search/latest_debate.json",
        )
        return params
    except Exception as e:
        logger.warning("Debate failed: %s. Using defaults.", e)
        return {
            "learning_rate": 3e-4,
            "hidden_dim": 128,
            "gamma": 0.99,
            "action_scale": 0.01,
        }


def perturb_params(params: dict, iteration: int) -> dict:
    """Apply random perturbation to hyperparameters (fallback for skip-debate)."""
    import numpy as np

    rng = np.random.default_rng(iteration + 42)

    perturbed = dict(params)
    # Perturb learning rate by ±50%
    factor = rng.uniform(0.5, 1.5)
    perturbed["learning_rate"] = max(1e-5, min(1e-2, params["learning_rate"] * factor))

    # Perturb gamma slightly
    perturbed["gamma"] = max(0.9, min(0.999, params["gamma"] + rng.uniform(-0.02, 0.02)))

    return perturbed


def main() -> int:
    args = parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    history_path = output_dir / "history.jsonl"

    logger.info("=" * 60)
    logger.info("ITERATIVE HYPERPARAMETER SEARCH")
    logger.info(f"  Max iterations: {args.iterations}")
    logger.info(f"  VAE epochs/iter: {args.vae_epochs}")
    logger.info(f"  RL episodes/iter: {args.rl_episodes}")
    logger.info(f"  Skip debate: {args.skip_debate}")
    logger.info("=" * 60)

    # Initial parameters
    params = {
        "learning_rate": 3e-4,
        "hidden_dim": 128,
        "gamma": 0.99,
        "action_scale": 0.01,
        "kl_weight": 0.1,
    }

    best_coherence = 0.0
    best_params = dict(params)
    best_iteration = -1

    for iteration in range(args.iterations):
        t0 = time.time()
        logger.info(f"\n{'=' * 40}")
        logger.info(f"ITERATION {iteration + 1}/{args.iterations}")
        logger.info(f"Params: {json.dumps(params, indent=2)}")
        logger.info(f"{'=' * 40}")

        # Step 1: Train VAE
        logger.info("[VAE] Training %d epochs...", args.vae_epochs)
        try:
            from cohezion.flume.training import FlumeVAETrainer, TrainConfig

            vae_config = TrainConfig(
                epochs=args.vae_epochs,
                lr=params["learning_rate"],
                kl_weight=params.get("kl_weight", 0.1),
                data_dir=args.data_dir,
                checkpoint_dir=str(output_dir / f"vae_iter{iteration}"),
                log_interval=5,
            )
            trainer = FlumeVAETrainer(vae_config)
            vae_metrics = trainer.train()
            vae_final = vae_metrics[-1] if vae_metrics else {}
            logger.info(
                "[VAE] Done: MSE=%.4f, KL=%.4f, Coh=%.4f",
                vae_final.get("mse", 0),
                vae_final.get("kl", 0),
                vae_final.get("coherence_loss", 0),
            )
        except Exception as e:
            logger.error("[VAE] Training failed: %s", e)
            vae_final = {}

        # Step 2: Train RL
        logger.info("[RL] Training %d episodes...", args.rl_episodes)
        try:
            from cohezion.rl.trainer import TrainingConfig, train

            rl_config = TrainingConfig(
                n_episodes=args.rl_episodes,
                lr=params["learning_rate"],
                gamma=params["gamma"],
                hidden_dim=int(params["hidden_dim"]),
                output_dir=str(output_dir / f"rl_iter{iteration}"),
                log_interval=20,
                save_interval=50,
            )
            rl_results = train(rl_config)
            if rl_results:
                tail = rl_results[-min(50, len(rl_results)) :]
                avg_coherence = sum(r.mean_coherence for r in tail) / len(tail)
                avg_reward = sum(r.total_reward for r in tail) / len(tail)
            else:
                avg_coherence = 0.0
                avg_reward = 0.0

            logger.info(
                "[RL] Done: avg_coherence=%.4f, avg_reward=%.2f",
                avg_coherence,
                avg_reward,
            )
        except Exception as e:
            logger.error("[RL] Training failed: %s", e)
            avg_coherence = 0.0
            avg_reward = 0.0

        # Step 3: Evaluate
        metrics = {
            "vae_mse": vae_final.get("mse", 0),
            "vae_kl": vae_final.get("kl", 0),
            "vae_coherence_loss": vae_final.get("coherence_loss", 0),
            "rl_coherence": avg_coherence,
            "rl_reward": avg_reward,
        }

        improved = avg_coherence > best_coherence
        if improved:
            best_coherence = avg_coherence
            best_params = dict(params)
            best_iteration = iteration

        # Record history
        elapsed = time.time() - t0
        record = {
            "iteration": iteration,
            "params": params,
            "metrics": metrics,
            "improved": improved,
            "best_coherence": best_coherence,
            "elapsed_s": round(elapsed, 1),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with open(history_path, "a") as f:
            f.write(json.dumps(record) + "\n")

        logger.info(
            "Iteration %d: coherence=%.4f (%s) | best=%.4f (iter %d)",
            iteration,
            avg_coherence,
            "improved" if improved else "no improvement",
            best_coherence,
            best_iteration,
        )

        # Step 4: Get new params (debate or perturbation)
        if iteration < args.iterations - 1:  # Skip on last iteration
            if args.skip_debate:
                params = perturb_params(best_params, iteration)
                logger.info("[PERTURB] New params: %s", params)
            else:
                logger.info("[DEBATE] Running Democratic Debate...")
                params = asyncio.run(run_debate_for_params(metrics))
                logger.info("[DEBATE] Suggested params: %s", params)

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("SEARCH COMPLETE")
    logger.info(f"  Best coherence: {best_coherence:.4f} (iteration {best_iteration})")
    logger.info(f"  Best params: {json.dumps(best_params, indent=2)}")
    logger.info(f"  History: {history_path}")
    logger.info("=" * 60)

    # Save best params
    best_path = output_dir / "best_params.json"
    with open(best_path, "w") as f:
        json.dump(
            {
                "params": best_params,
                "coherence": best_coherence,
                "iteration": best_iteration,
            },
            f,
            indent=2,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
