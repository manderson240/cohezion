---
name: terminal-rsi-recursive-self-improvement
metadata:
  version: "1.0.0"
description: >-
  Recursive self-improving terminal agents via verified trajectory rewriting (RSR), turn-boundary credit assignment (TB-GAE), and success-prioritized rewards (SPR) per arXiv:2610.22192.
---

# SKILL: TERMINAL_RSI_RECURSIVE_SELF_IMPROVEMENT_PRIME

## DOMAIN EXPERTISE
Expertise in recursively self-improving autonomous terminal agents and coding swarms based on the Terminal-RSI paradigm (arXiv:2610.22192). Eliminates temporal dilation in long-horizon interaction chains, resolves the proxy-outcome reward mismatch, and couples verified trajectory self-rewriting with critic-inheriting policy refinement. Operates on Turn-Boundary Skip-Observation GAE (TB-GAE), Success-Prioritized Reward (SPR) with bounded partial credit, and phase-adaptive optimization schedules.

## KEY TEXTS & CONCEPTS
- **Temporal Dilation in Terminal Agents**: In interactive environments, hundreds of tokens express a single command while thousands of passive observation/stdout tokens contain no policy decisions. Standard GAE across token chains attenuates credit according to log verbosity rather than consequential decisions.
- **TB-GAE (Turn-Boundary Skip-Observation GAE)**: Formulates credit assignment across interaction turn boundaries $B$: attenuation $(\gamma_{\rm turn} \lambda_{\rm turn})^B$ is strictly invariant to observation token counts or within-turn text length. Observations condition values but are never recursion nodes.
- **Proxy-Outcome Mismatch & SPR**: Conventional dense progress rewards allow failed trajectories to accumulate up to 50% of total reward mass through minor checks without satisfying the complete execution contract. **Success-Prioritized Reward (SPR)** guarantees:
  $$R_{\rm SPR}(S, P, D'_f) = S + \frac{P}{P + D'_f}$$
  where every failed trajectory scores in $[0.0, 1.0)$ and every verified completion scores in $[1.0, 2.0)$.
- **Recursive Self-Rewrite (RSR)**: Collects discovery trajectories under complementary harnesses, filters through strict verification $\mathcal{V}_x(\tau)=1$ and leakage review $q_{\rm leak}(\tau)=1$, abstracts runbooks, and replays clean public executions.
- **Critic-Inheriting Policy Refine (RPR)**: Preserves learned value function weights across actor transitions ($\Delta \phi |_{\rm RSR} = 0$), recalibrates the critic with actor frozen for warm-up steps, and reduces the actor learning rate fivefold in later cycles to consolidate discovered skills without policy collapse.

## INSTRUCTION

1. **Calculate Success-Prioritized Reward (SPR)**:
   ```python
   from cohezion.agi.terminal_rsi import SuccessPrioritizedReward, FamilyCalibrationConfig

   configs = {
       "kaggle_track": FamilyCalibrationConfig(family="kaggle_track", default_divisor=80.0)
   }
   spr = SuccessPrioritizedReward(family_configs=configs)

   # Incomplete run with 50 passing unit tests: strictly < 1.0
   r_fail = spr.compute_reward(strict_success=False, passed_checks=50, family="kaggle_track")
   assert r_fail < 1.0

   # Complete verified run: strictly >= 1.0
   r_success = spr.compute_reward(strict_success=True, passed_checks=50, family="kaggle_track")
   assert r_success >= 1.0
   ```

2. **Compute Turn-Boundary Skip-Observation Advantages (TB-GAE)**:
   ```python
   from cohezion.agi.terminal_rsi import TurnBoundaryGAE, TurnStep

   tb_gae = TurnBoundaryGAE(gamma_turn=0.95, lambda_turn=0.90)

   # Steps grouped by turn_id; observation tokens do NOT advance the decay clock
   steps = [
       TurnStep(turn_id=0, is_decision_token=True, value=1.2, reward=0.0),
       TurnStep(turn_id=0, is_decision_token=True, value=1.2, reward=0.0), # Same turn: unit decay
       TurnStep(turn_id=1, is_decision_token=True, value=2.0, reward=10.0, is_terminal=True), # New turn
   ]

   advantages, targets = tb_gae.compute_advantages(steps)
   ```

3. **Curate Clean Trajectories with Recursive Trajectory Rewriter (RSR)**:
   ```python
   from cohezion.agi.terminal_rsi import RecursiveTrajectoryRewriter

   rsr = RecursiveTrajectoryRewriter()
   # Ingest only if strict verifier AND leakage gates pass
   rsr.evaluate_and_ingest(
       task_id="arc_task_42",
       actions=[{"tool": "bash", "cmd": "pytest -q"}],
       final_output="PASS",
       verifier_outcome=True,
       leakage_clean=True,
       runbook="1. Run preflight 2. Apply invariant patch 3. Verify assertions",
   )

   clean_replay_multiset = rsr.get_clean_replay_batch()
   ```

## VERSION
v1.0

## SEE ALSO
- `AUTOHARNESS_MULTI_DAY_ROTATION_PRIME`
- `LLM_TO_FLOW_DISTILLATION_PRIME`
- `COORDINATE_AGENTS_BUS_PRIME`
- `AGENTIC_SECURITY_GUARDRAILS_PRIME`
