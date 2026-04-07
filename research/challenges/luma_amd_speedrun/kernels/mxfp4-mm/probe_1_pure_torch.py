"""
S500 Compliance Probe 1: Pure Torch
Tests if standard torch.matmul is allowed. (Expected: SUCCESS)
"""
#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

import torch
from task import input_t, output_t

def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    # Pure torch.matmul is the most 'blessed' path.
    # We use B as the weight for simplicity.
    return torch.matmul(A, B.T).to(torch.bfloat16)
