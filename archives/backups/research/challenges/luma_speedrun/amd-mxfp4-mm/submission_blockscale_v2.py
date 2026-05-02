#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM: Try gemm_a4w4_blockscale API (discovered via probe, 1471-row tuning CSV)."""

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Quantize A
    A_q, A_scale = dynamic_mxfp4_quant(A.contiguous())
    A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
    A_q_fp4 = A_q.view(dtypes.fp4x2)

    # gemm_a4w4_blockscale(XQ, WQ, x_scale, w_scale, Out, splitK=0)
    # Requires pre-allocated output and uses tuned CK kernels from CSV
    try:
        Out = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
        result = aiter.gemm_a4w4_blockscale(
            A_q_fp4,
            B_shuffle,
            A_scale_sh,
            B_scale_sh,
            Out,
            0,  # splitK=0 (default from tuning CSV)
        )
        return result
    except Exception as e:
        print(f"[blockscale] Failed: {e}")

    # Fallback to standard gemm_a4w4
    return aiter.gemm_a4w4(
        A_q_fp4,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
