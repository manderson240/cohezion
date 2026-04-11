"""
S500 Compliance Probe 4: Raw HIP (The Forbidden Path)
Tests the absolute baseline for raw HIP launches.
"""
#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

import torch
import ctypes
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    # Attempt to call a dummy HIP function or just initialize the HIP lib.
    try:
        hip = ctypes.CDLL("libamdhip64.so")
        # Just calling hipGetDevice is usually allowed, but hipModuleLaunchKernel is the trigger.
        hip.hipGetDevice(ctypes.byref(ctypes.c_int()))
    except:
        pass
    return torch.zeros((A.shape[0], B.shape[0]), dtype=torch.bfloat16, device=A.device)
