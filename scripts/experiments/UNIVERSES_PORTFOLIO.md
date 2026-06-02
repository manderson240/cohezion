---
title: "Universes Portfolio — experiments that improve Cohezion and target the RE-Universes role"
date: 2026-06-01
role: "Anthropic Research Engineer, Universes (greenhouse 5061517008)"
thesis: "The role builds agentic RL environments + rigorous evaluations that measure real capability. Cohezion already ships gymnasium RL envs (ManifoldEnv, SwarmEnv) and a falsifiable-eval-harness. The experiments that strengthen the application are the same ones that improve Cohezion."
---

# Universes Portfolio

Role deliverables (verbatim): "Build the next generation of agentic environments" · "Build
rigorous evaluations that measure real capability" · "ship environments into production training"
· "Debug and iterate rapidly across research and production ML stacks". Nice-to-haves: RL
environment/simulation systems, LLM eval, distributed/sandbox infra.

All experiments run on **local AMD silicon** (NPU 13306 / iGPU→router 13305 / CPU 13309), $0,
machine-always-on. Honest metrics, multi-seed, verdicts that can fail.

## Exp #1 — Reward-integrity eval  ✅ DONE (winner; found a real bug)
`universes_reward_integrity.py`. 3-arm falsifiable audit (null / random / competent-oracle) of
ManifoldEnv's reward *function*. Ground truth = HIHO-band occupancy, defined independently of the
reward (non-circular). **Result:** the `verifiable` reward mode is reward-hackable — null/random
out-score the only competent arm; do-nothing wins. `dense`/`curriculum` pass. Root cause:
`r_hiho = 1 - 4·var(pos)` rewards uniformity not 0.5-proximity, and drift penalties punish the
movement needed to reach the band. (RETRO-2026-06-01k.)
→ Maps to: "rigorous evaluations that measure real capability" + caught a reward-hacking vuln.

## Exp #2 — Active-Inference policy in the environment  (designed; runnable on fleet)
Use this session's `Observer`/`SurpriseRouter` as a *policy*: maintain a lightweight forward model
of the 19D obs; per step compute surprise (prediction error), route EXPLORE (larger perturbation)
vs EXPLOIT (PD toward setpoint). Baselines: pure-random, pure-PD. Metric: HIHO-band occupancy +
episode reward (under the FIXED dense reward) over long horizons (≥500 steps), 12 seeds.
Hypothesis: surprise-driven explore/exploit reaches and holds the band more than fixed policies.
Forward-model inference can route to the fleet. Falsifiable: if active inference ≤ pure-PD, report
honest negative.
→ Maps to: "agentic environments" + RL + long-horizon; empirically tests whether the Observer is useful.

## Exp #3 — Gated environment self-improvement (A-Evolve under the integrity gate)  (designed)
Let the harness propose reward-shaping edits (e.g. fix `r_hiho` → `1 - 4·mean((pos-0.5)²)`);
**gate every candidate with Exp #1**: accept only if the edited reward PASSES the 3-arm integrity
test (separates competence, aligned with capability) AND raises trained-policy band occupancy.
Exp #1 becomes the regression gate that prevents reward-hacking regressions during self-improvement.
→ Maps to: "ship environments into production training" + "iterate across research and production
stacks"; makes self-improvement safe by construction. (Builds on the honest-negative evolution_scaling.)

## Immediate Cohezion improvement unlocked by Exp #1
Fix the `verifiable` reward (`r_hiho` proximity term + drift-penalty weights), then re-run Exp #1
as the regression gate. Converts a found vulnerability into a hardened, capability-aligned
verifiable-reward mode — directly improving the RL environment cohezion ships.
