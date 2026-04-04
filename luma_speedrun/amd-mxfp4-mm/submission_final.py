#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM via aiter gemm_a4w4 - simple working implementation."""

import torch
from aiter import gemm_a4w4
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """GEMM kernel using gemm_a4w4."""
    x_fp4, x_scale, w_fp4, w_scale, q_dtype = data
    return gemm_a4w4(x_fp4, w_fp4.t(), x_scale, w_scale)
