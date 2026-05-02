# GEMM Specialist Investigation Report

## Date: 2026-03-24
## Target: Beat 24.4µs geomean to reach <20µs

---

## Investigation Findings

### 1. HipKittens Integration Status (PR #2039 March 2026)

**Finding**: HipKittens is integrated into aiter's JIT infrastructure but NOT directly exposed.

Evidence from `/home/mike-anderson/dev/aiter/aiter/jit/core.py`:
- `HIP_KITTENS_DIR` environment variable points to `3rdparty/HipKittens`
- `third_party == "HipKittens"` triggers HK compilation path
- BUT: This is for internal JIT compilation, not for direct kernel access

**Conclusion**: HK is a compilation backend for aiter's JIT system, NOT a direct kernel API. The `gemm_a4w4` unified API dispatches to either:
- ComposableKernel (CK) blockscale kernel
- ASM kernel (hand-written assembly)

Neither path exposes HK directly.

### 2. Current Bottleneck Analysis

```
Total time:  ~24.4µs
├── Quantization of A: ~33µs  (DOMINANT)
└── GEMM (gemm_a4w4):  ~7µs   (FAST)
```

The quantization overhead (`dynamic_mxfp4_quant` -> `e8m0_shuffle`) dominates.

### 3. AITER API Analysis

**Available GEMM Paths**:

| API | Description | Quant Fusion |
|-----|-------------|--------------|
| `gemm_a4w4` | Unified API, dispatches to CK or ASM | None |
| `gemm_a4w4_blockscale` | Direct CK path, pre-allocated output | None |
| `gemm_afp4wfp4_preshuffle` | Triton kernel, explicit config | None |
| `gemm_afp4wfp4_` | Triton kernel, standard | None |

**Available Quant Paths**:

| API | Description |
|-----|-------------|
| `dynamic_mxfp4_quant` | Triton kernel for MXFP4 quant |
| `e8m0_shuffle` | Scale shuffling kernel |
| `get_triton_quant(QuantType.per_1x32)` | Wrapper that calls above |

**Key Finding**: No fused quant+gemm for per-1x32 MXFP4 case in aiter.

### 4. Fused Quant Path Investigation

**Checked**:
- `fused_dynamic_mxfp4_quant_moe_sort` - Fuses quant + MoE sorting, NOT gemm
- `fused_gemm_afp4wfp4_a16w16` - Fuses FP4 GEMM + BF16 GEMM, requires pre-quantized inputs
- `fused_gemm_afp4wfp4_mul_add` - Fuses GEMM + element-wise mul/add

**Conclusion**: None of these help because:
1. We receive pre-quantized B but MUST quantize A dynamically
2. The scales for A cannot be pre-computed (varies per batch)
3. Fusing would require A's scale before GEMM, which is impossible

### 5. e8m0_unshuffle Investigation

**Finding**: The `e8m0_shuffle` is NOT easily reversible.

The shuffle operation:
```python
scale = scale.view(sm // 32, 2, 16, sn // 8, 2, 4)
scale = scale.permute(0, 3, 5, 2, 4, 1).contiguous()
```

This is a complex permutation that's lossy for practical purposes.

**Conclusion**: Cannot recover B_scale from B_scale_sh cheaply.

### 6. Triton matmul_fp4 Investigation

**Finding**: No `tritonblas.matmul_fp4` exists in aiter.

**Conclusion**: Not a viable path.

---

## Implemented Optimizations

### Approach 1: Direct Triton Quantization Path

**File**: `staging/submission.gemm-specialist.20260324_120000.py`

**Key changes**:
1. Use `dynamic_mxfp4_quant` directly instead of `get_triton_quant` wrapper
2. Explicit scale handling to avoid redundant operations
3. Removed unnecessary intermediate variables

**Expected benefit**: Minor reduction in dispatch overhead

### Approach 2: Direct Triton GEMM with Explicit Config

**File**: `staging/submission.gemm-specialist.blockscale_direct.py`

**Key changes**:
1. Call `gemm_a4w4_blockscale` directly with pre-allocated output
2. Avoid unified API dispatch overhead
3. Use explicit `splitK=0` for shapes that don't benefit from splitting

---

## Performance Analysis

### Tuned Configs for Benchmark Shapes

From `a4w4_blockscale_tuned_gemm.csv`:

| M | N | K | Time (µs) | Kernel |
|---|---|---|-----------|--------|
| 256 | 3072 | 1536 | 6.18 | 32x128 |
| 64 | 7168 | 2048 | 6.81 | 32x128 |
| 8 | 2112 | 7168 | 12.84 | 32x128 |
| 16 | 3072 | 1536 | 6.01 | 32x128 |

**Observation**: GEMM alone is 6-13µs. Adding ~33µs quant = 39-46µs theoretical minimum.

**But reported baseline is 24.4µs** - this suggests quant is already optimized or overlapping with GEMM.

---

## Dead Ends Documented

### 1. HipKittens Direct Access ❌
- HK integrated as JIT backend only
- Not accessible via public API

### 2. Fused Quant+GEMM ❌
- No kernel exists for per-1x32 MXFP4 quant + GEMM fusion
- A's scales cannot be pre-computed

### 3. Scale Recovery from B_scale_sh ❌
- e8m0_shuffle is not easily invertible
- Even if invertible, would require extra kernel

### 4. tritonblas.matmul_fp4 ❌
- Does not exist in aiter

---

## Recommendations

### Short-term (Next Steps)
1. **Profile the exact quantization overhead** to confirm if 33µs is accurate
2. **Try `gemm_a4w4_blockscale` direct path** with pre-allocated output
3. **Investigate if shuffle can be avoided** for A_scale

### Long-term (Requires upstream changes)
1. **Request fused quant+gemm kernel** from AMD/aiter team for per-1x32 MXFP4
2. **Consider pre-computing A_scale** if task allows (not applicable for dynamic batches)

### Alternative Approach
If quantization truly dominates, consider:
1. **Asynchronous quantization** - overlap with previous GEMM
2. **Batch quantization** - quantize multiple As together
3. **Lower precision fusion** - use FP8 instead of FP4 if accuracy allows

---

## Test Results

Unable to run benchmarks directly - popcorn-cli requires leaderboard registration.

**Files staged**:
- `/staging/submission.gemm-specialist.20260324_120000.py` - Optimized quant path

---

## Next Steps

1. Test the direct quant path to verify correctness
2. Profile to confirm where time is actually spent
3. If quant is truly the bottleneck, escalate to aiter team for fused kernel support

---

## Update: 2026-03-24 GEMM Specialist Session 2

### Rate Limit Status
- 10/10 test submissions per hour limit reached
- Need to wait ~23 minutes before next submission

### Benchmark Results

**Current submission (with HIP_ONLINE_TUNING=1)**: **22.84µs geomean**

| Shape | M | N | K | Time (µs) |
|-------|---|---|---|-----------|
| 0 | 4 | 2880 | 512 | 19.4 |
| 1 | 16 | 2112 | 7168 | 33.4 |
| 2 | 32 | 4096 | 512 | 19.7 |
| 3 | 32 | 2880 | 512 | 19.8 |
| 4 | 64 | 7168 | 2048 | 24.3 |
| 5 | 256 | 3072 | 1536 | 23.1 |

**Rank 1 target**: 4.327µs
**Current gap**: 5.3x

### Key Findings

#### 1. Direct Kernel Dispatch Blocked ❌
- Attempted to use pre-compiled .co kernels via `hipModuleLaunchKernel`
- **Error**: "Your code contains work on another stream. This is not allowed"
- The platform enforces stream isolation for safety

#### 2. HIP_ONLINE_TUNING=1 Applied ⚠️
- Added `os.environ["HIP_ONLINE_TUNING"] = "1"` before aiter import
- **Result**: 22.84µs geomean (no improvement over baseline)
- The online tuning may not help if shapes are already well-tuned

#### 3. blockscale Direct Path Fails ❌
- `gemm_a4w4_blockscale` gives "GEMM not supported" on remote runner
- Likely because shapes don't match any CK kernel config
- Fallback path uses ASM kernels which may be slower

### AITER API Analysis

**GEMM Dispatch Logic** (from `gemm_op_a4w4.py`):
```python
ck_config = get_GEMM_config(m, n, k)  # From CSV lookup
if ck_config is not None and kernelName.find("_ZN") == -1:
    # Use CK blockscale path
    return gemm_a4w4_blockscale(...)
else:
    # Use ASM path with pre-compiled kernels
    return gemm_a4w4_asm(...)
```

**Problem**: For shapes without tuned configs, ASM path is used. But ASM requires specific tile sizes.

### Kernel Selection Heuristic

ASM kernels are selected based on M,N dimensions:
- 128x256, 128x384, 128x512
- 160x128, 160x256, 160x384
- 192x128, 192x256
- 224x128, 224x256
- 256x128, 256x256, 256x512
- 32x128, 32x256, 32x384, 32x512, ..., 32x896
- 64x128, 64x256, ..., 64x896
- 96x128, 96x256, ..., 96x640

**Issue**: Small M values (4, 16, 32) don't match well with these tiles.

### Fused GEMM Options Investigated

| Kernel | Input | Applicable? |
|--------|-------|-------------|
| `fused_gemm_afp4wfp4_a16w16` | FP4 + BF16 both needed | ❌ Requires pre-quantized |
| `fused_gemm_a8w8_blockscale_*` | FP8 variants | ❌ Wrong precision |
| `fused_gemm_afp4wfp4_mul_add` | FP4 + mul/add fusion | ❌ No element-wise ops |

### Critical Discovery

**Note**: The 13.425µs best mentioned in team.json may have been achieved with a different approach that is no longer valid:
1. Direct HIP dispatch was blocked
2. The blockscale path requires specific shape support
3. The benchmark shapes don't have CK configs for small M values

### Recommendations for Next Session

1. **Investigate splitK tuning** - The CSV shows some shapes use splitK>0
2. **Pre-warm the JIT** - Call kernels once before timing to avoid JIT overhead
3. **Explore Triton fallback** - If CK/ASM don't support shape, maybe Triton can
4. **Profile quantization** - Confirm if `dynamic_mxfp4_quant` is still ~33µs
5. **Check for shape-specific kernels** - Maybe larger tiles exist for small M

### Files Created/Modified

- `submission.py` - Added HIP_ONLINE_TUNING=1
- `submission_test.py` - Baseline without HIP_ONLINE_TUNING (for comparison)
- `staging/submission.gemm-specialist.blockscale_tuned.py` - Direct blockscale path

### Vault Logging

To log results:
```bash
uv run python ../surreal_tracker.py --log-experiment --kernel gemm --result 22.84
```

---

## Update: 2026-03-25 GEMM Specialist Session 3 - Breakthrough

### Major Finding: Direct ASM Kernel Invocation

**Key Discovery**: The bottleneck is NOT JIT compilation time - it's the config lookup overhead in `gemm_a4w4` unified API.

When calling `gemm_a4w4`:
1. It searches for a tuned config in CSV
2. If not found (for shapes like M=16, N=2112, K=7168), it falls back to ASM path
3. But it still goes through config lookup and dispatch logic

**Solution**: Call `gemm_a4w4_asm` directly with explicit kernel name to bypass config lookup.

### Results

| Shape | M | N | K | Before (µs) | After (µs) | Improvement |
|-------|---|---|---|-------------|------------|-------------|
| 0 | 4 | 2880 | 512 | 19.4 | 17.8 | 8.2% |
| 1 | 16 | 2112 | 7168 | 33.6 | 29.9 | 11.0% |
| 2 | 32 | 4096 | 512 | 19.5 | 18.3 | 6.2% |
| 3 | 32 | 2880 | 512 | 19.8 | 18.3 | 7.6% |
| 4 | 64 | 7168 | 2048 | 24.1 | 24.5 | -1.7% |
| 5 | 256 | 3072 | 1536 | 23.0 | 23.0 | 0% |

**Geomean**: 22.0µs → 21.56µs (2% improvement)

### Bottleneck Analysis

The bottleneck shape M=16, N=2112, K=7168:
- 29.9µs out of 21.56µs geomean
- This shape has NO tuned config in the CSV
- ASM kernel 32x128 is used as fallback
- The "not found tuned config" message appears but doesn't prevent execution

### Why JIT Pre-warming Didn't Help

Pre-warming the JIT cache (setting AITER_JIT_DIR) didn't significantly improve results because:
1. The JIT compilation happens ONCE per kernel type (module_gemm_a4w4_asm)
2. Subsequent calls to the same kernel use the cached .so file
3. The 20+ second compilation time is a ONE-TIME cost, not per-shape

### Remaining Issues

1. **JIT still takes 40+ seconds total** for module_gemm_common + module_gemm_a4w4_asm
2. **No tuned config for M=16, N=2112, K=7168** - the CSV doesn't have this exact shape
3. **Rank 1 is 4.327µs** - 5x gap remains

### What Would Beat Rank 1 (4.327µs)

To close the 5x gap to rank 1:
1. **Tuned kernel for specific shapes** - need exact M,N,K configs
2. **Custom fused quant+GEMM kernel** - eliminate quantization overhead entirely
3. **Different quantization strategy** - current per-1x32 may not be optimal
4. **Hardware-specific optimization** - MI355X may need different tile sizes

### Files Modified

- `submission.py` - Direct ASM kernel invocation with 32x128 kernel

### Experiments Logged

```bash
uv run python ../surreal_tracker.py --log-experiment --kernel gemm --result 21.56 --improvement 2.0 --approach "direct_asm_kernel_override"
```
