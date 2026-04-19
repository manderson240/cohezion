#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""torch.compile on the aiter GEMM path — eliminate Python overhead.

If torch.compile can fuse the quant+shuffle+gemm into a single graph,
it would eliminate ~2µs Python overhead per call.
"""

import torch
from aiter import dtypes
import aiter
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def _gemm_core(A, B_shuffle, B_scale_sh):
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


# Try to compile the core function
try:
    _compiled = torch.compile(_gemm_core, mode="default", backend="inductor")
    _USE_COMPILED = True
    print("[compile] torch.compile succeeded")
except Exception as e:
    _compiled = _gemm_core
    _USE_COMPILED = False
    print(f"[compile] torch.compile failed: {e}")


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    return _compiled(A, B_shuffle, B_scale_sh)
