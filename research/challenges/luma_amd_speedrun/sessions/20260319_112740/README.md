# Session 20260319 — Summary Report

**Date:** March 19, 2026  
**Agent:** Cloud Reasoning Agent (Hermes)  
**Purpose:** Refine Luma AMD Speedrun plan with K-Search × R-Zero × AutoResearch

---

## Executive Summary

Examined the existing V1 orchestration plan and identified critical gaps. Created V2 plan with:

1. **K-Search principles** — V-scores, world model co-evolution, K=7 stagnation
2. **R-Zero methodology** — Minimal agent loop, recursive skill acquisition
3. **AutoResearch patterns** — Simple autonomous search, iteration speed focus

**Key Finding:** The 16.7× MLA gap (72µs vs 4.3µs leader) cannot be closed by incremental tuning. Requires breakthrough thinking.

---

## What Was Created

### Core Files

| File | Purpose |
|------|---------|
| `ORCHESTRATION_PLAN_V2.md` | Comprehensive V2 plan with multi-agent architecture |
| `spawn_agents.py` | R-Zero × K-Search agent spawning implementation |
| `vault/decisions/20260319_decisions.md` | Strategic decisions log |
| `challengers/mla/mla_aiter_v2.py` | MLA max-tuned variant with hidden op discovery |

### Key Innovations in V2

#### 1. Parallel Breakthrough Tracks (V-Score Prioritized)

```
MLA Strategy:
├── Track 1 (V=0.95): Probe AITER for hidden ASM kernel paths
├── Track 2 (V=0.80): Exhaustive AITER env var grid search  
└── Track 3 (V=0.30): Custom HIP MFMA kernel with persistence

MoE Strategy (maintenance):
└── Continue with adaptive KSPLIT (V=0.90, gap 1.03×)

GEMM Strategy (maintenance):
└── Inline quantization to eliminate 10-13µs overhead (V=0.70)
```

#### 2. Experiential Recursive Learning

```python
# After each breakthrough:
Skill = {
    observation: "Context before",
    action: "What changed", 
    reward: "Performance delta"
}
# Extracted to vault/skills/ for future agents
```

#### 3. World Model Co-Evolution

```python
V_SCORE_RULES = {
    "breakthrough": {"v_delta": +0.2},  # speedup > 2×
    "improvement": {"v_delta": +0.1},   # speedup > 1.1×
    "regression": {"v_delta": -0.05},    # speedup < 0.95×
    "crash": {"v_delta": -0.1},
    "stagnation_threshold": 7,  # K=7 fails → mark stale
}
```

---

## The 16.7× MLA Gap — Root Cause Analysis

### Why 72µs vs 4.3µs?

The leader's performance implies something fundamentally different:

```
72µs ÷ 4.3µs = 16.7× faster

Possible explanations:
1. Direct ASM kernel (no Python overhead)
2. Persistent KV cache in L2 (no global memory loads)
3. Wave-level SIMD with __shfl_xor
4. MXFP4 KV throughout (4-bit vs FP8's 8-bit)
5. Hardware prefetching + double buffering
```

### The Fundamental Problem with Current Approach

`mla_aiter_max_tuned.py` uses AITER's `mla_decode_fwd` which:
- Has ~20-30µs Python call + metadata setup overhead
- Uses generic kernel paths, not competition-optimized
- Doesn't exploit CDNA 3 MFMA at full utilization

`mla_mfma_pure.py` correctly identifies MFMA but:
- Has compilation complexity (HIP source in Python string)
- Falls back to AITER on any error
- Doesn't handle persistent mode correctly

---

## Strategic Decisions (from vault/decisions/20260319_decisions.md)

| Decision | Rationale |
|----------|-----------|
| MLA is breakthrough priority | 16.7× gap = highest impact |
| Multi-agent specialization | R-Zero shows simple loop achieves SOTA |
| World model co-evolution | K-Search's core insight |
| Skill extraction on breakthrough | Recursive learning compounds |
| MoE/GEMM maintenance mode | Already close to leader |

---

## How to Use This Plan

### Step 1: Generate Variants

```bash
# Spawn MLA agent (this generates code via Ollama)
python3 spawn_agents.py --kernel mla --all

# Spawn GEMM agents
python3 spawn_agents.py --kernel gemm --all

# Spawn MoE agents
python3 spawn_agents.py --kernel moe --all
```

### Step 2: Submit to MI355X

```bash
# Test correctness
popcorn submit --no-tui --mode test --gpu MI355X \
  --leaderboard amd-mixed-mla \
  $KERNELS/mixed-mla/submission.py

# Benchmark
popcorn submit --no-tui --mode benchmark --gpu MI355X \
  --leaderboard amd-mixed-mla \
  $KERNELS/mixed-mla/submission.py

# Submit to leaderboard if improvement
popcorn submit --no-tui --mode leaderboard --gpu MI355X \
  --leaderboard amd-mixed-mla \
  $KERNELS/mixed-mla/submission.py
```

### Step 3: Update World Model

```bash
# After each benchmark
python3 run_orchestration.py update-world-model \
  --kernel mla --result-file results.json
```

### Step 4: Extract Skills

Skills are automatically extracted on breakthrough (speedup > 2×) and stored in `vault/skills/`.

---

## Ollama Integration

Local Ollama is available with these models:

| Model | Role | Status |
|-------|------|--------|
| `qwen3.5:cloud` | Code generation | Working |
| `qwen2.5-coder:14b` | Local code gen | Available |
| `deepseek-r1:7b` | Strategic reasoning | Available |
| `phi3:mini` | Fast updates | Available |

**Note:** qwen3.5:cloud timed out on first call but succeeded on retry. Use with patience.

---

## Exit Conditions

Stop autonomous research when:

1. **MLA < 10µs** — Breakthrough achieved (7× improvement)
2. **All three kernels in top-10** — Qualifier goal met
3. **100 iterations** — Resource limit
4. **Human explicit stop** — Mike intervention

---

## Key Insights from Reference Papers

### From K-Search (arXiv:2602.19128v2)
- Planning-implementation decoupling is critical
- World model co-evolution enables faster convergence
- Non-monotonic paths require patience (K=7 stagnation)
- V-scores enable rational strategy selection

### From R-Zero
- Minimal agent loop: Generate → Execute → Evaluate → Repeat
- Recursive skill acquisition from successful experiments
- Multi-agent specialization accelerates exploration
- Experience replay enables learning from failures

### From karpathy/autoresearch
- Simple autonomous loop can achieve SOTA results
- Don't over-engineer — let the search discover patterns
- Human review only at milestones
- Code quality matters less than iteration speed

---

## Files Created/Modified

```
sessions/20260319_112740/
├── ORCHESTRATION_PLAN_V2.md          # V2 comprehensive plan
├── spawn_agents.py                    # Multi-agent spawning
├── run_orchestration.py              # V1 orchestration (stubs)
├── vault/
│   ├── decisions/
│   │   └── 20260319_decisions.md    # Strategic decisions
│   ├── patterns/
│   ├── skills/
│   └── failures/
├── world-model/
│   ├── hypotheses.json                # V-scores + hypotheses
│   └── experiments/
└── challengers/
    ├── mla/
    │   ├── mla_mfma_pure.py         # V1 MFMA approach
    │   ├── mla_aiter_max_tuned.py   # V1 AITER max-tuned
    │   └── mla_aiter_v2.py          # V2 with hidden op discovery
    ├── gemm/
    │   └── gemm_variants.py          # V1 variants
    └── moe/
        └── moe_variants.py          # V1 variants
```

---

## Next Steps

1. **Review V2 plan** — Understand the architecture
2. **Spawn agents** — Generate initial variants via Ollama
3. **Submit to popcorn-cli** — Test on MI355X
4. **Update world model** — Track V-scores
5. **Extract skills** — On breakthrough
6. **Iterate** — Until MLA < 10µs or top-10

---

**The 16.7× gap is waiting to be closed.** Good luck, agent. 🚀
