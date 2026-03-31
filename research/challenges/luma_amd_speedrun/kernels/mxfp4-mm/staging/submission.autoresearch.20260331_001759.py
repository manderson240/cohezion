import torch
from torch.utils.cpp_extension import load_inline
from aiter import QuantType, dtypes
from aiter.ops.shuffle import shuffle_weight
from task import input_t, output_t
import os

# Constants matching reference implementation
SCALE_GROUP_SIZE = 32
BLOCK_M = 64
BLOCK_N = 64
BLOCK_K = 64  # Must be divisible by 64 (256 bits for fp4 packing)
WARP_SIZE = 64
GRID_SIZE = (1024, 1024, 1)

# HIP kernel source with block-wise GEMM and lifted scales
HIP_SRC = r'''
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <hip/hip_bfloat16.h>

// Unpack fp4 to float (2 values per byte)
__device__ __forceinline__ void unpack_fp4(
    const uint8_t packed,
    float& a,
    float& b
) {
    uint8_t a_val = (packed >> 0) & 0x0F;
    uint8_t b_val = (packed >> 4) & 0x0F;
    
    // Convert signed 4-bit to float (0-7 = 0 to 7, 8-15 = -8 to -1)
    a = (a_val < 8) ? (float)a_val : (float)(a_val - 16);
    b = (b_val < 8) ? (float)b_val : (float)(b_val - 16);
}

// Convert E8M0 scale (uint8_t) to float
__device__ __forceinline__ float e8m0_to_float(uint8_t s) {
    union {
        uint8_t i;
        float f;
    } u;
    u.i = s;
    return u.f;
}

// FP4 GEMM kernel
__global__ void fp4_gemm(
    const uint8_t* __restrict__ A,    // [M, K/2] packed fp4
    const uint8_t* __restrict__ B,    // [N, K/2] packed fp4 (shuffled)
    const uint8_t* __restrict__ A_s,  // [M, K/32] E8M0 scales
    const uint8_t* __restrict__ B_s,  // [N, K/32] E8M0 scales
    const int M,
    const int N,
    const int K,
    float* __restrict__ C             // [M, N]
) {
    const int BLOCK_M_SIZE = 64;
    const int BLOCK_N_SIZE = 64;
    const int BLOCK_K_SIZE = 64;  // In fp4 units: K/2 / (K/64) = 32 fp4 values
    
    const int block_m = blockIdx.x;
    const int block_n = blockIdx.y;
    
    const int tid = threadIdx.x;
    
    // Shared memory buffers
    __shared__ uint8_t sA[1024];  // 64 * 64 / 2 = 2048 bytes / 2 = 1024 fp4 pairs
    __shared__ uint8_t sB[1024];
    __shared__ float sAS[64];     // Scale for A block
    __shared__ float sBS[64];     // Scale for B block
    
    // Each thread computes a 4x4 tile of output
    const int m_start = block_m * BLOCK_M_SIZE;
    const int n_start = block_n * BLOCK_N_SIZE;
    
    const int m_idx = m_start + (tid / 16);
    const int n_idx = n_start + (tid % 16);
    
    if (m_idx >= M || n_idx >= N) return;
    
    float acc = 0.0f;
    
    // Process K in blocks
    for (int kb = 0; kb < K / 2; kb += BLOCK_K_SIZE / 2) {
        // Load A and B data to shared memory
        const int a_idx = m_idx * (K/2) + kb + (tid % 64);
        const int b_idx = n_idx * (K/2) + kb + (tid % 64);
        
        if (tid < 64) {
            if (kb + tid/2 < K/2) {
                sA[tid] = A[a_idx];
                sB[tid] = B[b_idx];
            }
        }
        __syncthreads();
        
        // Process each fp4 pair in the block
        const int block_k = (tid / 2) % 32;
        const int vec_idx = tid / 64;
        if (vec_idx < 4) {
            const int k_idx = kb + block_k * 2 + vec_idx;
            
            // Unpack fp4 values
            float a_val0, a_val1, b_val0, b_val1;
            unpack_fp4(sA[block_k * 2 + vec_idx], a_val0, a_val1);
            unpack_fp4(sB[block_k * 2 + vec_idx], b_val0, b_val1);
            
            // Get scales
            const int scale_idx_a = m_idx * (K / 32) + block_k;
            const int scale_idx_b = n_idx * (K / 32) + block_k;
            float a_scale = e8m0_to_float(A_s[scale_idx_a]);
            float b_scale = e8m0_to_float(B_s[scale_idx_b]);
            
            // Compute contribution
            acc += (a_val0 * b_val0 + a_val1 * b_val1) * a_scale * b_scale;
        }
        __syncthreads();
    }
    
    // Store result
    const int c_idx = m_idx * N + n_idx;
    C[c_idx] = acc;
}

// Main kernel entry point
extern "C" void fp4_gemm_kernel(
    const uint8_t* A,
    const uint8_t* B,
    const uint8_t* A_s,
    const uint8_t* B_s,
    int M,
    int N,
    int K,
    float* C
) {
    dim3 grid(M / 64, N / 64);
    dim3 block(64);
    fp4_gemm<<<grid, block>>>(A, B, A_s, B_s, M, N, K, C);
}
'''

# C++ wrapper
CPP_WRAPPER = r'''
#include <torch/extension.h>
#include <ATen/ATen.h>
#include <ATen/cuda/CUDAContext.h>
#include <vector>

void fp4_gemm_kernel(
    const uint8_t* A,
    const uint8_t* B,
    const uint8_t* A_s,
    const uint8_t* B_s,
    int M,
    int N,
    int K,
    float* C
);

at::Tensor fp4_gemm(
    const at::Tensor& A,    // [M, K/2] uint8 (packed fp4)
    const at::Tensor& B,    // [N, K/2] uint8 (packed fp4)
    const at::Tensor& A_s,  // [M, K/32] uint8 (E8M0 scales)
    const at::Tensor& B_s   // [N, K/32] uint8 (E8M0 scales)
) {
    const auto M = A.size(0);
    const auto K = A.size(1) * 2;  // original K in elements
    const auto N = B.size(0);
    
    auto options = A.options().dtype(torch::kFloat32);
    at::Tensor C = at::empty({M, N}, options);
    
    auto stream = at::cuda::getCurrentCUDAStream();
    at::cuda::setCurrentCUDAStream(stream);
    
    fp4_gemm_kernel(
        A.data_ptr<uint8_t>(),
        B.data_ptr<uint8_t>(),
        A_s.data_ptr<uint8_t>(),
        B_s.data_ptr<uint8_t>(),
        M, N, K,
        C.data_ptr<float>()
    );
    
    return C;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("fp4_gemm", &fp4_gemm, "FP4 GEMM kernel (HIP)");
}
'''

# Load the kernel
module = load_inline(
    name='fp4_gemm_kernel',
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=['fp4_gemm'],
    extra_cuda_cflags=[
        "--offload-arch=gfx950",
        "-std=c++20",
        "-Xcompiler", "-fPIC"
    ],
    verbose=False,
    build_directory=os.path.join(os.path.dirname(__file__), "build")
)


def custom_kernel(data: input_t) -> output_t:
    """
    Custom HIP kernel for FP4 GEMM: A (bf16) @ B (MXFP4) -> C (bf16).
    
    Implementation details:
    - Quantize A to MXFP4 with per-1x32 scaling (same as reference)
    - Use pre-shuffled B and B scales from input
    - Launch custom HIP kernel with block-wise computation and lifted scales
    - Return bf16 output tensor
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    B = B.contiguous()
    m, k = A.shape
    n, _ = B.shape
    
    # Quantize A to MXFP4 with per-1x32 scaling (same as reference)
    from aiter import get_triton_quant
    quant_func = get_triton_quant(QuantType.per_1x32)
    A_q, A_scale = quant_func(A, shuffle=False)
    
    # Convert to packed uint8 format for kernel
    # A_q: [m, k//2] dtypes.fp4x2 -> [m, k//2] uint8
    A_packed = A_q.view(torch.uint8)
    
    # B_shuffle: [n, k//2] dtypes.fp4x2 -> [n, k//2] uint8
    B_packed = B_shuffle.view(torch.uint8)
    
    # A_scale: [m, k//32] E8M0 -> uint8
    A_scale_packed = A_scale.view(torch.uint8)
    
    # B_scale_sh: [n, k//32] E8M0 -> uint8
    B_scale_packed = B_scale_sh.view(torch.uint8)
    
    # Run the custom HIP kernel
    C_f32 = module.fp4_gemm(A_packed, B_packed, A_scale_packed, B_scale_packed)
    
    # Convert to bf16
    return C_f32.to(torch.bfloat16)