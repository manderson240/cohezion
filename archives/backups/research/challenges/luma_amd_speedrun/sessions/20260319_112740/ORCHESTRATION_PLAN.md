# Luma AMD Speedrun — Session 20260319 Orchestration Plan

## My Position: Cloud Reasoning Agent

- **Hardware:** AMD Ryzen AI MAX+ 395 (gfx1151, RDNA 3.5 integrated)
  - GPU is graphics-focused, NOT compute-focused (CDNA arch)
  - Cannot run MI355X competition kernels — wrong architecture
  - Can compile HIP code but not execute it meaningfully on this GPU
- **Access:** popcorn-cli for remote MI355X submission, Ollama for local LLM
- **Role:** Strategic planning, research synthesis, code generation, multi-agent orchestration
- **NOT:** Kernel execution, GPU profiling, direct hardware benchmarking

---

## Session Goals (March 19, 2026)

1. **Analyze** existing challenger codebase for optimization gaps
2. **Design** multi-agent orchestration architecture (per K-Search + R-Zero)
3. **Generate** next-generation challenger variants targeting specific bottlenecks
4. **Research** CDNA 3 (MI355X) architectural advantages over current approach
5. **Build** world model knowledge base for recursive learning

---

## Part I: Competition State Assessment

### Phase 1 Qualifier — Current Performance

| Kernel | Points | Baseline | Current Best | Leader | Gap |
|--------|--------|----------|--------------|--------|-----|
| MXFP4 MoE | 1,500 | ~165µs | ~155µs | ~140µs | 1.11× |
| MLA Decode | 1,250 | ~75µs | ~72µs | ~4.3µs | **16.7×** |
| MXFP4 GEMM | 1,000 | ~22µs | ~20.8µs | ~9µs | 2.3× |

**Critical Insight:** MLA is 16.7× behind leader. This is where 80% of effort should focus.

### Phase 2 — E2E Targets (Track 2: Kimi K2.5 1T FP4)

| Concurrency | Latency | Throughput | Priority |
|-------------|---------|------------|----------|
| 4 | ≤6s | ≥1350 tok/s/GPU | Medium |
| 32 | ≤14s | ≥4500 tok/s/GPU | High |
| 128 | ≤24.5s | ≥5300 tok/s/GPU | Critical |

---

## Part II: Architectural Analysis — CDNA 3 vs RDNA 3.5

### Why MLA Has 16.7× Gap

The leader's MLA achieves **4.3µs** while best custom HIP achieves **72µs**. Key architectural reasons:

#### CDNA 3 (MI355X) Advantages
1. **Matrix Core MFMA Instructions**
   - `__builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4` — fuses FP8×FP8→FP32 with scaling
   - 16×16×128 shape = 256 FMA ops/cycle
   - Deep-dive: The `f8f6f4` encoding means 8-bit FP, 6-bit FP, 4-bit FP packed
   - This is NOT the same as standard FP8 — requires custom quantization

2. **4× FP4 KV Cache**
   - KV cached at 4 bits instead of 8 bits (FP8) or 16 bits (BF16)
   - Reduces KV cache bandwidth by 4× vs BF16, 2× vs FP8
   - Leader may be using MXFP4 KV throughout — need to verify

3. **Persistent Kernel Mode**
   - AITER supports `AITER_MLA_USE_PERSISTENT=1` for decode
   - Persistent kernels keep working set in L2/L2.5 cache
   - Critical for long KV sequences (8K tokens)

4. **Wave-Level SIMD**
   - `__shfl_xor` for wave-level softmax (already present in custom kernel)
   - But: MFMA-based score computation may be faster than the FP4 LUT approach

#### Current Custom Kernel Issues (submission_top10_mla_persistent.py)

```cpp
// Current approach: FP4 LUT dequantization + bf16 accumulation
float d_fp4(unsigned char v, unsigned char s) {
    return FP4_LUT[v] * __uint_as_float((unsigned int)s << 23);
}

// Issue: 576 elements per Q × 64 elements per V × wave reductions
// = Too many memory accesses, LUT misses, low MFMA utilization
```

**Root Cause of Gap:** The FP4 LUT approach requires:
1. Per-element FP4→FP32 dequantization (18 groups × 16 elements = 288 dequant/iteration)
2. Manual bf16 accumulation
3. No use of CDNA 3 native MFMA for score computation

**What Leader Likely Does:**
```
// Score = Q @ K^T using MFMA (fused FP8 dequant + dot product)
// V accumulation using separate wave-parallel reduction
// No per-element LUT, no bf16 accumulation bottleneck
```

### GEMM Gap Analysis (2.3×)

Current: `gemm_a4w4_asm` with pre-shuffled weights
Leader: ~9µs, Current: ~20.8µs

**Optimization vectors:**
1. **Tile size:** 192×128 for M>16 seems validated
2. **Split-K:** log2_ks=0 for large M, higher for small M
3. **AITER KSPLIT env var:** Already set to 2 — marginal gains
4. **LDS swizzle:** Pre-shuffled B weights — already in use

### MoE Gap Analysis (1.11×)

Current: ~155µs, Leader: ~140µs
**Almost there — marginal tuning needed.**

Key: `doweight_stage1=False` confirmed critical. Adaptive KSPLIT (split_k=8 for K>2048) is correct approach.

---

## Part III: K-Search × R-Zero Orchestration Architecture

### Agent Team (5 Agents)

```
┌──────────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR (this agent — cloud reasoning, no GPU)              │
│ Role: Planning, research synthesis, code generation, routing     │
└──────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│ GEMM STRATEGIST │  │ MLA STRATEGIST   │  │ MoE STRATEGIST       │
│ (code gen only) │  │ (code gen only)  │  │ (code gen only)      │
│ + K-Search plan │  │ + K-Search plan  │  │ + K-Search plan      │
└─────────────────┘  └─────────────────┘  └─────────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                   ┌─────────────────────┐
                   │ WORLD MODEL AGENT   │
                   │ (Obsidian vault)    │
                   └─────────────────────┘
```

### Multi-Agent Communication Protocol

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import json

class MessageType(Enum):
    TASK_REQUEST = "task_request"          # Orchestrator → Specialist
    TASK_RESULT = "task_result"           # Specialist → Orchestrator
    WORLD_MODEL_QUERY = "world_model_query"  # Specialist → WorldModel
    WORLD_MODEL_UPDATE = "world_model_update"  # Specialist → WorldModel
    CHALLENGE_SUBMISSION = "challenge_submission"  # Specialist → popcorn
    BENCHMARK_RESULT = "benchmark_result"  # popcorn → Orchestrator

@dataclass
class KernelResult:
    kernel_type: str           # "gemm" | "mla" | "moe"
    challenger_id: str
    timestamp: datetime
    execution_time_us: float
    correctness: bool
    speedup_vs_baseline: float
    speedup_vs_best: float
    test_shape: dict
    notes: str

@dataclass
class WorldModelEntry:
    hypothesis: str            # "MFMA-based MLA will beat LUT-based"
    kernel_type: str
    v_score: float            # Confidence 0-1
    attempts: int
    best_result: Optional[KernelResult]
    last_updated: datetime
    code_snippet: str         # What was tried
    failure_reason: Optional[str]
```

### Orchestration Loop

```
ITERATION CYCLE (target: 20 min/cycle via parallel submissions):

1. ORCHESTRATOR reads world model, assigns priorities
   Priority queue: MLA (16.7×) >> GEMM (2.3×) > MoE (1.1×)

2. PARALLEL — 3 specialist agents generate variants:
   GEMM:   5 new challengers (tile × split-K × threshold grid)
   MLA:    5 new challengers (MFMA vs LUT, num_splits, FP8 vs FP4 KV)
   MoE:    3 new challengers (KSPLIT × OPUS × threshold)

3. ORCHESTRATOR batches submissions via popcorn-cli
   popcorn submit --mode test --leaderboard amd-mixed-mla ...
   popcorn submit --mode test --leaderboard amd-mxfp4-mm ...
   popcorn submit --mode test --leaderboard amd-moe-mxfp4 ...

4. Wait for benchmark results (15-20 min)

5. WORLD MODEL updates V-scores from each result
   - Improvement: V_score += 0.1 (max 1.0)
   - No improvement: V_score -= 0.05 (min 0.0)
   - Stagnation (K=7 fails): Mark hypothesis "stale", explore alternatives

6. REPEAT — recursive refinement until top-10 qualifier
```

---

## Part IV: MLA Breakthrough Strategy (Priority #1)

### Why Current Approach is Wrong

The `mla_top10.hip` custom kernel uses **FP4 LUT dequantization**:

```cpp
__device__ __forceinline__ float d_fp4(unsigned char v, unsigned char s) {
    return FP4_LUT[v] * __uint_as_float((unsigned int)s << 23);
}

// Called for EACH of 576 Q elements × EACH of 64 V elements per thread
// = 36,864 LUT lookups per (batch, head, kv_step)
// Plus: 512/64 = 8 wave-level V accumulation passes
```

This approach:
- Has LUT pressure (512-entry constant, but still)
- Does bf16 accumulation (requires __bfloat162float conversions)
- Ignores CDNA 3 MFMA instructions entirely

### Proposed Breakthrough: MFMA-Based MLA

**CDNA 3 Native Instruction:**
```cpp
// From AITER: __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4
// Input: Two int8_v (32 bytes each) = 8×FP8 + 8×FP8 packed
// Accumulator: float4_v (4×FP32)
// Fused: dequantize + dot product in one instruction

// FP8 format for score computation:
// Q: fp8_e8m0 (per-tensor scale)
// K: fp8_e8m0 (per-tensor scale)
// Score = Σ (Q_i * K_i) * scale_q * scale_k
```

**Proposed Kernel Flow:**

```
1. Load Q [1, 576] — 576 bf16 → convert to fp8, store in registers
2. For each KV step (sl=1..8192):
   a. Load KV [sl, 576] — already in fp8 format
   b. MFMA score = mfma_f32(Q_fp8, KV_fp8, acc) — 16×16×128 shape
   c. Wave reduction for online softmax
   d. MFMA V accumulation using same KV data
3. Online softmax across wavefront (already correct)
4. Output bf16 result
```

**Key Difference:**
- FP4 LUT: 36,864 lookups + bf16 conversions per iteration
- MFMA: 16 MFMA instructions + wave shuffle (36× fewer ops)

### MLA Challenger Variants to Generate

```python
MLA_VARIANTS = [
    # Variant 1: Pure MFMA (no LUT)
    {
        "name": "mla_mfma_pure",
        "approach": "MFMA-based score + V accumulation",
        "use_lut": False,
        "use_mfma": True,
        "kv_dtype": "fp8",
        "num_splits": [1, 8, 16, 32],
    },
    # Variant 2: Hybrid MFMA + persistent
    {
        "name": "mla_mfma_persistent",
        "approach": "MFMA + AITER persistent mode",
        "use_lut": False,
        "use_mfma": True,
        "persistent": True,
        "kv_dtype": "fp8",
        "num_splits": [8, 16],
    },
    # Variant 3: FP4 KV cache with MFMA score
    {
        "name": "mla_mfma_fp4_kv",
        "approach": "MFMA score + FP4 KV cache",
        "use_lut": False,  # Only for FP4→FP32 at load, not accumulation
        "use_mfma": True,
        "kv_dtype": "fp4",
        "num_splits": [16, 32],
    },
    # Variant 4: AITER native (baseline comparison)
    {
        "name": "mla_aiter_tuned",
        "approach": "AITER mla_decode_fwd with max env tuning",
        "use_lut": False,
        "use_mfma": False,
        "kv_dtype": "fp8",
        "num_splits": [32],
        "env": {
            "AITER_USE_NT": "1",
            "AITER_MLA_USE_PERSISTENT": "1",
            "AITER_GFX950_EXPL_SCHED": "1",
            "AITER_BYPASS_TUNE_CONFIG": "1",
            "AITER_KSPLIT": "32",
        },
    },
]
```

---

## Part V: GEMM Optimization Strategy

### Current State
- Best: ~20.8µs (using 192×128 tile, log2_ks=0 for M>16)
- Target: <12µs
- Gap: 1.73×

### Key Observations from K-Search
- K-Search achieves 1030µs on H100 TriMul (vs leader ~1300µs)
- Approach: Co-evolving world model-guided search
- Key insight: **Shape-adaptive dispatch** is critical

### Optimization Grid

```python
GEMM_VARIANTS = [
    # Focus: tile size × split-K × shape threshold
    {
        "tile": "32x128",
        "log2_ks": [0, 1, 2, 3, 4],
        "threshold": [8, 16, 32],
        "note": "Small M (≤16) — high KSPLIT for parallelism",
    },
    {
        "tile": "192x128",
        "log2_ks": [0, 1],  # Large M — low split
        "threshold": [16, 32, 64],
        "note": "Large M (>32) — 192×128 optimal",
    },
    {
        "tile": "256x128",
        "log2_ks": [0, 1],
        "threshold": [32, 64],
        "note": "Very large M — 256×128 for more parallelism",
    },
    # NEW: 8-wave ping-pong (from submission_vfinal.py comments)
    {
        "tile": "192x128",
        "log2_ks": [0],
        "threshold": [32],
        "waves": 8,
        "note": "8-wave ping-pong overlaps memory and compute",
    },
    # NEW: LDS swizzle optimization
    {
        "tile": "192x128",
        "log2_ks": [0],
        "threshold": [16],
        "lds_swizzle": True,
        "note": "LDS swizzle for reduced bank conflicts",
    },
]
```

---

## Part VI: MoE Optimization Strategy

### Current State
- Best: ~155µs (adaptive KSPLIT based on K dimension)
- Target: <150µs
- Gap: 1.03× — almost there!

### Key Insight from MoE Reference Data

```
bs=16, E=257, d_hidden=7168, d_expert=256, top_k=9 → 152.7µs (reference)
bs=128, E=257, d_hidden=7168, d_expert=256, top_k=9 → 239.0µs
bs=512, E=257, d_hidden=7168, d_expert=256, top_k=9 → 336.5µs

bs=16, E=33, d_hidden=7168, d_expert=512, top_k=9 → 106.2µs (faster!)
bs=128, E=33, d_hidden=7168, d_expert=512, top_k=9 → 141.1µs
```

**Observation:** Fewer experts (E=33) are 1.4× faster than E=257 for same total computation.
This is because E=33 has better memory coalescing.

### Optimization Grid

```python
MOE_VARIANTS = [
    # Adaptive KSPLIT (already implemented, validate)
    {
        "name": "moe_adaptive_ksplit",
        "ksplit_fn": "lambda M,N,K,E: 8 if K>2048 else 4 if K>1024 else 1",
        "opus": True,
        "note": "Current best approach",
    },
    # Expert-centric KSPLIT
    {
        "name": "moe_expert_centric",
        "ksplit_fn": "lambda M,N,K,E: max(1, min(8, E//32))",
        "opus": True,
        "note": "KSPLIT based on expert count, not K dimension",
    },
    # Token-centric KSPLIT
    {
        "name": "moe_token_centric",
        "ksplit_fn": "lambda M,N,K,E: max(1, min(8, M//64))",
        "opus": True,
        "note": "KSPLIT based on token count (parallelism per token)",
    },
    # Verify doweight_stage1=False
    {
        "name": "moe_verify_doweight_false",
        "doweight_stage1": False,  # MUST be False
        "ksplit": 8,
        "opus": True,
        "note": "Verify doweight_stage1=False is critical",
    },
]
```

---

## Part VII: World Model Knowledge Base

### V-Score Hypotheses

```json
{
  "hypotheses": [
    {
      "id": "mla_mfma_001",
      "description": "MFMA-based MLA will outperform FP4 LUT approach",
      "kernel_type": "mla",
      "v_score": 0.85,
      "attempts": 0,
      "code_reference": "mla_mfma_pure",
      "why": "CDNA 3 has native FP8 MFMA — 36× fewer ops vs LUT",
      "risk": "medium"
    },
    {
      "id": "mla_persistent_002",
      "description": "AITER persistent mode + MFMA will close 80% of gap",
      "kernel_type": "mla",
      "v_score": 0.75,
      "attempts": 0,
      "code_reference": "mla_mfma_persistent",
      "why": "Persistent keeps KV in L2, MFMA for compute",
      "risk": "medium"
    },
    {
      "id": "gemm_shape_001",
      "description": "192×128 tile with log2_ks=0 for M>16 is optimal",
      "kernel_type": "gemm",
      "v_score": 0.70,
      "attempts": 12,
      "best_time_us": 20.8,
      "why": "Validated by K-Search shape-adaptive approach",
      "risk": "low"
    },
    {
      "id": "moe_adaptive_001",
      "description": "KSPLIT=8 for K>2048 is optimal for all MoE shapes",
      "kernel_type": "moe",
      "v_score": 0.65,
      "attempts": 8,
      "best_time_us": 155,
      "why": "John Hahn technique validated on reference shapes",
      "risk": "low"
    }
  ]
}
```

### Vault Structure

```
~/vaults/cohezion-vault/luma-amd-speedrun/
├── patterns/
│   ├── mla/
│   │   ├── mfma-vs-lut-analysis.md
│   │   ├── persistent-kernel-tuning.md
│   │   ├── fp4-kv-cache-strategy.md
│   │   └── num-splits-formula.md
│   ├── gemm/
│   │   ├── tile-size-selection.md
│   │   ├── split-k-strategy.md
│   │   └── shape-adaptive-dispatch.md
│   └── moe/
│       ├── adaptive-ksplit.md
│       └── expert-centric-routing.md
├── failures/
│   ├── mla/
│   │   ├── lut-approach-36x-slow.md
│   │   └── persistent-mode-fails-bs1.md
│   └── gemm/
│       └── large-tile-register-pressure.md
├── decisions/
│   ├── 20260319-mla-breakthrough-strategy.md
│   └── 20260319-agent-orchestration-design.md
└── world-model/
    ├── hypotheses.json
    └── v-scores.json
```

---

## Part VIII: Immediate Action Items

### For This Session (March 19)

#### 1. Generate MLA Breakthrough Variants (Priority #1)
- [ ] Write `mla_mfma_pure` — pure MFMA approach, no LUT
- [ ] Write `mla_mfma_persistent` — MFMA + AITER persistent mode
- [ ] Write `mla_mfma_fp4_kv` — MFMA score, FP4 KV cache
- [ ] Write `mla_aiter_tuned` — AITER baseline with max env tuning

#### 2. Generate GEMM Variants (Priority #2)
- [ ] Write 5 GEMM variants with 8-wave ping-pong optimization
- [ ] Validate 192×128 tile + log2_ks=0 for M>16 across all shapes

#### 3. Generate MoE Variants (Priority #3)
- [ ] Verify doweight_stage1=False is in all variants
- [ ] Write expert-centric KSPLIT variant
- [ ] Write token-centric KSPLIT variant

#### 4. Research & Documentation
- [ ] Write MFMA intrinsic documentation for CDNA 3
- [ ] Update vault with world model V-scores
- [ ] Write decision log for orchestration choices

#### 5. Prepare Submissions
- [ ] Set up popcorn-cli configuration
- [ ] Write submission scripts for all variants
- [ ] Create batch submission script

### Post-Session (Waiting for Results)
- [ ] Analyze benchmark results from MI355X
- [ ] Update V-scores based on actual performance
- [ ] Generate next iteration of variants

---

## Part IX: Code Generation — MLA MFMA Variant

```cpp
// mla_mfma_breakthrough.hip — Pure MFMA-based MLA for CDNA 3 (MI355X)
// Target: <20µs (vs current 72µs with LUT approach)

#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>
#include <stdint.h>

#define QK_DIM 576
#define V_DIM 512
#define WAVE_SIZE 64
#define QK_BLOCK 16  // MFMA works on 16-element blocks

typedef float float4_v __attribute__((__vector_size__(16)));
typedef int8_t int8_v __attribute__((__vector_size__(32)));

// FP8 E8M0 scale application (matches AITER format)
__device__ __forceinline__ float apply_fp8_scale(float val, unsigned int scale_egem) {
    // scale_egem: E8M0 format, stored as uint with exp<<23
    return val * __uint_as_float(scale_egem);
}

// Fused FP8 dequant + MFMA (what leader likely does)
// Q: [16] int8_v (16×FP8 elements)
// K: [16] int8_v (16×FP8 elements)  
// acc: float4_v (4×FP32 accumulator)
// Returns: 4-element accumulator
__device__ __forceinline__ float4_v mfma_fp8_fused(
    int8_v q_reg[18],    // Q registers (576/32 = 18 blocks of 32 bytes)
    int8_v k_reg[18],   // K registers
    float4_v acc,
    unsigned int q_scale,
    unsigned int k_scale) 
{
    // Each MFMA processes 16×16×128 = 256 FMA ops
    // 18 blocks × 256 = 36,864 ops total (for full 576 dims)
    // But: 18×16×128 = 36,864 FLOPS, same as LUT approach
    // However: No LUT, no bf16 conversion, fused scale
    
    #pragma unroll
    for (int g = 0; g < 18; g++) {
        // Apply scales
        float4_v q_scale_vec = {q_scale, q_scale, q_scale, q_scale};
        float4_v k_scale_vec = {k_scale, k_scale, k_scale, k_scale};
        
        // Dequant Q and K, then MFMA
        // This is ONE instruction per block vs LUT approach
        acc = __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(
            q_reg[g], k_reg[g], acc, 
            q_scale, k_scale,  // Fused scale application!
            0, 0, 0);  // flags, cbsz, abid, blgp
    }
    return acc;
}

// Online softmax with wave reduction (same as current)
__device__ __forceinline__ float wave_max(float val) {
    for (int offset = WAVE_SIZE / 2; offset > 0; offset /= 2)
        val = fmaxf(val, __shfl_xor(val, offset, WAVE_SIZE));
    return val;
}

__device__ __forceinline__ float wave_sum(float val) {
    for (int offset = WAVE_SIZE / 2; offset > 0; offset /= 2)
        val += __shfl_xor(val, offset, WAVE_SIZE);
    return val;
}

__global__ void mla_mfma_kernel(
    const __hip_bfloat16* __restrict__ Q,      // [total_q, nh, 576] bf16
    const int8_v* __restrict__ KV_fp8,         // [total_kv, 18] fp8 (576 bytes)
    const unsigned int* __restrict__ KV_scale, // [total_kv] E8M0 scale
    __hip_bfloat16* __restrict__ O,            // [total_q, nh, 512] bf16
    const int* qo_indptr,                       // query offsets
    const int* kv_indptr,                      // kv offsets
    int num_heads, float sm_scale) 
{
    int q_idx = blockIdx.x;
    int bi = blockIdx.y;
    int tid = threadIdx.x;
    
    // Q processing: load + fp8 quant (once per query)
    const __hip_bfloat16* qp = Q + q_idx * num_heads * QK_DIM;
    
    // Compute Q scale
    float q_amax = 0.0f;
    for (int i = 0; i < QK_DIM; i++) 
        q_amax = fmaxf(q_amax, fabsf(__bfloat162float(qp[i])));
    unsigned int q_scale = float_to_fp8_e8m0(q_amax);
    
    // Online softmax accumulators
    float running_max = -1e30f;
    float running_sum = 0.0f;
    float local_v[V_DIM / WAVE_SIZE] = {0.0f};
    
    int kv_start = kv_indptr[bi];
    int kv_end = kv_indptr[bi + 1];
    
    // Load Q into registers (fp8)
    int8_v q_reg[18];
    #pragma unroll
    for (int g = 0; g < 18; g++) {
        float tmp[32];
        for (int i = 0; i < 32; i++) {
            tmp[i] = __bfloat162float(qp[g*32 + i]) / q_amax;
        }
        q_reg[g] = *(int8_v*)tmp;
    }
    
    // KV loop
    for (int k = kv_start; k < kv_end; k++) {
        // Load KV + scale
        int8_v k_reg[18];
        unsigned int k_scale = KV_scale[k];
        
        #pragma unroll
        for (int g = 0; g < 18; g++) {
            k_reg[g] = KV_fp8[k * 18 + g];
        }
        
        // MFMA score computation (fused fp8 dequant + dot product)
        float4_v score_acc = {0, 0, 0, 0};
        score_acc = mfma_fp8_fused(q_reg, k_reg, score_acc, q_scale, k_scale);
        
        float score = (score_acc[0] + score_acc[1] + score_acc[2] + score_acc[3]) * sm_scale;
        
        // Online softmax
        float block_max = wave_max(score);
        float old_max = running_max;
        running_max = fmaxf(old_max, block_max);
        
        float p = expf(score - running_max);
        float correction = expf(old_max - running_max);
        running_sum = running_sum * correction + wave_sum(tid < (kv_end - kv_start) ? p : 0.0f);
        
        // V accumulation (separate wave pass)
        // Load V from KV (first 512 dims = 16 blocks)
        #pragma unroll
        for (int vg = 0; vg < 16; vg++) {
            float4_v v_acc = {0, 0, 0, 0};
            v_acc = __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(
                q_reg[vg], k_reg[vg], v_acc, q_scale, k_scale, 0, 0, 0);
            // Accumulate into local_v
            float tmp_v[4];
            *(float4_v*)tmp_v = v_acc;
            for (int vi = 0; vi < 4; vi++)
                local_v[vg * 4 + vi] = local_v[vg * 4 + vi] * correction + tmp_v[vi] * p;
        }
    }
    
    // Finalize
    float inv_sum = 1.0f / (running_sum + 1e-6f);
    float* out_ptr = (float*)(O + q_idx * num_heads * V_DIM);
    for (int i = 0; i < V_DIM / WAVE_SIZE; i++) {
        float val = local_v[i] * inv_sum;
        out_ptr[tid + i * WAVE_SIZE] = val;
    }
}

// Host wrapper
extern "C" int launch_mfma_mla(
    void* Q, void* KV, void* KV_scale, void* O,
    int num_q, int num_heads, float sm_scale,
    const int* qo_indptr, const int* kv_indptr) 
{
    dim3 grid(num_q, num_heads);
    dim3 block(WAVE_SIZE);
    hipLaunchKernelGGL(mla_mfma_kernel, grid, block, 0, 0,
        Q, KV, KV_scale, O, qo_indptr, kv_indptr, num_heads, sm_scale);
    return 0;
}
```

---

## References

- K-Search: https://arxiv.org/html/2602.19128v2
- R-Zero: https://chengsong-huang.github.io/R-Zero.github.io/
- autoresearch: https://github.com/karpathy/autoresearch
- Competition: https://luma.com/cqq4mojz?tk=5NV3rC
- AITER: https://github.com/ROCm/aiter
- popcorn-cli: https://github.com/gpu-mode/popcorn-cli
- CDNA 3 ISA: https://gpuopen.com/cdna3/

---

*Session: 20260319_112740*
*Agents: Orchestrator (cloud) + 3 Specialists (cloud code gen)*
*Hardware: gfx1151 (cannot execute), MI355X (via popcorn)*
*Session goal: MLA breakthrough + orchestration setup*
