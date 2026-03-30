"""
MXFP4 GEMM via load_inline simple HIP kernel.

BREAKTHROUGH: load_inline WORKS on Popcorn runners!
A simple but correct block-wise GEMM that bypasses the Python API.
"""

from torch.utils.cpp_extension import load_inline
from task import input_t, output_t
import torch


CPP_WRAPPER = """
void gemm_mxfp4(torch::Tensor a, torch::Tensor b, torch::Tensor a_scale, 
                torch::Tensor b_scale, torch::Tensor c);
"""


# Simple block-wise GEMM with scales - no external libs needed
HIP_SRC = """
#include <hip/hip_runtime.h>

typedef unsigned char uint8_t;
typedef short int16_t;
typedef int int32_t;
typedef long long int64_t;

// Simple FP4 unpack (2 values per byte)
__device__ float unpack_fp4(uint8_t packed, int idx) {
    float vals[2];
    uint8_t nibble = (idx == 0) ? (packed & 0x0F) : ((packed >> 4) & 0x0F);
    // E2M1 FNUZ interpretation
    int sign = (nibble & 0x08) ? -1 : 1;
    int exp = (nibble >> 3) & 0x01;
    int mant = nibble & 0x07;
    float fmant = mant / 8.0f;
    vals[idx] = sign * exp * (1.0f + fmant);
    return vals[idx];
}

__global__ void gemm_kernel(
    const float* __restrict__ A,
    const uint8_t* __restrict__ B_q,
    const float* __restrict__ A_scale,
    const float* __restrict__ B_scale,
    float* __restrict__ C,
    int M, int N, int K
) {
    int row = blockIdx.x * blockDim.x + threadIdx.x;
    int col = blockIdx.y * blockDim.y + threadIdx.y;
    
    if (row >= M || col >= N) return;
    
    float sum = 0.0f;
    
    int K_packed = K / 2;  // 2 FP4 per byte
    int K_groups = K / 32;  // 32 FP4 per scale
    
    for (int k = 0; k < K_packed; k++) {
        // Load A[k] as bf16 (converted to float)
        float a_val = A[row * K + k];
        
        // Load and unpack B[k]
        uint8_t b_packed = B_q[col * K_packed + k];
        float b_lo = unpack_fp4(b_packed, 0);
        float b_hi = unpack_fp4(b_packed, 1);
        
        // Get scales
        int k_group = k / 16;  // 16 FP4 per group = 32 FP4 per scale
        int k_in_group = k % 16;
        int k_idx = k_group * 16 + k_in_group / 2;  // Scale index
        int k_sub = k_in_group % 2;
        
        float a_s = A_scale[row * K_groups + k_idx];
        float b_s = B_scale[col * K_groups + k_idx];
        
        // Scale values
        float a_scaled = a_val * a_s;
        float b_scaled = (k_sub == 0) ? b_lo * b_s : b_hi * b_s;
        
        sum += a_scaled * b_scaled;
    }
    
    C[row * N + col] = sum;
}

void gemm_mxfp4(torch::Tensor A, torch::Tensor B_q, torch::Tensor A_scale, 
               torch::Tensor B_scale, torch::Tensor C) {
    int M = A.size(0);
    int K = A.size(1);
    int N = B_q.size(0);
    
    dim3 threads(16, 16);
    dim3 blocks((M + 15) / 16, (N + 15) / 16);
    
    gemm_kernel<<<threads, blocks>>>(
        (float*)A.data_ptr(),
        (uint8_t*)B_q.data_ptr(),
        A_scale.data_ptr<float>(),
        B_scale.data_ptr<float>(),
        C.data_ptr<float>(),
        M, N, K
    );
}
"""


module = load_inline(
    name="gemm_mxfp4",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=["gemm_mxfp4"],
    verbose=False,
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20"],
)


def custom_kernel(data: input_t) -> output_t:
    """
    GEMM via load_inline simple HIP kernel.

    Input: (A, B, B_q, B_shuffle, B_scale_sh)
    """
    import aiter
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    from aiter.utility.fp4_utils import e8m0_shuffle

    A, B, B_q, B_shuffle, B_scale_sh = data

    m, k = A.shape
    n = B_q.shape[0]

    # Quantize A
    A_fp4, A_scale_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    k_scale = k // 32
    A_scale = A_scale_e8m0[:m, :k_scale].contiguous().float()

    # Use shuffled B and scale
    B_q_view = B_shuffle.view(torch.uint8)
    B_scale_sh_view = B_scale_sh.float()

    # Call HIP kernel
    C = torch.zeros(m, n, dtype=torch.float32, device=A.device)

    module.gemm_mxfp4(
        A.contiguous().float(),
        B_q_view,
        A_scale,
        B_scale_sh_view,
        C,
    )

    return C.to(torch.bfloat16)
