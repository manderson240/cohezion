"""MXFP4 GEMM — test torch.cuda._compile_kernel() HIPRTC path.

HIPRTC compiles device-only kernels WITHOUT spawning hipcc subprocess.
This might avoid the "work on another stream" error since no new HIP
context is created. If this works, we can use MFMA intrinsics directly.

RFC: https://github.com/pytorch/pytorch/issues/152032
"""

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


# Test if _compile_kernel exists
HAS_COMPILE_KERNEL = False
try:
    from torch.cuda import _compile_kernel

    HAS_COMPILE_KERNEL = True
    print("torch.cuda._compile_kernel AVAILABLE!")
except ImportError:
    print("torch.cuda._compile_kernel NOT available")

# Also try torch._C._cuda_compile_kernel
HAS_C_COMPILE = False
try:
    compile_fn = torch._C._cuda_compile_kernel
    HAS_C_COMPILE = True
    print("torch._C._cuda_compile_kernel AVAILABLE!")
except AttributeError:
    print("torch._C._cuda_compile_kernel NOT available")

# Check torch version for HIPRTC support
print(f"torch version: {torch.__version__}")
print(f"HIP available: {torch.cuda.is_available()}")


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
