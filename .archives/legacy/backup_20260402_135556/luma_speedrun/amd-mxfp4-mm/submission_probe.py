"""Probe: list f4gemm kernels + check for bf16-input paths."""

import os
import glob
import sys

import torch
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

# Probe: list all available f4gemm kernels
_cos = sorted(glob.glob("/home/runner/aiter/hsa/gfx950/f4gemm/*.co"))
for co in _cos:
    print(f"KERNEL: {os.path.basename(co)}")

# Check if there's a gemm that takes bf16 A directly
print(f"\naiter dir: {[x for x in dir(aiter) if 'gemm' in x.lower()]}")

# Check deepgemm_ck
try:
    from aiter import deepgemm_ck

    print(f"deepgemm_ck available: {dir(deepgemm_ck)}")
except ImportError:
    print("deepgemm_ck not available")

# Check hipblaslt
try:
    from aiter import hipblaslt_gemm

    print(f"hipblaslt_gemm available")
except (ImportError, AttributeError):
    print("hipblaslt_gemm not available")

# Check for blockscale gemm
try:
    from aiter import gemm_a4w4_blockscale

    print(f"gemm_a4w4_blockscale available")
except (ImportError, AttributeError):
    print("gemm_a4w4_blockscale not available")


@torch.no_grad()
def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    A_q, A_scale = dynamic_mxfp4_quant(A)
    A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)
    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
