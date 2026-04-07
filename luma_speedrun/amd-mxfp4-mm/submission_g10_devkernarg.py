#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""G10: HIP_FORCE_DEV_KERNARG=1 on aiter GEMM baseline.

This env var forces device-side kernel argument passing, saving ~6µs per launch
for split-K kernels. Even non-split kernels may benefit from faster arg transfer.
Source: ROCm Flash Decoding blog.

Combined with pre-resolved function references for minimal Python overhead.
"""

import os
os.environ["HIP_FORCE_DEV_KERNARG"] = "1"

import torch
from aiter import dtypes
import aiter
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

# Pre-resolve all function references
_gemm = aiter.gemm_a4w4
_quant = dynamic_mxfp4_quant
_shuffle = e8m0_shuffle
_fp4x2 = dtypes.fp4x2
_fp8_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    Aq, Asc = _quant(A.contiguous())
    Ash = _shuffle(Asc).view(_fp8_e8m0)
    return _gemm(Aq.view(_fp4x2), B_shuffle, Ash, B_scale_sh,
                 dtype=_bf16, bpreshuffle=True)
