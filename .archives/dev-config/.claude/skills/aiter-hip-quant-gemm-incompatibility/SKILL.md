---
name: aiter-hip-quant-gemm-incompatibility
description: |
  Silent correctness failure when using aiter's per_1x32_f4_quant_hip with gemm_a4w4.
  Use when: (1) considering per_1x32_f4_quant_hip as a faster alternative to
  dynamic_mxfp4_quant, (2) GEMM correctness tests fail with small numerical
  differences (e.g., 165 vs 163), (3) debugging FP4 quantization mismatches on
  AMD MI355X (gfx950).
author: Claude Code (Session 96)
version: 1.0.0
---

# aiter per_1x32_f4_quant_hip + gemm_a4w4 Incompatibility

## Problem

`per_1x32_f4_quant_hip` (HIP C++ quantization kernel) produces FP4 values and E8M0 scales
in a format that is **silently incompatible** with `gemm_a4w4` (CK ASM GEMM kernel).
No exception is raised — the code runs successfully but produces wrong output values.

## Symptoms

- GEMM correctness tests show small numerical differences: `ERROR at (0, 0): 165.0 163.0`
- Errors appear across ALL output positions, not just edge cases
- Both `shuffle=True` and `shuffle=False` produce wrong results
- The `try/except` fallback pattern does NOT catch this — no exception is raised

## Root Cause

The HIP quant kernel (`dynamic_per_group_scaled_quant_fp4` in C++) quantizes BF16→FP4
using a different rounding/packing convention than the Triton `dynamic_mxfp4_quant` kernel.
The ASM GEMM kernel (`f4gemm_bf16_per1x32Fp4_BpreShuffle_*`) expects the Triton format.

## Solution

**ONLY use the Triton quantization path with gemm_a4w4:**

```python
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle

# CORRECT: Triton quant + Triton shuffle
Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
result = aiter.gemm_a4w4(Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True)

# WRONG: HIP quant (silent failure, no exception)
# Aq, Ash = per_1x32_f4_quant_hip(A.contiguous(), shuffle=True)  # PRODUCES WRONG VALUES
# Aq, Asc = per_1x32_f4_quant_hip(A.contiguous(), shuffle=False)  # ALSO WRONG
```

## Verification

Run correctness test: `popcorn submit <file> --mode test --leaderboard amd-mxfp4-mm --no-tui`

With Triton path: `Passed 6/6 tests`
With HIP quant path: `Testing failed — ran successfully but did not pass all tests`

## Context

- Verified on AMD MI355X (gfx950) via Popcorn runner, April 6, 2026
- aiter version on runner: torch 2.10.0+rocm7.1
- The HIP quant kernel may work correctly with OTHER GEMM implementations — this
  incompatibility is specifically with the CK ASM `f4gemm_bf16_per1x32Fp4_BpreShuffle` kernels
