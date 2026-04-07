"""
S500 Compliance Probe 3: aiter Wrapper
Tests if the high-level aiter.gemm_a4w4 is allowed.
"""
#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

import torch
import aiter
from task import input_t, output_t

def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    # The official reference path.
    # Many of our previous attempts used this and failed with S500.
    return aiter.gemm_a4w4(B_q, B_shuffle, B_scale_sh, B_scale_sh, dtype=torch.bfloat16, bpreshuffle=True)
