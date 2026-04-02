#!/usr/bin/env python3
"""Compound Training Cycle — the compound engineering loop applied to RL.

This script IS the compound loop:
  1. TRAIN: Run algorithm on ManifoldEnv with best-known config
  2. EVALUATE: Compare against baselines with UniverseEvaluator
  3. PERSIST: Save run to SurrealDB with full diagnostic
  4. COMPARE: Check if this run improves on prior best
  5. REFINE: If improved, log the finding for skill refinement
  6. REPORT: Print results table with historical context

Usage:
    .venv/bin/python scripts/compound_training_cycle.py                    # SAC dense (best known)
    .venv/bin/python scripts/compound_training_cycle.py --algo ppo         # PPO curriculum
    .venv/bin/python scripts/compound_training_cycle.py --steps 200000     # More training
    .venv/bin/python scripts/compound_training_cycle.py --history          # Show all runs
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.request
from base64 import b64encode
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("HIP_VISIBLE_DEVICES", "")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger("compound-train")

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_HEADERS = {
    "Accept": "application/json",
    "surreal-ns": "cohezion",
    "surreal-db": "cohezion",
    "Authorization": "Basic " + b64encode(b"root:root").decode(),
}


def surreal_query(sql: str) -> list:
    """Execute SurrealQL and return results."""
    try:
        req = urllib.request.Request(
            SURREAL_URL, data=sql.encode(), headers=SURREAL_HEADERS, method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read())
    except Exception:
        return []


def get_best_run() -> dict | None:
    """Get the best training run from SurrealDB by reward."""
    results = surreal_query("SELECT * FROM training_run ORDER BY reward DESC LIMIT 1;")
    if results and results[0].get("status") == "OK" and results[0]["result"]:
        return results[0]["result"][0]
    return None


def get_run_history() -> list:
    """Get all training runs ordered by date."""
    results = surreal_query(
        "SELECT algorithm, timesteps, reward_mode, reward, convergence_rate, random_reward, diagnostic FROM training_run ORDER BY reward DESC;"
    )
    if results and results[0].get("status") == "OK":
        return results[0]["result"]
    return []


def train_and_evaluate(algo: str, steps: int, reward_mode: str, ent_coef: float) -> dict:
    """Train an agent and evaluate against baselines."""
    import numpy as np
    from gymnasium import spaces

    from cohezion.environments.manifold_env import ManifoldEnv
    from cohezion.eval.universe_evaluator import (
        UniverseEvaluator,
        greedy_hiho_policy,
        random_policy,
    )

    env = ManifoldEnv(max_steps=200, seed=42, reward_mode=reward_mode)
    env.action_space = spaces.Box(low=-0.1, high=0.1, shape=(12,), dtype=np.float32)

    logger.info(
        "Training %s (%dK steps, %s reward, ent=%.2f)...",
        algo,
        steps // 1000,
        reward_mode,
        ent_coef,
    )
    start = time.time()

    if algo.upper() == "SAC":
        from stable_baselines3 import SAC

        model = SAC(
            "MlpPolicy",
            env,
            verbose=0,
            seed=42,
            learning_rate=3e-4,
            batch_size=256,
            device="cpu",
            ent_coef=ent_coef,
            learning_starts=1000,
            train_freq=1,
            gradient_steps=1,
        )
    else:
        from stable_baselines3 import PPO

        model = PPO(
            "MlpPolicy",
            env,
            verbose=0,
            seed=42,
            n_steps=512,
            batch_size=64,
            learning_rate=3e-4,
            device="cpu",
        )

    model.learn(total_timesteps=steps)
    train_time = time.time() - start
    logger.info("Training complete in %.1fs", train_time)

    # Evaluate
    evaluator = UniverseEvaluator(n_bootstrap=50)

    def trained_policy(obs):
        a, _ = model.predict(obs, deterministic=True)
        return np.clip(a, -0.1, 0.1).astype(np.float32)

    trained = evaluator.evaluate_policy(
        env, trained_policy, n_episodes=10, policy_name=f"{algo}-{reward_mode}"
    )
    rnd = evaluator.evaluate_policy(env, random_policy, n_episodes=10, policy_name="Random")
    greedy = evaluator.evaluate_policy(env, greedy_hiho_policy, n_episodes=10, policy_name="Greedy")

    return {
        "algorithm": algo,
        "timesteps": steps,
        "reward_mode": reward_mode,
        "ent_coef": ent_coef,
        "train_time": train_time,
        "coherence": trained.mean_coherence,
        "reward": trained.mean_reward,
        "stability": trained.mean_stability_duration,
        "convergence": trained.convergence_rate,
        "random_reward": rnd.mean_reward,
        "random_convergence": rnd.convergence_rate,
        "greedy_reward": greedy.mean_reward,
        "greedy_convergence": greedy.convergence_rate,
    }


def persist_run(run: dict) -> None:
    """Persist training run to SurrealDB."""
    best = get_best_run()
    is_improvement = best is None or run["reward"] > best.get("reward", 0)

    diagnostic = (
        f"{run['algorithm']} {run['reward_mode']} {run['timesteps'] // 1000}K: "
        f"reward={run['reward']:.2f} (vs random {run['reward'] - run['random_reward']:+.2f}, "
        f"vs greedy {run['reward'] - run['greedy_reward']:+.2f}). "
        f"{'NEW BEST!' if is_improvement else 'No improvement.'}"
    )

    sql = (
        f"CREATE training_run SET "
        f"algorithm = '{run['algorithm']}', "
        f"timesteps = {run['timesteps']}, "
        f"reward_mode = '{run['reward_mode']}', "
        f"ent_coef = {run['ent_coef']}, "
        f"training_time_s = {run['train_time']:.1f}, "
        f"coherence = {run['coherence']:.3f}, "
        f"reward = {run['reward']:.2f}, "
        f"stability = {run['stability']:.0f}, "
        f"convergence_rate = {run['convergence']:.2f}, "
        f"random_reward = {run['random_reward']:.2f}, "
        f"greedy_reward = {run['greedy_reward']:.2f}, "
        f"diagnostic = '{diagnostic}', "
        f"session = 87, date = '2026-04-01', created = time::now();"
    )
    surreal_query(sql)
    logger.info("Persisted to SurrealDB: %s", diagnostic)
    return is_improvement


def print_report(run: dict) -> None:
    """Print the compound training report."""
    print("\n" + "=" * 70)
    print("COMPOUND TRAINING CYCLE REPORT")
    print("=" * 70)
    print(f"  Algorithm:    {run['algorithm']} ({run['reward_mode']} reward)")
    print(f"  Steps:        {run['timesteps']:,}")
    print(f"  Train time:   {run['train_time']:.1f}s")
    print(f"  Coherence:    {run['coherence']:.3f}")
    print(f"  Reward:       {run['reward']:.2f}")
    print(f"  Stability:    {run['stability']:.0f} steps")
    print(f"  Convergence:  {run['convergence']:.1%}")
    print(f"  vs Random:    {run['reward'] - run['random_reward']:+.2f}")
    print(f"  vs Greedy:    {run['reward'] - run['greedy_reward']:+.2f}")
    print("=" * 70)

    # Historical context
    history = get_run_history()
    if history:
        print(f"\nTraining History ({len(history)} runs in SurrealDB):")
        for h in history:
            algo = h.get("algorithm", "?")
            mode = h.get("reward_mode", "curriculum")
            reward = h.get("reward", 0)
            vs_rnd = reward - h.get("random_reward", 0)
            print(
                f"  {algo:4s} {mode:10s} {h.get('timesteps', 0) // 1000:4d}K  reward={reward:7.2f}  vs_random={vs_rnd:+.2f}"
            )
    print()


def main():
    parser = argparse.ArgumentParser(description="Compound Training Cycle")
    parser.add_argument("--algo", default="SAC", choices=["SAC", "PPO"], help="Algorithm")
    parser.add_argument("--steps", type=int, default=100000, help="Training timesteps")
    parser.add_argument(
        "--reward", default="auto", choices=["auto", "curriculum", "dense"], help="Reward mode"
    )
    parser.add_argument("--ent-coef", type=float, default=0.05, help="SAC entropy coefficient")
    parser.add_argument("--history", action="store_true", help="Show history only")
    args = parser.parse_args()

    if args.history:
        history = get_run_history()
        print(f"\nTraining History ({len(history)} runs):")
        for h in history:
            algo = h.get("algorithm") or "?"
            mode = h.get("reward_mode") or "curriculum"
            reward = h.get("reward") or 0
            diag = (h.get("diagnostic") or "")[:60]
            print(f"  {algo:4s} {mode:10s} reward={reward:7.2f}  {diag}")
        return

    # Auto-select reward mode based on algorithm (from L246)
    reward_mode = args.reward
    if reward_mode == "auto":
        reward_mode = "dense" if args.algo == "SAC" else "curriculum"
        logger.info("Auto-selected reward_mode='%s' for %s (L246 matrix)", reward_mode, args.algo)

    run = train_and_evaluate(args.algo, args.steps, reward_mode, args.ent_coef)
    is_new_best = persist_run(run)
    print_report(run)

    if is_new_best:
        print(">>> NEW BEST RUN — triggering SkillRefiner to update RL_ENVIRONMENT_DESIGN_PRIME")
        try:
            from cohezion.compound.skill_refiner import SkillRefiner

            sr = SkillRefiner()
            result = sr.refine_from_training_runs()
            if result:
                print(f">>> Skill refined: {result}")
            else:
                print(">>> Skill already up to date")
        except Exception as e:
            print(f">>> Skill refinement failed (non-blocking): {e}")


if __name__ == "__main__":
    main()
