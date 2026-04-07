---
name: multi-model-kernel-optimization
description: |
  Multi-model orchestration pattern for GPU kernel optimization competitions.
  Use when: (1) optimizing GPU kernels across multiple problem types in parallel,
  (2) working on popcorn-cli or similar kernel competition submissions,
  (3) need to conserve expensive model budget while maximizing iteration speed,
  (4) user mentions "quarter on a string" or budget-conscious multi-agent work.
  Key insight: Opus orchestrates, Sonnet writes kernels, Haiku does infra,
  Ollama cloud models iterate API-level variants. Ollama FAILS at custom HIP
  kernel correctness (MFMA register layouts) but works for fused_moe/mla parameter tuning.
author: Claude Code
version: 1.0.0
---

# Multi-Model Kernel Optimization

## Problem

GPU kernel optimization requires many iterations but expensive models (Opus) burn
budget on implementation work that cheaper models can handle. Conversely, cheap models
(Ollama cloud) fail at bit-level HIP kernel correctness.

## Model-to-Task Routing (Verified Session 95)

| Model | Cost | Best For | Fails At |
|-------|------|----------|----------|
| **Opus** | $15/M | Strategy, pivots, skill refinement | Wasteful for kernel writing |
| **Sonnet** | $3/M | HIP kernel code, Triton kernels | Slow for iteration |
| **Haiku** | $0.25/M | Tool install, config, research | Complex kernel logic |
| **Ollama cloud** | Free | API parameter tuning, MoE/MLA variants | Custom HIP (0/4 correct) |
| **Ollama local** | Free | Syntax validation, fast checks | Everything complex |

## Workflow

```
Opus: Plan → delegate tasks to cheaper models
  ↓
Sonnet agents (background): Write custom kernels (MFMA, Triton)
Haiku agents (background): Install tools (GEAK), configure infra
Ollama scripts (nohup): Iterate API-level submissions
  ↓
popcorn-cli: test → benchmark → leaderboard (validation)
  ↓
Opus: Review results, pivot strategy, capture learnings
```

## Launch Pattern

```bash
# Ollama iteration (3 kernels in parallel)
cd luma_speedrun
nohup bash ollama_kernel_iterate.sh gemm deepseek-v3.2:cloud > /tmp/ollama_gemm.log 2>&1 &
nohup bash ollama_kernel_iterate.sh moe kimi-k2.5:cloud > /tmp/ollama_moe.log 2>&1 &
nohup bash ollama_kernel_iterate.sh mla qwen3.5:397b-cloud > /tmp/ollama_mla.log 2>&1 &
```

```python
# Claude Code agents (in session)
Agent(model=sonnet, name="gemm-specialist", subagent_type="kernel-writer", run_in_background=True, prompt="...")
Agent(model=haiku, name="geak-installer", run_in_background=True, prompt="...")
```

## Anti-Patterns (Verified)

1. **Ollama for MFMA kernels**: 0/4 correct (register types, output mapping wrong)
2. **Opus writing kernel code**: Wastes $15/M budget on work Sonnet handles
3. **Sequential submission**: Always run test/benchmark in background
4. **LDS for small-M shapes**: sync overhead > coalescing benefit for M<32

## GEAK Integration

GEAK (AMD-AGI) installed at `/home/mike-anderson/dev/geak/`:
```bash
source /home/mike-anderson/dev/geak/.geak_env/bin/activate
geak --repo <kernel_dir> --kernel-url <file> -m "ollama/deepseek-v3.2:cloud" --yolo --exit-immediately
```

## Verification

- All kernel submissions via `popcorn-cli submit --no-tui --mode test` first
- Only benchmark after test passes
- Only leaderboard after benchmark shows improvement
- Track results in `ollama_results.log` per kernel directory
