"""Can a trained policy drive ManifoldEnv to the HIHO vacuum, and do its worldlines separate?

WHY THIS EXPERIMENT EXISTS
--------------------------
`research/2026-07-10-journeys-exotic-vacuum-flume.md` grades the exotic-vacuum analogy
line by line. Its verdict: the ONLY non-decorative element is that coherence 0.5 is the
unique interior maximum of the shared `4c(1-c)` kernel. Two rows are marked DECORATION
for a concrete, measurable reason:

  * "journey = worldline"  -> every live journey has total_steps <= 1.
                              "A one-point path has no tangent, no curvature."
  * "coherence = order parameter" -> live variance is EXACTLY 0 (a static per-skill label).

A smoke test showed ManifoldEnv fixes the first (60 steps -> 60 journey points) but that
under RANDOM actions coherence sits at 0.870 +/- 0.0018 -- varying, yet nowhere near the
0.5 vacuum and barely moving. A worldline that never approaches the vacuum cannot test a
vacuum analogy. So the real question is whether a POLICY can get there.

PRIOR NEGATIVE WE MUST NOT REPEAT BLIND
---------------------------------------
`research/2026-07-10-jepa-journey-surprise-falsified.md`: JEPA journey-surprise was
FALSIFIED (AUC 0.456 vs 0.5 chance; trained slightly WORSE than untrained). Root cause was
diagnosed, not guessed: within-class embedding scatter 11.02 vs between-class centroid
distance 1.21 -- signal ~9x smaller than noise (ratio 0.11) -- plus underfit (3% loss
reduction, failing a >20% "learning happened" gate).

Both of those become PRE-REGISTERED GATES here so this run can return an honest negative
instead of rediscovering the same wall.

DESIGN (falsifiable-eval-harness discipline)
--------------------------------------------
arms:
  treatment       CEM-trained linear policy (19D obs -> 12D action)
  frozen baseline identical architecture, random init, NEVER trained -> must NOT reach HIHO
  placebo         treatment trajectories with labels shuffled -> separation must collapse

gates (declared BEFORE running):
  M0 learning happened : CEM mean return improves > 20%      (JEPA failed this at 3%)
  M1 reaches vacuum    : trained mean |coherence-0.5| < baseline
  M2 dwell time        : trained hiho_time_ratio > baseline
  M3 separation ratio  : between-centroid / within-scatter > 1.0   (JEPA got 0.11)

No new dependencies: hand-rolled CEM, numpy only. stable-baselines3 is deliberately NOT
installed -- resolving it risks replacing torch 2.8.0+rocm6.3 in the shared repo venv.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from cohezion.environments.manifold_env import ManifoldEnv


SEED = 20260812
EPISODE_STEPS = 200
CEM_ITERS = 12
CEM_POP = 24
CEM_ELITE = 6
EVAL_EPISODES = 12

OBS_DIM, ACT_DIM = 19, 12
N_PARAMS = OBS_DIM * ACT_DIM + ACT_DIM

# Pre-registered gates
GATE_LEARNING_IMPROVEMENT = 0.20
GATE_SEPARATION_RATIO = 1.0


def policy_action(theta: np.ndarray, obs: np.ndarray) -> np.ndarray:
    w = theta[: OBS_DIM * ACT_DIM].reshape(OBS_DIM, ACT_DIM)
    b = theta[OBS_DIM * ACT_DIM :]
    return np.tanh(obs @ w + b)


def rollout(theta: np.ndarray, seed: int, steps: int = EPISODE_STEPS) -> dict:
    """One episode. Returns return, coherence stats, and the 12D worldline."""
    env = ManifoldEnv()
    obs, _ = env.reset(seed=seed)
    total, coherences, states = 0.0, [], []
    hiho_ratio = 0.0
    for _ in range(steps):
        act = policy_action(theta, np.asarray(obs, dtype=np.float64))
        act = np.clip(act, env.action_space.low, env.action_space.high).astype(np.float32)
        obs, reward, terminated, truncated, info = env.step(act)
        total += float(reward)
        c = info.get("coherence")
        if c is not None:
            coherences.append(float(c))
        states.append(np.asarray(obs, dtype=np.float64)[:12])  # 12D axiomatic state
        hiho_ratio = float(info.get("hiho_time_ratio", hiho_ratio))
        if terminated or truncated:
            break
    arr = np.asarray(coherences) if coherences else np.array([np.nan])
    return {
        "return": total,
        "coh_mean": float(np.nanmean(arr)),
        "coh_std": float(np.nanstd(arr)),
        "abs_dev": float(np.nanmean(np.abs(arr - 0.5))),
        "hiho_time_ratio": hiho_ratio,
        "steps": len(states),
        "worldline": np.asarray(states),
    }


def train_cem(rng: np.random.Generator) -> tuple[np.ndarray, list[float]]:
    mu = np.zeros(N_PARAMS)
    sigma = np.ones(N_PARAMS) * 0.5
    history = []
    for it in range(CEM_ITERS):
        pop = rng.normal(mu, sigma, size=(CEM_POP, N_PARAMS))
        scores = np.array([rollout(p, seed=SEED + it, steps=100)["return"] for p in pop])
        elite = pop[np.argsort(scores)[-CEM_ELITE:]]
        mu, sigma = elite.mean(axis=0), elite.std(axis=0) + 1e-3
        history.append(float(scores.mean()))
        print(
            f"  CEM iter {it + 1:2d}/{CEM_ITERS}  mean_return={scores.mean():+.4f}  "
            f"best={scores.max():+.4f}",
            flush=True,
        )
    return mu, history


def separation_ratio(a: np.ndarray, b: np.ndarray) -> dict:
    """Between-centroid distance vs within-class scatter — the metric that killed JEPA."""
    ca, cb = a.mean(axis=0), b.mean(axis=0)
    between = float(np.linalg.norm(ca - cb))
    within = float(
        np.mean([np.linalg.norm(a - ca, axis=1).mean(), np.linalg.norm(b - cb, axis=1).mean()])
    )
    return {
        "between_centroid": between,
        "within_scatter": within,
        "ratio": between / within if within > 0 else float("inf"),
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    print("=" * 74)
    print("ARM: frozen baseline (random init, NEVER trained)")
    theta_base = rng.normal(0, 0.5, size=N_PARAMS)

    print("ARM: treatment (CEM training)")
    theta_trained, history = train_cem(np.random.default_rng(SEED + 1))

    print("\nEvaluating both arms on held-out seeds...")
    ev_seeds = [SEED + 1000 + i for i in range(EVAL_EPISODES)]
    base = [rollout(theta_base, s) for s in ev_seeds]
    trained = [rollout(theta_trained, s) for s in ev_seeds]

    def agg(rs, k):
        return float(np.mean([r[k] for r in rs]))

    wl_base = np.vstack([r["worldline"] for r in base])
    wl_trained = np.vstack([r["worldline"] for r in trained])
    sep = separation_ratio(wl_trained, wl_base)

    # placebo: shuffle the class labels — separation must collapse toward 0
    pooled = np.vstack([wl_trained, wl_base])
    idx = np.random.default_rng(SEED + 7).permutation(len(pooled))
    half = len(pooled) // 2
    sep_placebo = separation_ratio(pooled[idx[:half]], pooled[idx[half:]])

    # M0 must be robust to CEM's iteration-to-iteration noise. First-vs-last is NOT:
    # on the 2026-08-12 run it read +65.2%, while picking iters 5->6 from the SAME
    # history gives -241.3%. Series std was 4.0 on a mean near -10, so endpoint choice
    # dominates. Compare the mean of the first half against the second half instead.
    first, last = history[0], history[-1]
    endpoint_improvement = (last - first) / (abs(first) + 1e-9)
    half = len(history) // 2
    fh, sh = float(np.mean(history[:half])), float(np.mean(history[half:]))
    improvement = (sh - fh) / (abs(fh) + 1e-9)

    results = {
        "seed": SEED,
        "learning": {
            "first": first,
            "last": last,
            "endpoint_improvement_FRAGILE": endpoint_improvement,
            "first_half_mean": fh,
            "second_half_mean": sh,
            "improvement": improvement,
            "history": history,
        },
        "baseline": {
            k: agg(base, k) for k in ("return", "coh_mean", "abs_dev", "hiho_time_ratio", "steps")
        },
        "treatment": {
            k: agg(trained, k)
            for k in ("return", "coh_mean", "abs_dev", "hiho_time_ratio", "steps")
        },
        "separation": sep,
        "separation_placebo": sep_placebo,
    }

    print("\n" + "=" * 74)
    print("RESULTS")
    print("=" * 74)
    print(
        f"M0 learning happened : half-means {fh:+.4f} -> {sh:+.4f}  "
        f"improvement={improvement:+.1%}   gate>{GATE_LEARNING_IMPROVEMENT:.0%}  "
        f"{'PASS' if improvement > GATE_LEARNING_IMPROVEMENT else 'FAIL'}"
    )
    print(
        f"   (endpoint-only would read {endpoint_improvement:+.1%} — FRAGILE, "
        f"not used for the gate)"
    )
    print(
        f"M1 |coherence-0.5|   : baseline={results['baseline']['abs_dev']:.4f}  "
        f"trained={results['treatment']['abs_dev']:.4f}  "
        f"{'PASS' if results['treatment']['abs_dev'] < results['baseline']['abs_dev'] else 'FAIL'}"
    )
    print(
        f"   coherence mean    : baseline={results['baseline']['coh_mean']:.4f}  "
        f"trained={results['treatment']['coh_mean']:.4f}   (vacuum = 0.5)"
    )
    print(
        f"M2 hiho_time_ratio   : baseline={results['baseline']['hiho_time_ratio']:.4f}  "
        f"trained={results['treatment']['hiho_time_ratio']:.4f}  "
        f"{'PASS' if results['treatment']['hiho_time_ratio'] > results['baseline']['hiho_time_ratio'] else 'FAIL'}"
    )
    print(
        f"M3 separation ratio  : between={sep['between_centroid']:.4f}  "
        f"within={sep['within_scatter']:.4f}  ratio={sep['ratio']:.4f}  "
        f"gate>{GATE_SEPARATION_RATIO}  {'PASS' if sep['ratio'] > GATE_SEPARATION_RATIO else 'FAIL'}"
    )
    print(f"   placebo ratio     : {sep_placebo['ratio']:.4f}   (must be ~0 — shuffled labels)")
    print("   JEPA reference    : 0.1098  (1.21 / 11.02, the prior FALSIFIED run)")

    out = Path("/tmp/claude-1000/manifold_hiho_results.json")
    out.write_text(json.dumps(results, indent=2, default=float))
    print(f"\nresults -> {out}")


if __name__ == "__main__":
    main()
