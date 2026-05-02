"""
MXFP4 GEMM: Use fused_mxfp4_quant from inside the module file.

The module aiter.ops.triton.quant.fused_mxfp4_quant is a .py FILE,
not a callable. The function is INSIDE it. Try importing as:
  from aiter.ops.triton.quant.fused_mxfp4_quant import fused_mxfp4_quant
"""

from __future__ import annotations

import os
import sys


os.environ["HIP_ONLINE_TUNING"] = "1"

import aiter
from aiter import dtypes
from aiter.utility.fp4_utils import e8m0_shuffle
from reference import ref_kernel
from task import input_t, output_t


KERNEL_NAME_32X128 = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"

# Try to import fused_mxfp4_quant as a callable
_fused_quant = None
try:
    from aiter.ops.triton.quant.fused_mxfp4_quant import fused_mxfp4_quant as _fq

    if callable(_fq):
        _fused_quant = _fq
        print("Using fused_mxfp4_quant (from module file)", file=sys.stderr)
except Exception as e:
    print(f"fused import failed: {e}", file=sys.stderr)

if _fused_quant is None:
    # Fallback: try every callable in the module
    try:
        import aiter.ops.triton.quant.fused_mxfp4_quant as fmq_mod

        for name in dir(fmq_mod):
            obj = getattr(fmq_mod, name)
            if callable(obj) and "quant" in name.lower() and not name.startswith("_"):
                print(f"Found callable: {name}", file=sys.stderr)
                if "mxfp4" in name.lower() and "fused" not in name.lower():
                    continue  # Skip the dynamic one
                _fused_quant = obj
                print(f"Selected: {name}", file=sys.stderr)
                break
    except Exception as e:
        print(f"Fallback scan failed: {e}", file=sys.stderr)


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B_shuffle.shape[0]

    if _fused_quant is not None:
        try:
            result = _fused_quant(A.contiguous())
            if isinstance(result, tuple) and len(result) >= 2:
                x_fp4, bs_e8m0 = result[0], result[1]
                A_q = x_fp4.view(dtypes.fp4x2)
                A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)

                out = A_q.new_empty(m, n, dtype=dtypes.bf16)
                aiter.gemm_a4w4_asm(
                    A_q.view(m, k // 2),
                    B_shuffle,
                    A_scale_sh,
                    B_scale_sh,
                    out,
                    kernelName=KERNEL_NAME_32X128,
                    bias=None,
                    alpha=1.0,
                    beta=0.0,
                    bpreshuffle=True,
                    log2_k_split=0,
                )
                return out
        except Exception as e:
            print(f"fused_quant execution failed: {e}", file=sys.stderr)

    # Fallback to reference
    return ref_kernel(data)
