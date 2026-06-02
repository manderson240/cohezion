#!/usr/bin/env python3
"""Universes reward-integrity eval — a falsifiable 3-arm audit of ManifoldEnv's reward.

Portfolio experiment for the Anthropic "Research Engineer, Universes" profile: the role's
core deliverable is "rigorous evaluations that measure real capability." This applies the
falsifiable-eval-harness discipline to an RL environment's *reward function itself* and asks
the only question that matters for a training environment:

    Does the reward MEASURE capability, or can it be gamed?

Method — three arms, identical episodes, multiple seeds:
  * null       : a = 0          (does nothing; must score at the floor)
  * random     : a ~ U(action)  (baseline; no competence)
  * competent  : a = gain*(setpoint - position)   (privileged PD controller toward the HIHO
                 setpoint at 0.5 — optimizes GROUND-TRUTH capability, never the reward under test)

Ground-truth capability is HIHO-band occupancy (fraction of steps the system holds the
[0.4,0.6] coherence band) — defined independently of the reward. A reward "measures real
capability" iff its arm-ranking matches the band-occupancy ranking AND it separates competent
from random/null. If random ≈ competent, or the reward ranks arms differently from ground
truth, the reward is leaky/misaligned — a finding, reported as a verdict that can be False.

No leakage: the competent policy optimizes the setpoint (capability), not the reward. No cloud:
pure numpy + the local env. Honest: multi-seed mean±std, verdict can fail.
"""

from __future__ import annotations

import json
import statistics
import sys

import numpy as np

from cohezion.environments.manifold_env import ManifoldEnv


SEEDS = list(range(12))
HORIZON = 60
SETPOINT = 0.5  # HIHO band center


def _null_policy(env: ManifoldEnv) -> np.ndarray:
    return np.zeros(env.action_space.shape, dtype=np.float32)


def _random_policy(env: ManifoldEnv) -> np.ndarray:
    return env.action_space.sample()


def _competent_policy(env: ManifoldEnv) -> np.ndarray:
    """Privileged PD controller steering position toward the HIHO setpoint.

    Optimizes ground-truth capability (proximity to the band), NOT the reward under test —
    this is what keeps the eval non-circular.
    """
    pos = env._position[: env.action_space.shape[0]]
    return np.clip((SETPOINT - pos) * 1.0, -0.5, 0.5).astype(np.float32)


POLICIES = {"null": _null_policy, "random": _random_policy, "competent": _competent_policy}


def run_arm(policy_name: str, reward_mode: str) -> dict:
    """Run one policy across all seeds; return mean±std episode reward and band occupancy."""
    policy = POLICIES[policy_name]
    rewards, occupancies = [], []
    for seed in SEEDS:
        env = ManifoldEnv(reward_mode=reward_mode)
        env.reset(seed=seed)
        ep_reward, in_band = 0.0, 0
        for _ in range(HORIZON):
            action = policy(env)
            _obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            # ground-truth capability: is the system inside the HIHO band this step?
            dev = info.get("hiho_deviation")
            if dev is None:
                dev = abs(info.get("coherence", 0.0) - SETPOINT)
            if dev < 0.1:
                in_band += 1
            if terminated or truncated:
                break
        rewards.append(ep_reward)
        occupancies.append(in_band / HORIZON)
    return {
        "reward_mean": statistics.mean(rewards),
        "reward_std": statistics.pstdev(rewards),
        "band_mean": statistics.mean(occupancies),
        "band_std": statistics.pstdev(occupancies),
    }


def _ranking(stats: dict, key: str) -> list[str]:
    return sorted(stats, key=lambda a: stats[a][key], reverse=True)


def audit_reward_mode(reward_mode: str) -> dict:
    stats = {name: run_arm(name, reward_mode) for name in POLICIES}
    reward_rank = _ranking(stats, "reward_mean")
    band_rank = _ranking(stats, "band_mean")

    # Verdict 1: does the reward separate competence from non-competence?
    sep = stats["competent"]["reward_mean"] - max(
        stats["random"]["reward_mean"], stats["null"]["reward_mean"]
    )
    separates = sep > 0.0
    # Verdict 2: does the reward ranking match ground-truth capability ranking?
    aligned = reward_rank == band_rank
    # Verdict 3: gameability — competent must also win on ground truth (sanity of the oracle)
    oracle_valid = band_rank[0] == "competent"

    capability_measuring = bool(separates and aligned and oracle_valid)
    return {
        "reward_mode": reward_mode,
        "stats": stats,
        "reward_ranking": reward_rank,
        "band_ranking": band_rank,
        "competent_minus_baseline": round(sep, 4),
        "separates_competence": separates,
        "ranking_aligned_with_capability": aligned,
        "oracle_valid": oracle_valid,
        "verdict_reward_measures_capability": capability_measuring,
    }


def main() -> int:
    print(
        f"Universes reward-integrity eval | {len(SEEDS)} seeds | horizon {HORIZON} | local/numpy\n"
    )
    results = []
    for mode in ("verifiable", "dense", "curriculum"):
        r = audit_reward_mode(mode)
        results.append(r)
        print(f"=== reward_mode = {mode} ===")
        print(f"{'arm':<11} {'reward (mean±std)':<24} {'HIHO band occ.':<18}")
        for name in POLICIES:
            s = r["stats"][name]
            print(
                f"{name:<11} {s['reward_mean']:+8.3f} ± {s['reward_std']:<10.3f}  "
                f"{s['band_mean']:.2f} ± {s['band_std']:.2f}"
            )
        print(f"reward ranking : {' > '.join(r['reward_ranking'])}")
        print(f"capability rank: {' > '.join(r['band_ranking'])}")
        print(
            f"VERDICT: reward measures capability = {r['verdict_reward_measures_capability']} "
            f"(separates={r['separates_competence']}, aligned={r['ranking_aligned_with_capability']})\n"
        )

    with open("autoresearch.jsonl", "a") as f:
        f.write(
            json.dumps(
                {
                    "experiment": "universes_reward_integrity",
                    "horizon": HORIZON,
                    "seeds": len(SEEDS),
                    "results": [
                        {
                            "reward_mode": r["reward_mode"],
                            "verdict": r["verdict_reward_measures_capability"],
                            "reward_ranking": r["reward_ranking"],
                            "band_ranking": r["band_ranking"],
                            "competent_minus_baseline": r["competent_minus_baseline"],
                        }
                        for r in results
                    ],
                }
            )
            + "\n"
        )
    print("logged -> autoresearch.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
