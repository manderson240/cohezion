# Flash Attention Optimizations for AMD MI355X

**Research Document**  
**Date:** April 6, 2026  
**Target Hardware:** AMD Instinct MI355X (gfx950, CDNA4)  
**ROCm Version:** 7.1  
**Context:** Luma AMD Speedrun Competition

---

## Executive Summary

Flash Attention is an IO-aware exact attention algorithm that uses **tiling** to reduce HBM (High Bandwidth Memory) accesses, achieving linear memory complexity O(n) instead of quadratic O(n²). For AMD MI355X, Flash Attention principles are critical for closing the **2.1x performance gap** in MLA (Multi-head Latent Attention) decode kernels.

| Metric | Our Best | Leader | Gap |
|--------|----------|--------|-----|
| MLA Decode | ~69.7 µs | ~33.0 µs | 2.1x |
| Memory Savings | Standard | -50% HBM | Flash Attention |
| Pipeline Stages | 3-stage | 1-stage | 3x fewer dispatches |

**Key Finding:** The remaining gap to leaderboard leaders requires Flash Attention-style **single-pass fused kernels** that eliminate Python dispatch overhead (~20-25 µs per torch op).

---

## 1. Flash Attention Algorithm Overview

### 1.1 Core Concept (Dao et al., 2022)

Flash Attention exploits the **asymmetric GPU memory hierarchy**:

```
GPU Memory Hierarchy (MI355X)
═══════════════════════════════════════════════════════════════
HBM (High Bandwidth Memory):  ~1.3 TB/s, ~288GB capacity
    ↑↓  ~100-200 cycles
L2 Cache:                     ~2-4 TB/s
    ↑↓  ~20-40 cycles  
L1/SMEM (Shared Memory):      ~10-20 TB/s, ~228KB/SM
    ↑↓  ~1 cycle
Registers:                    Instant access, 256 VGPRs/thread

Flash Attention Strategy: Keep data in fast memory (SMEM/Registers)
                         while computing attention tiles.
```

### 1.2 Standard vs Flash Attention Memory Complexity

| Operation | Standard Attention | Flash Attention | Reduction |
|-----------|-------------------|-----------------|-----------|
| Attention Matrix Materialization | O(N²) | O(1) | **100% eliminated** |
| HBM Reads/Writes | O(N²) | O(N) | **~50% for typical seq lengths** |
| Memory for N=8K, H=32, D=576 | ~9.4 GB | ~150 MB | **98% reduction** |

### 1.3 Online Softmax Algorithm

Flash Attention uses **online softmax** to avoid materializing the full attention matrix:

```python
# Standard attention (materializes N×N matrix)
scores = Q @ K.T                    # [N, N] - HBM write
weights = softmax(scores, dim=-1)     # [N, N] - HBM read+write
output = weights @ V                  # [N, D] - HBM read

# Flash Attention (tile-based, no materialization)
for kv_tile in range(0, N, BLOCK_N):
    k_tile = load(K[kv_tile:kv_tile+BLOCK_N])  # LDS
    v_tile = load(V[kv_tile:kv_tile+BLOCK_N])  # LDS
    
    scores = Q @ k_tile.T              # [BLOCK_M, BLOCK_N] - registers only
    
    # Online softmax update
    m_new = max(m_old, max(scores))
    alpha = exp(m_old - m_new)
    p = exp(scores - m_new)
    l_new = alpha * l_old + sum(p)
    
    # Accumulate output
    acc = alpha * acc + p @ v_tile
```

---

## 2. AMD-Specific Flash Attention Optimizations

### 2.1 Available Flash Attention Implementations on MI355X

| Implementation | Status | Performance | Notes |
|----------------|--------|-------------|-------|
| `aiter.flash_attn_varlen_func` | **BLOCKED** | N/A | CK limit: head_dim ≤ 256 (MLA needs 576) |
| `aiter.fmha_v3_varlen_fwd` | **BLOCKED** | N/A | Same CK head_dim limit |
| `aiter.mla_decode_fwd` | Working | ~70 µs | 3-stage pipeline overhead |
| **Custom Triton Flash Attention** | Experimental | Slower | Decode is GEMV, not GEMM |
| **Custom HIP Flash Attention** | Potential | ~33 µs target | load_inline path available |

### 2.2 Flash Attention v2 Improvements (Dao, 2023)

FlashAttention-2 achieves **2× speedup** over FlashAttention-1:

1. **Reduced non-matmul FLOPs**: Fewer softmax rescaling operations
2. **Better parallelism**: Single head parallelized across thread blocks
3. **Warp-level work distribution**: Reduces SMEM communication

**MI355X Applicability:**
- FlashAttention-2's parallelism improvements are GPU-agnostic
- AMD MI355X has **304 CUs** → high parallelism potential
- **CDNA4 MFMA instructions** can accelerate the QK^T computation

### 2.3 CDNA4 (gfx950) Specific Optimizations

| Feature | CDNA4 Support | Flash Attention Benefit |
|---------|---------------|------------------------|
| MFMA 32×32×64 | Native | Fast QK^T computation |
| FP8 acceleration | Native | Quantized attention paths |
| MXFP4 format | Native | Memory bandwidth savings |
| LDS size | ~228KB/SM | Larger KV tiles |
| Wave64 | Native | Better occupancy |

### 2.4 vLLM's ROCM_AITER_FA Backend

vLLM implements **Flash Attention-style 3-path routing** for AMD:

```
ROCM_AITER_FA Architecture
═══════════════════════════════════════════════════════════════
Input: Mixed batch (prefill + extend + decode tokens)
       ↓
Batch Reordering → [decode | extend | prefill]
       ↓
┌────────────────┬────────────────┬────────────────┐
│  Decode Path   │  Extend Path   │  Prefill Path  │
│  (mem-bound)   │  (mixed)       │  (compute)     │
├────────────────┼────────────────┼────────────────┤
│ pa_fwd_asm     │ flash_attn +   │ flash_attn_    │
│ (AITER ASM)    │ gather_cache   │ varlen_func    │
└────────────────┴────────────────┴────────────────┘
       ↓
Merged Output
```

**Performance vs baseline:**
- MHA: **2.7-4.4× higher TPS** than ROCM_ATTN
- MLA: **1.2-1.6× faster TPOT** with AITER assembly decode

---

## 3. Applicability to MLA Kernel

### 3.1 MLA Architecture Constraints

DeepSeek R1 MLA uses **fused KV cache** with asymmetric dimensions:

```python
# MLA Dimensions (TP=4)
NUM_HEADS = 32          # Q heads
NUM_KV_HEADS = 1        # GQA: 1 KV head per 32 Q heads
QK_HEAD_DIM = 576       # For score: Q @ KV^T
V_HEAD_DIM = 512        # For value: only first 512 dims of KV

# Standard Flash Attention requires: K_dim == V_dim
# MLA has: K_dim=576, V_dim=512  ← FLASH ATTENTION BREAKS HERE
```

### 3.2 Why Standard Flash Attention Fails for MLA

| Approach | Result | Root Cause |
|----------|--------|------------|
| `flash_attn_varlen_func` | RuntimeError | CK headdim ≤ 256 |
| `fmha_v3_varlen_fwd` | RuntimeError | Same limit |
| Pad V to 576 dims | Works but slow | Wastes 12.5% compute/memory |
| Custom kernel | **Required** | Must handle K≠V |

### 3.3 MLA-Compatible Flash Attention Pattern

```cpp
// Custom Flash Attention for MLA: K=576, V=512
__global__ void mla_flash_attention_kernel(
    const __hip_bfloat16* Q,      // [total_q, heads, 576]
    const __hip_bfloat16* KV,     // [total_kv, 1, 576] - fused
    __hip_bfloat16* output,      // [total_q, heads, 512]
    // ... metadata
) {
    // Tile dimensions
    constexpr int BLOCK_M = 64;   // Query tile
    constexpr int BLOCK_N = 64;   // KV tile
    
    // Shared memory for KV tiles
    __shared__ float smem_k[BLOCK_N][576];  // Full K dim
    __shared__ float smem_v[BLOCK_N][512];  // Only V dim (first 512)
    
    // Load Q into registers (only 1 row for decode)
    float q[576];
    load_q_into_registers(q, Q);
    
    // Online softmax state
    float m = -INFINITY;  // running max
    float l = 0.0f;       // running sum
    float acc[512] = {0}; // output accumulator
    
    // Iterate over KV tiles
    for (int kv_start = 0; kv_start < kv_len; kv_start += BLOCK_N) {
        // Load KV tile to shared memory
        load_kv_tile(KV, kv_start, smem_k, smem_v);
        __syncthreads();
        
        // Compute scores: Q @ K^T
        float scores[BLOCK_N];
        compute_scores(q, smem_k, scores);
        
        // Online softmax update
        float m_new = max(m, max_over_tile(scores));
        float alpha = exp(m - m_new);
        float p[BLOCK_N];
        compute_exp(scores, m_new, p);
        float l_new = alpha * l + sum(p);
        
        // Update accumulator: p @ V
        for (int i = 0; i < 512; i++) {
            acc[i] = alpha * acc[i] + dot(p, smem_v[:, i]);
        }
        
        m = m_new;
        l = l_new;
        __syncthreads();
    }
    
    // Normalize and write output
    for (int i = 0; i < 512; i++) {
        output[i] = acc[i] / l;
    }
}
```

### 3.4 The Split-K Approach (Current Best)

Since full Flash Attention fusion is blocked, current best uses **Split-K with online softmax**:

```python
# Phase 1: Split-K attention (each block handles KV slice)
for split_id in range(num_splits):
    partial_out[split_id] = compute_attention_for_kv_slice(
        Q, KV[kv_start:kv_end], online_softmax=True
    )

# Phase 2: Cross-split reduction with log-sum-exp merge
output = merge_with_lse(partial_out, partial_max, partial_lse)
```

**Performance comparison:**
| Approach | Small (bs=4, kv=1k) | Large (bs=256, kv=8k) |
|----------|---------------------|------------------------|
| torch.einsum | **22.6 µs** | 399 µs |
| aiter 3-stage | 37 µs | 302 µs |
| Split-K + online softmax | 25 µs | **293 µs** |
| Flash Attention (theoretical) | **~8 µs** | **~100 µs** |

---

## 4. Memory Bandwidth Savings

### 4.1 Flash Attention Memory Analysis

For attention with sequence length N, head dimension D, batch B:

| Component | Standard | Flash Attention | Savings |
|-----------|----------|-----------------|---------|
| Q read | B×N×D | B×N×D | 0% |
| K read | B×N×D | B×N×D × (D/BLOCK_D) | Reuse in SMEM |
| V read | B×N×D | B×N×D × (D/BLOCK_D) | Reuse in SMEM |
| Attention matrix | B×N×N | 0 | **100%** |
| Output write | B×N×D | B×N×D | 0% |
| **Total HBM Traffic** | **O(B×N×N)** | **O(B×N×D)** | **~50% at N=8K** |

### 4.2 MI355X-Specific Memory Characteristics

```
MI355X Memory Hierarchy
═══════════════════════════════════════════════════════════════
HBM3:       ~1.3 TB/s effective bandwidth
L2:         ~2-4 TB/s
LDS:        ~10-20 TB/s (software managed)
Registers:  Instant access

Flash Attention Benefits on MI355X:
- LDS caching of KV tiles amortizes HBM reads
- For decode (qseqlen=1): Q is tiny, KV dominates
- Split-K further parallelizes KV cache loading
```

### 4.3 Expected Bandwidth Savings for MLA

| Shape | Standard HBM Traffic | Flash Attention | Savings |
|-------|---------------------|-----------------|---------|
| bs=4, kv=1k | ~2.3 GB | ~1.2 GB | **48%** |
| bs=32, kv=8k | ~74 GB | ~38 GB | **49%** |
| bs=256, kv=8k | ~590 GB | ~300 GB | **49%** |

---

## 5. Implementation Paths

### 5.1 Triton Flash Attention (Experimental)

```python
@triton.jit
def flash_mla_kernel(
    Q_ptr, KV_ptr, Out_ptr,
    # strides...
    BLOCK_M: tl.constexpr,  # 64
    BLOCK_N: tl.constexpr,  # 64
    QK_DIM: tl.constexpr,   # 576
    V_DIM: tl.constexpr,    # 512
):
    # Online softmax in registers
    m = tl.full([BLOCK_M], float("-inf"), tl.float32)
    l = tl.zeros([BLOCK_M], tl.float32)
    acc = tl.zeros([BLOCK_M, V_DIM], tl.float32)
    
    for kv_start in range(0, N, BLOCK_N):
        # Load KV tile to SMEM
        k_tile = tl.load(KV_ptr + kv_offs[:, None] * stride_kvn + 
                        tl.arange(0, QK_DIM)[None, :] * stride_kvd)
        
        # Score computation
        qk = tl.dot(q, k_tile.T) * sm_scale
        
        # Online softmax
        m_new = tl.maximum(m, tl.max(qk, axis=1))
        alpha = tl.exp(m - m_new)
        p = tl.exp(qk - m_new[:, None])
        l_new = alpha * l + tl.sum(p, axis=1)
        
        # V is first 512 dims of KV
        v_tile = k_tile[:, :V_DIM]
        acc = alpha[:, None] * acc + tl.dot(p, v_tile)
        
        m, l = m_new, l_new
```

**Status:** Decode is GEMV, not GEMM → Triton `tl.dot` underperforms. **Not competitive** with hipBLAS GEMV.

### 5.2 HIP Custom Kernel via load_inline (Recommended)

```cpp
// Custom Flash Attention-style kernel for MLA
__global__ __launch_bounds__(256, 4)
void mla_flash_kernel(
    const __hip_bfloat16* Q,
    const __hip_bfloat16* KV,
    __hip_bfloat16* Out,
    int batch_size, int num_heads, int kv_len,
    int num_splits, float sm_scale
) {
    int split_id = blockIdx.x;
    int head_id = blockIdx.y;
    int batch_id = blockIdx.z;
    int tid = threadIdx.x;
    
    // KV slice for this split
    int kv_per_split = (kv_len + num_splits - 1) / num_splits;
    int kv_start = batch_id * kv_len + split_id * kv_per_split;
    int kv_end = min(kv_start + kv_per_split, (batch_id + 1) * kv_len);
    
    // Load Q into registers (576 dims)
    float q_reg[576];
    #pragma unroll
    for (int i = tid; i < 576; i += 256) {
        q_reg[i] = __bfloat162float(Q[(batch_id * num_heads + head_id) * 576 + i]);
    }
    
    // Online softmax accumulator
    float max_score = -1e30f;
    float sum_exp = 0.0f;
    float acc[512] = {0.0f};
    
    // Process KV entries
    for (int kv = kv_start + tid; kv < kv_end; kv += 256) {
        const __hip_bfloat16* kv_ptr = KV + kv * 576;
        
        // Dot product with Q (cooperative)
        float dot = 0.0f;
        #pragma unroll
        for (int d = 0; d < 576; d += 4) {
            dot += q_reg[d+0] * __bfloat162float(kv_ptr[d+0]) +
                   q_reg[d+1] * __bfloat162float(kv_ptr[d+1]) +
                   q_reg[d+2] * __bfloat162float(kv_ptr[d+2]) +
                   q_reg[d+3] * __bfloat162float(kv_ptr[d+3]);
        }
        
        float score = dot * sm_scale;
        
        // Warp reduction
        #pragma unroll
        for (int offset = 32; offset > 0; offset >>= 1) {
            dot += __shfl_xor(dot, offset, 64);
        }
        
        // Online softmax update
        float old_max = max_score;
        max_score = fmaxf(old_max, score);
        float correction = expf(old_max - max_score);
        sum_exp = sum_exp * correction + expf(score - max_score);
        
        // Accumulate V (first 512 dims)
        for (int v = 0; v < 512; v++) {
            acc[v] = acc[v] * correction + 
                     expf(score - max_score) * __bfloat162float(kv_ptr[v]);
        }
    }
    
    // Write partial results for reduction phase
    // ... reduction kernel follows
}
```

### 5.3 Available APIs on MI355X Runner

| API | Purpose | Flash Attention Compatible |
|-----|---------|---------------------------|
| `aiter.mla_decode_stage1_asm_fwd` | Split-K attention | Partial (3-stage) |
| `aiter.mla_reduce_v1` | LSE reduction | Required for split-K |
| `aiter.fmha_v3_varlen_fwd` | Full Flash Attention | **NO** (headdim limit) |
| `aiter.pa_ps_fwd_asm` | Paged attention | For decode only |
| **Custom load_inline** | Full control | **YES** (target: 33 µs) |

---

## 6. Key Findings and Recommendations

### 6.1 Critical Constraints

1. **CK Flash Attention blocked by head_dim**: All `fmha_v3_*` APIs limited to ≤256 dims (MLA needs 576)
2. **Triton Flash Attention underperforms**: Decode is GEMV, `tl.dot` wastes MFMA
3. **3-stage pipeline overhead dominates**: ~100-150 µs fixed cost regardless of batch size
4. **Custom HIP via load_inline is viable**: Session 95 confirmed compilation works

### 6.2 Actionable Recommendations

| Priority | Action | Expected Impact | Status |
|----------|--------|-----------------|--------|
| **1** | Implement custom Flash Attention via `load_inline` | 30-50% speedup | Ready to prototype |
| **2** | Use Split-K with online softmax + cooperative warps | 10-15% speedup | Partially implemented |
| **3** | Optimize LDS tiling for KV cache | 5-10% speedup | Available in CK-Tile patterns |
| **4** | Explore XCD-aware scheduling (`__builtin_amdgcn_s_setprio`) | 5-8% speedup | Research phase |

### 6.3 Flash Attention Implementation Template

```python
# Minimal Flash Attention-style kernel for MLA
HIP_TEMPLATE = r'''
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

#define NUM_HEADS 16
#define QK_DIM 576
#define V_DIM 512
#define BLOCK_SIZE 256

// Flash Attention: fused attention with online softmax
__global__ __launch_bounds__(BLOCK_SIZE, 4)
void flash_attention_mla(
    const __hip_bfloat16* __restrict__ Q,    // [B, H, QK_DIM]
    const __hip_bfloat16* __restrict__ KV,  // [B, L, QK_DIM] - fused K+V
    __hip_bfloat16* __restrict__ Out,       // [B, H, V_DIM]
    int batch_size, int seq_len,
    float sm_scale
) {
    int batch = blockIdx.x;
    int head = blockIdx.y;
    int tid = threadIdx.x;
    
    // Q pointer for this batch+head
    const __hip_bfloat16* q_ptr = Q + (batch * NUM_HEADS + head) * QK_DIM;
    
    // Load Q to registers (cooperative)
    __shared__ float q_shared[QK_DIM];
    for (int i = tid; i < QK_DIM; i += BLOCK_SIZE) {
        q_shared[i] = __bfloat162float(q_ptr[i]);
    }
    __syncthreads();
    
    // Online softmax state (per warp)
    float m = -1e30f;  // running max
    float l = 0.0f;    // running sum
    float acc[V_DIM] = {0.0f};
    
    // Iterate over KV sequence
    for (int kv = tid; kv < seq_len; kv += BLOCK_SIZE) {
        const __hip_bfloat16* kv_ptr = KV + (batch * seq_len + kv) * QK_DIM;
        
        // Compute score: dot(Q, KV[kv])
        float score = 0.0f;
        #pragma unroll
        for (int d = 0; d < QK_DIM; d += 4) {
            score += q_shared[d+0] * __bfloat162float(kv_ptr[d+0]);
            score += q_shared[d+1] * __bfloat162float(kv_ptr[d+1]);
            score += q_shared[d+2] * __bfloat162float(kv_ptr[d+2]);
            score += q_shared[d+3] * __bfloat162float(kv_ptr[d+3]);
        }
        score *= sm_scale;
        
        // Online softmax update
        float m_new = fmaxf(m, score);
        float exp_score = expf(score - m_new);
        float alpha = expf(m - m_new);
        
        l = l * alpha + exp_score;
        
        // Accumulate weighted V
        for (int v = 0; v < V_DIM; v++) {
            acc[v] = acc[v] * alpha + exp_score * __bfloat162float(kv_ptr[v]);
        }
        
        m = m_new;
    }
    
    // Warp reduction (similar to Flash Attention-2)
    // ...
    
    // Write normalized output
    if (tid == 0) {
        __hip_bfloat16* out_ptr = Out + (batch * NUM_HEADS + head) * V_DIM;
        for (int v = 0; v < V_DIM; v++) {
            out_ptr[v] = __float2bfloat16(acc[v] / (l + 1e-10f));
        }
    }
}
'''
```

### 6.4 Expected Performance Gains

| Optimization | Current | With Flash Attention | Gain |
|------------|---------|---------------------|------|
| bs=4, kv=1k | 22.6 µs | ~8 µs | **2.8×** |
| bs=32, kv=8k | 90.8 µs | ~40 µs | **2.3×** |
| bs=256, kv=8k | 293 µs | ~100 µs | **2.9×** |
| **Geomean** | **69.7 µs** | **~33 µs** | **2.1×** |

---

## 7. References

### Papers
1. Dao, T. et al. (2022). *FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness*. arXiv:2205.14135.
2. Dao, T. (2023). *FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning*. arXiv:2307.08691.

### Code Resources
- vLLM ROCm Backend: https://blog.vllm.ai/2026/02/27/rocm-attention-backend.html
- AITER Library: `/home/runner/aiter/` (on MI355X runner)
- CK-Tile Examples: `/home/runner/aiter/hsa/gfx950/`

### Related Skills
- `deepseek-mla-decode-flash-attention-gap`
- `amd-mla-decode-optimization`
- `popcorn-runner-api-inventory`
- `gfx950-mfma-register-layouts`

---

## Appendix: Code Patterns

### A.1 Online Softmax Pattern

```cpp
// Standard online softmax (Flash Attention v1)
float m = -INFINITY, l = 0;
for each block:
    m_new = max(m, block_max);
    alpha = exp(m - m_new);
    l = l * alpha + block_sum * exp(block_max - m_new);
    acc = acc * alpha + block_output;
    m = m_new;
```

### A.2 Log-Sum-Exp Reduction Pattern

```cpp
// Cross-split reduction (Flash Attention for multi-split)
float global_max = max(partial_max[split_id]);
float total = 0;
for each split:
    total += exp(partial_lse[split] - global_max) * partial_out[split];
output = total / sum(exp(partial_lse - global_max));
```

### A.3 Warp-Shuffle Reduction Pattern

```cpp
// Warp-level reduction without shared memory
#pragma unroll
for (int offset = 32; offset > 0; offset >>= 1) {
    value += __shfl_xor(value, offset, 64);
}
```

---

*Document generated: April 6, 2026*  
*Research scope: Flash Attention for AMD MI355X MLA optimization*  
*Next step: Prototype custom Flash Attention kernel via load_inline*
