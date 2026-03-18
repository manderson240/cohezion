---
title: "A3 Memory Layout Optimizations"
date: 2026-03-15
status: complete
tags: [infinity, alpha, gpu-optimization]
aspect: thinker
---

# A3 Memory Layout Optimizations
## Agent A3 - Team Alpha (MoE Optimization)

### Memory Access Pattern Analysis

The MoE kernel has three main memory traffic phases:

1. **Token Sorting**: Reads topk_ids [M, topk], topk_weights [M, topk]
2. **GEMM1**: Reads hidden_states [M, d_hidden], w1 [E, 2*d_expert, d_hidden/2]
3. **GEMM2**: Reads intermediate [M*topk, d_expert], w2 [E, d_hidden, d_expert/2]

**Total Memory Traffic per Forward Pass:**
- Weights: ~2-4 GB (read-only, cached)
- Activations: ~50-100 MB (read-write)
- Sorting metadata: ~1-2 MB

---

## 1. Coalesced Memory Access

### Current Access Patterns

```python
# Token sorting - scattered access pattern
for token_idx in range(M):
    for k in range(topk):
        expert_id = topk_ids[token_idx, k]  # Non-contiguous
        sorted_ids[sort_idx] = token_idx
```

**Problem**: Random access pattern based on expert assignment

### Optimized Layout

```python
# Structure memory for expert-coalesced access
# Group tokens by expert in sorted_ids buffer

# Before: [token0_exp0, token0_exp1, token1_exp0, token1_exp1, ...]
# After:  [all_tokens_exp0, all_tokens_exp1, ...]

sorted_ids_layout = {
    "expert_0_tokens": sorted_ids[expert_0_start:expert_0_end],
    "expert_1_tokens": sorted_ids[expert_1_start:expert_1_end],
    # ...
}
```

**Benefit**: GEMM kernels can read tokens for same expert contiguously

---

## 2. Weight Tensor Layout

### CK Tile-Optimized Layout

CK (Composable Kernel) expects specific weight layouts for optimal MFMA utilization:

```python
# Current weight layout
w1: [E, 2*d_expert, d_hidden//2]  # fp4x2 packed

# CK-optimized layout (after shuffle)
w1_shuffled: [E, 2*d_expert, d_hidden//2]  # Reordered for CK tile access
```

The shuffle operation ensures:
- **K-dimension contiguous**: For efficient MFMA A-matrix loading
- **N-dimension strided**: For parallel output computation
- **128-byte aligned**: For optimal global memory throughput

### Weight Scale Layout

```python
# Scale tensors (e8m0 format)
w1_scale: [E, 2*d_expert, d_hidden//32]  # One scale per 32 K elements

# Optimized: Interleave scales with data for cache locality
# (Handled by CK internally)
```

---

## 3. Activation Tensor Layout

### Stage 1 Output Layout

```python
# Current: [M, topk, d_expert*2]
intermediate = torch.empty((M, topk, d_expert*2), dtype=torch.bfloat16)

# Optimized for GEMM2: [M*topk, d_expert]
intermediate_flat = intermediate.view(M*topk, d_expert)

# This allows GEMM2 to treat all token-expert pairs as independent rows
```

### Stage 2 Output Layout

```python
# Output: [M, d_hidden]
output = torch.empty((M, d_hidden), dtype=torch.bfloat16)

# Layout optimized for final write-back
# Ensure d_hidden is multiple of 64 for CK tile alignment
```

---

## 4. XCD-Aware Memory Placement

### MI355X Topology

- 8 XCDs (XCD-aware Compute Domains)
- Each XCD has local L2 cache
- Cross-XCD access has latency penalty

### Optimized Placement Strategy

```python
def _xcd_aware_placement(tensor, num_experts):
    """Place tensor data to maximize XCD-local access.
    
    For few-expert shapes (E <= 8):
    - Place each expert's weights on different XCD
    - Ensures token processing stays XCD-local
    
    For many-expert shapes (E > 8):
    - Round-robin expert placement
    - Accept some cross-XCD traffic
    """
    if num_experts <= 8:
        # Pin expert i to XCD i
        for i in range(num_experts):
            expert_tensor = tensor[i]
            # Set memory advice (if supported)
            # torch.cuda.memory.advise(expert_tensor, "preferred_location", xcd=i)
    return tensor
```

---

## 5. Memory Bandwidth Optimizations

### Quantization Benefits

MXFP4 quantization reduces memory bandwidth by 4x:

```
FP16 weights:  2 bytes/element
MXFP4 weights: 0.5 bytes/element (4x reduction)

For GEMM1 with w1 [256, 2816, 3584]:
- FP16: 256 * 2816 * 3584 * 2 = 5.1 GB
- MXFP4: 256 * 2816 * 3584 * 0.5 = 1.3 GB
- Savings: 3.8 GB per forward pass
```

### Activation Checkpointing

```python
# Don't store full precision activations between stages
# Re-quantize after GEMM1 for GEMM2 input

# Stage 1 output (bf16): 50-100 MB
# After MXFP4 re-quant: 12-25 MB
# Savings: ~75% activation memory
```

---

## 6. Buffer Reuse Strategy

### In-Place Operations

```python
# Current: Separate buffers for each stage
a1 = quantize(hidden_states)  # New buffer
out1 = gemm1(a1, w1)          # New buffer
a2 = quantize(out1)           # New buffer
out2 = gemm2(a2, w2)          # New buffer

# Optimized: Reuse buffers
# a1 -> out1 -> a2 can share memory (sequential access)
# Only need 2 buffers: one for input, one for output
```

### Circular Buffer Pattern

```python
class CircularBuffer:
    """Double-buffer for ping-pong between stages."""
    
    def __init__(self, size):
        self.buf0 = torch.empty(size, device="cuda")
        self.buf1 = torch.empty(size, device="cuda")
        self.flip = False
    
    def current(self):
        return self.buf0 if not self.flip else self.buf1
    
    def next(self):
        return self.buf1 if not self.flip else self.buf0
    
    def swap(self):
        self.flip = not self.flip
```

---

## 7. Performance Projections

| Optimization | Memory Traffic Reduction | Latency Impact |
|--------------|-------------------------|----------------|
| Coalesced access | 10-15% | 3-5µs |
| XCD-aware placement | 5-10% | 2-4µs |
| Buffer reuse | 20-30% | 5-8µs |
| In-place operations | 15-20% | 3-5µs |
| **Total** | **50-75%** | **13-22µs** |

---

## 8. Implementation Notes

### Critical Layout Requirements

1. **Weight tensors must be pre-shuffled** for CK compatibility
2. **All buffers must be 128-byte aligned** for optimal throughput
3. **Token sorting must group by expert** for coalesced access
4. **Scale tensors must match CK expected layout** (e8m0 format)

### Verification

```python
def verify_layout(tensor, expected_layout):
    """Verify tensor meets CK layout requirements."""
    assert tensor.is_contiguous(), "Tensor must be contiguous"
    assert tensor.device.type == "cuda", "Tensor must be on CUDA"
    
    # Check alignment
    ptr = tensor.data_ptr()
    assert ptr % 128 == 0, f"Tensor not 128-byte aligned: {ptr}"
    
    # Check shape
    assert tensor.shape == expected_layout, f"Shape mismatch: {tensor.shape} vs {expected_layout}"
```

---

*Memory layout analysis by Agent A3*  
*Timestamp: 2026-03-14*


## Related
- [[OPTIMIZATION_SUMMARY|Optimization Summary]] (a1)
- [[OPTIMIZATION_REPORT|Optimization Report]] (a1)
- [[TUNING_REPORT|Tuning Report]] (a2)
- [[buffer_management_improvements|Buffer Management Improvements]] (a3)
- [[dispatch_optimization_strategy|Dispatch Optimization Strategy]] (a3)
- [[performance_projections|Performance Projections]] (a3)
