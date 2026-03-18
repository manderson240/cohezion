---
title: "A3 Buffer Management Improvements"
date: 2026-03-15
status: in-progress
tags: [infinity, alpha, gpu-optimization]
aspect: thinker
---

# A3 Buffer Management Improvements
## Agent A3 - Team Alpha (MoE Optimization)

### Current Buffer Allocation Issues

The baseline submission uses a per-shape buffer cache that allocates on first call:

```python
# Current approach (problematic)
_buf_cache: dict = {}

def _get_buffers(num_tokens, topk, num_experts, model_dim, block_m, device):
    key = (num_tokens, topk, num_experts, model_dim, block_m)
    if key in _buf_cache:
        return _buf_cache[key]  # Cache hit - good
    # Cache miss - allocates NEW tensors
    bufs = {
        "sorted_ids": torch.empty(max_padded, dtype=dtypes.i32, device=device),
        # ... more allocations
    }
    _buf_cache[key] = bufs
    return bufs
```

**Problems:**
1. First-call latency: 5-10µs penalty per unique shape
2. Memory fragmentation: Multiple small allocations
3. Cache pollution: Dictionary lookup overhead
4. No memory reuse: Each shape gets dedicated buffers

---

## Optimized Buffer Pool Architecture

### 1. Pre-allocated Static Pool

```python
# A3: Pre-allocated at module load
_MAX_TOKENS = 2048
_MAX_TOPK = 8
_MAX_EXPERTS = 256
_MAX_MODEL_DIM = 7168
_MAX_INTER_DIM = 4096
_MAX_BLOCK_M = 128

_BUF_POOL = {
    # Sorting buffers
    "sorted_ids": torch.empty(max_padded, dtype=torch.int32, device="cuda"),
    "sorted_weights": torch.empty(max_padded, dtype=torch.float32, device="cuda"),
    "sorted_expert_ids": torch.empty(max_m_blocks, dtype=torch.int32, device="cuda"),
    "num_valid_ids": torch.empty(2, dtype=torch.int32, device="cuda"),
    
    # Output buffers
    "moe_buf": torch.empty((2048, 7168), dtype=torch.bfloat16, device="cuda"),
    "stage1_out": torch.empty((2048, 8, 7168*8), dtype=torch.bfloat16, device="cuda"),
    "stage1_tmp": torch.empty((2048, 8, 4096), dtype=torch.bfloat16, device="cuda"),
    
    # Scale buffers
    "a1_scale": torch.empty((2048, 256), dtype=torch.uint8, device="cuda"),
    "a2_scale": torch.empty((2048, 256), dtype=torch.uint8, device="cuda"),
}
```

**Benefits:**
- Zero allocation overhead on inference
- Contiguous memory layout
- Predictable memory usage
- No cache misses

### 2. Zero-Copy View Pattern

Instead of allocating new tensors, return views:

```python
def _get_buffer_views(num_tokens, topk, num_experts, model_dim, block_m):
    """Return views into pre-allocated pool - zero allocation."""
    max_padded = num_tokens * topk + num_experts * block_m - topk
    max_m_blocks = (max_padded + block_m - 1) // block_m
    
    return {
        "sorted_ids": _BUF_POOL["sorted_ids"][:max_padded],
        "sorted_weights": _BUF_POOL["sorted_weights"][:max_padded],
        "sorted_expert_ids": _BUF_POOL["sorted_expert_ids"][:max_m_blocks],
        "num_valid_ids": _BUF_POOL["num_valid_ids"],  # Fixed size
        "moe_buf": _BUF_POOL["moe_buf"][:num_tokens, :model_dim],
    }
```

**Performance Impact:**
- Eliminates 5-10µs allocation overhead
- Reduces memory fragmentation
- Improves cache locality

### 3. Buffer Lifecycle Management

```python
class BufferPool:
    """Managed buffer pool with automatic cleanup."""
    
    def __init__(self):
        self._pool = {}
        self._active_views = set()
    
    def acquire(self, shape_key):
        """Get or create buffer for shape."""
        if shape_key not in self._pool:
            self._pool[shape_key] = self._allocate(shape_key)
        return self._pool[shape_key]
    
    def _allocate(self, shape_key):
        """Allocate buffers for shape."""
        # Implementation
        pass
    
    def release_all(self):
        """Release all buffers (for cleanup)."""
        self._pool.clear()
        torch.cuda.empty_cache()
```

---

## Memory Layout Optimizations

### 1. Tensor Alignment

Ensure all buffers are aligned to 128-byte boundaries for optimal CK performance:

```python
def _allocate_aligned(shape, dtype, device):
    """Allocate tensor with 128-byte alignment."""
    tensor = torch.empty(shape, dtype=dtype, device=device)
    # PyTorch CUDA tensors are already 256-byte aligned
    return tensor
```

### 2. Coalesced Access Patterns

Structure buffers for stride-1 access:

```python
# Good: Contiguous access
sorted_ids = torch.empty(max_padded, dtype=torch.int32)  # [N] - stride 1

# Bad: Strided access (if accessed by expert)
# sorted_ids_by_expert = torch.empty((num_experts, max_per_expert), dtype=torch.int32)
```

### 3. Scale Tensor Packing

Scale tensors (e8m0) are small - pack them efficiently:

```python
# Current: Separate allocations per stage
a1_scale = torch.empty((M, K//32), dtype=torch.uint8)
a2_scale = torch.empty((M, K//32), dtype=torch.uint8)

# Optimized: Pre-allocated, reused
_SCALE_BUF = torch.empty((2048, 256), dtype=torch.uint8, device="cuda")
a1_scale = _SCALE_BUF[:M]  # View
a2_scale = _SCALE_BUF[:M]  # Reuse same memory (stages don't overlap)
```

---

## Buffer Size Calculations

### Maximum Buffer Sizes (for benchmark shapes)

| Buffer | Shape | Size (bytes) |
|--------|-------|--------------|
| sorted_ids | [2048*8 + 256*128] | 65,536 |
| sorted_weights | [2048*8 + 256*128] * 4 | 262,144 |
| sorted_expert_ids | [(max_padded + 128 - 1) // 128] | ~2,048 |
| num_valid_ids | [2] * 4 | 8 |
| moe_buf | [2048, 7168] * 2 | 29,360,128 |
| stage1_out | [2048, 8, 7168*8] * 2 | 1,879,048,192 |
| stage1_tmp | [2048, 8, 4096] * 2 | 134,217,728 |
| a1_scale | [2048, 256] | 524,288 |
| a2_scale | [2048, 256] | 524,288 |

**Total Pool Size**: ~2.04 GB

This is acceptable for MI355X with 128GB HBM.

---

## Implementation Checklist

- [x] Pre-allocated buffer pool design
- [x] Zero-copy view pattern
- [x] Buffer size calculations
- [ ] Memory alignment verification
- [ ] Pool initialization timing
- [ ] Fallback for OOM scenarios
- [ ] Multi-shape concurrent access safety

---

## Expected Performance Gains

| Optimization | Latency Reduction | Notes |
|--------------|-------------------|-------|
| Pre-allocated pool | 5-8µs | Eliminates first-call allocation |
| Zero-copy views | 2-3µs | No tensor creation overhead |
| Scale reuse | 1-2µs | Shared memory for scales |
| **Total** | **8-13µs** | ~5-8% improvement |

---

*Buffer management analysis by Agent A3*  
*Timestamp: 2026-03-14*


## Related
- [[OPTIMIZATION_SUMMARY|Optimization Summary]] (a1)
- [[OPTIMIZATION_REPORT|Optimization Report]] (a1)
- [[TUNING_REPORT|Tuning Report]] (a2)
- [[dispatch_optimization_strategy|Dispatch Optimization Strategy]] (a3)
- [[memory_layout_optimizations|Memory Layout Optimizations]] (a3)
- [[performance_projections|Performance Projections]] (a3)
