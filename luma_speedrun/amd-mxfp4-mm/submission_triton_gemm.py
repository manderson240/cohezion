#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM via Triton FP4 GEMM path (gemm_afp4wfp4_preshuffle).

Uses aiter's Triton-based FP4xFP4 GEMM instead of the CK ASM path.
The Triton kernel may have different autotuning for competition shapes.
Falls back to CK ASM baseline on any error.
"""

import torch
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

# Try Triton GEMM path
_triton_gemm = None
try:
    from aiter.ops.triton.gemm.basic.gemm_afp4wfp4 import gemm_afp4wfp4_preshuffle
    _triton_gemm = gemm_afp4wfp4_preshuffle
except ImportError:
    pass

_gemm = aiter.gemm_a4w4
_fp4x2 = dtypes.fp4x2
_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Quantize A
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(_e8m0)

    if _triton_gemm is not None:
        try:
            M, K_half = Aq.shape
            N = B_shuffle.shape[0]
            out = torch.empty((M, N), dtype=_bf16, device=A.device)
            result = _triton_gemm(
                Aq.view(_fp4x2),
                B_shuffle,
                Ash,
                B_scale_sh,
                dtype=_bf16,
                y=out,
            )
            return result
        except Exception:
            pass

    # Fallback: CK ASM path
    return _gemm(
        Aq.view(_fp4x2), B_shuffle, Ash, B_scale_sh,
        dtype=_bf16, bpreshuffle=True,
    )
