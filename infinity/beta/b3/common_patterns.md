---
title: "AMD MI355X Kernel Optimization: Common Patterns"
date: 2026-03-15
status: in-progress
tags: [infinity, beta, gpu-optimization]
aspect: thinker
---

# AMD MI355X Kernel Optimization: Common Patterns

**Agent**: B3 (Code Technique Extractor)  
**Team**: Beta (Research & Intelligence)

## Pattern Catalog

### P1: Adaptive Environment Variable Dispatch

**Use Case**: Switch kernel implementations based on workload characteristics.

**Template**:
```python
import os

_state: dict = {"ksplit": None}

def set_ksplit(estimated_m: int, num_experts: int) -> None:
    """Adaptive KSPLIT selection based on token density."""
    global _state
    
    if estimated_m >= 100:
        ks = "default"
    elif num_experts >= 200 and estimated_m < 10:
        ks = "4"
    else:
        ks = "2"
    
    if _state["ksplit"] != ks:
        if ks == "default":
            os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
            os.environ.pop("AITER_KSPLIT", None)
        else:
            os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
            os.environ["AITER_KSPLIT"] = ks
        _state["ksplit"] = ks
```

**Key Insight**: Only update env vars when value changes to avoid syscall overhead.

---

### P2: Shape-Based Multi-Path Dispatch

**Use Case**: Route to different implementations based on tensor shapes.

**Template**:
```python
def custom_kernel(data: input_t) -> output_t:
    M, N, K = extract_dims(data)
    
    # Small shapes: custom Triton
    if M <= 32:
        return triton_path(data)
    
    # Medium shapes: optimized library
    elif M <= 256:
        return library_path(data)
    
    # Large shapes: reference implementation
    else:
        return ref_kernel(data)
```

**Benefits**:
- Optimized path for common cases
- Fallback for edge cases
- Easy to extend with new paths

---

### P3: Precomputed Buffer Cache

**Use Case**: Avoid repeated torch.empty() overhead.

**Template**:
```python
_buf_cache: dict[tuple, dict[str, torch.Tensor]] = {}

def get_buffers(shape_key: tuple, device: torch.device) -> dict[str, torch.Tensor]:
    """Get or create pre-allocated buffers."""
    if shape_key not in _buf_cache:
        _buf_cache[shape_key] = {
            "buffer1": torch.empty(size1, dtype=dtype1, device=device),
            "buffer2": torch.empty(size2, dtype=dtype2, device=device),
        }
    return _buf_cache[shape_key]
```

**Benefits**:
- Eliminates allocation overhead
- Reuses memory across calls
- Thread-safe if used correctly

---

### P4: B-Matrix Preprocessing Cache

**Use Case**: Cache weight preprocessing across kernel calls.

**Template**:
```python
_weight_cache: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}

def get_preprocessed_weights(
    B_q: torch.Tensor, 
    B_scale: torch.Tensor,
    n: int, 
    k: int
) -> tuple[torch.Tensor, torch.Tensor]:
    """Get transposed B and unshuffled scales, cached by data_ptr."""
    cache_key = B_q.data_ptr()
    
    if cache_key not in _weight_cache:
        B_t = B_q.view(torch.uint8).t().contiguous()
        B_scale_unshuffled = unshuffle_scale(B_scale, n, k)
        _weight_cache[cache_key] = (B_t, B_scale_unshuffled)
    
    return _weight_cache[cache_key]
```

**Key Insight**: Use data_ptr() as cache key to detect same underlying storage.

---

### P5: CUDA Graph Capture Pattern

**Use Case**: Eliminate kernel launch overhead for repetitive sequences.

**Template**:
```python
_graphs: dict = {}
_ncalls: dict = {}
_WARMUP = 3

def custom_kernel(data: input_t) -> output_t:
    key = compute_shape_key(data)
    _ncalls[key] = _ncalls.get(key, 0) + 1
    
    # Warmup: normal execution
    if _ncalls[key] <= _WARMUP:
        return compute(data)
    
    # Capture graph on first post-warmup call
    if key not in _graphs:
        try:
            # Create static buffers
            static_inputs = clone_to_static(data)
            
            torch.cuda.synchronize()
            g = torch.cuda.CUDAGraph()
            
            with torch.cuda.graph(g):
                static_output = compute(static_inputs)
            
            _graphs[key] = {
                "graph": g,
                "inputs": static_inputs,
                "output": static_output,
            }
        except Exception as e:
            _graphs[key] = None  # Mark as failed
            return compute(data)
    
    # Replay captured graph
    entry = _graphs[key]
    copy_to_static(data, entry["inputs"])
    entry["graph"].replay()
    return entry["output"]
```

**Critical**: Must warmup before capture (JIT compilation).

---

### P6: Fallback Chain with Logging

**Use Case**: Try optimized paths, gracefully degrade on failure.

**Template**:
```python
_USE_OPTIMIZED = True

def custom_kernel(data: input_t) -> output_t:
    if _USE_OPTIMIZED:
        try:
            return optimized_path(data)
        except Exception as e:
            log_once(f"Optimized path failed: {e}")
            _USE_OPTIMIZED = False
    
    return fallback_path(data)

_logged_errors: set = set()

def log_once(msg: str) -> None:
    if msg not in _logged_errors:
        print(msg, file=sys.stderr)
        _logged_errors.add(msg)
```

**Benefits**:
- Production-safe
- Debuggable
- No repeated error spam

---

### P7: Inline MXFP4 Quantization

**Use Case**: Fuse quantization into GEMM loop.

**Template**:
```python
@triton.jit
def mxfp4_quant_inline(x, BLOCK_K: tl.constexpr, BLOCK_M: tl.constexpr):
    QUANT_GROUP: tl.constexpr = 32
    NUM_GROUPS: tl.constexpr = BLOCK_K // QUANT_GROUP
    
    # Reshape into quant groups
    x_grouped = tl.reshape(x, [BLOCK_M, NUM_GROUPS, QUANT_GROUP])
    
    # Compute amax per group
    amax = tl.max(tl.abs(x_grouped), axis=2)
    
    # Extract and round exponent
    u32 = amax.to(tl.int32, bitcast=True)
    exponent = ((u32 >> 23) & 0xFF)
    round_case = ((u32 & 0x400000) != 0) & (((u32 & 0x3FFFFF) != 0) | (exponent > 0))
    exp_val = tl.where(round_case, exponent + 1, exponent)
    
    # Compute E8M0 scale
    scale_unbiased = exp_val - 129
    bs_e8m0 = (scale_unbiased + 127).to(tl.uint8)
    quant_scale_inv = tl.exp2(-scale_unbiased.to(tl.float32))
    
    # Quantize to 4-bit
    qx = x_grouped * quant_scale_inv[:, :, None]
    sign = (qx < 0).to(tl.int32)
    x_abs = tl.abs(qx)
    
    # Map to fp4 codes (e2m1)
    mag = tl.where(x_abs < 0.25, 0,
          tl.where(x_abs < 0.75, 1,
          tl.where(x_abs < 1.25, 2,
          tl.where(x_abs < 1.75, 3,
          tl.where(x_abs < 2.5,  4,
          tl.where(x_abs < 3.5,  5,
          tl.where(x_abs < 5.0,  6, 7)))))))
    
    codes = (sign << 3) | mag
    codes_flat = tl.reshape(codes, [BLOCK_M, BLOCK_K])
    
    # Pack to fp4x2
    idx_k = tl.arange(0, BLOCK_K)
    shift = tl.where(idx_k % 2 == 1, 4, 0)
    shifted = (codes_flat & 0xF) << shift[None, :]
    x_fp4 = tl.sum(
        tl.reshape(shifted, [BLOCK_M, BLOCK_K // 2, 2]), axis=2
    ).to(tl.uint8)
    
    return x_fp4, tl.reshape(bs_e8m0, [BLOCK_M, NUM_GROUPS])
```

**Critical**: Must match aiter C++ backend bit-exactly.

---

### P8: Online Softmax for Flash Attention

**Use Case**: Single-pass attention without materialized attention matrix.

**Template**:
```python
@triton.jit
def flash_attention_kernel(Q_ptr, K_ptr, V_ptr, Out_ptr, ...):
    # Load query
    q = tl.load(Q_ptr + ...)
    
    # Initialize online softmax accumulators
    m_i = -float("inf")  # Max score so far
    l_i = 0.0            # Sum of exp scores
    acc = tl.zeros([V_DIM], dtype=tl.float32)
    
    # Stream over KV sequence
    for start_n in range(0, seqlen, BLOCK_N):
        # Load K block
        k = tl.load(K_ptr + ...)
        
        # Compute QK scores
        qk = tl.sum(q[None, :] * k, axis=1) * sm_scale
        
        # Online softmax update
        m_ij = tl.max(qk, axis=0)
        p = tl.exp(qk - m_ij)
        l_ij = tl.sum(p, axis=0)
        
        # Update running statistics
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        l_i = l_i * alpha + l_ij * beta
        acc = acc * alpha
        
        # Load V and accumulate
        v = tl.load(V_ptr + ...)
        acc += tl.sum(p[:, None] * v, axis=0) * beta
        m_i = m_new
    
    # Normalize and store
    out = (acc / l_i).to(tl.bfloat16)
    tl.store(Out_ptr + ..., out)
```

**Benefits**:
- O(1) memory vs O(N²)
- Single pass over KV cache
- Numerically stable

---

### P9: Group-M Swizzle for L2 Locality

**Use Case**: Improve cache locality across compute units.

**Template**:
```python
@triton.jit
def swizzled_gemm_kernel(A_ptr, B_ptr, C_ptr, ...):
    # Standard 1D program ID
    pid = tl.program_id(0)
    
    # Compute grid dimensions
    num_blocks_m = tl.cdiv(M, BLOCK_M)
    num_blocks_n = tl.cdiv(N, BLOCK_N)
    
    # Group-M swizzle
    GROUP_SIZE_M: tl.constexpr = 8
    num_blocks_in_group = GROUP_SIZE_M * num_blocks_n
    group_id = pid // num_blocks_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_blocks_m - first_pid_m, GROUP_SIZE_M)
    
    # Compute actual block indices
    pid_m = first_pid_m + ((pid % num_blocks_in_group) % group_size_m)
    pid_n = (pid % num_blocks_in_group) // group_size_m
    
    # Continue with normal GEMM...
```

**Benefit**: Threads in same group access similar memory regions, improving L2 hit rate.

---

### P10: Autotune Configuration Generator

**Use Case**: Systematically explore tile size configurations.

**Template**:
```python
def make_autotune_configs():
    """Generate configs covering all expected shape ranges."""
    configs = []
    
    for block_m in [16, 32, 64, 128]:
        for block_n in [64, 128, 256]:
            for block_k in [128, 256]:
                for num_warps in [4, 8]:
                    for num_stages in [1, 2]:
                        # Skip invalid/wasteful configs
                        if block_m == 128 and block_n == 256:
                            continue  # Register pressure
                        if block_k == 256 and block_n == 256:
                            continue  # Shared memory
                        if block_m > 64 and num_warps < 8:
                            continue  # Under-utilization
                        
                        configs.append(triton.Config(
                            {
                                "BLOCK_M": block_m,
                                "BLOCK_N": block_n,
                                "BLOCK_K": block_k,
                                "GROUP_SIZE_M": 8,
                            },
                            num_warps=num_warps,
                            num_stages=num_stages,
                        ))
    
    return configs


@triton.autotune(configs=make_autotune_configs(), key=["M", "N", "K"])
@triton.jit
def autotuned_kernel(...):
    ...
```

**Key**: Prune obviously bad configs to reduce autotune time.

---

### P11: Dimension Padding for Alignment

**Use Case**: Handle non-power-of-2 dimensions efficiently.

**Template**:
```python
# Constants
REAL_DIM = 576
PADDED_DIM = 640  # Next multiple of 64

@triton.jit
def padded_kernel(In_ptr, Out_ptr, ...):
    # Load with padding
    offs = tl.arange(0, PADDED_DIM)
    mask = offs < REAL_DIM
    
    x = tl.load(In_ptr + offs, mask=mask, other=0.0)
    
    # Compute...
    
    # Store with padding
    tl.store(Out_ptr + offs, result, mask=mask)
```

**Benefit**: Enables vectorized loads/stores even with odd dimensions.

---

### P12: Hybrid Dispatch with Thresholds

**Use Case**: Combine multiple implementations with automatic routing.

**Template**:
```python
# Thresholds
SMALL_THRESHOLD = 32768
MEDIUM_THRESHOLD = 262144

def custom_kernel(data: input_t) -> output_t:
    workload_size = compute_size(data)
    
    if workload_size <= SMALL_THRESHOLD:
        # Fast path for small workloads
        return triton_bf16_path(data)
    
    elif workload_size <= MEDIUM_THRESHOLD:
        # Balanced path for medium workloads
        return triton_fp8_path(data)
    
    else:
        # Optimized path for large workloads
        return asm_path(data)
```

**Benefits**:
- Optimal implementation per workload size
- Graceful degradation
- Easy to tune thresholds

---

## Pattern Selection Guide

| Pattern | Use When | Expected Gain |
|---------|----------|---------------|
| P1: Adaptive Env Vars | Using aiter library | 10-30% |
| P2: Shape Dispatch | Multiple shape regimes | 20-50% |
| P3: Buffer Cache | Repeated allocations | 5-15% |
| P4: Weight Cache | Static weights | 10-20% |
| P5: CUDA Graphs | Repetitive kernel sequences | 20-40% |
| P6: Fallback Chain | Production code | Safety |
| P7: Inline Quant | MXFP4 GEMM | 30-50% |
| P8: Online Softmax | Attention decode | 40-60% |
| P9: Group-M Swizzle | Large GEMMs | 10-20% |
| P10: Autotune | Unknown optimal config | 20-40% |
| P11: Dim Padding | Non-power-of-2 dims | 10-20% |
| P12: Hybrid Dispatch | Wide shape range | 30-60% |

## Anti-Patterns to Avoid

### A1: Unconditional Env Var Updates
```python
# BAD: Updates every call
os.environ["AITER_KSPLIT"] = compute_ksplit(data)

# GOOD: Only update when changed
if _prev_ksplit != new_ksplit:
    os.environ["AITER_KSPLIT"] = new_ksplit
    _prev_ksplit = new_ksplit
```

### A2: Materialized Attention Matrix
```python
# BAD: O(N²) memory
attn = Q @ K.T  # [N, N] matrix
out = attn @ V

# GOOD: O(1) memory with online softmax
# See Pattern P8
```

### A3: Integer Indexing on 3D Tensors
```python
# BAD: Not supported in Triton
x = tensor[i, j, k]

# GOOD: Use reshape
x_grouped = tl.reshape(tensor, [M, N_GROUPS, GROUP_SIZE])
x = x_grouped[i, j, k]
```

### A4: Non-Bijective Tile Mapping
```python
# BAD: Some tiles computed twice, others never
tile_id = (pid * NUM_XCDS) // total_tiles

# GOOD: Use modulo for bijective mapping
tile_id = pid % total_tiles
xcd_id = tile_id % NUM_XCDS
```

### A5: Ignoring doweight_stage1 Semantics
```python
# BAD: Thinking it's just performance
doweight_stage1=True  # Actually changes computation!

# GOOD: Understand parameter semantics
# doweight_stage1=True applies weights in stage 1
# doweight_stage1=False applies weights in stage 2
```

## Implementation Checklist

- [ ] Profile baseline before optimization
- [ ] Identify bottleneck (compute vs memory vs launch)
- [ ] Select appropriate patterns for bottleneck type
- [ ] Implement with fallback chain
- [ ] Verify correctness on all shapes
- [ ] Benchmark against baseline
- [ ] Document chosen parameters
- [ ] Add comments explaining non-obvious optimizations


## Related
- [[john_hahn_intelligence_analysis|John Hahn Intelligence Analysis]] (b1)
- [[B1_SUMMARY|B1 Summary]] (b1)
- [[README|Readme]] (b2)
- [[performance_cluster_report|Performance Cluster Report]] (b2)
- [[leaderboard_trend_analysis|Leaderboard Trend Analysis]] (b2)
- [[optimization_ceiling_prediction|Optimization Ceiling Prediction]] (b2)
- [[strategic_recommendations|Strategic Recommendations]] (b2)
- [[best_practices_guide|Best Practices Guide]] (b3)
- [[technique_extraction_report|Technique Extraction Report]] (b3)
