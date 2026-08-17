---
title: "Technical Specification: Hyperbolic Hallucination Horizon (Experiment 1)"
experiment_id: "EXP-LOCAL-001"
status: "SPECIFIED"
version: "1.0"
date: "2026-08-16"
authors: ["Antigravity Master Orchestrator", "deepseek-v4-pro:cloud"]
hardware_target: "AMD Strix Halo (NPU XDNA2 + iGPU Radeon 8060S + CPU Ryzen 9)"
---

# EXP-001: Hyperbolic Hallucination Horizon

## 1. Theoretical Foundation & Hypothesis
In high-dimensional hyperbolic embeddings (12D Poincaré ball model $\mathbb{B}^{12}$), factual completions follow smooth, stable geodesic paths, whereas hallucinated/confabulated completions exhibit abrupt orthogonal curvature deviations. 
We hypothesize that the local Lyapunov exponent $\lambda$ of embedding trajectory perturbations predicts hallucination $\ge 300\text{ ms}$ before lexical incoherence appears in generated tokens:
$$\lambda = \lim_{t \to \infty} \frac{1}{t} \ln \frac{\|\delta \mathbf{z}(t)\|}{\|\delta \mathbf{z}(0)\|}$$
Where $\mathbf{z}(t) \in \mathbb{B}^{12}$ is the projected semantic state at token step $t$.

## 2. Hardware Architecture & Partitioning
- **NPU (AMD XDNA2 @ 50 TOPS)**: Continuously embeds token prefix sequences using `embed-gemma-300m-FLM` (:13305), projecting them into 12D Poincaré coordinates using the holographic projection formula:
  $$d_P(u, v) = \text{arcosh}\left(1 + 2\frac{\|u - v\|^2}{(1 - \|u\|^2)(1 - \|v\|^2)}\right), \quad \|u\| \le 0.99$$
- **iGPU (Radeon 8060S Vulkan/ROCm)**: Executes token generation using `Qwen3-Coder-30B-A3B-Instruct-GGUF`.
- **CPU (Ryzen 9 7945HX)**: Computes perturbation divergence $\delta \mathbf{z}$, tracks Lyapunov exponent $\lambda$, and validates output against AutoHarness AST formal rules.

## 3. Resurrectable Implementation Blueprint
```python
# Standalone execution blueprint if codebase is reconstructed:
import math
import numpy as np

def compute_poincare_distance(u: np.ndarray, v: np.ndarray) -> float:
    norm_u_sq = min(float(np.sum(u**2)), 0.99)
    norm_v_sq = min(float(np.sum(v**2)), 0.99)
    diff_sq = float(np.sum((u - v)**2))
    num = 2.0 * diff_sq
    den = (1.0 - norm_u_sq) * (1.0 - norm_v_sq)
    return math.acosh(max(1.0, 1.0 + num / den))

def compute_lyapunov_divergence(traj: list[np.ndarray]) -> float:
    if len(traj) < 3:
        return 0.0
    deltas = [compute_poincare_distance(traj[i], traj[i-1]) for i in range(1, len(traj))]
    log_growths = [math.log(max(1e-6, deltas[i] / max(1e-6, deltas[i-1]))) for i in range(1, len(deltas))]
    return float(np.mean(log_growths))
```

## 4. SurrealDB & Obsidian Dual-Store Schema
- **SurrealDB Table `exp_hallucination_horizon`**:
  ```sql
  DEFINE TABLE exp_hallucination_horizon SCHEMAFULL;
  DEFINE FIELD prompt ON exp_hallucination_horizon TYPE string;
  DEFINE FIELD token_trajectory ON exp_hallucination_horizon TYPE array<object>;
  DEFINE FIELD lyapunov_exponent ON exp_hallucination_horizon TYPE float;
  DEFINE FIELD verified_correct ON exp_hallucination_horizon TYPE bool;
  DEFINE FIELD timestamp ON exp_hallucination_horizon TYPE datetime DEFAULT time::now();
  ```
- **Obsidian Vault File**: `~/vaults/cohezion-vault/experiments/EXP-001-hyperbolic-hallucination.md`
