#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM: Try gemm_a4w4_asm with explicit kernel selection and log2_k_split."""

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

    A_q, A_scale = dynamic_mxfp4_quant(A.contiguous())
    A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
    A_q_fp4 = A_q.view(dtypes.fp4x2)

    # Pre-allocate output
    out = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    # Try gemm_a4w4_asm with auto kernel selection
    try:
        # Get padded M for kernel selection
        padded_m = aiter.get_padded_m(M, N, K, 1)
        kernel_name = f"_ZN5aiter{len(f'f4gemm_bf16_per1x32Fp4_BpreShuffle_{padded_m}x128')}f4gemm_bf16_per1x32Fp4_BpreShuffle_{padded_m}x128E"

        result = aiter.gemm_a4w4_asm(
            A_q_fp4,
            B_shuffle,
            A_scale_sh,
            B_scale_sh,
            out,
            kernel_name,
            bpreshuffle=True,
        )
        return result
    except Exception as e:
        print(f"[asm_tuned] Failed: {e}")

    # Fallback to standard gemm_a4w4
    return aiter.gemm_a4w4(
        A_q_fp4,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
