#!/usr/bin/env python3
"""Debug script to capture popcorn-cli benchmark output format."""

import subprocess
from pathlib import Path

POPCORN_CLI = Path.home() / ".local" / "bin" / "popcorn-cli"

# Test with a simple GEMM submission
kernel = "gemm"
leaderboard = "amd-mxfp4-mm"
kernel_dir = Path("/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels/mxfp4-mm")
submission_path = kernel_dir / "submission.py"

if not submission_path.exists():
    print(f"Submission not found: {submission_path}")
    print("Creating a minimal test submission...")
    kernel_dir.mkdir(parents=True, exist_ok=True)
    submission_path.write_text('''
import torch
import triton
import triton.language as tl

def mxfp4_mm(M, N, K, A_vals, A_scales, B_vals, B_scales):
    """Minimal MXFP4 GEMM for testing."""
    # Simple fallback to demonstrate parsing
    A_fp32 = A_vals.float() * A_scales.unsqueeze(-1)
    B_fp32 = B_vals.float() * B_scales.unsqueeze(-1)
    C = torch.matmul(A_fp32, B_fp32.t())
    return C

if __name__ == "__main__":
    # Test shapes
    M, N, K = 64, 64, 64
    A_vals = torch.randint(0, 16, (M, K), dtype=torch.uint8)
    A_scales = torch.ones(M, dtype=torch.float32)
    B_vals = torch.randint(0, 16, (N, K), dtype=torch.uint8)
    B_scales = torch.ones(N, dtype=torch.float32)
    result = mxfp4_mm(M, N, K, A_vals, A_scales, B_vals, B_scales)
    print(f"Result shape: {result.shape}")
''')

cmd = [
    str(POPCORN_CLI),
    "submit",
    "--no-tui",
    "--mode", "benchmark",
    "--gpu", "MI355X",
    "--leaderboard", leaderboard,
    str(submission_path),
]

print(f"Running: {' '.join(cmd)}")
print("=" * 60)

result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

print("STDOUT:")
print(result.stdout)
print("=" * 60)
print("STDERR:")
print(result.stderr)
print("=" * 60)
print(f"Return code: {result.returncode}")
