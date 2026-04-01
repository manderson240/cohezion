"""
MXFP4 GEMM with persistent JIT cache.

Set AITER_JIT_DIR to /tmp/aiter_jit_cache to persist compiled kernels
across runs, avoiding repeated JIT compilation.
"""

from __future__ import annotations

import os


# Set JIT cache directory BEFORE importing aiter
os.environ["AITER_JIT_DIR"] = "/tmp/aiter_jit_cache"
os.makedirs("/tmp/aiter_jit_cache", exist_ok=True)

# Enable HIP online tuning
os.environ["HIP_ONLINE_TUNING"] = "1"

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    
    # Quantize A with MXFP4
    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A)
    A_q = x_fp4.view(dtypes.fp4x2)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)
    
    # Use unified gemm_a4w4 API
    return aiter.gemm_a4w4(
        A_q, B_shuffle, A_scale_sh, B_scale_sh,
        dtype=dtypes.bf16, bpreshuffle=True,
    )
