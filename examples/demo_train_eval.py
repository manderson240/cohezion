#!/usr/bin/env python3
"""Train a small PPO agent on the 12D manifold and compare it with a random policy.

This is what ``make demo`` runs. It needs the RL extra (``uv sync --extra rl``) because it
imports stable-baselines3; everything else is the repository's own code. Takes a few
minutes on CPU; no network, GPU or local inference is used.
"""

from __future__ import annotations

import sys

import numpy as np


try:
    from stable_baselines3 import PPO
except ImportError:  # pragma: no cover - exercised only on installs without the extra
    sys.stderr.write("demo: stable-baselines3 is not installed. Run: uv sync --extra rl\n")
    sys.exit(2)

from gymnasium import spaces

from cohezion.environments.manifold_env import ManifoldEnv
from cohezion.eval.universe_evaluator import UniverseEvaluator, random_policy


TIMESTEPS = 5_000
EPISODES = 5


def main() -> int:
    print("=== Cohezion demo: physics-grounded agent training ===")
    env = ManifoldEnv(max_steps=100, seed=42, render_mode="human")
    env.action_space = spaces.Box(low=-0.1, high=0.1, shape=(12,), dtype=np.float32)

    print(f"Training PPO for {TIMESTEPS} steps on the 12D Riemannian manifold...")
    model = PPO("MlpPolicy", env, verbose=0, seed=42, n_steps=256)
    model.learn(total_timesteps=TIMESTEPS)

    def trained_policy(obs):
        action, _ = model.predict(obs, deterministic=True)
        return np.clip(action, -0.1, 0.1).astype(np.float32)

    print(f"\n=== Evaluation over {EPISODES} episodes: trained PPO vs random ===")
    evaluator = UniverseEvaluator(n_bootstrap=50)
    ppo = evaluator.evaluate_policy(env, trained_policy, n_episodes=EPISODES, policy_name="PPO")
    rnd = evaluator.evaluate_policy(env, random_policy, n_episodes=EPISODES, policy_name="Random")
    for name, r in (("PPO", ppo), ("Random", rnd)):
        print(
            f"{name:7s} coherence={r.mean_coherence:.3f}  reward={r.mean_reward:.2f}  "
            f"stability={r.mean_stability_duration:.0f}"
        )
    verdict = "outperforms" if ppo.mean_reward > rnd.mean_reward else "underperforms"
    print(f"\nResult: PPO {verdict} random by {abs(ppo.mean_reward - rnd.mean_reward):.2f} reward")
    print("Demo complete. Longer runs: make train (20K steps) or make benchmark (100K).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
