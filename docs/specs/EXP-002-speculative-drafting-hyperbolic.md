---
title: "Technical Specification: Dual-Silicon Speculative Drafting with Hyperbolic Gates (Experiment 2)"
experiment_id: "EXP-LOCAL-002"
status: "SPECIFIED"
version: "1.0"
date: "2026-08-16"
authors: ["Antigravity Master Orchestrator", "deepseek-v4-pro:cloud"]
hardware_target: "AMD Strix Halo (NPU XDNA2 + iGPU Radeon 8060S + CPU Ryzen 9)"
---

# EXP-002: Dual-Silicon Speculative Drafting with Hyperbolic Acceptance Gates

## 1. Theoretical Foundation & Hypothesis
Standard speculative decoding uses exact token match or top-$p$ probability ratios. We hypothesize that gating candidate blocks $K \in [3, 8]$ using **hyperbolic geodesic distance** $d_P(\mathbf{z}_{\text{draft}}, \mathbf{z}_{\text{target}}) \le \theta$ enables:
1. High acceptance rates ($\alpha \ge 75\%$) even with domain-shifted draft models.
2. $>180\text{ tok/s}$ sustained decode throughput on AMD Strix Halo without sacrificing token distribution fidelity.

## 2. Hardware Architecture & Partitioning
- **NPU (XDNA2)**: Runs ultra-fast draft generator `llama3.2-1b-FLM` (prefill $>1,300\text{ tok/s}$, decode $>140\text{ tok/s}$) proposing $K=4$ token sequences.
- **iGPU (Radeon 8060S Vulkan/ROCm)**: Runs primary target model `Qwen3-Coder-30B-A3B-Instruct-GGUF` verifying the $K$-token block in a single forward pass.
- **CPU (Ryzen 9 7945HX)**: Manages lockless ring buffer, computes conformal factor $\lambda(u) = \frac{2}{1 - \|u\|^2}$, and adjusts threshold $\theta$ dynamically based on KV-cache pressure.

## 3. Resurrectable Implementation Blueprint
```python
# Standalone execution blueprint:
from dataclasses import dataclass

@dataclass
class SpeculativeBlock:
    draft_tokens: list[int]
    draft_embeddings: list[list[float]]
    target_logits: list[list[float]]

def evaluate_hyperbolic_acceptance(draft_vec: list[float], target_vec: list[float], threshold: float = 0.45) -> bool:
    import math
    u, v = tuple(draft_vec[:3]), tuple(target_vec[:3])
    norm_u = min(sum(x*x for x in u), 0.99)
    norm_v = min(sum(x*x for x in v), 0.99)
    diff_sq = sum((x-y)**2 for x, y in zip(u, v))
    num = 2.0 * diff_sq
    den = (1.0 - norm_u) * (1.0 - norm_v)
    d_p = math.acosh(max(1.0, 1.0 + num / den))
    return d_p <= threshold
```

## 4. SurrealDB & Obsidian Dual-Store Schema
- **SurrealDB Table `exp_speculative_drafting`**:
  ```sql
  DEFINE TABLE exp_speculative_drafting SCHEMAFULL;
  DEFINE FIELD draft_model ON exp_speculative_drafting TYPE string;
  DEFINE FIELD target_model ON exp_speculative_drafting TYPE string;
  DEFINE FIELD tokens_per_sec ON exp_speculative_drafting TYPE float;
  DEFINE FIELD acceptance_rate ON exp_speculative_drafting TYPE float;
  DEFINE FIELD avg_geodesic_distance ON exp_speculative_drafting TYPE float;
  DEFINE FIELD timestamp ON exp_speculative_drafting TYPE datetime DEFAULT time::now();
  ```
- **Obsidian Vault File**: `~/vaults/cohezion-vault/experiments/EXP-002-speculative-drafting.md`
