#!/usr/bin/env python3
"""Cohezion quickstart — a runnable, offline-safe introduction.

Demonstrates ManifoldEnv: a Gymnasium-compatible environment where an agent navigates a
12D Riemannian manifold toward the HIHO stability equilibrium (coherence -> 1.0, deviation
-> 0.0). This is genuinely representative of the repo's "12D agentic universe" physics core,
not a toy example — the same env is used for RL training (Stable-Baselines3, TRL) elsewhere
in this codebase.

Design constraint: this script must run with ZERO network access, ZERO credentials, and no
dependency on the local inference fleet (:13305) — a new user's fleet won't be up yet, and a
quickstart that dies on an offline router is worse than none. ManifoldEnv is pure numpy/
gymnasium physics, so nothing here reaches outside the process. If you extend this script to
show inference, gate it behind a reachability check and degrade to a message + exit 0.

Run: uv run python examples/quickstart.py
"""

from __future__ import annotations

import logging
import sys


# Importing cohezion eagerly registers unrelated model-provider classes (name-only, no
# network calls) and logs INFO/WARNING noise that has nothing to do with this demo and could
# be mistaken for inference/network activity. Suppress up to INFO; real problems (WARNING+)
# still surface.
logging.disable(logging.INFO)


def main() -> int:
    try:
        from cohezion.environments import ManifoldEnv
    except ImportError as exc:
        print(f"ManifoldEnv unavailable ({exc}) — skipping quickstart demo.")
        return 0

    print("Cohezion quickstart: ManifoldEnv (12D HIHO manifold)\n")

    env = ManifoldEnv(seed=42)
    env.action_space.seed(42)  # reset(seed=...) does not seed the action space itself
    obs, info = env.reset(seed=42)
    print(f"reset -> obs.shape={obs.shape}  coherence={info['coherence']:.4f}")

    for step in range(1, 11):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        print(
            f"step {step:2d}  coherence={info['coherence']:.4f}  "
            f"hiho_deviation={info['hiho_deviation']:.4f}  "
            f"reward={reward:+.4f}  stage={info['curriculum_stage']}"
        )
        if terminated:
            print("terminated: HIHO equilibrium reached and held.")
            break
        if truncated:
            break

    print(
        f"\nepisode summary: {info['trajectory_length']} positions visited, "
        f"episode_reward={info['episode_reward']:+.4f}"
    )
    print("\nQuickstart complete. No network, credentials, or local inference were used.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
