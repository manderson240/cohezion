#!/usr/bin/env python3
"""Train RL agents on ManifoldEnv — validate the HIHO thesis.

Trains PPO on the 12D Riemannian manifold with 3-stage curriculum reward.
Produces learning curves and evaluation metrics for the research paper.

Usage:
    uv run python scripts/train_manifold_agent.py [--timesteps 50000] [--seed 42]
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def train_ppo(timesteps: int = 50_000, seed: int = 42) -> dict:
    """Train PPO on ManifoldEnv and return metrics."""
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback

    from cohezion.environments.manifold_env import ManifoldEnv

    # Custom callback to log per-episode metrics
    class ManifoldCallback(BaseCallback):
        def __init__(self):
            super().__init__()
            self.episode_rewards: list[float] = []
            self.episode_lengths: list[int] = []
            self.episode_convergences: list[bool] = []
            self.episode_stages: list[int] = []
            self.episode_coherences: list[float] = []

        def _on_step(self) -> bool:
            # Check if episode ended
            for info in self.locals.get("infos", []):
                if "episode" in info:
                    self.episode_rewards.append(info["episode"]["r"])
                    self.episode_lengths.append(info["episode"]["l"])
                if "curriculum_stage" in info:
                    self.episode_stages.append(info["curriculum_stage"])
                if "avg_coherence" in info:
                    self.episode_coherences.append(info["avg_coherence"])
                if (
                    info.get("TimeLimit.truncated", False) is False
                    and "terminal_observation" in info
                ):
                    self.episode_convergences.append(True)
            return True

    env = ManifoldEnv(max_steps=500, seed=seed)
    callback = ManifoldCallback()

    logger.info("Training PPO on ManifoldEnv (%d timesteps, seed=%d)", timesteps, seed)
    start = time.time()

    model = PPO(
        "MlpPolicy",
        env,
        verbose=0,
        seed=seed,
        n_steps=256,
        batch_size=64,
        n_epochs=10,
        learning_rate=3e-4,
        gamma=0.99,
        gae_lambda=0.95,
    )
    model.learn(total_timesteps=timesteps, callback=callback)

    train_time = time.time() - start
    logger.info("Training complete in %.1fs", train_time)

    # Save model
    output_dir = Path("results/training")
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save(str(output_dir / "ppo_manifold"))

    return {
        "algorithm": "PPO",
        "timesteps": timesteps,
        "seed": seed,
        "train_time_seconds": round(train_time, 2),
        "n_episodes": len(callback.episode_rewards),
        "mean_reward": round(
            float(np.mean(callback.episode_rewards)) if callback.episode_rewards else 0, 4
        ),
        "std_reward": round(
            float(np.std(callback.episode_rewards)) if callback.episode_rewards else 0, 4
        ),
        "mean_coherence": round(
            float(np.mean(callback.episode_coherences)) if callback.episode_coherences else 0, 4
        ),
        "max_stage_reached": max(callback.episode_stages) if callback.episode_stages else 1,
        "episode_rewards": [round(r, 4) for r in callback.episode_rewards],
        "episode_coherences": [round(c, 4) for c in callback.episode_coherences],
    }


def evaluate_trained(model_path: str, n_episodes: int = 50, seed: int = 42) -> dict:
    """Evaluate a trained model using UniverseEvaluator."""
    from stable_baselines3 import PPO

    from cohezion.environments.manifold_env import ManifoldEnv
    from cohezion.eval.universe_evaluator import (
        UniverseEvaluator,
        greedy_hiho_policy,
        random_policy,
    )

    model = PPO.load(model_path)
    env = ManifoldEnv(max_steps=500, seed=seed)
    evaluator = UniverseEvaluator(n_bootstrap=200)

    def trained_policy(obs):
        action, _ = model.predict(obs, deterministic=True)
        return action

    logger.info("Evaluating trained PPO vs baselines (%d episodes each)", n_episodes)

    comparison = evaluator.compare_policies(
        env,
        {
            "PPO (trained)": trained_policy,
            "Greedy HIHO": greedy_hiho_policy,
            "Random": random_policy,
        },
        n_episodes=n_episodes,
    )

    print("\n" + comparison.summary_table())
    print(f"\nBest policy: {comparison.best_policy}")
    print(f"Ranking: {comparison.ranking}")

    return comparison.to_dict()


def plot_learning_curve(metrics: dict, output_path: str = "results/training/learning_curve.png"):
    """Generate learning curve plot."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        rewards = metrics["episode_rewards"]
        if not rewards:
            logger.warning("No episode rewards to plot")
            return

        # Smoothed learning curve
        window = min(20, len(rewards) // 3) if len(rewards) > 3 else 1
        smoothed = np.convolve(rewards, np.ones(window) / window, mode="valid")

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Left: reward curve
        axes[0].plot(rewards, alpha=0.3, color="steelblue", label="Episode reward")
        axes[0].plot(
            range(window - 1, window - 1 + len(smoothed)),
            smoothed,
            color="darkblue",
            linewidth=2,
            label=f"Moving avg (w={window})",
        )
        axes[0].set_xlabel("Episode")
        axes[0].set_ylabel("Reward")
        axes[0].set_title(f"PPO on ManifoldEnv — {metrics['timesteps']} timesteps")
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Right: coherence curve
        coherences = metrics.get("episode_coherences", [])
        if coherences:
            axes[1].plot(coherences, alpha=0.3, color="forestgreen", label="Episode coherence")
            coh_smoothed = np.convolve(coherences, np.ones(window) / window, mode="valid")
            axes[1].plot(
                range(window - 1, window - 1 + len(coh_smoothed)),
                coh_smoothed,
                color="darkgreen",
                linewidth=2,
                label=f"Moving avg (w={window})",
            )
            axes[1].axhline(
                y=0.5, color="red", linestyle="--", alpha=0.5, label="HIHO target (0.5)"
            )
            axes[1].set_xlabel("Episode")
            axes[1].set_ylabel("Avg Coherence")
            axes[1].set_title("Coherence Trajectory")
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150)
        plt.close()
        logger.info("Learning curve saved to %s", output_path)
    except ImportError:
        logger.warning("matplotlib not available, skipping plot")


def main():
    parser = argparse.ArgumentParser(description="Train RL agents on ManifoldEnv")
    parser.add_argument("--timesteps", type=int, default=50_000, help="Training timesteps")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--eval-episodes", type=int, default=20, help="Evaluation episodes")
    args = parser.parse_args()

    # Train
    metrics = train_ppo(args.timesteps, args.seed)
    logger.info(
        "Training results: %d episodes, mean_reward=%.4f, mean_coherence=%.4f, max_stage=%d",
        metrics["n_episodes"],
        metrics["mean_reward"],
        metrics["mean_coherence"],
        metrics["max_stage_reached"],
    )

    # Plot
    plot_learning_curve(metrics)

    # Evaluate
    eval_results = evaluate_trained("results/training/ppo_manifold", args.eval_episodes, args.seed)

    # Save all results
    output_dir = Path("results/training")
    with open(output_dir / "training_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    with open(output_dir / "evaluation_results.json", "w") as f:
        json.dump(eval_results, f, indent=2)

    logger.info("All results saved to results/training/")


if __name__ == "__main__":
    main()
