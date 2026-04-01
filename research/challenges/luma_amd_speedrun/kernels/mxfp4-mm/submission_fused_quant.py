"""
MXFP4 GEMM with fused_mxfp4_quant (discovered via probe).

Tests whether fused_mxfp4_quant is faster than dynamic_mxfp4_quant.
Also probes its signature and output format.
"""

from __future__ import annotations

import inspect
import os
import sys


os.environ["HIP_ONLINE_TUNING"] = "1"

import aiter
from aiter import dtypes
from aiter.utility.fp4_utils import e8m0_shuffle
from reference import ref_kernel
from task import input_t, output_t


KERNEL_NAME_32X128 = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B_shuffle.shape[0]

    # === Probe fused_mxfp4_quant signature ===
    try:
        from aiter.ops.triton.quant import fused_mxfp4_quant

        sig = inspect.signature(fused_mxfp4_quant)
        print(f"fused_mxfp4_quant signature: {sig}", file=sys.stderr)

        # Try calling it like dynamic_mxfp4_quant
        result = fused_mxfp4_quant(A.contiguous())
        if isinstance(result, tuple):
            print(f"fused_mxfp4_quant returns tuple of {len(result)}", file=sys.stderr)
            for i, r in enumerate(result):
                if hasattr(r, "shape"):
                    print(f"  [{i}] {r.dtype} {r.shape}", file=sys.stderr)
                else:
                    print(f"  [{i}] {type(r).__name__}: {r}", file=sys.stderr)

            x_fp4 = result[0]
            bs_e8m0 = result[1]

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
        else:
            print(f"fused_mxfp4_quant returned non-tuple: {type(result)}", file=sys.stderr)
    except Exception as e:
        print(f"fused_mxfp4_quant failed: {e}", file=sys.stderr)

    # Fallback to ref_kernel
    return ref_kernel(data)
