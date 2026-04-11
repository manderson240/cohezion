#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM: Try per_1x32_f4_quant_hip for faster A quantization."""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"

import torch
import aiter
from aiter import dtypes
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Try HIP-native FP4 quantization (might be faster than Triton)
    try:
        A_fp4, A_scale = aiter.per_1x32_f4_quant_hip(A.contiguous())
        # Try using scale directly (hip quant may already produce shuffled format)
        A_scale_sh = A_scale.view(dtypes.fp8_e8m0)
        A_fp4_view = A_fp4.view(dtypes.fp4x2)
        print(f"[hip_quant] SUCCESS (no shuffle): A_fp4={A_fp4.shape} A_scale={A_scale.shape}")
    except Exception as e:
        print(f"[hip_quant] Failed: {e}, falling back to Triton")
        from aiter.ops.triton.quant import dynamic_mxfp4_quant

        A_fp4, A_scale = dynamic_mxfp4_quant(A.contiguous())
        A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
        A_fp4_view = A_fp4.view(dtypes.fp4x2)

    return aiter.gemm_a4w4(
        A_fp4_view,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
