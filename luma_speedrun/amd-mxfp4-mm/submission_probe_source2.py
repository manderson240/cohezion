#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Probe: Read the E8M0 scale computation from aiter's Triton kernel."""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Read fused_mxfp4_quant.py and find the scale computation
    fpath = "/home/runner/aiter/aiter/ops/triton/quant/fused_mxfp4_quant.py"
    with open(fpath) as f:
        src = f.read()

    # Search for scale-related code
    lines = src.split("\n")
    for i, line in enumerate(lines):
        lo = line.lower()
        if any(
            kw in lo
            for kw in [
                "e8m0",
                "scale",
                "shared_exp",
                "amax",
                "clamp",
                "log2",
                "biased",
                "floor",
                "ceil",
                "ilogb",
                "frexp",
                "max_norm",
                "fp4",
                "clz",
                "lzcnt",
            ]
        ):
            # Print context: 2 lines before, the line, 2 lines after
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            for j in range(start, end):
                print(f"L{j + 1}: {lines[j]}")
            print("---")

    # Do the actual GEMM
    import aiter

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
    )
