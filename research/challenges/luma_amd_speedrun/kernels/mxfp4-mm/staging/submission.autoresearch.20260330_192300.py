import torch
from torch.utils.cpp_extension import load_inline
import aiter
from aiter import QuantType, dtypes
from aiter.ops.shuffle import shuffle_weight
from task import input_t, output_t

SCALE_GROUP_SIZE = 32

CPP_WRAPPER = """
#include <torch/extension.h>
#include <ATen/ATen.h>

torch::Tensor fp4_mm(
    const torch::Tensor& A,
    const torch::Tensor& B_q,
    const torch::Tensor& A_scale,
    const torch::Tensor& B_scale,
    int M, int N, int K
) {
    return torch::empty({M, N}, A.options().dtype(torch::kBFloat16));
}
"""

HIP_SRC = R"""
#include <hip/hip_runtime.h>
#include <torch/extension.h>
#include <ATen/ATen.h>
#include <cuda_bf16.h>

using namespace at;

// FP4 unpack helpers (packed 2 per byte)
__device__ __forceinline__ void unpack_fp4(
    const uint8_t* packed, int idx, float& val, float& scale) {
    uint8_t val8 = packed[idx];
    // Lower 4 bits
    int4_t l = static_cast<int4_t>(val8 & 0xF);
    // Upper 4 bits
    int4_t u = static_cast<int4_t>((val8 >> 4) & 0xF);
    // Convert to float with scale
    val = static_cast<float>(l) * scale;
    // For now just return first value; real unpacking done in kernel
}

// E8M0 decode: exponent only, bias=127
__device__ __forceinline__ float e8m0_to_f32(uint8_t x) {
    union {
        uint32_t i;
        float f;
    } u;
    u.i = (static_cast<uint32_t>(x) << 24) | 0x7F800000u;
    return u.f;
}

// MXFP4 dequantization
__device__ __forceinline__ float mxfp4_to_f32(uint8_t packed, float scale) {
    uint8_t lo = packed & 0x0F;
    uint8_t hi = (packed >> 4) & 0x0F;
    float v_lo = static_cast<float>(static_cast<int4_t>(lo)) * scale;
    float v_hi = static_cast<float>(static_cast<int4_t>(hi)) * scale;
    // We only return one value here for simplicity in test kernel
    return v_lo;
}

__global__ void fp4_gemm_kernel(
    const half2* __restrict__ A,          // [M, K/2] in bf16 (as half2)
    const uint8_t* __restrict__ B_q,      // [N, K/2] FP4 packed
    const half* __restrict__ A_scale,     // [M, K/32] E8M0 (bf16)
    const half* __restrict__ B_scale,     // [N, K/32] E8M0 (bf16)
    float* __restrict__ C,                // [M, N] output (f32 for accumulation)
    int M, int N, int K) {
    
    // Block tiling: 32x32x32
    const int BLOCK_M = 32;
    const int BLOCK_N = 32;
    const int BLOCK_K = 32; // 1 scale group = 32 elements (16 half2)

    int m = blockIdx.y * BLOCK_M + threadIdx.y;
    int n = blockIdx.x * BLOCK_N + threadIdx.x;

    if (m >= M || n >= N) return;

    // Accumulator
    float acc = 0.0f;

    // Compute over K dimension in blocks of 32 (1 scale group)
    for (int kb = 0; kb < K / 32; kb++) {
        // Dequantize A block: get scale for this scale group
        float a_scale_val = e8m0_to_f32(__half2float(A_scale[m * (K/32) + kb]));
        
        // Dequantize B block: get scale for this scale group
        float b_scale_val = e8m0_to_f32(__half2float(B_scale[n * (K/32) + kb]));

        // Process 32 elements in K (16 half2 words)
        for (int k = 0; k < 16; k++) {
            int idx_a = m * (K/2) + kb * 16 + k;
            int idx_b = n * (K/2) + kb * 16 + k;

            // Load A as half2 (bf16)
            half2 a_h2 = A[idx_a];
            float a_val = static_cast<float>(__half2float(a_h2));
            
            // Load B FP4 packed (2 values per byte)
            uint8_t b_packed = B_q[idx_b];
            // Dequantize first FP4 value
            float b_val = mxfp4_to_f32(b_packed, b_scale_val);
            
            acc += a_val * b_val;
        }
    }

    // Store result (C is f32; caller converts to bf16)
    C[m * N + n] = acc;
}

torch::Tensor fp4_mm(
    const torch::Tensor& A,        // [M, K] bf16
    const torch::Tensor& B_q,      // [N, K] FP4 packed (as uint8)
    const torch::Tensor& A_scale,  // [M, K//32] E8M0 (bf16)
    const torch::Tensor& B_scale,  // [N, K//32] E8M0 (bf16)
    int M, int N, int K) {

    // Prepare input shapes: A is [M, K], but kernel expects [M, K/2] half2
    // B_q is [N, K], but kernel expects [N, K/2] uint8 (2 fp4 per byte)
    // A_scale: [M, K//32], B_scale: [N, K//32]
    
    TORCH_CHECK(A.dtype() == at::kBFloat16, "A must be bf16");
    TORCH_CHECK(B_q.dtype() == at::kUInt8, "B_q must be uint8");
    TORCH_CHECK(A_scale.dtype() == at::kBFloat16, "A_scale must be bf16");
    TORCH_CHECK(B_scale.dtype() == at::kBFloat16, "B_scale must be bf16");

    int K_half = K / 2;
    int K_scale = K / 32;

    // Output: [M, N] in f32
    auto options = torch::TensorOptions().dtype(torch::kFloat32).device(A.device());
    torch::Tensor C = torch::empty({M, N}, options);

    // Launch kernel
    const int BLOCK_M = 32;
    const int BLOCK_N = 32;
    dim3 block(BLOCK_N, BLOCK_M);
    dim3 grid((N + BLOCK_N - 1) / BLOCK_N, (M + BLOCK_M - 1) / BLOCK_M);

    hipLaunchKernelGGL(
        fp4_gemm_kernel,
        grid, block, 0, 0,
        (const half2*)A.data_ptr<c10::BFloat16>(),
        B_q.data_ptr<uint8_t>(),
        (const half*)A_scale.data_ptr<c10::BFloat16>(),
        (const half*)B_scale.data_ptr<c10::BFloat16>(),
        (float*)C.data_ptr<float>(),
        M, N, K_half
    );

    // Convert f32 -> bf16
    return C.to(torch::kBFloat16);
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("fp4_mm", &fp4_mm, "FP4 GEMM kernel (MI355X optimized)");
}
"""

module = load_inline(
    name='fp4_mm_kernel',
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=['fp4_mm'],
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-Xcompiler=-fPIC"],
    verbose=False,
)

def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N, _ = B.shape
    
    # Ensure contiguity
    A = A.contiguous()
    B_q = B_q.contiguous()
    B_scale_sh = B_scale_sh.contiguous()
    
    # Quantize A with same scheme as B
    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale = quant_func(A, shuffle=False)
    
    # Convert FP4 packed to uint8 tensor for kernel (A_q is dtypes.fp4x2)
    A_q_u8 = torch.empty(A_q.shape[0], A_q.shape[1] * 2, dtype=torch.uint8, device=A.device)
    # Unpack fp4x2 -> uint8 (each fp4x2 = 1 byte → 2 fp4 values)
    # But kernel expects [M, K] FP4 packed as uint8, where K is original K
    # Actually A_q has shape [M, K//2] (fp4x2 packed), so unpack to [M, K] uint8
    # For simplicity in this kernel, we treat the packed tensor as is
    # Since kernel uses 2 fp4 per uint8, we keep A_q as [M, K//2] and adjust indexing
    
    # Adjust: kernel expects A as [M, K/2] half2 and B_q as [N, K/2] uint8
    # So we need A_q to be [M, K/2] uint8 (but kernel reads as half2 → use A directly)
    # Let's use A directly as input (bf16) since kernel handles dequant
    # kernel uses A as [M, K/2] half2, which is just A.view(torch.float16).view(half2)
    
    # Actually: A is [M, K] bf16. Kernel expects [M, K/2] half2 (same memory layout)
    # So pass A directly with adjusted shape
    
    # Prepare for kernel call
    A_h2 = A.view(torch.float16).contiguous()
    
    # Ensure B_q is uint8 (it's already fp4x2, but stored as uint8 in B_shuffle)
    # B_shuffle is already shuffled and quantized as uint8
    B_q_u8 = B_shuffle.view(torch.uint8).contiguous()
    
    # Scale tensors: A_scale [M, K//32], B_scale_sh [N, K//32]
    A_scale_f32 = A_scale.to(torch.float32)
    B_scale_f32 = B_scale_sh.to(torch.float32)
    
    # Call kernel (M, N, K are original dims)
    C_f32 = module.fp4_mm(A_h2, B_q_u8, A_scale, B_scale_sh, M, N, K)
    
    return C_f32.to(torch.bfloat16)