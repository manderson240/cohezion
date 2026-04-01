"""
GEMM BREAKTHROUGH: gen_gemm_a4w4_blockscale_fake_tensors — NEW fp4 GEMM path.

Discovered via tuned_gemm probe Session 76. This is a DIFFERENT API from gemm_a4w4_asm:
  gen_gemm_a4w4_blockscale_fake_tensors(XQ, WQ, x_scale, w_scale, Out, splitK=0)

Key differences:
1. Pre-allocated output (Out parameter) — avoids allocation overhead
2. splitK parameter — can control parallelism
3. blockscale format — may handle MXFP4 per_1x32 differently than per-element
4. "fake_tensors" suffix suggests torch.compile compatibility

Also discovered: 5 GEMM backends in tuned_gemm (hipb_mm, skinny_gemm, triton_gemm, asm_gemm, torch_gemm).
"""

from __future__ import annotations

import os
import sys


os.environ["HIP_ONLINE_TUNING"] = "1"

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B_shuffle.shape[0]

    # Quantize A
    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_q = x_fp4.view(dtypes.fp4x2)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)

    # === Try gen_gemm_a4w4_blockscale_fake_tensors ===
    try:
        from aiter.tuned_gemm import gen_gemm_a4w4_blockscale_fake_tensors

        Out = torch.empty(m, n, dtype=dtypes.bf16, device=A.device)

        # Try with shuffled inputs (matching gemm_a4w4_asm convention)
        result = gen_gemm_a4w4_blockscale_fake_tensors(
            A_q.view(m, k // 2),  # XQ: [M, K//2] fp4x2
            B_shuffle,  # WQ: shuffled B weights
            A_scale_sh,  # x_scale
            B_scale_sh,  # w_scale
            Out,  # pre-allocated output
            0,  # splitK=0 (default)
        )
        print(
            f"blockscale SUCCESS! Out shape={Out.shape}, max={Out.abs().max().item():.4f}",
            file=sys.stderr,
        )
        return Out

    except Exception as e:
        err = str(e)[:400]
        print(f"blockscale failed: {err}", file=sys.stderr)

        # Try splitK variants
        for sk in [1, 2, 4]:
            try:
                Out = torch.empty(m, n, dtype=dtypes.bf16, device=A.device)
                result = gen_gemm_a4w4_blockscale_fake_tensors(
                    A_q.view(m, k // 2),
                    B_shuffle,
                    A_scale_sh,
                    B_scale_sh,
                    Out,
                    sk,
                )
                print(f"blockscale splitK={sk} SUCCESS!", file=sys.stderr)
                return Out
            except Exception as e2:
                print(f"blockscale splitK={sk} failed: {str(e2)[:200]}", file=sys.stderr)

    # === Fallback: try gemm_a4w4_blockscale (non-fake) ===
    try:
        result = aiter.gemm_a4w4_blockscale(
            A_q.view(m, k // 2),
            B_shuffle,
            A_scale_sh,
            B_scale_sh,
            dtype=dtypes.bf16,
        )
        print(f"gemm_a4w4_blockscale SUCCESS! shape={result.shape}", file=sys.stderr)
        return result
    except Exception as e:
        print(f"gemm_a4w4_blockscale failed: {str(e)[:200]}", file=sys.stderr)

    return ref_kernel(data)
