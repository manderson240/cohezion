"""Minimal probe: just check torch version and available APIs."""

import sys
import torch
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

# Safe probes via stderr (runner captures this)
print(f"PROBE: torch={torch.__version__}", file=sys.stderr)
print(f"PROBE: has _compile_kernel={hasattr(torch.cuda, '_compile_kernel')}", file=sys.stderr)
print(f"PROBE: has _C compile={hasattr(torch._C, '_cuda_compile_kernel')}", file=sys.stderr)

# Check tritonblas for Triton-based FP4
try:
    import tritonblas
    print(f"PROBE: tritonblas={dir(tritonblas)}", file=sys.stderr)
except ImportError:
    print("PROBE: tritonblas NOT available", file=sys.stderr)


@torch.no_grad()
def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    A_q, A_scale = dynamic_mxfp4_quant(A)
    A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)
    return aiter.gemm_a4w4(
        A_q, B_shuffle, A_scale_sh, B_scale_sh,
        dtype=dtypes.bf16, bpreshuffle=True,
    )
