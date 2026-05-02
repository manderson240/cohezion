"""Minimal load_inline test — does load_inline compilation itself cause stream error?

Test 1: Compile a trivial C++ function that does NO GPU work (just returns input)
Test 2: If that works, try a kernel that uses at::cuda::getCurrentCUDAStream()
"""

from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


# Test: C++ wrapper that does NO kernel launch — just returns a clone
HIP_SOURCE = r"""
#include <torch/extension.h>

torch::Tensor passthrough(torch::Tensor input) {
    return input.clone();
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("passthrough", &passthrough, "Just clone the input");
}
"""

CPP_SOURCE = "torch::Tensor passthrough(torch::Tensor input);"

try:
    _module = load_inline(
        name="minimal_test",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["passthrough"],
        verbose=False,
        extra_cuda_cflags=["-O3", "--offload-arch=gfx950"],
    )
    HAS_MODULE = True
except Exception as e:
    print(f"load_inline failed: {e}")
    HAS_MODULE = False


def custom_kernel(data: input_t) -> output_t:
    """Minimal test: use load_inline compiled module for a no-op."""
    import aiter
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    from aiter.utility.fp4_utils import e8m0_shuffle

    A, B, B_q, B_shuffle, B_scale_sh = data

    # Always use aiter for the actual GEMM (known to work on correct stream)
    A_q, A_scale_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_scale_sh = e8m0_shuffle(A_scale_e8m0).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)
    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
