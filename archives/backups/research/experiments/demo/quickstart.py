#!/usr/bin/env python3
"""Cohezion Quickstart: Train an RL agent on a 12D Riemannian manifold.

Demonstrates:
  - A Gymnasium-compatible environment (ManifoldEnv-v0) with 19D observations
    and 12D continuous actions
  - Lagrangian dynamics with a symplectic (Stormer-Verlet) integrator on a
    fabric-block Riemannian metric
  - SU(2) spinor coherence tracking via the Bloch sphere
  - HIHO (0.5) attractor potential driving agents toward stability

The training loop uses a simple "coherence-gradient" policy: measure
which action directions improve coherence, then bias future actions
toward those directions. This is intentionally minimal -- the point is
to show the environment's physics, not a production PPO implementation.

Why this matters for LLM training:
  Each trajectory through the 12D manifold produces reward signals grounded
  in differential geometry (Riemannian metric, gauge curvature, spinor
  alignment). These signals can train reward models or generate DPO
  preference pairs -- connecting physics-based evaluation to language
  model improvement.

Usage:
  uv run python quickstart.py              # 50 episodes, default seed
  uv run python quickstart.py --episodes 100 --seed 42
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np


def get_env():
    """Create ManifoldEnv, trying gymnasium.make first, then direct import."""
    try:
        import gymnasium as gym

        # Trigger registration by importing the module
        import cohezion.environments.manifold_env  # noqa: F401

        env = gym.make("Cohezion/ManifoldEnv-v0")
        print("[OK] Created ManifoldEnv via gymnasium.make()")
        return env
    except Exception:
        pass

    try:
        from cohezion.environments.manifold_env import ManifoldEnv

        env = ManifoldEnv()
        print("[OK] Created ManifoldEnv via direct import")
        return env
    except ImportError as e:
        print(f"[ERROR] Cannot import ManifoldEnv: {e}")
        print("Install cohezion first: cd .. && uv pip install -e .")
        sys.exit(1)


class CoherenceGradientPolicy:
    """Minimal policy that learns which action directions improve coherence.

    Maintains a running estimate of the coherence gradient in action space
    and biases actions toward improving directions. This is a lightweight
    stand-in for PPO/SAC -- sufficient to demonstrate the environment's
    physics without requiring torch or stable-baselines3.
    """

    def __init__(self, action_dim: int, lr: float = 0.1, explore: float = 0.3):
        self.action_dim = action_dim
        self.lr = lr
        self.explore = explore
        self.mean_action = np.zeros(action_dim, dtype=np.float32)
        self._prev_coherence = None
        self._prev_action = None

    def act(self, obs: np.ndarray, info: dict, rng: np.random.Generator) -> np.ndarray:
        """Select action: biased random walk toward coherence improvement."""
        noise = rng.normal(0, self.explore, self.action_dim).astype(np.float32)
        action = np.clip(self.mean_action + noise, -0.5, 0.5)

        # Update mean toward directions that improved coherence
        coherence = info.get("coherence", 0.5)
        if self._prev_coherence is not None and self._prev_action is not None:
            delta = coherence - self._prev_coherence
            self.mean_action += self.lr * delta * self._prev_action
            self.mean_action = np.clip(self.mean_action, -0.3, 0.3)

        self._prev_coherence = coherence
        self._prev_action = action.copy()
        return action

    def reset(self):
        """Reset per-episode state but keep learned bias."""
        self._prev_coherence = None
        self._prev_action = None


def run_training(n_episodes: int = 50, seed: int = 0, max_steps: int = 200) -> dict:
    """Train agent and collect trajectory data.

    Returns dict with episode summaries and full trajectory data.
    """
    env = get_env()
    rng = np.random.default_rng(seed)
    policy = CoherenceGradientPolicy(action_dim=12)

    all_episodes = []
    all_trajectories = []

    print(f"\n{'=' * 70}")
    print(f"  Training: {n_episodes} episodes, max {max_steps} steps each")
    print("  Manifold: 12D Riemannian, Lagrangian dynamics, HIHO attractor")
    print("  Observation: 19D (12D state + 3D Bloch vector + 4D fiber base)")
    print("  Action: 12D continuous velocity perturbation")
    print(f"{'=' * 70}\n")

    header = f"{'Ep':>4} | {'Steps':>5} | {'Coherence':>9} | {'Reward':>8} | {'HIHO dev':>8} | {'Charge':>7} | {'YM Action':>9} | {'Term':>4}"
    print(header)
    print("-" * len(header))

    t_start = time.time()

    for ep in range(n_episodes):
        obs, info = env.reset(seed=int(rng.integers(0, 2**31)))
        policy.reset()

        ep_reward = 0.0
        ep_trajectory = []
        terminated = False
        truncated = False

        for step in range(max_steps):
            action = policy.act(obs, info, rng)
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward

            # Record trajectory step
            ep_trajectory.append(
                {
                    "step": step,
                    "state_12d": obs[:12].tolist(),
                    "bloch_vector": obs[12:15].tolist(),
                    "fiber_base": obs[15:19].tolist(),
                    "coherence": info["coherence"],
                    "hiho_deviation": info["hiho_deviation"],
                    "charge_polarity": info["charge_polarity"],
                    "spin_rotation": info["spin_rotation"],
                    "spin_precession": info["spin_precession"],
                    "yang_mills_action": info["yang_mills_action"],
                    "potential_energy": info["potential_energy"],
                    "kinetic_energy": info["kinetic_energy"],
                    "reward": float(reward),
                    "action": action.tolist(),
                }
            )

            if terminated or truncated:
                break

        # Episode summary
        final_coherence = info["coherence"]
        final_hiho_dev = info["hiho_deviation"]
        final_charge = info["charge_polarity"]
        final_ym = info["yang_mills_action"]
        n_steps = step + 1
        term_flag = "HIHO" if terminated else "trunc"

        episode_data = {
            "episode": ep,
            "steps": n_steps,
            "total_reward": ep_reward,
            "final_coherence": final_coherence,
            "final_hiho_deviation": final_hiho_dev,
            "final_charge_polarity": final_charge,
            "final_yang_mills": final_ym,
            "terminated": terminated,
            "trajectory": ep_trajectory,
        }

        all_episodes.append(episode_data)
        all_trajectories.extend(ep_trajectory)

        # Print every episode (50 is small enough)
        print(
            f"{ep:4d} | {n_steps:5d} | {final_coherence:9.4f} | {ep_reward:8.3f} | "
            f"{final_hiho_dev:8.4f} | {final_charge:+7.3f} | {final_ym:9.4f} | {term_flag}"
        )

    elapsed = time.time() - t_start

    # Summary statistics
    coherences = [e["final_coherence"] for e in all_episodes]
    rewards = [e["total_reward"] for e in all_episodes]
    steps = [e["steps"] for e in all_episodes]
    hiho_terminations = sum(1 for e in all_episodes if e["terminated"])

    print(f"\n{'=' * 70}")
    print(f"  Summary ({elapsed:.1f}s total)")
    print(f"{'=' * 70}")
    print(f"  Coherence   : {np.mean(coherences):.4f} +/- {np.std(coherences):.4f}")
    print(f"  Reward      : {np.mean(rewards):.4f} +/- {np.std(rewards):.4f}")
    print(f"  Steps/ep    : {np.mean(steps):.1f} +/- {np.std(steps):.1f}")
    print(f"  HIHO reached: {hiho_terminations}/{n_episodes} episodes")
    print(f"  Total steps : {sum(steps):,}")
    print(f"  Data points : {len(all_trajectories):,} trajectory steps")
    print(f"{'=' * 70}")

    return {
        "config": {
            "n_episodes": n_episodes,
            "seed": seed,
            "max_steps": max_steps,
            "manifold_dim": 12,
            "obs_dim": 19,
            "action_dim": 12,
        },
        "summary": {
            "mean_coherence": float(np.mean(coherences)),
            "std_coherence": float(np.std(coherences)),
            "mean_reward": float(np.mean(rewards)),
            "std_reward": float(np.std(rewards)),
            "mean_steps": float(np.mean(steps)),
            "hiho_terminations": hiho_terminations,
            "total_trajectory_steps": len(all_trajectories),
            "elapsed_seconds": elapsed,
        },
        "episodes": all_episodes,
    }


def main():
    parser = argparse.ArgumentParser(description="Cohezion ManifoldEnv quickstart training")
    parser.add_argument("--episodes", type=int, default=50, help="Number of episodes (default: 50)")
    parser.add_argument("--seed", type=int, default=0, help="Random seed (default: 0)")
    parser.add_argument(
        "--max-steps", type=int, default=100, help="Max steps per episode (default: 100)"
    )
    args = parser.parse_args()

    data = run_training(n_episodes=args.episodes, seed=args.seed, max_steps=args.max_steps)

    # Save trajectory data
    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "trajectories.json"

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n  Trajectory data saved to: {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")
    print("\n  Next: uv run python evaluate.py")


if __name__ == "__main__":
    main()
