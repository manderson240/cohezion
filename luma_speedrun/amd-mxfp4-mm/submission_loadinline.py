"""MXFP4 GEMM — Pure load_inline custom HIP kernel.

Based on official template-hip.py from gpu-mode/reference-kernels.
Uses block-wise GEMM with scales LIFTED outside the inner loop.

Key patterns from official template:
1. Block-wise GEMM with scales OUTSIDE inner loop (lifted scaling)
2. Pre-allocated output tensor
3. Native HIP types
4. dim3(16, 16) thread block

FP4 e2m1 format:
- Sign bit, 2-bit exponent, 1-bit mantissa
- Bias = 1, so exponent field 0,1,2,3 → actual exp -1,0,1,2
- Values: 0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0 (positive and negative)

E8M0 format:
- 8-bit exponent-only, bias 127
- f32 = 2^(e8m0 - 127)
"""

import os
from torch.utils.cpp_extension import load_inline

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"

from task import input_t, output_t

CPP_WRAPPER = """
void mxfp4_gemm(
    torch::Tensor A_packed,  // packed FP4, shape (M, K/2)
    torch::Tensor B_packed,  // packed FP4, shape (N, K/2)  
    torch::Tensor A_scale,   // E8M0 scales, shape (M, K/32)
    torch::Tensor B_scale,   // E8M0 scales, shape (N, K/32)
    torch::Tensor C          // output, shape (M, N)
);
"""

CUDA_SRC = r"""
#include <hip/amd_detail/amd_hip_fp8.h>
#include <hip/amd_detail/amd_hip_bf16.h>

constexpr int BLOCK = 16;

// FP4 e2m1 lookup table: index = 4-bit FP4 value
// Values: 0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0 (positive and negative)
__device__ inline float fp4_e2m1_to_f32(uint8_t fp4_val) {
    // Sign bit (bit 3), then 2-bit exponent, 1-bit mantissa
    int sign = (fp4_val >> 3) & 1;
    int exp = (fp4_val >> 1) & 3;
    int mant = fp4_val & 1;
    
    float vals[16] = {
        0.0f, 0.5f, 1.0f, 1.5f,   // positive denormal/normal
        2.0f, 3.0f, 4.0f, 6.0f,   // positive larger
        -0.0f, -0.5f, -1.0f, -1.5f,  // negative
        -2.0f, -3.0f, -4.0f, -6.0f
    };
    
    float f = vals[fp4_val & 0xF];
    return sign ? -f : f;
}

// E8M0 to f32: exponent-only format with bias 127
// f32 = 2^(e8m0 - 127)
__device__ inline float e8m0_to_f32(uint8_t e8m0) {
    if (e8m0 == 0) return 0.0f;
    if (e8m0 == 255) return 0.0f;  // NaN/Inf -> 0 for safety
    
    int exp = int(e8m0) - 127;
    return exp2f((float)exp);
}

// Unpack FP4 from packed byte: idx 0 = lower nibble, idx 1 = upper nibble
__device__ inline float unpack_fp4(uint8_t packed, int idx) {
    uint8_t nibble = (idx == 0) ? (packed & 0xF) : ((packed >> 4) & 0xF);
    return fp4_e2m1_to_f32(nibble);
}

__global__ void mxfp4_gemm_kernel(
    const uint8_t* __restrict__ A,   // packed FP4, shape (M, K/2)
    const uint8_t* __restrict__ B,   // packed FP4, shape (N, K/2)
    const uint8_t* __restrict__ As,  // E8M0 scales, shape (M, K/32)
    const uint8_t* __restrict__ Bs,   // E8M0 scales, shape (N, K/32)
    __hip_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    // Block index
    int bx = blockIdx.x;
    int by = blockIdx.y;
    // Thread index within block
    int tx = threadIdx.x;
    int ty = threadIdx.y;
    
    // Global row/col for this thread
    int row = bx * BLOCK + tx;
    int col = by * BLOCK + ty;
    
    if (row >= M || col >= N) return;
    
    // K is divisible by 64 (scale group 32, pack 2)
    int k_scale_groups = K / 32;
    int k_packed = K / 2;
    
    float acc = 0.0f;
    
    // Loop over scale groups (each scale group = 32 K elements = 16 packed bytes)
    for (int sg = 0; sg < k_scale_groups; sg++) {
        float block_acc = 0.0f;
        
        // Inner loop over 32 K elements within this scale group
        for (int kk = 0; kk < 32; kk++) {
            int k_idx = sg * 32 + kk;
            
            // A[row, k_idx] - unpack from packed
            int a_packed_idx = row * k_packed + k_idx / 2;
            int a_nibble = k_idx % 2;
            float a_val = unpack_fp4(A[a_packed_idx], a_nibble);
            
            // B[col, k_idx] - unpack from packed
            int b_packed_idx = col * k_packed + k_idx / 2;
            int b_nibble = k_idx % 2;
            float b_val = unpack_fp4(B[b_packed_idx], b_nibble);
            
            block_acc += a_val * b_val;
        }
        
        // LIFTED SCALE: apply scale ONCE per scale group, not per element
        // Scale layout: (M, K/32) and (N, K/32)
        float a_scale = e8m0_to_f32(As[row * k_scale_groups + sg]);
        float b_scale = e8m0_to_f32(Bs[col * k_scale_groups + sg]);
        
        acc += block_acc * a_scale * b_scale;
    }
    
    C[row * N + col] = (__hip_bfloat16)acc;
}

void mxfp4_gemm(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C
) {
    int M = A_packed.size(0);
    int k_packed = A_packed.size(1);
    int K = k_packed * 2;
    int N = B_packed.size(0);
    
    dim3 blocks((M + BLOCK - 1) / BLOCK, (N + BLOCK - 1) / BLOCK);
    dim3 threads(BLOCK, BLOCK);
    
    mxfp4_gemm_kernel<<<blocks, threads, 0, 0>>>(
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
    cuda_sources=[CUDA_SRC],
    functions=["mxfp4_gemm"],
    verbose=True,
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
)


def custom_kernel(data: input_t) -> output_t:
    """
    MXFP4 GEMM using pure load_inline custom HIP kernel.

    Input data: (A, B, B_q, B_shuffle, B_scale_sh)
    - A: bf16, shape (M, K)
    - B: bf16, shape (N, K)
    - B_q: packed FP4, shape (N, K/2)
    - B_shuffle: shuffled packed FP4 for aiter GEMM (not used here)
    - B_scale_sh: shuffled E8M0 scales, shape (N, K/32)

    Our kernel uses:
    - A_q: packed FP4 from quantizing A
    - A_scale_sh: shuffled E8M0 from quantizing A
    - B_q and B_scale_sh (both already shuffled)
    """
    import aiter
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    from aiter.utility.fp4_utils import e8m0_shuffle
    import torch

    A, B, B_q, B_shuffle, B_scale_sh = data

    M, K = A.shape
    N = B.shape[0]
    k_scale_groups = K // 32

    # Quantize A to MXFP4
    A_q, A_scale = dynamic_mxfp4_quant(A.contiguous())
    A_scale_u8 = A_scale[:M, :k_scale_groups].contiguous().view(dtypes.fp8_e8m0)
    A_scale_sh = e8m0_shuffle(A_scale_u8)
    A_q_packed = A_q.view(dtypes.fp4x2)

    # A_q_packed is now (M, K/2), B_shuffle is (N, K/2)
    # A_scale_sh is (M, K/32), B_scale_sh is (N, K/32)

    # Convert views to uint8 for load_inline
    A_packed = A_q_packed.view(torch.uint8)
    B_packed = B_shuffle.view(torch.uint8)
    A_scale_bytes = A_scale_sh.view(torch.uint8)
    B_scale_bytes = B_scale_sh.view(torch.uint8)

    # Allocate output
    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    # Call our custom HIP kernel
    module.mxfp4_gemm(A_packed, B_packed, A_scale_bytes, B_scale_bytes, C)

    return C
