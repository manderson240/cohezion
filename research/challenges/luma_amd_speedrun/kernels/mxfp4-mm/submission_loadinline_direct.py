"""
MXFP4 GEMM — Pure load_inline custom HIP kernel following official template.

BREAKTHROUGH: Official template-hip.py from gpu-mode/reference-kernels PROVES
load_inline WORKS on Popcorn runners!

This is how rank 1 achieves 1µs - NOT using Python API!

Key patterns from official template:
1. Block-wise GEMM with scales LIFTED outside inner loop
2. Pre-allocated output tensor passed as parameter
3. Native HIP types: __hip_bfloat16
4. dim3(16, 16) thread blocks

FP4 e2m1 values: 0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0 (positive and negative)
"""

import os
from torch.utils.cpp_extension import load_inline

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"

from task import input_t, output_t

CPP_WRAPPER = """
void mxfp4_gemm(
    torch::Tensor A_packed,
    torch::Tensor B_packed, 
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C
);
"""

HIP_SRC = """
#include <hip/hip_runtime.h>
#include <hip/amd_detail/amd_hip_fp8.h>
#include <hip/amd_detail/amd_hip_bf16.h>

constexpr int BLOCK = 16;

// FP4 e2m1 to float
__device__ inline float fp4_to_f32(uint8_t fp4) {
    float vals[16] = {
        0.0f, 0.5f, 1.0f, 1.5f, 2.0f, 3.0f, 4.0f, 6.0f,
        -0.0f, -0.5f, -1.0f, -1.5f, -2.0f, -3.0f, -4.0f, -6.0f
    };
    return vals[fp4 & 0xF];
}

__device__ inline float unpack_fp4(uint8_t packed, int idx) {
    uint8_t nibble = (idx == 0) ? (packed & 0xF) : ((packed >> 4) & 0xF);
    return fp4_to_f32(nibble);
}

__device__ inline float e8m0_to_f32(uint8_t e8m0) {
    if (e8m0 == 0) return 0.0f;
    if (e8m0 == 255) return 0.0f;
    return exp2f((float)((int)e8m0 - 127));
}

__global__ void mxfp4_kernel(
    const uint8_t* A,
    const uint8_t* B,
    const uint8_t* As,
    const uint8_t* Bs,
    __hip_bfloat16* C,
    int M, int N, int K
) {
    int bx = blockIdx.x;
    int by = blockIdx.y;
    int tx = threadIdx.x;
    int ty = threadIdx.y;
    
    int row = bx * BLOCK + tx;
    int col = by * BLOCK + ty;
    
    if (row >= M || col >= N) return;
    
    int k_blocks = K / 32;
    int k_packed = K / 2;
    
    float result = 0.0f;
    
    // Lifted scale pattern from official template
    for (int kb = 0; kb < k_blocks; kb++) {
        float block_result = 0.0f;
        
        for (int kk = 0; kk < 32; kk++) {
            int k_idx = kb * 32 + kk;
            
            int a_packed_idx = row * k_packed + k_idx / 2;
            float a_val = unpack_fp4(A[a_packed_idx], k_idx % 2);
            
            int b_packed_idx = col * k_packed + k_idx / 2;
            float b_val = unpack_fp4(B[b_packed_idx], k_idx % 2);
            
            block_result += a_val * b_val;
        }
        
        // LIFTED: scale applied once per block, not per element
        float a_scale = e8m0_to_f32(As[row * k_blocks + kb]);
        float b_scale = e8m0_to_f32(Bs[col * k_blocks + kb]);
        
        result += block_result * a_scale * b_scale;
    }
    
    C[row * N + col] = (__hip_bfloat16)result;
}

void mxfp4_gemm(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C
) {
    int M = A_packed.size(0);
    int K = A_packed.size(1) * 2;
    int N = B_packed.size(0);
    
    dim3 blocks((M + BLOCK - 1) / BLOCK, (N + BLOCK - 1) / BLOCK);
    dim3 threads(BLOCK, BLOCK);
    
    mxfp4_kernel<<<blocks, threads>>>(
        (const uint8_t*)A_packed.data_ptr(),
        (const uint8_t*)B_packed.data_ptr(),
        (const uint8_t*)A_scale.data_ptr(),
        (const uint8_t*)B_scale.data_ptr(),
        (__hip_bfloat16*)C.data_ptr(),
        M, N, K
    );
}
"""

os.environ["CXX"] = "clang++"

module = load_inline(
    name="mxfp4_gemm",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=["mxfp4_gemm"],
    verbose=False,
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
)


def custom_kernel(data: input_t) -> output_t:
    """MXFP4 GEMM using pure load_inline HIP kernel."""
    import torch
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    from aiter.utility.fp4_utils import e8m0_shuffle

    A, B, B_q, B_shuffle, B_scale_sh = data

    M, K = A.shape
    N = B.shape[0]
    k_scale_groups = K // 32

    # Quantize A to MXFP4
    A_fp4, A_scale = dynamic_mxfp4_quant(A.contiguous())

    # Prepare scales
    k_scale_valid = k_scale_groups
    A_scale_bytes = A_scale[:M, :k_scale_valid].contiguous().view(torch.uint8)
    A_scale_sh = e8m0_shuffle(A_scale_bytes.view(dtypes.fp8_e8m0))
    A_scale_sh_bytes = A_scale_sh.view(torch.uint8)

    # Get packed views
    A_packed = A_fp4.view(torch.uint8)
    B_packed = B_shuffle.view(torch.uint8)
    B_scale_bytes = B_scale_sh.view(torch.uint8)

    # Allocate output
    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    # Call custom HIP kernel
    module.mxfp4_gemm(A_packed, B_packed, A_scale_sh_bytes, B_scale_bytes, C)

    return C
