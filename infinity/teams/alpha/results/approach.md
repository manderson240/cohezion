# Team Alpha: MLA Performance Optimization Approach

## Problem Analysis

**Current State:**
- Hybrid einsum + aiter approach: ~69μs
- Rank: ~22 on leaderboard
- Gap to #1 (n8_gr8_): 16x slower (4.33μs)

**Root Cause:**
aiter's 3-stage pipeline has ~100-150μs fixed overhead:
1. `get_mla_metadata_v1()` — ~5-20μs
2. `mla_decode_stage1_asm_fwd()` — ~70-120μs  
3. `mla_decode_reduce_fwd()` — ~10-30μs

For small decode (bs=4, kv=1k), actual attention compute is <10μs. Pipeline overhead dominates.

## Solution: Custom Triton Flash Attention Kernel

### Architecture

**Single Fused Kernel:**
- Eliminates 3-stage pipeline overhead
- Fuses: Q@K^T → online softmax → @V in one kernel launch
- No intermediate buffers or metadata

**Key Optimizations:**

1. **GEMV-Optimized (qseqlen=1)**
   - No padding Q to 16 (aiter requirement)
   - Direct vector loads for Q: 576 elements
   - Grid: (batch_size, num_heads) — minimal thread divergence

2. **K≠V Dimension Handling**
   - QK dim: 576 (absorbed query/key)
   - V dim: 512 (compressed value)
   - Single KV buffer: load 576 for K, first 512 for V
   - No separate K/V buffers needed

3. **Online Softmax (Flash Attention v2)**
   - Running max + sum tracking
   - No intermediate score storage
   - Numerically stable: `m_new = max(m_prev, max(scores))`

4. **Tiling Strategy**
   - BLOCK_N adaptive based on kvseqlen:
     - ≤512: 32
     - ≤2048: 64
     - ≤8192: 128
     - >8192: 256
   - Balances parallelism vs register pressure

5. **Memory Access Pattern**
   - Coalesced KV loads via `tl.arange`
   - Q loaded once per (batch, head)
   - V loaded on-demand during accumulation

### Implementation Details

```python
# Grid: (batch_size, num_heads)
pid_batch = tl.program_id(0)
pid_head = tl.program_id(1)

# Single Q load (576 elements)
q = tl.load(q_base + q_offs * stride_q_d)

# Loop over KV in blocks
for n_start in range(0, kv_len, BLOCK_N):
    # Load K block: [BLOCK_N, 576]
    k = tl.load(k_ptrs, mask=n_mask)
    
    # QK dot product: [BLOCK_N]
    scores = tl.sum(k * q, axis=1) * sm_scale
    
    # Online softmax update
    m_new = tl.maximum(m_prev, tl.max(scores))
    alpha = exp(m_prev - m_new)
    p = exp(scores - m_new)
    
    # Load V block: [BLOCK_N, 512]
    v = tl.load(v_ptrs, mask=n_mask)
    
    # Accumulate: rescale + weighted sum
    acc = acc * alpha + sum(p * v, axis=0)
```

### Expected Performance

**Theoretical:**
- Memory bandwidth: ~1.2 TB/s (MI355X HBM)
- Q read: bs * nheads * 576 * 2B
- KV read: bs * kvseqlen * 576 * 2B (K) + 512 * 2B (V)
- For bs=4, nheads=32, kvseqlen=1024:
  - Total memory: ~5.4 MB
  - Time @ 1.2 TB/s: ~4.5μs

**Target: <20μs** (4x improvement from 69μs)

## Testing Strategy

1. **Correctness:** Compare against reference with rtol=1e-2, atol=1e-2
2. **Benchmark:** All shapes from task.yml
3. **Profiling:** Nsight Compute for memory bandwidth utilization

## Files

- `submission_alpha_triton.py` — Optimized Triton kernel
- `approach.md` — This document

## Timeline

- Hour 0-6: Kernel implementation ✓
- Hour 6-12: Testing and debugging
- Hour 12-18: Performance tuning
- Hour 18-24: Final validation and submission

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Triton compilation errors | Test locally first, use simple kernel |
| Numerical precision issues | Online softmax with float32 accumulation |
| Register pressure | Tune BLOCK_N, use bf16 where possible |
| Memory coalescing | Use contiguous KV layout, verify strides |

## Next Steps

1. Test kernel correctness on local MI355X
2. Profile with Nsight Compute
3. Tune BLOCK_N for each shape
4. Consider FP8 quantization for Q/KV
5. Submit to leaderboard
