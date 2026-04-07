#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Probe: Read the actual Triton kernel source for E8M0 scale."""

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

    # Find the _triton_kernels source
    base = "/home/runner/aiter/aiter/ops/triton/_triton_kernels/quant"
    for f in sorted(os.listdir(base)):
        print(f"[DIR] {f}")

    # Read the fused_mxfp4_quant kernel
    fpath = os.path.join(base, "fused_mxfp4_quant.py")
    with open(fpath) as f:
        src = f.read()

    print(f"[SRC] Kernel file: {len(src)} chars")

    # Find scale-related patterns
    lines = src.split('\n')
    printed = set()
    for i, line in enumerate(lines):
        lo = line.lower()
        if any(kw in lo for kw in ['shared_exp', 'e8m0', 'biased_exp', 'scale_exp',
                                      'amax', 'max_val', 'block_scale',
                                      'clamp_val', 'fp4_max', 'quant_fp4']):
            start = max(0, i-2)
            end = min(len(lines), i+3)
            for j in range(start, end):
                if j not in printed:
                    printed.add(j)
                    print(f"L{j+1}: {lines[j]}")
            print("---")

    # Do the actual GEMM
    import aiter
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh,
                           dtype=dtypes.bf16, bpreshuffle=True)
