"""
MXFP4 GEMM using reference approach with get_triton_quant(QuantType.per_1x32).

Based on: reference.py
Key insight: Use QuantType.per_1x32 quantization matching the reference.
"""

from __future__ import annotations

import os


os.environ["HIP_ONLINE_TUNING"] = "1"

import aiter
from aiter import QuantType, dtypes
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    A = A.contiguous()
    B = B.contiguous()
    m, k = A.shape
    n, _ = B.shape

    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale_sh = quant_func(A, shuffle=True)

    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
