"""MXFP4 GEMM — test torch.cuda._compile_kernel() for HIPRTC compilation.

_compile_kernel is available on Torch 2.10.0+rocm7.1!
This compiles device-only kernels via HIPRTC (no hipcc subprocess).
If it avoids the "work on another stream" error, we can use MFMA intrinsics.
"""

import sys
import torch
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

# Test _compile_kernel with a trivial kernel
_COMPILED = None
try:
    # Simple identity kernel as proof of concept
    _kernel_src = """
    extern "C" __global__ void identity_copy(
        const float* __restrict__ input,
        float* __restrict__ output,
        int N
    ) {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        if (idx < N) output[idx] = input[idx];
    }
    """
    _COMPILED = torch.cuda._compile_kernel(
        _kernel_src,
        "identity_copy",
    )
    print(f"PROBE: _compile_kernel SUCCESS! type={type(_COMPILED)}", file=sys.stderr)
except Exception as e:
    print(f"PROBE: _compile_kernel FAILED: {e}", file=sys.stderr)


@torch.no_grad()
def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    A_q, A_scale = dynamic_mxfp4_quant(A)
    A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)
    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
