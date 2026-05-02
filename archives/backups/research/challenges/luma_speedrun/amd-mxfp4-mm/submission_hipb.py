#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Try hipb_mm (hipBLASLt) with FP4 quantized inputs.

hipb_mm supports scaleA/scaleB and bpreshuffle — may work with MXFP4.
solution_index selects from hipBLASLt's tuned kernel library.
"""

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


_gemm = aiter.gemm_a4w4
_quant = dynamic_mxfp4_quant
_shuffle = e8m0_shuffle


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    Aq, Asc = _quant(A.contiguous())
    Ash = _shuffle(Asc).view(dtypes.fp8_e8m0)

    # Try hipb_mm with MXFP4 inputs
    try:
        out = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
        result = aiter.hipb_mm(
            Aq.view(dtypes.fp4x2),
            B_shuffle,
            0,  # solution_index = 0 (auto or first)
            None,  # bias
            dtypes.bf16,  # out_dtype
            Ash,  # scaleA
            B_scale_sh,  # scaleB
            None,  # scaleOut
            True,  # bpreshuffle
        )
        return result
    except Exception as e:
        print(f"[hipb_mm] Failed: {e}")
        # Fallback to standard gemm_a4w4
        return _gemm(
            Aq.view(dtypes.fp4x2),
            B_shuffle,
            Ash,
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True,
        )
