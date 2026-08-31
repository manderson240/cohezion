---
title: "Technical Specification: Multi-Agent Debate with Poincaré Consensus Dynamics (Experiment 5)"
experiment_id: "EXP-LOCAL-005"
status: "SPECIFIED"
version: "1.0"
date: "2026-08-16"
authors: ["Antigravity Master Orchestrator", "deepseek-v4-pro:cloud"]
hardware_target: "AMD Strix Halo (NPU XDNA2 + iGPU Radeon 8060S + CPU Ryzen 9)"
---

# EXP-005: Multi-Agent Debate with Poincaré Consensus Dynamics

## 1. Theoretical Foundation & Hypothesis
When diverse local models engage in multi-turn debate on complex mathematical proofs, their belief states can be tracked as trajectories in 12D Poincaré hyperbolic space. 
We hypothesize that consensus convergence occurs if and only if the zeroth Betti number of the trajectory point cloud satisfies $\beta_0 \to 1$ under Vietoris-Rips filtration, and the trajectory geodesic centroid stabilizes.

## 2. Hardware Architecture & Partitioning
- **NPU (XDNA2)**: Hosts `qwen3.6-moe-35b-a3b-FLM` (Architect Agent) and `llama3.2-1b-FLM` (Cynical Critic Agent).
- **iGPU (Radeon 8060S)**: Hosts `Qwen3-Coder-30B-A3B-Instruct-GGUF` (Formal Synthesizer & ZKFV Verifier Agent).
- **CPU (Ryzen 9)**: Computes persistent homology, Betti numbers $\beta_0$, and hyperbolic geodesic distances between agent state representations.

## 3. Resurrectable Implementation Blueprint
```python
# Standalone execution blueprint:
import numpy as np

def compute_swarm_hyperbolic_centroid(agent_vectors: list[np.ndarray]) -> np.ndarray:
    # Frechet mean on Poincare ball
    weights = [1.0 / (1.0 - min(float(np.sum(v**2)), 0.99)) for v in agent_vectors]
    total_w = sum(weights)
    weighted_sum = sum(w * v for w, v in zip(weights, agent_vectors))
    centroid = weighted_sum / max(1e-6, total_w)
    # Ensure centroid remains inside unit ball
    norm = np.linalg.norm(centroid)
    if norm >= 1.0:
        centroid = (centroid / norm) * 0.99
    return centroid

def evaluate_consensus_convergence(agent_vectors: list[np.ndarray], threshold: float = 0.25) -> bool:
    centroid = compute_swarm_hyperbolic_centroid(agent_vectors)
    max_dist = max(float(np.linalg.norm(v - centroid)) for v in agent_vectors)
    return max_dist <= threshold
```

## 4. SurrealDB & Obsidian Dual-Store Schema
- **SurrealDB Table `exp_poincare_consensus`**:
  ```sql
  DEFINE TABLE exp_poincare_consensus SCHEMAFULL;
  DEFINE FIELD debate_topic ON exp_poincare_consensus TYPE string;
  DEFINE FIELD agent_roles ON exp_poincare_consensus TYPE array<string>;
  DEFINE FIELD betti_zero ON exp_poincare_consensus TYPE int;
  DEFINE FIELD centroid_norm ON exp_poincare_consensus TYPE float;
  DEFINE FIELD converged ON exp_poincare_consensus TYPE bool;
  DEFINE FIELD timestamp ON exp_poincare_consensus TYPE datetime DEFAULT time::now();
  ```
- **Obsidian Vault File**: `~/vaults/cohezion-vault/experiments/EXP-005-poincare-consensus.md`
