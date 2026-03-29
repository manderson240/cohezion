import torch
import aiter
from aiter import QuantType, dtypes
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "staging"))

from reference import ref_kernel, generate_input
from staging.submission_gemm_optimizer import custom_kernel

def test_mismatch(m, n, k, seed):
    print(f"Testing M={m}, N={n}, K={k}, seed={seed}")
    data = generate_input(m, n, k, seed)
    
    # Reference
    ref_out = ref_kernel(data)
    
    # Custom
    custom_out = custom_kernel(data)
    
    # Compare
    diff = (ref_out - custom_out).abs()
    max_diff = diff.max().item()
    mean_diff = diff.mean().item()
    
    print(f"Max diff: {max_diff}")
    print(f"Mean diff: {mean_diff}")
    
    if torch.allclose(ref_out, custom_out, rtol=1e-02, atol=1e-02):
        print("MATCH")
    else:
        print("MISMATCH")

if __name__ == "__main__":
    # Use one of the test cases from task.yml
    # tests:
    #  - {"m": 8, "n": 2112, "k": 7168, "seed": 124}
    test_mismatch(8, 2112, 7168, 124)
