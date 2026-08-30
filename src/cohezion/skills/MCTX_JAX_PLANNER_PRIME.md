---
name: mctx-jax-planner-prime
description: "Expertise in deploying Google DeepMind's Mctx (Monte Carlo Tree Search in JAX) on AMD GPUs/CPUs for parallelized multi-step planning, Kaggle ARC-AGI grid search, and AIMO theorem state exploration."
metadata:
  version: "v1.0"
  concepts: ["Monte Carlo Tree Search (MCTS)", "JAX JIT Accelerator", "MuZero Search Policy", "PUCT Action Selection"]
  see_also: ["KAGGLE_AUTOHARNESS_PRIME", "SWARM_ORCHESTRATION_PRIME"]
  source: "src/cohezion/skills/MCTX_JAX_PLANNER_PRIME.md"
---

# SKILL: MCTX_JAX_PLANNER_PRIME

## DOMAIN EXPERTISE
Expertise in Monte Carlo Tree Search (MCTS) utilizing DeepMind's `mctx` JAX-native primitives. Enables batched, parallel tree-search policies across local AMD silicon without Python GIL bottlenecks.

## KEY TEXTS & CONCEPTS
- **DeepMind Mctx**: High-throughput JIT-compiled search algorithms (AlphaZero, MuZero, Gumbel MuZero) running natively in JAX.
- **PUCT (Predictor Upper Confidence Bounds for Trees)**: Balancing exploration and exploitation across agent reasoning branches.
- **Hardware Acceleration on AMD**: JAX ROCm / CPU vectorization mapping thousands of tree simulations per second on 128GB unified memory.

## INSTRUCTION
1. Define the policy-value network representation:
   ```python
   import mctx
   import jax.numpy as jnp

   # Execute batched Gumbel MuZero tree search
   def run_mctx_planning(root_state, recurrent_fn, num_simulations=64):
       policy_output = mctx.gumbel_muzero_policy(
           params={},
           rng_key=jax.random.PRNGKey(42),
           root=root_state,
           recurrent_fn=recurrent_fn,
           num_simulations=num_simulations
       )
       return policy_output.action
   ```
2. Integrate Mctx planning into Kaggle ARC-AGI 2026 search loops to discover spatial grid transformation sequences with zero LLM hallucinations.

## VERSION
v1.0
