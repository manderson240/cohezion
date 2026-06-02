#!/usr/bin/env python3
"""R-Zero ascension — challenger/solver self-play co-evolution on ManifoldEnv.

Unifies three threads into one autonomous loop that runs overnight on local silicon ($0):

  * Challenger = the Instigator (cohezion's ConsortiumInstigator is the adversarial half that
    "self-improves by discovering harder challenges"). Here it raises environment difficulty
    `d` toward the R-Zero ~50%-success frontier — the point of maximum learning signal.
  * Solver = this session's active-inference policy (SurpriseRouter explore/exploit) in
    ManifoldEnv: a naive forward model gives a surprise signal; low surprise -> EXPLOIT (PD
    toward the HIHO setpoint), high surprise -> EXPLORE (add epistemic noise).
  * Ascension = the difficulty ceiling the Solver can hold at >=50% success. It rises ONLY if
    the Solver's parameters genuinely improve via co-evolution; if tuning cannot push the
    frontier, the ceiling plateaus and we report that honestly.

Goal framing ("transcendent ascension"): maximize the capability ceiling without reward-hacking
— difficulty is over the *start distance from the setpoint*, success is ground-truth HIHO-band
occupancy (not the reward under test), so the loop cannot game its way up.

Deterministic-fallback, robust for unattended overnight runs: no external/LLM calls in the hot
loop (the AI-capable machine runs the numeric self-play locally). Pure numpy + the env.
"""

from __future__ import annotations

import json
import sys
import time

import numpy as np

from cohezion.environments.manifold_env import ManifoldEnv
from cohezion.world_model.surprise_router import ActionMode, SurpriseRouter


SETPOINT = 0.5
SUCCESS_BAND = 0.12  # band occupancy fraction that counts as "solved"


def _start_at_distance(env: ManifoldEnv, d: float, rng: np.random.Generator) -> None:
    """Privileged challenger move: place the start at L∞ distance ~d from the setpoint."""
    dim = env._position.shape[0]
    direction = rng.choice([-1.0, 1.0], size=dim)
    env._position = np.clip(SETPOINT + direction * d, -1.5, 2.0).astype(np.float32)
    env._velocity = np.zeros(dim, dtype=np.float32)


def run_episode(theta: dict, d: float, seed: int, horizon: int) -> float:
    """Run the active-inference Solver one episode at difficulty d; return band occupancy."""
    env = ManifoldEnv(reward_mode="dense")  # dense passed the integrity audit (RETRO-k)
    env.reset(seed=seed)
    rng = np.random.default_rng(seed + 7919)
    _start_at_distance(env, d, rng)
    router = SurpriseRouter(explore_threshold=theta["explore_threshold"])
    adim = env.action_space.shape[0]
    prev_pos = env._position[:adim].copy()
    in_band = 0
    for _ in range(horizon):
        # naive forward model: predict persistence; surprise = how much the world moved us
        actual = env._position[:adim]
        surprise = float(np.linalg.norm(actual - prev_pos))
        decision = router.observe(surprise)
        base = theta["pd_gain"] * (SETPOINT - env._position[:adim])
        if decision.mode is ActionMode.EXPLORE:
            base = base + rng.normal(0.0, theta["explore_noise"], size=adim)
        action = np.clip(base, -0.5, 0.5).astype(np.float32)
        prev_pos = env._position[:adim].copy()
        _obs, _r, term, trunc, info = env.step(action)
        dev = info.get("hiho_deviation")
        if dev is None:
            dev = abs(info.get("coherence", 0.0) - SETPOINT)
        if dev < 0.1:
            in_band += 1
        if term or trunc:
            break
    return in_band / horizon


def success_rate(theta: dict, d: float, episodes: int, horizon: int, seed0: int) -> float:
    solved = sum(
        1 for k in range(episodes) if run_episode(theta, d, seed0 + k, horizon) >= SUCCESS_BAND
    )
    return solved / episodes


def adapt_solver(
    best: dict,
    d: float,
    episodes: int,
    horizon: int,
    rng: np.random.Generator,
    n_cand: int,
    seed0: int,
) -> tuple[dict, float]:
    """Solver self-improvement: random-search θ around current best, keep the best at difficulty d."""
    best_theta = dict(best)
    best_sr = success_rate(best_theta, d, episodes, horizon, seed0)
    for _ in range(n_cand):
        cand = {
            "pd_gain": float(np.clip(best["pd_gain"] + rng.normal(0, 0.3), 0.1, 3.0)),
            "explore_noise": float(np.clip(best["explore_noise"] + rng.normal(0, 0.1), 0.0, 0.6)),
            "explore_threshold": float(
                np.clip(best["explore_threshold"] + rng.normal(0, 0.1), 0.2, 0.9)
            ),
        }
        sr = success_rate(cand, d, episodes, horizon, seed0)
        if sr > best_sr:
            best_theta, best_sr = cand, sr
    return best_theta, best_sr


def main() -> int:
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    deadline_s = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0  # 0 = no wallclock cap
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 20260601  # vary across overnight cycles
    # Structural solver budget — swept overnight to test whether the ceiling is budget- or
    # dynamics-limited: argv[4]=horizon, argv[5]=n_cand (search width), argv[6]=episodes.
    horizon = int(sys.argv[4]) if len(sys.argv) > 4 else 40
    n_cand = int(sys.argv[5]) if len(sys.argv) > 5 else 6
    episodes = int(sys.argv[6]) if len(sys.argv) > 6 else 6
    rng = np.random.default_rng(seed)
    theta = {"pd_gain": 1.0, "explore_noise": 0.1, "explore_threshold": 0.6}
    d = 0.3
    ceiling = 0.0
    t0 = time.time()
    print(f"R-Zero ascension | rounds<={rounds} | local self-play | start d={d}\n")
    print(
        f"{'round':<6}{'difficulty':<12}{'success':<10}{'ceiling':<10}{'pd_gain':<9}{'noise':<8}{'thr':<6}"
    )
    for rnd in range(rounds):
        # 1. Solver co-evolves at the current frontier.
        theta, sr = adapt_solver(theta, d, episodes, horizon, rng, n_cand, seed0=rnd * 101)
        # 2. Ceiling = hardest difficulty held at >=50% success.
        ascended = False
        if sr >= 0.5 and d > ceiling:
            ceiling, ascended = d, True
        # 3. Challenger (Instigator) drives difficulty toward the 50% frontier.
        if sr > 0.55:
            d = float(min(d * 1.15, 2.0))  # too easy -> harder
        elif sr < 0.45:
            d = float(max(d * 0.9, 0.02))  # too hard -> easier
        flag = "  ASCEND" if ascended else ""
        print(
            f"{rnd:<6}{d:<12.3f}{sr:<10.2f}{ceiling:<10.3f}"
            f"{theta['pd_gain']:<9.2f}{theta['explore_noise']:<8.2f}{theta['explore_threshold']:<6.2f}{flag}"
        )
        with open("autoresearch.jsonl", "a") as f:
            f.write(
                json.dumps(
                    {
                        "experiment": "r_zero_ascension",
                        "round": rnd,
                        "seed": seed,
                        "horizon": horizon,
                        "n_cand": n_cand,
                        "difficulty": round(d, 4),
                        "success_rate": round(sr, 3),
                        "ceiling": round(ceiling, 4),
                        "theta": {k: round(v, 4) for k, v in theta.items()},
                        "ascended": ascended,
                    }
                )
                + "\n"
            )
        if deadline_s and (time.time() - t0) > deadline_s:
            print(f"\n[deadline {deadline_s:.0f}s reached at round {rnd}]")
            break
    print(
        f"\nFINAL capability ceiling (max difficulty held at >=50%): {ceiling:.3f} "
        f"[horizon={horizon} n_cand={n_cand} episodes={episodes} seed={seed}]"
    )
    print("logged -> autoresearch.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
