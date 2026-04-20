# GPU MODE Speedrun: Orchestrated Multi-Agent Kernel Optimization Plan

## Executive Summary

This plan refines and extends the existing R-Zero-inspired single-agent approach into a proper **orchestrated team of specialist agents** using three foundational papers:

- **K-Search** (arXiv:2602.19128v2) — Co-Evolving Intrinsic World Model for kernel generation
- **R-Zero** — Self-Evolving Reasoning via Challenger-Solver co-evolution
- **autoresearch** (karpathy) — Autonomous agent research paradigm via `program.md`

The goal: achieve **top-10 qualifying** in Phase 1 and **grand prize** ($650K) in Phase 2 Track 2 (Kimi K2.5 FP4).

---

## Part I: Competition Architecture

### Phase 1 — Qualifier Kernels (Top 10 Advances)

| Kernel | Points | Current | Target | Leader |
|--------|--------|---------|--------|--------|
| MXFP4 MoE | 1,500 | ~155µs | <150µs | ~140µs |
| MLA Decode | 1,250 | ~72µs | <20µs | ~4.3µs |
| MXFP4 GEMM | 1,000 | ~20.8µs | <12µs | ~9µs |

**Scoring:** `Max_Points * [1 - (rank / 20)]` per kernel, summed. Must be top-20 AND beat baseline.

### Phase 2 — E2E Inference (Track 2: Kimi K2.5 1T FP4)

**Targets (8× MI355X):**
- Conc=4: latency ≤6s, throughput ≥1350 tok/s/GPU
- Conc=32: latency ≤14s, throughput ≥4500 tok/s/GPU
- Conc=128: latency ≤24.5s, throughput ≥5300 tok/s/GPU
- Accuracy: GSM8K ≥ 0.9325
- Framework: AMD ATOM or vLLM

---

## Part II: Multi-Agent Team Architecture

### Agent Team Composition

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR AGENT                          │
│         (Strategic planner, routes work to specialists)          │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│  GEMM SPECIALIST │  │  MLA SPECIALIST │  │   MoE SPECIALIST    │
│  (1–2 agents)   │  │   (2–3 agents)  │  │    (1–2 agents)     │
└─────────────────┘  └─────────────────┘  └─────────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                   ┌─────────────────────┐
                   │   WORLD MODEL AGENT │
                   │  (Co-evolving store) │
                   └─────────────────────┘
```

### Agent Roles

#### 1. Orchestrator Agent
- **Skill:** `autonomous-ai-agents` for spawning sub-agents
- **Responsibility:**
  - Analyze incoming MI355X benchmark results
  - Assign tasks to specialist agents based on priority
  - Maintain global state across all kernels
  - Decide when to mutate, when to pivot strategy
  - Route to vault for persistent learnings

#### 2. GEMM Specialist (1–2 agents)
- **Focus:** MXFP4 GEMM kernel optimization
- **Knowledge domains:**
  - Tile size selection (32×128, 192×128, 256×128)
  - Split-K strategy (log2_ks = 0–4)
  - Shape-adaptive kernel dispatch
- **Target:** <12µs from current ~20.8µs

#### 3. MLA Specialist (2–3 agents) — CRITICAL PATH
- **Focus:** MLA decode kernel (biggest gap to leader: 72µs vs 4.3µs)
- **Knowledge domains:**
  - `num_kv_splits` optimization formula
  - FP8 KV cache utilization
  - Wave-level parallelism (wave shfl_xor for softmax)
  - intra_batch vs inter-batch modes
- **Target:** <20µs from current ~72µs (14× gap — highest leverage)

#### 4. MoE Specialist (1–2 agents)
- **Focus:** MXFP4 MoE kernel optimization
- **Knowledge domains:**
  - Adaptive KSPLIT based on tokens/expert
  - OPUS sorting efficiency
  - Expert scheduling
- **Target:** <150µs from current ~155µs

#### 5. World Model Agent
- **Skill:** `note-taking` with Obsidian for structured knowledge
- **Responsibility:**
  - Maintain co-evolving world model of what works
  - Track hypothesis → execution → outcome mappings
  - Assign confidence scores V ∈ [0,1] to strategies
  - Feed updated beliefs back to all specialists
  - Persist patterns across sessions

---

## Part III: K-Search Co-Evolution Framework

### The Core Loop (per K-Search paper)

```
┌──────────────────────────────────────────────────────────────┐
│ 1. PLAN                  2. GENERATE           3. EXECUTE   │
│    High-level strategy →  Code generation  →   MI355X run   │
│         ↑                              │                    │
│         │                              ▼                    │
│    ┌────┴────┐              ┌────────────────────┐           │
│    │ World   │◄────────────│  Execution Results │           │
│    │ Model   │              └────────────────────┘           │
│    │(co-eval)│                         │                    │
│    └────▲────┘                         ▼                    │
│         │               ┌────────────────────────┐          │
│         └───────────────│  World Model Update    │          │
│                         │  V(s) scores adjusted  │          │
│                         └────────────────────────┘          │
└──────────────────────────────────────────────────────────────┘
```

### Key K-Search Principles Applied

1. **Decouple Planning from Implementation**
   - High-level algorithmic intent specified first
   - Code instantiation handled by specialist agents
   - Example: "Use 192×128 tile with KSPLIT=0 for M>32" (plan) vs. actual kernel call (impl)

2. **Co-Evolving World Model**
   - Each execution updates belief state
   - Strategies with high V scores get more exploration budget
   - Low-V strategies pruned after stagnation (K=7 attempts)

3. **Non-Monotonic Path Tolerance**
   - Temporary implementation defects don't invalidate good strategies
   - Partial improvements count as signal
   - Staged rollout: test on subset before full benchmark

4. **Stagnation Detection**
   - If K=7 consecutive attempts yield <1.05× improvement → pivot
   - Track per-kernel per-strategy stagnation separately

---

## Part IV: R-Zero Experiential Recursive Learning

### Challenger-Solver Co-Evolution

```
┌────────────────────────────────────────────────────────────────┐
│                      CHALLENGER AGENT                          │
│  Role: Probe the solver's weaknesses, generate harder variants │
│  Input: Current solver performance, world model beliefs        │
│  Output: New challenger variants at edge of solver capability  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼ intent + variant
┌────────────────────────────────────────────────────────────────┐
│                       SOLVER AGENT                             │
│  Role: Continuously improve by solving challenger's tasks      │
│  Input: Challenger variants, execution feedback                 │
│  Output: Solved kernels, performance metrics                   │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    MAJORITY VOTE LABELING                      │
│  Role: Generate pseudo-labels from multiple solver attempts    │
│  Output: Training signal for next iteration                    │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    RELATIVE POLICY OPTIMIZATION               │
│  Role: Update challenger/solver based on outcome              │
│  Output: Refined world model, new hypothesis priorities       │
└────────────────────────────────────────────────────────────────┘
```

### R-Zero Principles Applied

1. **Curriculum Generation**
   - Challengers generate problems right at the edge of solver capability
   - Not too easy (no learning signal), not too hard (no progress)
   - Adaptive: as solver improves, challengers push boundaries

2. **Majority Vote Pseudo-Labels**
   - For borderline kernels (correct but slow), run multiple trials
   - Majority outcome = ground truth for training signal
   - Reduces noise from transient errors

3. **Recursive Meta-Learning**
   - Each iteration refines both challenger strategy AND solver approach
   - Meta-loop: learn HOW to learn better kernels
   - "Learning to learn kernels"

---

## Part V: autoresearch Paradigm (Karpathy)

### The program.md Framework

The `program.md` file is the **research constitution** that defines how the autonomous agent swarm operates. Key structure:

```markdown
# program.md

## Role Definition
You are an autonomous kernel optimization researcher...

## Core Loop
1. Read current benchmark results
2. Analyze what changed since last run
3. Generate hypothesis for improvement
4. Implement change locally
5. Validate syntax/logic locally
6. Submit to MI355X runner
7. Log results to vault
8. Repeat

## Success Criteria
- GEMM < 12µs
- MLA < 20µs
- MoE < 150µs

## Vault Integration
Document all learnings in ~/vaults/cohezion-vault/luma-amd-speedrun/
```

### Extension: Multi-Agent program.md Hierarchy

Each specialist agent gets its own `program_<kernel>.md`:

- `program_gemm.md` — GEMM-specific research constitution
- `program_mla.md` — MLA-specific (most detailed, biggest gap)
- `program_moe.md` — MoE-specific

The Orchestrator has `program_orchestrator.md` that coordinates.

---

## Part VI: Concrete Implementation Plan

### Week 1–2: Foundation (March 19 – April 2)

#### Setup Multi-Agent Orchestration
```bash
# Spawn orchestrator + 3 specialist agents
delegate_task goal="Act as GEMM Specialist for AMD GPU MODE competition" ...
delegate_task goal="Act as MLA Specialist for AMD GPU MODE competition" ...
delegate_task goal="Act as MoE Specialist for AMD GPU MODE competition" ...
```

#### Implement World Model Store
- Use Obsidian vault at `~/vaults/cohezion-vault/luma-amd-speedrun/`
- Create pattern/failure/decisions structure
- Implement V-score (confidence) tracking per hypothesis

#### Bootstrap Baseline Challengers
- Run 33 GEMM + 33 MoE + 34 MLA = 100 challengers
- Establish true baseline metrics on MI355X
- Populate world model with initial V-scores

### Week 3–4: K-Search Exploration (April 3 – April 20)

#### Per-Kernel Search Strategy

**GEMM (small gap, easier wins):**
- Grid: tile sizes × log2_ks × shape thresholds
- Focus: shape-adaptive dispatch (M≤threshold → small tile)
- Stagnation: after 7 fails on a tile, move to next

**MLA (largest gap, highest priority):**
- Grid: num_kv_splits × (fast_mode, intra_batch)
- Priority hypotheses:
  - `num_splits=1` with `intra_batch=True` (simpler path)
  - `num_splits=8` with `intra_batch=False` (parallelism)
- Analyze: wave-level softmax, FP8 KV cache hits
- Investigate: why leader achieves 4.3µs (4.3× vs our 72µs)

**MoE (moderate gap):**
- Grid: KSPLIT × OPUS flag × threshold bounds
- Focus: est_m < threshold → KSPLIT=4-8
- Analyze: expert load balancing

### Week 5–6: R-Zero Recursive Refinement (April 21 – May 5)

#### Co-Evolution Loop
1. **Challenger generation:** Push boundaries of current best
2. **Solver execution:** Multiple trials with majority voting
3. **Policy update:** Adjust V-scores based on outcomes
4. **Meta-learning:** Refine hypothesis generation itself

#### Mutation Strategy
- Every 20 iterations: take top-20% performers
- Apply mutation operators:
  - GEMM: ±1 log2_ks, ±1 threshold level
  - MLA: ×2 or ÷2 num_splits
  - MoE: ±1 KSPLIT, shift threshold bounds

### Week 7: Phase 2 Preparation (May 6 – May 12)

#### E2E Integration
- Port winning Phase 1 kernels into vLLM or ATOM framework
- Ensure mergeability (AMD-agnostic code)
- Test Concurrency 4, 32, 128 configurations
- Verify accuracy: GSM8K ≥ 0.9325

#### Final Tuning
- Per-concurrency optimization
- Throughput vs latency tradeoff analysis
- Stability testing across multiple runs

---

## Part VII: Key Technical Insights

### MLA — The Critical Path

**Current State:** 72µs vs Leader 4.3µs = 16.7× gap

**Hypothesis for Breakthrough:**

1. **KV Cache Bypass**
   - Leader may be bypassing full KV cache computation
   - Investigate: persistent kernel reuse

2. **num_kv_splits Formula Refinement**
   ```
   Optimal splits ≈ min((bs * i) / compute_units, 
                        avg_kv / (avg_kv + 84.1 * i))
   ```
   - Current: naive splits (try 1, 2, 4...)
   - Better: compute optimal splits analytically per shape

3. **Wave-Level Parallelism**
   - MLA softmax is parallel over KV heads
   - Use `__shfl_xor` for wave-level reduction
   - Current code may be sequentializing this

4. **FP8 KV Cache**
   - 2× bandwidth savings vs BF16
   - Ensure KV data is in FP8 format end-to-end

### GEMM — Steady Improvement

**Current State:** 20.8µs vs Leader ~9µs = 2.3× gap

**Priority Actions:**
1. Tile size: 192×128 for M>16 seems best
2. Split-K: log2_ks=0 for large M, log2_ks=3-4 for small M
3. Shape-adaptive dispatch: critical for variable batch sizes

### MoE — Marginal Gains

**Current State:** 155µs vs Leader ~140µs = 1.1× gap

**Priority Actions:**
1. OPUS sorting: always enable
2. KSPLIT adaptive: higher for sparse, lower for dense
3. **CRITICAL:** Never use `doweight_stage1=True` (broken)

---

## Part VIII: Agent Communication Protocol

### Message Types

```python
from enum import Enum

class MessageType(Enum):
    TASK_REQUEST = "task_request"        # Orchestrator → Specialist
    TASK_RESULT = "task_result"           # Specialist → Orchestrator
    WORLD_MODEL_UPDATE = "world_model_update"  # Specialist → WorldModel
    HYPOTHESIS_REQUEST = "hypothesis_request"  # Specialist → WorldModel
    HYPOTHESIS_RESPONSE = "hypothesis_response"  # WorldModel → Specialist
    CHALLENGE_GENERATED = "challenge_generated"  # Challenger → Solver
    SOLUTION_RESULT = "solution_result"    # Solver → Challenger
```

### Orchestrator Priority Queue

```python
# Priority: MLA > MoE > GEMM (by gap-to-leader × impact)
PRIORITY_ORDER = ["mla", "moe", "gemm"]

# Per-kernel: stagnation tracking
STAGNATION_THRESHOLD = 7  # K-Search: try K=7 times before pivot
MIN_IMPROVEMENT = 1.05    # 5% minimum improvement to count as progress
```

---

## Part IX: Vault Structure

```
~/vaults/cohezion-vault/luma-amd-speedrun/
├── patterns/
│   ├── gemm/
│   │   ├── tile-size-selection.md
│   │   ├── split-k-strategy.md
│   │   └── shape-adaptive-dispatch.md
│   ├── mla/
│   │   ├── kv-split-formula.md
│   │   ├── fp8-kv-cache.md
│   │   └── wave-parallelism.md
│   └── moe/
│       ├── ksplit-adaptive.md
│       └── opus-sorting.md
├── failures/
│   ├── mla/
│   │   └── high-split-failures.md
│   └── gemm/
│       └── large-tile-failures.md
├── decisions/
│   ├── 20260319-gemm-tile-strategy.md
│   ├── 20260320-mla-split-strategy.md
│   └── ...
└── world-model/
    ├── hypotheses.json
    └── v-scores.json
```

---

## Part X: Immediate Action Items (Next 24 Hours)

### For Mike-Anderson (Human)
1. [ ] Register for competition by March 30
2. [ ] Join AMD Developer Program
3. [ ] Set up popcorn-cli on MI355X access
4. [ ] Create Obsidian vault structure

### For Agent Team
1. [ ] Spawn 3 specialist sub-agents
2. [ ] Load `program_gemm.md`, `program_mla.md`, `program_moe.md`
3. [ ] Run initial 100-challenger sweep
4. [ ] Populate world model with baseline V-scores
5. [ ] Analyze MLA gap: why 16.7× vs leader?

### Success Metrics (This Week)
- GEMM: Establish stable <15µs configuration
- MLA: Identify top 3 split configurations
- MoE: Achieve <155µs (match current leader baseline)

---

## References

- K-Search: https://arxiv.org/html/2602.19128v2
- R-Zero: https://chengsong-huang.github.io/R-Zero.github.io/
- autoresearch: https://github.com/karpathy/autoresearch
- Competition: https://luma.com/cqq4mojz?tk=5NV3rC
- Reference Kernels: https://github.com/gpu-mode/reference-kernels/tree/main/problems/amd_202602

---

*Plan synthesized: March 19, 2026*
*Inspired by K-Search, R-Zero, and karpathy/autoresearch*
*For GPU MODE Hackathon 2026 — $1.1M total prizes*
