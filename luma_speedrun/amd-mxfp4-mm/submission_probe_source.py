#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Probe: Read aiter's quant source code from runner filesystem."""

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

    # Find and read the quant source
    import aiter.ops.triton.quant as qmod
    qfile = qmod.__file__
    print(f"[SRC] quant module: {qfile}")

    # Read the __init__.py
    try:
        with open(qfile) as f:
            src = f.read()
        # Print the relevant function (first 4000 chars)
        print(f"[SRC] File length: {len(src)}")
        # Find dynamic_mxfp4_quant definition
        idx = src.find("def dynamic_mxfp4_quant")
        if idx >= 0:
            print(f"[SRC] dynamic_mxfp4_quant found at offset {idx}:")
            print(src[idx:idx+3000])
        else:
            print("[SRC] Function not found, printing first 3000 chars:")
            print(src[:3000])
    except Exception as e:
        print(f"[SRC] Error reading: {e}")

    # Also check for Triton kernel files
    quant_dir = os.path.dirname(qfile)
    print(f"[SRC] Files in {quant_dir}:")
    for f in sorted(os.listdir(quant_dir)):
        print(f"  {f}")

    # Read any .py files that might contain the kernel
    for fname in sorted(os.listdir(quant_dir)):
        if fname.endswith('.py') and fname != '__init__.py':
            fpath = os.path.join(quant_dir, fname)
            try:
                with open(fpath) as f:
                    content = f.read()
                if 'mxfp4' in content.lower() or 'e8m0' in content.lower() or 'fp4' in content.lower():
                    print(f"\n[SRC] {fname} ({len(content)} chars):")
                    print(content[:3000])
            except Exception as e:
                print(f"[SRC] Error reading {fname}: {e}")

    # Do the actual GEMM
    import aiter
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh,
                           dtype=dtypes.bf16, bpreshuffle=True)
