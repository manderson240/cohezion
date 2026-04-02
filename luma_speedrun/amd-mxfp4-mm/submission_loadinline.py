"""MXFP4 GEMM via load_inline Custom HIP Kernel.

Strategy: Bypass Python API ceiling by compiling HIP C++ at runtime.
Uses torch.utils.cpp_extension.load_inline() which is proven on Popcorn runner.

Approach: MFMA-tiled GEMM with fused FP4 unpacking and E8M0 scaling.
Target: <10us from current 22.8us baseline.

References:
- K-Search (arXiv:2602.19128) for systematic optimization
- HipKittens (arXiv:2511.08083) for tile primitives
- CK-Tile gfx950 MXFP4 support
"""

import os
import torch
from torch.utils.cpp_extension import load_inline

from task import input_t, output_t

# HIP C++ source for MXFP4 GEMM kernel
HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

// MXFP4 unpacking: 2 values per uint8 byte
__device__ __forceinline__ float unpack_fp4_lo(uint8_t byte) {
    // Low nibble: MXFP4 values [0, 0.5, 1, 1.5, 2, 3, 4, 6]
    static __device__ const float LUT[16] = {
        0.0f, 0.5f, 1.0f, 1.5f, 2.0f, 3.0f, 4.0f, 6.0f,
        -0.0f, -0.5f, -1.0f, -1.5f, -2.0f, -3.0f, -4.0f, -6.0f
    };
    return LUT[byte & 0xF];
}

__device__ __forceinline__ float unpack_fp4_hi(uint8_t byte) {
    static __device__ const float LUT[16] = {
        0.0f, 0.5f, 1.0f, 1.5f, 2.0f, 3.0f, 4.0f, 6.0f,
        -0.0f, -0.5f, -1.0f, -1.5f, -2.0f, -3.0f, -4.0f, -6.0f
    };
    return LUT[(byte >> 4) & 0xF];
}

// E8M0 scale: f32 = 2^(e8m0 - 127)
__device__ __forceinline__ float e8m0_to_float(uint8_t val) {
    return exp2f((float)((int)val - 127));
}

// Simple MXFP4 GEMM kernel: C = A @ B^T with FP4 inputs and E8M0 scales
// Each thread computes one output element (naive, will be tiled later)
__global__ void mxfp4_gemm_naive(
    const uint8_t* __restrict__ A_packed,   // [M, K/2] packed FP4
    const uint8_t* __restrict__ B_packed,   // [N, K/2] packed FP4
    const uint8_t* __restrict__ A_scale,    // [M, K/32] E8M0 scales
    const uint8_t* __restrict__ B_scale,    // [N, K/32] E8M0 scales
    at::BFloat16* __restrict__ C,           // [M, N] output
    int M, int N, int K
) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;

    if (row >= M || col >= N) return;

    float acc = 0.0f;
    int K_half = K / 2;
    int scale_stride_a = K / 32;
    int scale_stride_b = K / 32;

    for (int k = 0; k < K_half; k++) {
        // Unpack two FP4 values from each byte
        uint8_t a_byte = A_packed[row * K_half + k];
        uint8_t b_byte = B_packed[col * K_half + k];

        float a_lo = unpack_fp4_lo(a_byte);
        float a_hi = unpack_fp4_hi(a_byte);
        float b_lo = unpack_fp4_lo(b_byte);
        float b_hi = unpack_fp4_hi(b_byte);

        // Apply E8M0 scales (one scale per 32 elements)
        int scale_idx = (2 * k) / 32;
        float sa = e8m0_to_float(A_scale[row * scale_stride_a + scale_idx]);
        float sb = e8m0_to_float(B_scale[col * scale_stride_b + scale_idx]);

        acc += a_lo * b_lo * sa * sb;
        acc += a_hi * b_hi * sa * sb;
    }

    C[row * N + col] = __float2bfloat16(acc);
}

// Python-callable wrapper
torch::Tensor mxfp4_gemm_hip(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    int M, int N, int K
) {
    auto C = torch::empty({M, N}, torch::TensorOptions()
        .dtype(torch::kBFloat16)
        .device(A_packed.device()));

    dim3 block(16, 16);
    dim3 grid((N + block.x - 1) / block.x, (M + block.y - 1) / block.y);

    mxfp4_gemm_naive<<<grid, block, 0, at::cuda::getCurrentCUDAStream()>>>(
        A_packed.data_ptr<uint8_t>(),
        B_packed.data_ptr<uint8_t>(),
        A_scale.data_ptr<uint8_t>(),
        B_scale.data_ptr<uint8_t>(),
        reinterpret_cast<at::BFloat16*>(C.data_ptr()),
        M, N, K
    );

    return C;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("mxfp4_gemm_hip", &mxfp4_gemm_hip, "MXFP4 GEMM via HIP");
}
"""

CPP_SOURCE = "torch::Tensor mxfp4_gemm_hip(torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, int, int, int);"

# Compile at import time
try:
    _module = load_inline(
        name="mxfp4_gemm_hip",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["mxfp4_gemm_hip"],
        verbose=False,
        extra_cuda_cflags=["-O3", "--offload-arch=gfx950"],
    )
    HAS_CUSTOM_KERNEL = True
except Exception as e:
    print(f"load_inline failed: {e}, falling back to reference")
    HAS_CUSTOM_KERNEL = False


def custom_kernel(input: input_t) -> output_t:
    """Run custom HIP MXFP4 GEMM kernel."""
    A, B, A_scale, B_scale = input.A, input.B, input.A_scale, input.B_scale
    M, K_half = A.shape
    N = B.shape[0]
    K = K_half * 2

    return _module.mxfp4_gemm_hip(A, B, A_scale, B_scale, M, N, K)


def ref_kernel(input: input_t) -> output_t:
    """Reference kernel (baseline anchor)."""
    from aiter import gemm_a4w4

    return gemm_a4w4(input.A, input.B, input.A_scale, input.B_scale)


def kernel(input: input_t) -> output_t:
    """Two Builders: try custom, fall back to reference."""
    if HAS_CUSTOM_KERNEL:
        return custom_kernel(input)
    return ref_kernel(input)
