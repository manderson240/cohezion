---
name: hyperbolic-goal-loop-engineering
metadata:
  version: "1.0.0"
description: >-
  Refactor linear execution traces into closed-loop hyperbolic goal controllers with Poincaré Lyapunov potentials, Terminal-RSI SPR gating, and Zobrist anti-cycle livelock evasion.
---

# SKILL: HYPERBOLIC_GOAL_LOOP_ENGINEERING_PRIME

## DOMAIN EXPERTISE
Expertise in transforming passive, open-loop execution traces into active, goal-directed closed-loop controllers embedded in Poincaré hyperbolic manifold space. Eliminates temporal drift and livelocks by framing agent execution as a Lyapunov potential minimization problem $V(\mathbf{z}) = d_{\mathbb{D}}(\mathbf{z}_t, \mathbf{z}^*)$, enforced by Terminal-RSI Success-Prioritized Reward (SPR) gates ($R_{\rm SPR} \ge 1.0$), 64-bit SplitMix64 Zobrist orbit hashing, and sub-microsecond zero-copy shared memory state synchronization (`/dev/shm/cohezion_mesh`).

## KEY TEXTS & CONCEPTS
- **Trace-to-Loop Refactoring**: Linear traces $[a_0, a_1, \dots, a_T]$ record history without enforcing closure. Converting a trace into a closed-loop controller binds the agent to an invariant goal predicate $\mathcal{P}(\mathbf{s}^*) = 1$, executing iterations `Perceive -> Hypothesize -> AutoHarness Verify -> Dispatch -> Evaluate Delta` until convergence.
- **Poincaré Hyperbolic Lyapunov Potential**: Hierarchical goals embed into the open unit ball $\mathbb{D}^{16}$ with metric:
  $$d_{\mathbb{D}}(\mathbf{u}, \mathbf{v}) = \operatorname{arcosh}\left(1 + 2 \frac{\|\mathbf{u} - \mathbf{v}\|^2}{(1 - \|\mathbf{u}\|^2)(1 - \|\mathbf{v}\|^2)}\right)$$
  Monotonic convergence requires $\Delta V(\mathbf{z}_t) \le -\alpha \cdot \text{progress}$, driving the agent toward the origin (target state).
- **SPR Closed-Loop Gating**: Uses Success-Prioritized Reward (arXiv:2610.22192) $R_{\rm SPR}(S, P, D'_f) = S + \frac{P}{P + D'_f}$ where incomplete steps are bounded in $[0.0, 1.0)$ and verified terminal solutions score $\ge 1.0$. The loop is forbidden from exiting on proxy metrics alone.
- **Zobrist Orbit Hashing & Livelock Evasion**: Computes 64-bit SplitMix64 hashes over state tuples $(action, strict\_success, passed\_checks, \text{potential})$. Repeating a hash within the history window triggers `GoalState.LIVELOCK_DETECTED` and prompts an orthogonal invariant perturbation.
- **Zero-Copy RAM Synchronization**: Refactored Goal-Loop states are broadcast to `/dev/shm/cohezion_mesh` via `SharedMemoryDataProductBuffer` using binary `CDMP` headers, enabling sub-microsecond cross-agent state awareness.

## INSTRUCTION

1. **Refactor Linear Trace Events into an Active Hyperbolic Goal-Loop**:
   ```python
   from cohezion.compound.hyperbolic_goal_loop import HyperbolicGoalLoopRefactorEngine

   engine = HyperbolicGoalLoopRefactorEngine()
   events = [
       {"action": "explore_hypothesis", "strict_success": False, "passed_checks": 10},
       {"action": "tune_invariants", "strict_success": False, "passed_checks": 30},
       {"action": "autoharness_verify", "strict_success": True, "passed_checks": 60},
   ]

   goal, controller = engine.refactor_trace(
       trace_id="kaggle_arc2_v17",
       events=events,
       domain="arc_agi",
   )

   assert goal.state == "converged"
   assert controller.history[-1]["spr_score"] >= 1.0
   ```

2. **Run Closed-Loop Iteration with Livelock Detection**:
   ```python
   import numpy as np
   from cohezion.compound.hyperbolic_goal_loop import HyperbolicGoal, HyperbolicLoopController, GoalState

   goal = HyperbolicGoal(goal_id="g_live", intent="Optimize RSNA Blend")
   controller = HyperbolicLoopController(loop_id="loop_rsna", goal=goal)

   converged, spr_score, potential = controller.evaluate_step(
       action_name="apply_kolmogorov_projection",
       strict_success=True,
       passed_checks=50,
       new_coord=np.zeros(16),  # Reached target origin
   )

   if converged:
       print("Goal converged with Lyapunov potential:", potential)
   ```

3. **Persist Refactored Graph into SurrealDB**:
   ```python
   # Upserts formal vertices and creates relation: goal->executed_by->autonomous_loop
   engine.persist_to_surreal(goal, controller)
   ```

## VERSION
v1.0

## SEE ALSO
- `TERMINAL_RSI_RECURSIVE_SELF_IMPROVEMENT_PRIME`
- `COORDINATE_AGENTS_BUS_PRIME`
- `AUTOHARNESS_MULTI_DAY_ROTATION_PRIME`
- `LLM_TO_FLOW_DISTILLATION_PRIME`
