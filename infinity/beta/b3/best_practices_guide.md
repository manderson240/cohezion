---
title: "AMD MI355X Kernel Optimization: Best Practices Guide"
date: 2026-03-15
status: in-progress
tags: [infinity, beta, gpu-optimization]
aspect: thinker
---

# AMD MI355X Kernel Optimization: Best Practices Guide

**Agent**: B3 (Code Technique Extractor)  
**Team**: Beta (Research & Intelligence)  
**Target**: AMD MI355X (gfx950)

## Quick Reference

### Critical Environment Variables

```python
# Always set for bandwidth-bound workloads
os.environ["AITER_USE_NT"] = "1"

# Alternative token sorting (often faster)
os.environ["AITER_USE_OPUS_MOE_SORTING"] = "1"

# Override CSV tuning configs
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

# Split-K parallelism (adaptive selection required)
os.environ["AITER_KSPLIT"] = "4"  # or "2", "default"

# Tile size override
os.environ["AITER_BLOCK_M"] = "64"  # or "32", "128"
```

### Shape Thresholds

| Workload | Small | Medium | Large |
|----------|-------|--------|-------|
| MoE tokens/expert | < 32 | 32-100 | > 100 |
| GEMM M dimension | <= 32 | 32-256 | > 256 |
| MLA total KV | <= 32k | 32k-256k | > 256k |

## Best Practices by Category

### 1. MoE (Mixture of Experts)

#### ✅ DO

**Use adaptive KSPLIT selection**:
```python
def select_ksplit(estimated_m, num_experts):
    if estimated_m >= 100:
        return "default"  # Dense
    elif num_experts >= 200 and estimated_m < 10:
        return "4"      # Very sparse (256E)
    else:
        return "2"      # Moderate
```

**Cache environment variable state**:
```python
_prev_ksplit = None

def set_ksplit(ks):
    global _prev_ksplit
    if _prev_ksplit != ks:
        os.environ["AITER_KSPLIT"] = ks
        _prev_ksplit = ks
```

**Use shuffled weights**:
```python
# Input provides both original and shuffled
return fused_moe(
    hidden_states,
    gate_up_weight_shuffled,  # Use shuffled
    down_weight_shuffled,
    ...
)
```

**Enable OPUS sorting for sparse shapes**:
```python
if num_experts >= 128:
    os.environ["AITER_USE_OPUS_MOE_SORTING"] = "1"
```

#### ❌ DON'T

**Never set doweight_stage1=True**:
```python
# WRONG: Changes computation, not just performance
fused_moe(..., doweight_stage1=True)

# CORRECT: Keep False (default behavior)
fused_moe(..., doweight_stage1=False)
```

**Don't update env vars every call**:
```python
# WRONG: Syscall overhead
for data in batch:
    os.environ["AITER_KSPLIT"] = compute_ksplit(data)
    fused_moe(data)

# CORRECT: Cache and only update on change
set_ksplit(compute_ksplit(data))
fused_moe(data)
```

**Don't ignore estimated_m calculation**:
```python
# WRONG: Fixed ksplit
os.environ["AITER_KSPLIT"] = "4"

# CORRECT: Shape-aware selection
estimated_m = (num_tokens * topk) // num_experts
ks = select_ksplit(estimated_m, num_experts)
```

### 2. GEMM (MXFP4)

#### ✅ DO

**Fuse quantization into GEMM loop**:
```python
@triton.jit
def fused_gemm_kernel(A_ptr, B_ptr, C_ptr, ...):
    for k_start in range(0, K, BLOCK_K):
        a_bf16 = tl.load(...)
        a_fp4, a_scale = mxfp4_quant_inline(a_bf16)
        b_q = tl.load(...)
        b_scale = tl.load(...)
        acc = tl.dot_scaled(a_fp4, a_scale, "e2m1", 
                           b_q, b_scale, "e2m1", acc=acc)
```

**Cache preprocessed weights**:
```python
_weight_cache = {}

def get_preprocessed(B_q, B_scale_sh):
    key = B_q.data_ptr()
    if key not in _weight_cache:
        B_t = B_q.view(torch.uint8).t().contiguous()
        B_scale = unshuffle_e8m0(B_scale_sh)
        _weight_cache[key] = (B_t, B_scale)
    return _weight_cache[key]
```

**Use autotune for tile sizes**:
```python
@triton.autotune(configs=make_configs(), key=["M", "N", "K"])
@triton.jit
def kernel(...):
    ...
```

**Match aiter bit-exact quantization**:
```python
# Critical: Round-up logic must match C++
round_case = ((u32 & 0x400000) != 0) & \
             (((u32 & 0x3FFFFF) != 0) | (exponent > 0))
exp_val = tl.where(round_case, exponent + 1, exponent)
```

**Use Group-M swizzle**:
```python
# Improves L2 locality
GROUP_SIZE_M: tl.constexpr = 8
num_blocks_in_group = GROUP_SIZE_M * num_blocks_n
group_id = pid // num_blocks_in_group
```

#### ❌ DON'T

**Don't use separate quant + GEMM**:
```python
# WRONG: Two separate passes
a_q, a_s = dynamic_mxfp4_quant(a)
out = gemm_mxfp4(a_q, a_s, b_q, b_s)

# CORRECT: Fused in one kernel
out = fused_quant_gemm(a, b_q, b_s)
```

**Don't forget scale unshuffle**:
```python
# WRONG: Using shuffled scales directly
out = gemm(a, b, scale_shuffled)

# CORRECT: Unshuffle first
scale = unshuffle_e8m0(scale_shuffled)
out = gemm(a, b, scale)
```

**Don't use integer indexing on 3D tensors**:
```python
# WRONG: Not supported
tensor[i, j, k]

# CORRECT: Reshape then index
grouped = tl.reshape(tensor, [M, N, K])
grouped[i, j, k]
```

### 3. MLA (Multi-Head Latent Attention)

#### ✅ DO

**Use online softmax for decode**:
```python
@triton.jit
def flash_decode(Q_ptr, KV_ptr, Out_ptr, ...):
    m_i = -float("inf")
    l_i = 0.0
    acc = tl.zeros([V_DIM], dtype=tl.float32)
    
    for start_n in range(0, seqlen, BLOCK_N):
        k = tl.load(K_ptr + ...)
        qk = tl.sum(q[None, :] * k, axis=1) * sm_scale
        
        m_ij = tl.max(qk, axis=0)
        p = tl.exp(qk - m_ij)
        l_ij = tl.sum(p, axis=0)
        
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        l_i = l_i * alpha + l_ij * beta
        acc = acc * alpha
        
        v = tl.load(V_ptr + ...)
        acc += tl.sum(p[:, None] * v, axis=0) * beta
        m_i = m_new
    
    out = (acc / l_i).to(tl.bfloat16)
```

**Implement hybrid dispatch**:
```python
def custom_kernel(data):
    total_kv = bs * kvseqlen
    
    if total_kv <= 32768:
        return triton_bf16_path(data)  # Small
    elif total_kv <= 262144:
        return triton_fp8_path(data)   # Medium
    else:
        return aiter_asm_path(data)    # Large
```

**Pad non-power-of-2 dimensions**:
```python
QK_HEAD_DIM = 576
QK_PAD_DIM = 640  # Next multiple of 64

offs = tl.arange(0, QK_PAD_DIM)
mask = offs < QK_HEAD_DIM
x = tl.load(ptr + offs, mask=mask, other=0.0)
```

**Use fp8 KV cache for medium shapes**:
```python
if total_kv <= 262144:
    kv_fp8, kv_scale = quantize_fp8(kv_bf16)
    return triton_fp8_decode(q, kv_fp8, kv_scale)
```

#### ❌ DON'T

**Don't use fast_mode=True**:
```python
# WRONG: Actually SLOWER on MI355X
mla_decode_fwd(..., fast_mode=True)

# CORRECT: Use default (fast_mode=False)
mla_decode_fwd(..., fast_mode=False)
```

**Don't materialize attention matrix**:
```python
# WRONG: O(N²) memory
attn = torch.matmul(Q, K.T)
out = torch.matmul(attn, V)

# CORRECT: O(1) memory with online softmax
# See flash decode pattern above
```

**Don't forget to fold KV scale**:
```python
# WRONG: Separate multiply
qk = torch.matmul(Q, K.T) * sm_scale
qk = qk * kv_scale

# CORRECT: Fold into sm_scale
effective_scale = sm_scale * kv_scale
qk = torch.matmul(Q, K.T) * effective_scale
```

## Performance Optimization Checklist

### Pre-Optimization

- [ ] Profile baseline with torch.profiler
- [ ] Identify bottleneck type:
  - [ ] Compute-bound (low occupancy, high ALU utilization)
  - [ ] Memory-bound (high cache miss, bandwidth saturation)
  - [ ] Launch-bound (many small kernels, high dispatch overhead)
- [ ] Document current performance metrics

### Optimization Phase

- [ ] Implement shape-based dispatch
- [ ] Add environment variable tuning
- [ ] Cache preprocessed weights
- [ ] Fuse operations where possible
- [ ] Use appropriate tile sizes
- [ ] Add CUDA graphs for repetitive sequences
- [ ] Implement fallback chain

### Verification

- [ ] Test correctness on all shape variants
- [ ] Verify numerical accuracy (rtol=1e-2 for fp4)
- [ ] Benchmark against baseline
- [ ] Profile optimized version
- [ ] Document speedup achieved

## Debugging Tips

### Numerical Mismatches

**MXFP4 quantization mismatch**:
```python
# Check bit-exact match with reference
# Common issues:
# 1. Wrong round-up logic
# 2. Missing scale unshuffle
# 3. Incorrect exponent bias (129 vs 127)
```

**Silent wrong results**:
```python
# Check XCD remapping bijectivity
# Wrong: tile_id = (pid * NUM_XCDS) // total_tiles
# Right: tile_id = pid % total_tiles
```

### Performance Issues

**Low occupancy**:
- Check tile sizes (BLOCK_M, BLOCK_N, BLOCK_K)
- Verify num_warps matches workload
- Check for register spilling

**High launch overhead**:
- Use CUDA graphs
- Batch small operations
- Cache kernel launches

**Cache thrashing**:
- Add Group-M swizzle
- Check memory access patterns
- Verify coalesced loads

## Code Review Checklist

### For MoE Submissions

- [ ] Uses adaptive KSPLIT selection
- [ ] Caches env var state
- [ ] Uses shuffled weights
- [ ] doweight_stage1=False
- [ ] Has fallback to fused_moe

### For GEMM Submissions

- [ ] Fuses quantization if applicable
- [ ] Unshuffles scales correctly
- [ ] Uses autotune or optimal tile sizes
- [ ] Handles all M sizes (4, 16, 64, 256)
- [ ] Caches preprocessed weights

### For MLA Submissions

- [ ] Uses online softmax for decode
- [ ] Implements hybrid dispatch
- [ ] Pads non-power-of-2 dimensions
- [ ] fast_mode=False (if using aiter)
- [ ] Handles both bf16 and fp8 KV

## Reference Implementations

### MoE: Adaptive KSPLIT
```python
# File: submission_opus_adaptive.py
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_USE_OPUS_MOE_SORTING"] = "1"

estimated_m = topk_ids.numel() // num_experts
if estimated_m >= 50:
    os.environ.pop("AITER_KSPLIT", None)
elif num_experts >= 200 and estimated_m < 10:
    os.environ["AITER_KSPLIT"] = "4"
else:
    os.environ["AITER_KSPLIT"] = "2"
```

### GEMM: Fused Quant+GEMM
```python
# File: submission_fused_triton.py
@triton.autotune(configs=make_configs(), key=["M", "N", "K"])
@triton.jit
def _fused_mxfp4_gemm_kernel(...):
    for k_start in range(0, K, BLOCK_K):
        a_bf16 = tl.load(...)
        a_fp4, a_scale = _mxfp4_quant_op_precise(a_bf16, ...)
        b_q = tl.load(...)
        b_scale = tl.load(...)
        acc = tl.dot_scaled(a_fp4, a_scale, "e2m1",
                           b_q, b_scale, "e2m1", acc=acc)
```

### MLA: Flash Decode
```python
# File: submission_triton_flash.py
@triton.jit
def _mla_flash_decode_bf16(...):
    m_i = -float("inf")
    l_i = 0.0
    acc = tl.zeros([V_DIM], dtype=tl.float32)
    
    for start_n in range(0, kvseqlen, BLOCK_N):
        k = tl.load(KV_ptr + ...)
        qk = tl.sum(q[None, :] * k, axis=1) * sm_scale
        
        m_ij = tl.max(qk, axis=0)
        p = tl.exp(qk - m_ij)
        l_ij = tl.sum(p, axis=0)
        
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        l_i = l_i * alpha + l_ij * beta
        acc = acc * alpha
        
        v = tl.load(KV_ptr + ...)
        acc += tl.sum(p[:, None] * v, axis=0) * beta
        m_i = m_new
```

## Resources

- **Skills**: `aiter-kernel-parameter-semantics`, `triton-fp4-inline-quantization`
- **Reference**: `amd-gfx950-tl-dot-scaled-constraints`
- **Vault**: `~/vaults/cohezion-vault/infinity/beta/b3/`

## Summary

Top performers on MI355X combine:
1. **Foundation**: Proper env var tuning + adaptive dispatch
2. **Mid-tier**: Custom Triton kernels with fused operations
3. **Breakthrough**: Direct hardware dispatch + graph capture

The 2-5x speedup gap is primarily algorithmic - matching kernel implementation to workload characteristics and bypassing unnecessary overhead.


## Related
- [[john_hahn_intelligence_analysis|John Hahn Intelligence Analysis]] (b1)
- [[B1_SUMMARY|B1 Summary]] (b1)
- [[README|Readme]] (b2)
- [[performance_cluster_report|Performance Cluster Report]] (b2)
- [[leaderboard_trend_analysis|Leaderboard Trend Analysis]] (b2)
- [[optimization_ceiling_prediction|Optimization Ceiling Prediction]] (b2)
- [[strategic_recommendations|Strategic Recommendations]] (b2)
- [[technique_extraction_report|Technique Extraction Report]] (b3)
- [[common_patterns|Common Patterns]] (b3)
