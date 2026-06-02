#!/usr/bin/env python3
"""Train PPO on ManifoldEnv with SMALL actions — the README's winning recipe.

The flagship finding: large actions fight the Lagrangian attractor (coherence
collapses); actions scaled toward [-0.1, 0.1] *cooperate* with it. The default
ManifoldEnv action space is Box(-0.5, 0.5); a `SmallActionWrapper` scales every
policy's action by 0.2 so the effective action is ~[-0.1, 0.1]. Training AND
evaluation use the same wrapped env, so PPO/Random/Greedy are compared fairly.

Usage:
    python scripts/train_manifold_small_actions.py --timesteps 25000 --seed 42
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import gymnasium as gym
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class SmallActionWrapper(gym.ActionWrapper):
    """Scale actions toward the attractor-cooperating regime (factor 0.2 -> ~[-0.1, 0.1])."""

    def __init__(self, env: gym.Env, scale: float = 0.2) -> None:
        super().__init__(env)
        self.scale = scale

    def action(self, action: np.ndarray) -> np.ndarray:
        return np.asarray(action, dtype=np.float32) * self.scale


def _make_env(seed: int) -> gym.Env:
    from cohezion.environments.manifold_env import ManifoldEnv

    return SmallActionWrapper(ManifoldEnv(max_steps=500, seed=seed))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timesteps", type=int, default=25_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--eval-episodes", type=int, default=40)
    args = ap.parse_args()

    from stable_baselines3 import PPO

    from cohezion.eval.universe_evaluator import (
        UniverseEvaluator,
        greedy_hiho_policy,
        random_policy,
    )

    env = _make_env(args.seed)
    logger.info("Training PPO (small actions) %d timesteps, seed=%d", args.timesteps, args.seed)
    model = PPO(
        "MlpPolicy",
        env,
        verbose=0,
        seed=args.seed,
        n_steps=256,
        batch_size=64,
        n_epochs=10,
        learning_rate=3e-4,
        gamma=0.99,
        gae_lambda=0.95,
    )
    model.learn(total_timesteps=args.timesteps)

    out = Path("results/training")
    out.mkdir(parents=True, exist_ok=True)
    model.save(str(out / "ppo_manifold_small_actions"))

    def trained_policy(obs):
        action, _ = model.predict(obs, deterministic=True)
        return action

    evaluator = UniverseEvaluator(n_bootstrap=200)
    comparison = evaluator.compare_policies(
        _make_env(args.seed),
        {
            "PPO (small-actions)": trained_policy,
            "Greedy HIHO": greedy_hiho_policy,
            "Random": random_policy,
        },
        n_episodes=args.eval_episodes,
    )
    print("\n" + comparison.summary_table())
    print(f"\nBest policy: {comparison.best_policy}")
    print(f"Ranking: {comparison.ranking}")

    result = comparison.to_dict()
    result["recipe"] = "small-actions (scale=0.2, ~[-0.1,0.1]) + curriculum"
    (out / "evaluation_results_small_actions.json").write_text(json.dumps(result, indent=2))
    logger.info("Saved results/training/evaluation_results_small_actions.json")


if __name__ == "__main__":
    main()
