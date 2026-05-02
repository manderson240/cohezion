"""Test: defer load_inline compilation to inside custom_kernel().

Hypothesis: The runner detects stream violations during import.
If we defer load_inline to the first call of custom_kernel(),
the compilation happens on the harness's active stream context.
"""


from task import input_t, output_t


# Do NOT compile at import time
_module = None

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

// Minimal: just copy input to output as bf16
__global__ void identity_kernel(
    const at::BFloat16* __restrict__ input,
    at::BFloat16* __restrict__ output,
    int N
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) output[idx] = input[idx];
}

torch::Tensor run_identity(torch::Tensor input) {
    auto output = torch::empty_like(input);
    int N = input.numel();
    dim3 block(256);
    dim3 grid((N + 255) / 256);
    identity_kernel<<<grid, block, 0, at::cuda::getCurrentCUDAStream()>>>(
        reinterpret_cast<const at::BFloat16*>(input.data_ptr()),
        reinterpret_cast<at::BFloat16*>(output.data_ptr()),
        N
    );
    return output;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("run_identity", &run_identity, "Identity copy");
}
"""

CPP_SOURCE = "torch::Tensor run_identity(torch::Tensor input);"


def custom_kernel(data: input_t) -> output_t:
    """Defer load_inline to first call — compiles on harness stream context."""
    global _module

    import aiter
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    from aiter.utility.fp4_utils import e8m0_shuffle

    A, B, B_q, B_shuffle, B_scale_sh = data

    # Try deferred compilation
    if _module is None:
        try:
            from torch.utils.cpp_extension import load_inline

            _module = load_inline(
                name="deferred_test",
                cpp_sources=[CPP_SOURCE],
                cuda_sources=[HIP_SOURCE],
                functions=["run_identity"],
                verbose=False,
                extra_cuda_cflags=["-O3", "--offload-arch=gfx950"],
            )
        except Exception as e:
            print(f"Deferred load_inline failed: {e}")
            _module = False

    # Always fall back to aiter for correctness
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
