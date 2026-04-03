"""MXFP4 GEMM — Direct Triton tl.dot_scaled for MI355X.

Uses aiter's internal Triton GEMM kernel directly, bypassing the high-level
gemm_a4w4 wrapper that adds dispatch overhead.

Key insight from aiter source: the actual kernel uses
  tl.dot_scaled(a, a_scales, "e2m1", b, b_scales, "e2m1", acc)
which maps to MI355X's native MFMA instruction for MXFP4.

This variant tries calling aiter's Triton FP4 GEMM directly with
pre-shuffled inputs, avoiding the C++ wrapper layer.

Tolerance: rtol=1e-2, atol=1e-2
"""

import os
import sys

os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
os.environ["AITER_GFX950_EXPL_SCHED"] = "1"

import torch
from task import input_t, output_t

# Try importing the Triton GEMM directly
_triton_gemm = None
_triton_gemm_preshuffle = None
_use_triton = False

try:
    from aiter.ops.triton.gemm.basic.gemm_afp4wfp4 import (
        gemm_afp4wfp4_preshuffle,
    )

    _triton_gemm_preshuffle = gemm_afp4wfp4_preshuffle
    _use_triton = True
except ImportError:
    pass

if not _use_triton:
    try:
        from aiter.ops.triton.gemm.basic.gemm_afp4wfp4 import gemm_afp4wfp4

        _triton_gemm = gemm_afp4wfp4
        _use_triton = True
    except ImportError:
        pass

# Fallback imports
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Quantize A
    A_contig = A if A.is_contiguous() else A.contiguous()
    A_q, A_scale_e8m0 = dynamic_mxfp4_quant(A_contig)

    if _triton_gemm_preshuffle is not None:
        # Direct Triton path with pre-shuffled B
        A_scale_sh = e8m0_shuffle(A_scale_e8m0).view(dtypes.fp8_e8m0)
        try:
            return _triton_gemm_preshuffle(
                A_q.view(dtypes.fp4x2),
                B_shuffle,
                A_scale_sh,
                B_scale_sh,
                dtype=dtypes.bf16,
            )
        except Exception:
            pass  # Fall through to ASM path

    if _triton_gemm is not None:
        # Direct Triton path with un-shuffled B
        try:
            return _triton_gemm(
                A_q.view(dtypes.fp4x2),
                B_q,
                A_scale_e8m0,
                B_scale_sh,  # May need un-shuffled scale
                dtype=dtypes.bf16,
            )
        except Exception:
            pass  # Fall through to ASM path

    # Fallback: standard aiter ASM path
    A_scale_sh = e8m0_shuffle(A_scale_e8m0).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        A_q.view(dtypes.fp4x2),
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
