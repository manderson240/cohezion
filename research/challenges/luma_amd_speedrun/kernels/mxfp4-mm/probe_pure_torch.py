"""
Runner Probe: Testing Pure PyTorch and Basic Triton Path

Only perform a pure PyTorch operation to see if the S500 is triggered by 
ANY custom kernel or ONLY by specific aiter/HIP calls.
"""
#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

import torch
from task import input_t, output_t

def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B_shuffle.shape[0]
    
    # Pure PyTorch paths
    # Test 1: Simple Allocation and Addition
    out = torch.zeros((m, n), dtype=torch.bfloat16, device=A.device)
    out = out + 1.0
    
    # Test 2: Matrix Multiplication using PyTorch (which uses rocBLAS internally)
    # This will prove if THE RUNNER allows managed rocBLAS calls.
    # We use a tiny slice to keep it fast.
    A_tiny = A[:2, :2]
    B_tiny = B[:2, :2].T # Just to match shapes
    _ = torch.matmul(A_tiny, B_tiny)
    
    return out
