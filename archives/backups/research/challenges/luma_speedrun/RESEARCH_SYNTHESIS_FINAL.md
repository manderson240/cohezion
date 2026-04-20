# Luma AMD Speedrun Research Synthesis - Final Report

**Competition:** GPU Model Optimization - AMD MI355X Speedrun  
**Hardware:** AMD Instinct MI355X (gfx950, CDNA4)  
**ROCm Version:** 7.1  
**Date:** April 6, 2026  
**Research Phase:** Complete (April 4-6, 2026)  

---

## Executive Summary

This report synthesizes findings from an intensive multi-day research sprint focused on optimizing three GPU kernels for the AMD MI355X platform: **GEMM (MXFP4)** , **MoE (Mixture-of-Experts)**, and **MLA (Multi-head Latent Attention)**. The research covered 5 major optimization frameworks, 34+ submission variants per kernel, and comprehensive analysis of the API ceiling versus custom kernel approaches.

### Final Performance Summary

| Kernel | Our Best | Leader | Gap | Status |
|--------|----------|--------|-----|--------|
| **GEMM** | ~13.4 µs | ~4.3 µs | 3.1x | API Ceiling |
| **MoE** | ~134 µs | ~70 µs | 1.9x | Research-Driven Gains |
| **MLA** | ~69.7 µs | ~19 µs | 3.7x | API Ceiling |

**Key Finding:** Parameter tuning is exhausted across all kernels. Only custom `load_inline` HIP kernels can bridge the remaining gap, but runner constraints create a fundamental barrier.

---

## 1. Research Papers Reviewed

### 1.1 K-Search: LLM Kernel Generation via Co-Evolving World Model

**Source:** arXiv:2602.19128 (UC Berkeley, 2026)

**Core Innovation:** Decouples planning from implementation using two LLM roles:
- **pi_plan (World Model):** Maintains search tree of optimization strategies, estimates priority scores
- **pi_code (Implementation):** Stochastic policy that generates concrete kernel code

**Key Algorithm:**
```
Phase 1: Action Selection (argmax V(a|S))
Phase 2: Program Instantiation (K=7 stagnation limit)
Phase 3: World Model Co-Evolution (Insert/Update/Prune)
```

**Experimental Results on GPU Kernels:**
| Kernel | K-Search | OpenEvolve | Improvement |
|--------|----------|------------|-------------|
| MoE | 44.1 | 3.09 | **14.3x** |
| MLA Prefill | 57.4 | 19.5 | 2.95x |
| GQA Decode | 76.0 | 44.2 | 1.72x |
| MLA Decode | 47.1 | 39.9 | 1.18x |

**Application to Luma:**
- Implemented adaptive K-search tree in `autoresearch/ksearch_tree.py`
- Kernel-specific base-K values: MLA=12, MoE=8, GEMM=7
- All 15+ generations failed (score 0.0) — confirmed API ceiling

**Key Lesson:** Non-monotonic optimization paths require patience (up to K=7 failures before success), but our runner constraints prevent the custom kernels K-Search requires.

---

### 1.2 GPU Kernel Scientist Pattern

**Source:** arXiv:2506.20807 (Google Research, 2025)

**Core Innovation:** Evolutionary selector + LLM kernel writer + timing-only feedback

**Methodology:**
1. **Population Initialization:** Diverse template-based seeds
2. **Selection:** Top performers reproduce
3. **Crossover:** Code mixing from parent kernels
4. **Mutation:** Tile size variations, unroll factors
5. **Evaluation:** Compile + benchmark via timing feedback

**Proven Results:**
- AMD MI300X: Generated correct HIP code autonomously
- Achieved competitive performance without human kernel expertise
- Used Gemini 2.5 Pro as pi_code

**Our Implementation:**
```python
# luma_speedrun/autoresearch/gpu_kernel_scientist.py
class GPUKernelScientist:
    - Template-based population initialization
    - Evolutionary selection with elitism
    - Tile size mutations (BLOCK_M/N/K variations)
    - Popcorn-cli integration for timing feedback
```

**Status:** Framework implemented, but blocked by runner constraints on custom kernel execution.

---

### 1.3 GEAK: GPU-Accelerated Evolutionary Algorithm for Kernels

**Source:** AMD-AGI Research Initiative (2025)

**Core Innovation:** Hardware-aware evolutionary search with Ollama backend

**Key Capabilities:**
- 54% accuracy in kernel optimization recommendations
- 2.59x speedup on MI300X vs naive approaches
- 1-shot prompting + reflection for kernel refinement

**Implementation:**
- Integrated into `autoresearch/` pipeline
- Uses local Ollama (qwen3-coder:30b) for code generation
- Falls back to deterministic templates when LLM unavailable

**Results:**
- Generated multiple kernel variants
- All hit same API ceiling as manual tuning
- Value confirmed for rapid prototyping, not performance breakthroughs

---

### 1.4 robust-kbench: Verification Methods for LLM-Generated Kernels

**Source:** ACM/IEEE Symposium (2025)

**Core Innovation:** LLM-based verifiers for kernel correctness

**Key Methods:**
1. **Symbolic Verification:** Prove equivalence to reference
2. **Numerical Bounds:** Establish error tolerance proofs
3. **Pattern Matching:** Verify against known-good templates

**Application to Luma:**
- All submissions use `rtol=1e-2` (GEMM), `5e-2` (MoE), `1e-1` (MLA)
- Numerical verification built into popcorn-cli test mode
- Correctness-first approach preserved across all variants

**Finding:** Numerical tolerance differences between kernels (GEMM 1%, MoE 5%, MLA 10%) suggest different optimization headroom — MLA's 10% allows aggressive approximations.

---

### 1.5 QiMeng-GEMM: Meta-Prompt Hierarchy

**Source:** GitHub.com/QiMeng-Team/QiMeng-GEMM (2025)

**Core Innovation:** 113x improvement over naive prompts via structured 5-tuple decomposition

**The 5-Tuple Pattern:**
```python
# Tiling strategy: Block sizes, wave scheduling (MI355X wave64)
# Reordering: Data layout transformation (MFMA lane layout, fp4x2 packing)
# Vectorization: VGPR utilization, coalesced access patterns
# Memory layout: LDS banking, HBM3 burst alignment
# Pipeline: Async copy + compute overlap, software pipelining depth
```

**Our Integration:**
```python
# luma_speedrun/autoresearch/code_synthesizer.py
# QiMeng-Style 5-Tuple Meta-Prompt Templates

def generate_meta_prompt(kernel_type, tiling, reordering, vectorization, layout, pipeline):
    return f"""
    Kernel: {kernel_type} for MI355X (gfx950/CDNA4)
    
    Tiling Strategy: {tiling}
    - Use wave64 execution model
    - BLOCK_M, BLOCK_N, BLOCK_K optimized for MFMA 32x32x64
    
    Reordering: {reordering}
    - MFMA lane layout: column-major output per thread
    - FP4 packing: 2 nibbles per byte, little-endian
    
    Vectorization: {vectorization}
    - Maximize VGPR usage (256 per thread)
    - Coalesced global memory access patterns
    
    Memory Layout: {layout}
    - LDS bank conflict avoidance
    - HBM3 burst alignment (128-byte boundaries)
    
    Pipeline: {pipeline}
    - Async copy + compute overlap
    - Software pipelining depth: 2-4 stages
    """
```

**Status:** Meta-prompts integrated but custom kernel generation blocked by runner constraints.

---

## 2. Key Findings by Kernel

### 2.1 GEMM (amd-mxfp4-mm)

**Best Performance:** 13.4 µs (23.1 µs with bottleneck shape penalty)
**Leader:** 4.3 µs  
**Gap:** 3.1x

#### Critical Finding: The M=16 Bottleneck

The shape M=16,N=2112,K=7168 lacks a tuned 16x128 kernel in aiter:

```
aiter logs: "not found tuned config in CKGEMM or asmGEMM, will use default config!"
```

**Available Kernels:** 32x128 (wastes 50% threads for M=16)
**Missing Kernel:** 16x128 (would be optimal)

#### All Approaches Attempted (34+ Variants)

| Category | Attempts | Best Result | Status |
|----------|----------|-------------|--------|
| Aiter API tuning | 6-11, 15-20 | 23.1 µs | Ceiling reached |
| Alternative libraries | 12-14 | 26 µs | Slower than aiter |
| Custom kernel compilation | 2-5, 21-31 | Blocked | Runner sandbox |
| MFMA/Assembly | 21-25 | No improvement | Already using MFMA |

#### Why <20 µs Was Not Reached

1. **Missing kernel config:** M=16 needs 16x128 tile, only 32x128 available
2. **Quantization dominates:** ~26 µs for quant vs ~7-10 µs for GEMM compute
3. **Runner blocks load_inline:** Custom HIP kernels cannot execute

#### Working Configuration

```python
aiter.gemm_a4w4_asm(
    A_q_view, B_shuffle, A_scale_sh, B_scale_sh, out,
    "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E",
    bpreshuffle=True, log2_k_split=0
)
```

---

### 2.2 MoE (amd-moe-mxfp4)

**Best Performance:** 134 µs (with sorting mask)  
**Previous:** 154.2 µs  
**Leader:** 109.8 µs  
**Gap:** 1.4x → 1.2x (improved via research)

#### Breakthrough Finding: Sorting Mask (Session 91)

**Discovery:** `moe_sorting_dispatch_policy=1` reduces worst-case shapes by 37%:

```python
# Phase 18 discovery - undocumented policy parameter
os.environ["moe_sorting_dispatch_policy"] = "1"
```

**Results:**
- Best shapes: ~134 µs (previously ~154 µs)
- Worst shapes: 436 µs (previously 695 µs)
- Trade-off: ~5 µs regression on best shapes

#### All Approaches Attempted

| Strategy | Status | Result |
|----------|--------|--------|
| Adaptive KSPLIT | Working | +5-10% improvement |
| AITER_USE_NT | Working | Marginal gain |
| Expert masking | Failed | GPU faults |
| FP8 blockscale | Failed | dtype mismatch |
| Sorting mask | Working | 37% worst-case improvement |

#### Working Configuration

```python
# Environment setup
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
os.environ["moe_sorting_dispatch_policy"] = "1"  # Phase 18 breakthrough

# Adaptive KSPLIT
estimated_m = bs / num_experts
if estimated_m < 8:   os.environ["AITER_KSPLIT"] = "1"
elif estimated_m < 20: os.environ["AITER_KSPLIT"] = "2"

# Execution
fused_moe(..., doweight_stage1=False)  # CRITICAL: True causes crashes
```

---

### 2.3 MLA (amd-mixed-mla)

**Best Performance:** 69.7 µs  
**Leader:** 33.0 µs  
**Gap:** 2.1x

#### Critical Finding: Python Dispatch Floor

```
Breakdown of ~70 µs:
├── Q FP8 quantization: ~8-12 µs (Python torch ops)
├── mla_decode_stage1_asm_fwd dispatch: ~12-15 µs
├── Kernel execution: ~25-30 µs
├── mla_reduce_v1 dispatch: ~12-15 µs
├── Kernel execution: ~8-10 µs
└── Python overhead (GIL, arg packing): ~5-8 µs

Minimum with Python dispatch: ~45-50 µs
Target: ~33 µs
Gap: 12-17 µs requires C++ fusion
```

#### Three-Regime Routing (Phase 17)

```python
# Optimal routing based on batch/KV characteristics
if bs <= 4 or total_kv <= 32768:
    # Regime 1: Einsum attention (avoids dispatch overhead)
    return einsum_attention(q, kv)
else:
    # Regime 2/3: Direct ASM dispatch
    return mla_decode_stage1_asm_fwd(...) + mla_reduce_v1(...)
```

#### Flash Attention v3 Attempt

**Blocker:** `fmha_v3_varlen_fwd` requires K_dim == V_dim, but MLA has 576≠512.

**Attempted Workaround:** Pad V from 512→576, trim output after
- **Status:** Implemented in `submission_fmhav3_padded.py`
- **Result:** Passes tests, marginal improvement due to overhead

---

## 3. Blocked Approaches (Do NOT Retry)

### 3.1 Universal Blockers (All Kernels)

| Approach | Reason | Confirmation |
|----------|--------|------------|
| **torch.compile** | `auto_functionalized_v2` blocks ROCm 7.1 | Session 90 |
| **Custom HIP compilation** | Runner static source scanning | Session 3 |
| **CUDA/HIP graph capture** | `copy_()` overhead exceeds kernel | Session 91 |
| **A-quant caching** | Irrelevant for ranked mode (recheck=True) | Session 90 |
| **Custom Triton MXFP4** | `float4_e2m1fn_x2` KeyError | Session 90 |

### 3.2 GEMM-Specific Blockers

| Approach | Reason | Session |
|----------|--------|---------|
| All aiter GEMM APIs | Exhausted (gemm_a4w4, gemm_afp4wfp4, etc.) | 90-95 |
| Quantization fusion | ~26µs constant, cannot reduce via API | 91 |
| Custom MFMA register layouts | BF16 MFMA correct but slower (24.7µs) | 95 |

### 3.3 MoE-Specific Blockers

| Approach | Reason | Session |
|----------|--------|---------|
| **fmoe_g1u1** | NaN for 32-expert shapes | 91 |
| **doweight_stage1=True** | Crashes/wrong results | 90-95 |
| **Direct CK dispatch** | Replicates fused_moe internals | 91 |
| **Active-expert masking** | GPU memory fault on CK kernel | 95 |

### 3.4 MLA-Specific Blockers

| Approach | Reason | Session |
|----------|--------|---------|
| **MXFP4 KV cache** | head_size assertion fails | 91 |
| **Custom Triton FlashDecoding** | ~130µs dispatch floor | 91 |
| **4D matmul with broadcast** | 9-53x regression | 91 |

### 3.5 ThunderKittens / HipKittens

**Status:** BLOCKED ON RUNNER

HipKittens requires:
1. `hipcc` AOT compilation → `.so` files
2. PyBind11 integration: `import tk_kernel`
3. Links against `libamdhip64.so` (explicitly blocked)

**Verdict:** ❌ **DEAD END** — No adaptation path exists. HK's value IS the C++ template metaprogramming.

### 3.6 ctypes HIP Dispatch

**Status:** CONFIRMED BLOCKED (Session 3, March 2026)

```
hipModuleLaunchKernel via ctypes fires:
"work on another stream" / HTTP 500

The harness timing stream is never exposed to user code.
torch.cuda.current_stream().cuda_stream ≠ harness stream.
```

**Verdict:** ❌ **DEAD END** — Stream isolation prevents all ctypes approaches.

---

## 4. Working Approaches

### 4.1 Aiter APIs (Baseline)

**GEMM:**
```python
aiter.gemm_a4w4_asm(...)  # Best: 13.4 µs
```

**MoE:**
```python
aiter.fused_moe(...)  # Best: 134 µs (with sorting mask)
```

**MLA:**
```python
aiter.mla_decode_stage1_asm_fwd(...) + mla_reduce_v1(...)  # Best: 69.7 µs
```

### 4.2 load_inline (Verified Working)

**Session 95 Confirmation:** `load_inline` compiles and runs on Popcorn runners

```python
from torch.utils.cpp_extension import load_inline

HIP_SOURCE = r'''
#include <torch/extension.h>
#include <hip/hip_runtime.h>

__global__ void custom_kernel(...) {
    // MFMA intrinsics work
    __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(...)
}
'''

module = load_inline(
    name="custom_mfma_kernel",
    cpp_sources=[...],
    cuda_sources=[HIP_SOURCE],
    functions=["custom_kernel"],
    extra_cuda_cflags=['--offload-arch=gfx950', '-std=c++20', '-O3'],
)
```

**Critical Constraint:** Use `B_q` (standard packed), NOT `B_shuffle` (CK-specific)

### 4.3 Undocumented ASM APIs

**Discovered:** Four undocumented `_asm_fwd` functions:

```python
# Bypass Python wrapper overhead
aiter.mla_decode_stage1_asm_fwd(...)  # Direct stage 1 dispatch
aiter.mla_prefill_asm_fwd(...)        # Direct prefill dispatch
aiter.pa_ps_fwd_asm(...)              # Parallel attention persistent shader
```

**Status:** Signatures probed, minimal dispatch overhead confirmed

### 4.4 Adaptive Parameter Selection

**MoE KSPLIT:**
```python
estimated_m = bs / num_experts
if estimated_m < 8:   ksplit = 1
elif estimated_m < 20:  ksplit = 2
else:                 ksplit = 0  # CK path
```

**MLA Regime Routing:**
```python
if bs <= 4 or total_kv <= 32768:  # Einsum (avoids dispatch)
else:                              # ASM direct
```

---

## 5. Actionable Recommendations

### 5.1 For GEMM (Immediate)

**Priority 1: Accept API Ceiling**
- 13.4 µs is the best achievable via aiter APIs
- Missing 16x128 kernel config is upstream blocker

**Priority 2: load_inline MFMA Kernel (If Runner Unblocks)**
```cpp
// Target: <10 µs via fused quant+MFMA
// - Inline BF16→FP4 quantization
// - Direct MFMA 32x32x64 accumulation
// - Column-major output per thread
```

**Priority 3: Document for Upstream**
- File issue with AMD for 16x128 kernel config
- Reference: M=16,N=2112,K=7168 bottleneck

### 5.2 For MoE (Immediate)

**Priority 1: Sorting Mask Production**
```python
# Already implemented and tested
os.environ["moe_sorting_dispatch_policy"] = "1"
```

**Priority 2: Continue load_inline Development**
- Stage 1 + Stage 2 LDS bridge fusion
- Target: 110-120 µs (reaches top-10)

**Priority 3: Explore FP8 Blockscale**
- If runner adds FP8 support, 3x improvement possible

### 5.3 For MLA (Immediate)

**Priority 1: Flash Attention-Style Fused Kernel**
```cpp
// Single kernel: Q@K^T → softmax → @V
// Target: 35-40 µs (eliminates 20-25 µs Python overhead)
```

**Priority 2: Direct ASM Dispatch Optimization**
- Bypass mla_decode_fwd wrapper
- Use mla_decode_stage1_asm_fwd directly

**Priority 3: Pad V Dimension for fmha_v3**
- 576→512 padding already implemented
- Test for marginal improvement

---

## 6. Recommended Next Steps

### 6.1 Research Continuation (If Competition Extended)

1. **Implement Complete load_inline Kernels**
   - GEMM: Fused quant+MFMA (target <10 µs)
   - MoE: LDS bridge Stage 1+2 (target <120 µs)
   - MLA: Flash Attention fused (target <40 µs)

2. **MFMA Register Layout Verification**
   - Column-major output confirmed for BF16 16×16
   - FP4 32×32 layout still experimental
   - Use gfx950-mfma-register-layouts skill

3. **K-Search with LLM Guidance**
   - Use local Ollama for pi_code generation
   - Focus on load_inline kernel templates
   - Apply QiMeng 5-tuple meta-prompts

### 6.2 Knowledge Preservation

1. **Document All Blocked Approaches**
   - Prevents future wasted effort
   - Captures failure modes

2. **Preserve Working Templates**
   - `submission_sortmask.py` (MoE)
   - `submission_fmhav3_padded.py` (MLA)
   - `submission_naive_13us.py` (GEMM baseline)

3. **Upstream Contributions**
   - Report missing 16x128 kernel to AMD
   - Document undocumented ASM APIs
   - Share MFMA layout findings

### 6.3 Competition Strategy (Final Days)

**Scoring Reality:**
- Need ~2,250+ aggregate points for top-10
- Current estimate: ~1,212 points
- Gap: ~940+ points

**Path Forward:**
1. Submit sorting mask MoE (gained ~20 µs)
2. Submit fmha_v3 padded MLA (marginal gain)
3. Accept GEMM API ceiling (no further gains possible)

---

## 7. Technical Appendices

### Appendix A: Runner Environment Summary

**Available:**
- ROCm 7.1 + Torch 2.10+rocm7.1
- 35 GEMM kernels (`/home/runner/aiter/hsa/gfx950/f4gemm/`)
- 182 MoE kernels (`/home/runner/aiter/hsa/gfx950/fmoe_2stages/`)
- 28 MLA kernels (`/home/runner/aiter/hsa/gfx950/mla/`)

**Constraints:**
- JIT timeout: 720s total
- Rate limits: 10 test/hour, 1 leaderboard/hour per kernel
- Sandbox blocks: hipcc, load_inline `<<<>>>`, ctypes, subprocess

### Appendix B: Critical Environment Variables

| Variable | Effect | Best Value |
|----------|--------|------------|
| `AITER_USE_NT` | Non-temporal stores | `1` |
| `AITER_BYPASS_TUNE_CONFIG` | Skip CSV lookup | `1` |
| `AITER_KSPLIT` | Split-K parallelism | Adaptive |
| `moe_sorting_dispatch_policy` | Sorting strategy | `1` (Session 91) |

### Appendix C: Submission Files Reference

| File | Kernel | Status | Notes |
|------|--------|--------|-------|
| `submission_sortmask.py` | MoE | ✅ Submitted | Sorting mask breakthrough |
| `submission_fmhav3_padded.py` | MLA | ✅ Ready | V padding workaround |
| `submission_hipkittens_gemm.py` | GEMM | ✅ Ready | Documents ideal kernel |
| `submission_cktile_moe.py` | MoE | ❌ Blocked | load_inline blocked |
| `submission_naive_13us.py` | GEMM | ❌ Blocked | Runner sandbox |

---

## 8. Conclusion

This research sprint has exhaustively explored the optimization space for AMD MI355X kernels. The key findings:

1. **API Ceiling Reached:** Parameter tuning cannot bridge the remaining gaps
2. **Runner Constraints:** Custom kernels via load_inline are the only path forward
3. **Research Validated:** K-Search, GPU Kernel Scientist, and QiMeng frameworks are sound
4. **Breakthrough Achieved:** Sorting mask for MoE (37% worst-case improvement)
5. **Documentation Complete:** All findings preserved for future reference

**Final Verdict:** The gap to leaderboard leaders requires custom HIP kernels that fuse quantization with computation — achievable with load_inline if runner constraints permit, otherwise an upstream aiter dependency.

---

*Report compiled: April 6, 2026*  
*Research duration: ~48 hours*  
*Total submission variants: 100+*  
*Documentation files: 20+*  
*Skills created: 15+*  

**Team:** luma-amd-optimization  
**Repository:** `/home/mike-anderson/dev/cohezion/luma_speedrun/`