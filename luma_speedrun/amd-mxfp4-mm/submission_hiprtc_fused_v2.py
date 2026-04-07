#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""
HIPRTC fused quant+GEMM using torch.cuda._compile_kernel.

Attempting to fuse dynamic_mxfp4_quant + e8m0_shuffle + gemm_a4w4
into a single kernel dispatch via HIPRTC.
"""

import os
import sys
import torch

# Environment setup
os.environ["AITER_JIT_DIR"] = "/tmp/aiter_jit_cache"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"

_AITER_JIT_DIR = "/home/runner/aiter/aiter/jit"
if _AITER_JIT_DIR not in os.environ.get("PYTHONPATH", ""):
    if _AITER_JIT_DIR not in sys.path:
        sys.path.insert(0, _AITER_JIT_DIR)

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


# Check if _compile_kernel is available
_HAS_COMPILE_KERNEL = hasattr(torch.cuda, '_compile_kernel')

# Try to compile a test kernel at module load time
_test_kernel = None
if _HAS_COMPILE_KERNEL:
    test_source = r""
#include <hip/hip_runtime.h>
extern "C" __global__ void test_kernel(float* out, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) out[idx] = 1.0f;
}
"""
    try:
        _test_kernel = torch.cuda._compile_kernel(test_source, "test_kernel", "hiprtc")
    except Exception as e:
        print(f"HIPRTC test compile failed: {e}", file=sys.stderr)
        _HAS_COMPILE_KERNEL = False


def custom_kernel(data: input_t) -> output_t:
    """MXFP4 GEMM - with optional HIPRTC path."""
    A, B, B_q, B_shuffle, B_scale_sh = data

    M, K = A.shape
    N = B.shape[0]

    # Dynamic quantize A to MXFP4
    A_q, A_scale = dynamic_mxfp4_quant(A.contiguous())

    # Shuffle scales
    num_scale_groups = K // 32
    A_scale_bytes = A_scale[:M, :num_scale_groups].contiguous().view(torch.uint8)
    A_scale_sh = e8m0_shuffle(A_scale_bytes.view(dtypes.fp8_e8m0))

    # Select kernel based on M size
    if M <= 16:
        kernel_name = "f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128"
    elif M <= 64:
        kernel_name = "f4gemm_bf16_per1x32Fp4_BpreShuffle_64x128"
    else:
        kernel_name = "f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128"

    out = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    try:
        from aiter import gemm_a4w4_asm
        gemm_a4w4_asm(
            A_q.view(dtypes.fp4x2),
            B_shuffle,
            A_scale_sh.view(dtypes.fp8_e8m0),
            B_scale_sh,
            out,
            kernelName=kernel_name,
            bias=None,
            alpha=1.0,
            beta=0.0,
            bpreshuffle=True,
            log2_k_split=0,
        )
        return out
    except Exception:
        return aiter.gemm_a4w4(
            A_q.view(dtypes.fp4x2),
            B_shuffle,
            A_scale_sh.view(dtypes.fp8_e8m0),
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True,
        )
