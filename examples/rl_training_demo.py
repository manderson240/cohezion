#!/usr/bin/env python3
"""Demo: Training an RL agent to navigate a 256D latent universe.

Trains a REINFORCE policy network on the FlumeNav-v0 Gymnasium environment.
The agent learns to navigate 256D continuous latent space toward the HIHO
stability point (coherence = 0.5), shaped by Hamiltonian double-well dynamics.

Usage:
    uv run python examples/rl_training_demo.py
"""

from __future__ import annotations

import numpy as np

from cohezion.rl.environment import FlumeNavEnv
from cohezion.rl.trainer import TrainingConfig, train


def main() -> None:
    # --- Train ---
    config = TrainingConfig(n_episodes=50, max_steps=200, lr=3e-4, gamma=0.99)
    print(f"Training REINFORCE policy: {config.n_episodes} episodes, 256D action space")
    print("  Environment: FlumeNav-v0 (Hamiltonian dynamics, composite reward)")
    print()

    results = train(config)

    # --- Report training curve ---
    print("Training results (last 10 episodes):")
    print(f"  {'Episode':>8} {'Coherence':>10} {'Reward':>8} {'Steps':>6}")
    for r in results[-10:]:
        print(f"  {r.episode:>8} {r.mean_coherence:>10.4f} {r.total_reward:>8.1f} {r.steps:>6}")

    final_coherences = [r.mean_coherence for r in results[-10:]]
    print(f"\n  Mean coherence (last 10): {np.mean(final_coherences):.4f}")
    print(f"  Std coherence  (last 10): {np.std(final_coherences):.4f}")

    # --- Evaluate: run one episode with the raw environment ---
    print("\n--- Evaluation episode (untrained, showing environment dynamics) ---")
    env = FlumeNavEnv(z_dim=256, max_steps=50, use_hamiltonian=True)
    obs, info = env.reset(seed=42)
    coherences = []

    for step in range(50):
        # Random actions to show the environment's Hamiltonian dynamics
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        coherences.append(info["coherence"])
        if step % 10 == 0:
            print(
                f"  Step {step:>3}: coherence={info['coherence']:.4f}, "
                f"reward={reward:.3f}, mean_obs={obs.mean():.4f}"
            )
        if terminated or truncated:
            break

    print(f"\n  Episode coherence: mean={np.mean(coherences):.4f}, std={np.std(coherences):.4f}")
    print(
        f"  HIHO band (0.4-0.6) compliance: "
        f"{sum(0.4 <= c <= 0.6 for c in coherences) / len(coherences):.1%}"
    )


if __name__ == "__main__":
    main()
