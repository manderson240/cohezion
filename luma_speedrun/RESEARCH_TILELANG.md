# TileLang Research Document

**Research Date:** April 6, 2026  
**Researcher:** AI Research Assistant  
**Document Type:** AMD MI355X Kernel Optimization Feasibility Study  
**Competition:** Luma AMD Speedrun (April 2026)

---

## Executive Summary

**TileLang** is a new domain-specific language (DSL) for high-performance AI kernel development, released open-source in January 2025 by researchers from Peking University and Microsoft Research. It has gained significant traction (5.5k GitHub stars) for its ability to write GPU kernels using Pythonic syntax while achieving performance comparable to hand-optimized implementations.

**Key Finding for Competition:** TileLang has **DIRECT MI355X support** via PR #1718 (merged Jan 26, 2026) which added MI350/MI355 FP8 support for gfx950 architecture. This makes it immediately applicable to our competition kernels.

---

## 1. What is TileLang?

### 1.1 Core Concept
TileLang is a **tiled programming model** that decouples the scheduling space (thread binding, layout, tensorization, pipeline) from dataflow. It allows developers to:

- Focus on kernel dataflow patterns
- Leave most optimizations to the compiler
- Generate code for multiple backends (NVIDIA CUDA, AMD HIP/HIPCC, Apple Metal, WebGPU)

### 1.2 Key Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                      TileLang Frontend                        │
│  (Python DSL with decorators like @tilelang.jit)             │
├─────────────────────────────────────────────────────────────┤
│                   Scheduling Space                            │
│  • Thread binding                                            │
│  • Layout annotation (T.annotate_layout)                       │
│  • Tensorization (T.gemm → MMA/MFMA)                         │
│  • Pipeline annotation (T.Pipelined)                         │
├─────────────────────────────────────────────────────────────┤
│                    TVM Backend                              │
│  (Apache TVM compiler infrastructure)                         │
├─────────────────────────────────────────────────────────────┤
│              Target Code Generation                         │
│  • NVIDIA: CUDA/CUTLASS CuTe DSL                            │
│  • AMD: HIP/HIPCC                                           │
│  • Apple: Metal                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Language Primitives

| Primitive | Description | Example |
|-----------|-------------|---------|
| `T.Kernel` | Define kernel launch configuration | `T.Kernel(T.ceildiv(N, block_N), threads=128)` |
| `T.alloc_shared` | Allocate shared memory tile | `A_shared = T.alloc_shared((block_M, block_K), dtype)` |
| `T.alloc_fragment` | Allocate register fragment | `C_local = T.alloc_fragment((block_M, block_N), accum_dtype)` |
| `T.copy` | Memory copy (global ↔ shared ↔ local) | `T.copy(A[by*block_M, ko*block_K], A_shared)` |
| `T.gemm` | Tile-level GEMM (dispatches to MMA/MFMA) | `T.gemm(A_shared, B_shared, C_local)` |
| `T.Pipelined` | Enable multi-stage pipelining | `T.Pipelined(range, num_stages=3)` |
| `T.use_swizzle` | Enable L2 cache swizzling | `T.use_swizzle(panel_size=10, enable=True)` |

### 1.4 Example: Simple GEMM

```python
import tilelang
import tilelang.language as T

@tilelang.jit(target="hip")  # AMD HIP target
def matmul_kernel(
    A, B,
    block_M: int = 64,
    block_N: int = 64,
    block_K: int = 64,
):
    M, N, K = T.const('M, N, K')
    
    # Kernel grid
    with T.Kernel(T.ceildiv(N, block_N), T.ceildiv(M, block_M), threads=128) as (bx, by):
        A_shared = T.alloc_shared((block_M, block_K), T.float16)
        B_shared = T.alloc_shared((block_K, block_N), T.float16)
        C_local = T.alloc_fragment((block_M, block_N), T.float32)
        
        T.clear(C_local)
        
        # Pipelined K-loop
        for ko in T.Pipelined(T.ceildiv(K, block_K), num_stages=3):
            T.copy(A[by * block_M, ko * block_K], A_shared)
            T.copy(B[ko * block_K, bx * block_N], B_shared)
            T.gemm(A_shared, B_shared, C_local)
        
        T.copy(C_local, C[by * block_M, bx * block_N])
    
    return C
```

---

## 2. AMD MI355X Support

### 2.1 MI355X Compatibility Status

**VERIFIED: TileLang has active MI355X support.**

| Feature | Status | PR/Issue |
|---------|--------|----------|
| gfx950 architecture | ✅ Supported | #1878 (merged Feb 25, 2026) |
| MI350/MI355 FP8 | ✅ Supported | #1718 (merged Jan 26, 2026) |
| MI300X (MI300A/X) | ✅ Supported | Base support |
| Async Copy | ✅ Supported | PR #1421+ |
| MFMA instructions | ✅ Supported | #800, #1878 |
| 160KB Shared Memory | ✅ Supported | #1718 |

### 2.2 gfx950-Specific Features

From PR #1718 and #1878, TileLang supports:

- **FP8 E4M3 format**: MI355X uses `__hip_fp8_e4m3` (vs MI300X's `__hip_fp8_e4m3_fnuz`)
- **160KB LDS**: Increased from MI300X's 64KB limit
- **MFMA 16x16x32 BF16/FP16**: Native support for gfx950 matrix instructions
- **Dynamic shared memory**: Runtime query via `hipDeviceAttributeMaxSharedMemoryPerBlock`

### 2.3 Target String for MI355X

```python
# TileLang target specification for MI355X
target = "hip"  # or "hip -mcpu=gfx950"

# Example with specific architecture
@tilelang.jit(target="hip -mcpu=gfx950")
def my_kernel(...):
    ...
```

---

## 3. Comparison with Triton and CK-Tile

### 3.1 Comparison Matrix

| Aspect | TileLang | Triton | CK-Tile |
|--------|-----------|--------|---------|
| **Frontend** | Python DSL | Python DSL | C++ DSL |
| **Backend** | TVM | MLIR/Triton IR | CUTLASS-style |
| **AMD Support** | ✅ Active (gfx950) | ✅ Via ROCm | ✅ Via composable_kernel |
| **Compile Time** | Moderate | Fast | Slow |
| **Auto-Scheduling** | ✅ Layout Inference | ❌ Manual | ⚠️ Partial |
| **Learning Curve** | Low | Medium | High |
| **Debuggability** | ✅ T.print, layout viz | Limited | Difficult |
| **Performance** | SOTA | SOTA | SOTA |
| **Lines for MLA** | ~80 lines | ~200+ lines | ~500+ lines |

### 3.2 Key Differentiators

#### TileLang vs Triton

1. **Scheduling Decoupling**: TileLang explicitly separates scheduling from dataflow
2. **Layout Inference**: Automatic buffer shape/layout inference (Triton requires manual)
3. **Multi-Backend**: Single codebase for CUDA, HIP, Metal
4. **Simpler MLA**: TileLang achieves FlashMLA parity in ~80 lines vs Triton's complexity

#### TileLang vs CK-Tile

1. **Language**: Python vs C++ (huge productivity difference)
2. **Abstraction Level**: Higher-level vs low-level tile control
3. **Compilation**: TVM-based vs header-only C++ templates
4. **Debugging**: Built-in tools vs printf debugging

### 3.3 Performance Comparison (MLA Decoding)

From TileLang's own benchmarks on H100:

| Implementation | Batch 64 Performance | Batch 128 Performance |
|----------------|---------------------|----------------------|
| FlashMLA | Baseline | Baseline |
| TileLang | ✅ Comparable | ✅ Comparable |
| FlashInfer | ~15% slower | ~15% slower |
| Triton | ~20% slower | ~25% slower |

**Key Insight:** TileLang achieves parity with hand-optimized FlashMLA (CUTLASS-based) while requiring significantly less code.

---

## 4. Applicability to Our Kernels

### 4.1 GEMM (Matrix Multiplication)

**Status:** ✅ **FULLY APPLICABLE**

TileLang's core strength is GEMM optimization. Examples exist for:
- Standard FP16/BF16 GEMM
- Mixed-precision GEMM
- Dequantized GEMM (critical for MXFP4)
- Sparse GEMM (2:4 structured sparsity via `T.gemm_sp`)

**MXFP4 Consideration:**
TileLang supports custom data types and dequantization patterns. The dequant_gemm example shows per-thread operation control for bit-level manipulation.

```python
# TileLang MXFP4 GEMM would look like:
@tilelang.jit
def mxfp4_gemm(A_packed, B_packed, scale_a, scale_b):
    # A_packed: [M, K//2] uint8 (2 nibbles per byte)
    # Custom dequantization in shared memory
    # Then T.gemm on dequantized tiles
    ...
```

### 4.2 MoE (Mixture of Experts)

**Status:** ✅ **APPLICABLE**

TileLang has sparse GEMM support (`T.gemm_sp` for 2:4 sparsity from PR #526). For MoE:
- Expert parallelism via kernel grid
- Sparse routing via custom indexing
- Fine-grained control over token routing

**Limitation:** No built-in `fused_moe` equivalent like aiter. Would need custom implementation.

### 4.3 MLA (Multi-Head Latent Attention)

**Status:** ✅ **EXCELLENT SUPPORT**

This is TileLang's showcase feature:
- **DeepSeek MLA example**: Complete implementation in `examples/deepseek_mla/`
- **AMD MI300X support**: PR mentioned "high-performance FlashMLA for AMD MI300X"
- **Performance**: Parity with FlashMLA on H100

**Key Optimizations Used:**
1. Layout Inference for large head dimensions (576 for query/key, 512 for value)
2. Warp Specialization (producer-consumer pattern for TMA)
3. Threadblock Swizzling for L2 locality
4. Shared Memory Swizzling to avoid bank conflicts
5. Split-KV for small batch parallelism

**Code Example (simplified):**
```python
# From TileLang's MLA example (~80 lines total)
with T.Kernel(...) as (bx, by):
    # Q @ K with policy=FullCol splits warpgroups vertically
    acc_s = T.alloc_fragment([block_M, block_N], accum_dtype)
    T.gemm(Q_shared, K_shared, acc_s, policy=FullCol)
    
    # Softmax and P @ V
    ...
```

### 4.4 MLA on MI355X

**Specific Advantages:**
- **160KB LDS**: Allows larger tile sizes for MLA's big head dimensions
- **MFMA 16x16x32**: Efficient for the 576-dim query/key operations
- **FP8 support**: Native support for MI355X FP8 format

---

## 5. Integration Potential

### 5.1 Popcorn CLI Integration

**Feasibility:** ⚠️ **COMPLEX**

TileLang generates kernels via JIT compilation. For Popcorn CLI submission:

1. **Kernel Source Access**: TileLang can emit source code:
   ```python
   kernel = matmul_kernel.compile(...)
   source = kernel.get_kernel_source()
   ```

2. **Compilation Challenge**: The generated code depends on TileLang's runtime. For pure submission.py:
   - Option A: Emit pure HIP code (if possible)
   - Option B: Include minimal TileLang runtime in submission

3. **Runner Compatibility**: Would need to verify if TileLang-generated code works in Popcorn's restricted environment.

### 5.2 Development Workflow

**Recommended Approach:**

1. **Rapid Prototyping**: Use TileLang for quick kernel development
2. **Performance Tuning**: Leverage TileLang's autotuner
3. **Final Export**: Extract optimized HIP/PTX for submission

```python
# Development workflow
import tilelang

# 1. Define kernel
@tilelang.jit(target="hip")
def my_kernel(...):
    ...

# 2. Autotune
tuner = tilelang.autotuner.AutoTuner(my_kernel)
best_config = tuner.tune(search_space)

# 3. Export source
kernel = my_kernel.compile(..., **best_config)
hip_source = kernel.get_kernel_source()

# 4. Integrate into submission.py
```

### 5.3 Alternative: TileLang as Research Tool

Even if direct submission is complex, TileLang can:
- Generate reference implementations for comparison
- Provide layout/scheduling insights
- Serve as a testbed for optimization ideas

---

## 6. Pros and Cons for Competition

### 6.1 Advantages

1. **MI355X Support**: Fresh PR (#1718, #1878) means active gfx950 development
2. **MLA Excellence**: Proven FlashMLA-level performance
3. **Productivity**: Write kernels in days vs weeks
4. **Auto-Scheduling**: Layout inference reduces manual tuning
5. **Debugging**: Built-in tools (T.print, layout plotter)
6. **Python Ecosystem**: Integration with PyTorch, JAX

### 6.2 Disadvantages

1. **Compilation Overhead**: TVM-based compilation adds latency
2. **Runtime Dependency**: May require TileLang runtime in submission
3. **Novelty Risk**: Newer than Triton/CK, less battle-tested
4. **Documentation**: Still maturing vs Triton's extensive docs
5. **Popcorn Compatibility**: Unclear if JIT compilation works in runner

### 6.3 Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Runner incompatibility | HIGH | Test early with minimal example |
| JIT compilation overhead | MEDIUM | Pre-compile and cache |
| FP4/MXFP4 support | MEDIUM | Use custom type definitions |
| Performance regression | LOW | Benchmark against aiter baseline |

---

## 7. Research Conclusions

### 7.1 Verdict: Should We Use TileLang?

**RECOMMENDATION:**

| Use Case | Recommendation |
|----------|---------------|
| **MLA Kernel** | ✅ **Strong Yes** - TileLang's showcase feature, proven MI300X support, ~80 lines vs FlashMLA complexity |
| **GEMM/MXFP4** | ⚠️ **Maybe** - Good for prototyping, but aiter may be simpler for direct MXFP4 support |
| **MoE** | ⚠️ **Maybe** - No built-in fused_moe, would need custom implementation |
| **Research Tool** | ✅ **Yes** - Excellent for exploring optimizations before hand-coding |

### 7.2 Immediate Actions

1. **Test Basic Integration**: Verify TileLang works in Popcorn runner environment
   ```bash
   # Minimal test
   @tilelang.jit(target="hip")
   def test_kernel(x):
       return x * 2
   ```

2. **MLA Benchmark**: Port our MLA implementation to TileLang and compare vs aiter baseline

3. **FP8 Verification**: Test MI355X-specific FP8 support on competition shapes

4. **MXFP4 Exploration**: Investigate if TileLang can handle MXFP4 via custom types

### 7.3 Key Takeaways

1. **TileLang is production-ready** for AMD MI355X (gfx950) with active development
2. **MLA is the sweet spot** - TileLang achieves parity with hand-optimized kernels
3. **Integration complexity** exists but may be worth it for productivity gains
4. **Alternative use**: Even without direct submission, TileLang accelerates research

---

## 8. References

### Official Resources
- GitHub: https://github.com/tile-ai/tilelang
- Documentation: https://tilelang.com/
- Paper: "TileLang: A Composable Tiled Programming Model for AI Systems" (arXiv:2504.17577)

### Relevant PRs
- PR #1718: [AMD] Add MI350/MI355 FP8 support
- PR #1878: [AMD] Fix gfx950 ci and add 16x16x32_bf16/fp16 instructions support
- PR #1743: [AMD] Fix ROCm FP8 dtype selection and MFMA support on gfx942/gfx950

### Examples
- MLA: https://github.com/tile-ai/tilelang/tree/main/examples/deepseek_mla
- GEMM: https://github.com/tile-ai/tilelang/tree/main/examples/gemm
- Flash Attention: https://github.com/tile-ai/tilelang/tree/main/examples/flash_attention

---

## 9. Appendices

### Appendix A: Installation on ROCm

```bash
# From TileLang docs for gfx942/gfx950
pip install tilelang

# Or build from source for development
sudo apt-get install -y python3-setuptools gcc libtinfo-dev \
    zlib1g-dev build-essential cmake libedit-dev libxml2-dev

pip install git+https://github.com/tile-ai/tilelang
```

### Appendix B: TileLang vs Our Current Stack

| Component | Current | With TileLang |
|-----------|---------|---------------|
| Kernel Language | Python + Triton | Python + TileLang |
| Backend | ROCm/HIP via Triton | ROCm/HIP via TVM |
| AMD Support | Triton ROCm (limited) | Native, active development |
| ML Library | torch, aiter | torch, tilelang |
| Debug Workflow | print/trace | T.print, layout viz |

---

*Document Version: 1.0*  
*Last Updated: April 6, 2026*
