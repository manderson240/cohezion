#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Test: Can torch.mm (BF16) pass the 1% tolerance check?"""

import torch
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    return torch.mm(A, B.t())
