#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""hipb_mm with solution tuning: try different hipBLASLt kernel indices.

hipb_mm(mat1, mat2, solution_index, bias=None, out_dtype=None,
        scaleA=None, scaleB=None, scaleOut=None, bpreshuffle=None)

The bpreshuffle=True failed (hipblaslt too old), but WITHOUT bpreshuffle
we can try BF16 inputs directly. The shapes are A[M,K] @ B[N,K]^T.

Key: solution_index selects from hipBLASLt's tuned kernel library.
Different indices = different kernel configurations = different perf.
"""

import torch
from aiter import dtypes
import aiter
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

_best_solution = {}  # Cache best solution per shape


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Try hipb_mm with BF16 inputs (no MXFP4 quant needed!)
    # This only works if the 1% tolerance accepts BF16 vs MXFP4 reference
    # We already know torch.mm fails — but hipb_mm might use different precision

    # Since BF16 GEMM fails 1% tolerance, we MUST use MXFP4.
    # Fall back to standard aiter path.
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2),
        B_shuffle,
        Ash,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
