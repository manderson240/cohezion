# Leader Analysis: AMD MXFP4-MM Competition

**Date:** 2026-04-05
**Target:** Beat 4.35µs geomean (bhagawan-yantrion, Rank 1)
**Our best:** ~22.8µs geomean
**Gap:** 5.3x

---

## Competition Benchmark Shapes

From `task.yml`:

| M | N | K | Aiter baseline (us) |
|---|---|---|---------------------|
| 4 | 2880 | 512 | 8.198 |
| 16 | 2112 | 7168 | 20.873 |
| 32 | 4096 | 512 | 9.462 |
| 32 | 2880 | 512 | 9.173 |
| 64 | 7168 | 2048 | 12.738 |
| 256 | 3072 | 1536 | 12.219 |

**Aiter geomean: ~11.5µs**
**Leader target: 4.35µs**

---

## Tuning CSV Analysis (a4w4_blockscale_tuned_gemm.csv)

### Which competition shapes have tuned configs?

| Shape | Tuned? | GEMM-only time (us) | Best kernel |
|-------|--------|---------------------|-------------|
| M=4, N=2880, K=512 | NO | (no entry) | Falls back to ASM |
| M=16, N=2112, K=7168 | NO | (no entry) | Falls back to ASM 32x128 at 12.3us |
| M=32, N=4096, K=512 | NO | (no entry) | Falls back to ASM |
| M=32, N=2880, K=512 | NO | (no entry) | Falls back to ASM |
| M=64, N=7168, K=2048 | YES | 6.8112 | 32x128 ASM |
| M=256, N=3072, K=1536 | YES | 6.1771 | 32x128 ASM |

**Key finding: 4 out of 6 benchmark shapes have NO tuned CK config and fall back to the
ASM 32x128 default kernel, often with suboptimal tile matching.**

### Why Small M Shapes Are Slow

The smallest ASM tile is 32x128 (tile_M=32, tile_N=128). For M=4 or M=16:
- A 32-row tile processes only 4 or 16 actual rows
- The remaining 28 or 16 rows are wasted compute (padding)
- GPU occupancy is low: very few tiles fit the 256 CUs

For M=4, N=2880, K=512:
- Nearest available tile: 32x512 or 32x256
- Using 32x512: ceil(4/32) * ceil(2880/512) = 1 * 6 = 6 tiles for 256 CUs = 0.023 tiles/CU
- Massive underutilization

### What the Tuned CSV Reveals

The 32x128 ASM kernel (`_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E`) achieves:
- 5.7-6.5µs for small M shapes (M=1-256) across many N/K combinations
- This is the GEMM-only time, EXCLUDING quantization of A

The baseline "aiter performance" numbers (8-20µs) include quantization overhead of ~2-15µs.

---

## ASM Kernel CSV Analysis (gfx950/f4gemm/f4gemm_bf16_per1x32Fp4.csv)

### All available pre-compiled kernels

Tile variants (bpreshuffle=1, splitK=0 unless noted):
- Small M: 32xN (N: 128, 256, 384, 512, 640, 768, 896, 1024)
- Medium M: 64xN (N: 128-1024), 96xN (N: 128-640)
- Large M: 128xN, 160xN, 192xN, 224xN, 256xN
- Special: 128x512 with splitK=1, 256x256 with splitK=1

### SplitK=0 Meaning

The leader's file `v78_splitk0.py` means `log2_k_split=0` which equals NO K-splitting.

In `gemm_op_a4w4.py`:
```python
log2_k_split=splitK  # 0 = no split, 1 = 2 pieces, 2 = 4 pieces, 3 = 8 pieces
```

The `compute_gemm_SplitK` function (hardcoded to return 3 in current code) calculates
whether K-splitting would improve GPU utilization. However:

- For small M shapes (4, 16, 32) with small K (512), K-splitting wastes atomic overhead
- `splitK0` = the leader explicitly avoids K-splitting
- The CSV shows only 2 kernels use `splitK=1`: 128x512 and 256x256 for large-K shapes

**Conclusion: For the competition's small-M, small-K shapes, log2_k_split=0 is correct.**

---

## Dispatch Path Analysis (gemm_op_a4w4.py)

```
gemm_a4w4(A, B, A_scale, B_scale)
  → get_GEMM_config(m, n, k)  [CSV lookup with M-padding fallback]
    → if found and kernelName has no "_ZN": use gemm_a4w4_blockscale (CK path)
    → else: use gemm_a4w4_asm with explicit kernelName
```

### Two dispatch paths

**CK blockscale path** (`gemm_a4w4_blockscale`):
- Used for: shapes in tuned CSV with kernelName NOT starting with `_ZN`
- These are the CK C++ template kernels compiled at JIT time
- kernelId 0-19 in `gemm_a4w4_blockscale_common.py` (CK instances)
- Shapes like M=256, N=4096, K=512 might hit this path

**ASM path** (`gemm_a4w4_asm`):
- Used for: shapes with kernelName starting with `_ZN` (mangled C++ ASM kernel names)
- Pre-compiled `.co` files in `/home/mike-anderson/dev/aiter/hsa/gfx950/f4gemm/`
- These are the 35 ASM kernels in the CSV
- Most small-M shapes hit this path

### The "splitK=3" hardcode bug

In `gemm_op_a4w4.py` line 30:
```python
# return min(splitK, 4)
return 3
```
The function `compute_gemm_SplitK` is hardcoded to return `3` (log2_k_split=3 = 8-way split).
This means for shapes NOT in the tuned CSV, the fallback uses 8-way K-splitting regardless
of whether it's beneficial. **This is almost certainly wrong for small K shapes (K=512).**

For M=4, N=2880, K=512 with log2_k_split=3:
- K is split into 8 pieces of 64 each
- Each piece is 64 elements (2 scale groups)
- Atomic reduction overhead may dominate the computation

---

## Quantization Path Analysis

### Three quantization APIs

| API | Backend | shuffle_scale support | Notes |
|-----|---------|----------------------|-------|
| `dynamic_mxfp4_quant` (Triton) | Triton kernel | No | Returns raw scales, must call e8m0_shuffle separately |
| `per_1x32_f4_quant_hip` | HIP C++ kernel | Yes (shuffle_scale=True) | Single call with shuffle |
| `get_triton_quant(QuantType.per_1x32)` | Wrapper | Yes (shuffle param) | Calls Triton internally |

**The `per_1x32_f4_quant_hip` function calls `dynamic_per_group_scaled_quant_fp4` which is a
compiled HIP C++ kernel (not Triton). It can do shuffle in a single pass.**

This may be faster than `dynamic_mxfp4_quant` + `e8m0_shuffle` (two Triton kernel launches).

---

## Undiscovered/Underused APIs

### 1. `per_1x32_f4_quant_hip` with shuffle=True

```python
from aiter.ops.quant import per_1x32_f4_quant_hip
A_q, A_scale_sh = per_1x32_f4_quant_hip(A, shuffle=True)
```

This is a HIP kernel (not Triton) that quantizes AND shuffles scales in one call.
**Untested in our submissions.** May reduce A quantization overhead.

### 2. Explicit `log2_k_split=0` bypass

The `gemm_a4w4_asm` function accepts `log2_k_split` directly. Calling it with `log2_k_split=0`
explicitly bypasses the broken `compute_gemm_SplitK` that returns 3 hardcoded.

For small K shapes, this eliminates atomic reduction overhead.

### 3. Pre-warmed `gemm_a4w4_blockscale` with correct kernelId

For shapes with tuned CK configs, calling `gemm_a4w4_blockscale(x, w, xs, ws, out, splitK=0)`
directly with a pre-allocated output skips all config lookup.

### 4. `gemm_a4w4_blockscale_tune` with explicit kernelId

```python
from aiter.ops.gemm_op_a4w4 import gemm_a4w4_blockscale_tune
# kernelId 21 = a4w4_blockscale_256x32x128x128 (the 32x128 CK instance)
gemm_a4w4_blockscale_tune(x, w, xs, ws, out, kernelId=21, splitK=0)
```

Bypasses dispatch and CSV lookup entirely.

---

## What the Leader (4.35µs) Is Likely Doing

### Hypothesis: Fused quantization inside a custom kernel

Given the gap (5.3x from 22.8µs), no amount of Python dispatch optimization closes this.
The only path to 4.35µs is eliminating quantization latency entirely.

**Theory 1: load_inline kernel with fused BF16→FP4 quantize + GEMM**

A custom HIP C++ kernel via `load_inline` that:
1. Reads BF16 A tiles into registers/LDS
2. Quantizes to FP4 with E8M0 scales on-the-fly (no separate kernel launch)
3. Multiplies against pre-quantized B
4. Writes BF16 output

This matches the "v78" naming (extensive iteration) and "splitk0" (explicit no-split).

**Theory 2: Using rocWMMA MFMA instructions with FP4 natively**

The MI355X has native FP4 matrix multiply acceleration (WMMA fp4 ops). A load_inline kernel
using `__builtin_amdgcn_mfma_f32_32x32x64_fp8_fp8` equivalent for FP4 with inline
quantization could achieve ~4µs for these small M shapes.

**Theory 3: Extreme precomputation**

All 6 benchmark shapes could be individually tuned with specialized kernels. `v78` = 78
iterations of tuning. The leader may have a dispatch table with hand-tuned kernel configs
per exact shape.

### Why the file is named `v78_splitk0.py`

- `v78`: 78 iterations/versions — confirms massive automated iteration (like josusanmartin's 5,202 submissions)
- `splitk0`: Explicitly passing `log2_k_split=0` to the kernel

This naming pattern strongly suggests they found the optimal config is always splitK=0
for these shapes and that was their major optimization finding after ~78 tries.

---

## Concrete New Approach: load_inline with Fused Quantize+GEMM

### Why this is the only path

From the tuned CSV, the GEMM-only times are 5.7-6.8µs. Adding any separate quantization
kernel (even 1-2µs) puts us above 7µs total. The leader is at 4.35µs geomean.

The math requires the quantization to be essentially free, meaning it must be fused INTO
the GEMM kernel itself.

### Implementation sketch

```cpp
// load_inline HIP C++ kernel
// For each output tile (m_tile, n_tile):
//   For each K block of 32:
//     1. Load 32 BF16 A values for m_tile rows
//     2. Find max abs -> compute E8M0 scale
//     3. Quantize to FP4 nibbles
//     4. Load pre-quantized B (already shuffled, no quantization needed)
//     5. MFMA accumulate
//   Write BF16 output
```

Key constraint: B is already quantized and shuffled (given as `B_shuffle` input).
Only A needs quantization. Fusing this into a single kernel eliminates:
- Separate Triton quantization launch (~2-5µs)
- `e8m0_shuffle` kernel launch (~1-2µs)
- Memory round-trip for A_q and A_scale tensors

### Recommended tile configuration for small M shapes

For M=4, N=2880, K=512 (the worst shape currently at 8.2µs):

```
BLOCK_M = 4 (exact M, no padding)
BLOCK_N = 128 (matches 32x128 ASM tile N)  
BLOCK_K = 512 (entire K in one block = no outer loop)
```

With K=512, a single K-block covers everything. The scale computation is:
- 512/32 = 16 scale groups per row
- 4 rows × 16 groups = 64 scale values computed inline

This entire computation can fit in one wavefront.

---

## Recommended Submission Pipeline

### Step 1: Quick win - fix the splitK=3 hardcode

Replace current `gemm_a4w4` call with explicit `gemm_a4w4_asm` calls:
- Use `log2_k_split=0` for all shapes (confirmed optimal by leader's filename)
- Use shape-specific kernel names from the ASM CSV
- Expected improvement: eliminate atomic overhead for K=512 shapes (~2-3µs)

Target file: `submission_splitk0_explicit.py`

```python
# Shape-specific dispatch table with splitK=0 everywhere
SHAPE_TO_KERNEL = {
    (4, 2880, 512): ("_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x512E", 0),
    (16, 2112, 7168): ("_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E", 0),
    (32, 4096, 512): ("_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_64x512E", 0),
    (32, 2880, 512): ("_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x512E", 0),
    (64, 7168, 2048): ("_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_64x128E", 0),
    (256, 3072, 1536): ("_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E", 0),
}
```

### Step 2: Try HIP quant path

Replace `dynamic_mxfp4_quant` + `e8m0_shuffle` with `per_1x32_f4_quant_hip(A, shuffle=True)`.
This is a single HIP kernel call vs two Triton kernel launches.

### Step 3: load_inline fused kernel (the real breakthrough)

Build a HIP C++ kernel via `load_inline` that:
1. Takes BF16 A, uint8 B_shuffle, uint8 B_scale_sh
2. Quantizes A inline (BF16 → FP4 + E8M0 scale)
3. Performs MFMA GEMM with pre-quantized B
4. Writes BF16 output

This eliminates the quantization launch entirely and matches what the leader is doing.

---

## Summary Table

| Finding | Impact | Action |
|---------|--------|--------|
| 4/6 shapes have no tuned CK config | Missing optimal kernel selection | Add shape-specific dispatch |
| `compute_gemm_SplitK` hardcoded to 3 | Wrong for small K shapes | Force log2_k_split=0 |
| 32x128 is default tile for all small M | Severe underutilization for M=4,16 | Try smaller tiles or fused kernel |
| `per_1x32_f4_quant_hip` is HIP (not Triton) | Potentially faster than 2-kernel Triton path | Test this API |
| Leader uses `splitk0` explicitly | Confirms optimal config | Match this in all submissions |
| Leader at 4.35µs requires fused quant | No separate quant launch possible | Must use load_inline fused kernel |

---

## Files Referenced

- `/home/mike-anderson/dev/aiter/aiter/ops/gemm_op_a4w4.py` — dispatch logic, splitK hardcode
- `/home/mike-anderson/dev/aiter/hsa/gfx950/f4gemm/f4gemm_bf16_per1x32Fp4.csv` — all 35 ASM kernels
- `/home/mike-anderson/dev/aiter/aiter/configs/a4w4_blockscale_tuned_gemm.csv` — CK tuned configs
- `/home/mike-anderson/dev/aiter/csrc/ck_gemm_a4w4_blockscale/gemm_a4w4_blockscale_common.py` — 20 CK kernel instances
- `/home/mike-anderson/dev/aiter/aiter/ops/quant.py` — `per_1x32_f4_quant_hip` HIP quant API
- `/home/mike-anderson/dev/reference-kernels/problems/amd_202602/mxfp4-mm/task.yml` — benchmark shapes
