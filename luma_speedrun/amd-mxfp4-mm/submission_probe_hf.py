#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Probe: Check if hf-rocm-kernels or hipBLASLt are available on runner."""

import torch
from aiter import dtypes
import aiter
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Probe available libraries
    try:
        import hf_rocm_kernels
        print(f"[PROBE] hf_rocm_kernels available: {dir(hf_rocm_kernels)[:200]}")
    except ImportError:
        print("[PROBE] hf_rocm_kernels NOT available")

    try:
        import hipblas
        print(f"[PROBE] hipblas available")
    except ImportError:
        print("[PROBE] hipblas NOT available")

    try:
        import hipblaslt
        print(f"[PROBE] hipblaslt available")
    except ImportError:
        print("[PROBE] hipblaslt NOT available")

    try:
        from torch._C import _hipblaslt
        print(f"[PROBE] torch._C._hipblaslt available")
    except (ImportError, AttributeError):
        print("[PROBE] torch._C._hipblaslt NOT available")

    # Check for Triton dot_scaled
    try:
        import triton
        import triton.language as tl
        print(f"[PROBE] triton version: {triton.__version__}")
        # Check if tl.dot_scaled exists
        if hasattr(tl, 'dot_scaled'):
            print("[PROBE] tl.dot_scaled AVAILABLE")
        else:
            print("[PROBE] tl.dot_scaled NOT available")
    except ImportError:
        print("[PROBE] triton NOT available")

    # Check aiter for any alternative GEMM APIs
    gemm_funcs = [x for x in dir(aiter) if 'gemm' in x.lower() or 'mm' in x.lower()]
    print(f"[PROBE] aiter GEMM functions: {gemm_funcs}")

    # Do actual GEMM
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh,
        dtype=dtypes.bf16, bpreshuffle=True,
    )
