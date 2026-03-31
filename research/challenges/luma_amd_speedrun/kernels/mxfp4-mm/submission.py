import torch
from torch.utils.cpp_extension import load_inline
from aiter import QuantType, dtypes
from aiter.ops.shuffle import shuffle_weight
from task import input_t, output_t
from utils import make_match_reference

# Constants matching reference
SCALE_GROUP_SIZE = 32


HIP_SRC = r'''
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <hip/hip_bfloat16.h>
#include <rocwmma/rocwmma.hpp>

using namespace rocwmma;

// MI355X (gfx950) specific configs
using int8_t = int8_t;
using fp8_t = __hip_fp8_e4m3_fnuz;
using bf16_t = hip_bfloat16;
using f32 = float;

// Tile sizes optimized for MI355X
constexpr int WAVE_SIZE = 64;
constexpr int M_BLOCK = 128;
constexpr int N_BLOCK = 128;
constexpr int K_BLOCK = 128; // Must be multiple of 64 for fp4 pack

// MFMA config for MI355X
constexpr int MFMA_SIZE = 16;
constexpr int MFMA_TYPE = 32; // 16x16x32

// FP4 packing: 2 elements per byte
__device__ __forceinline__ void unpack_fp4(
    const uint8_t* packed, int idx, float& val, float& scale) {
    uint8_t byte = packed[idx / 2];
    uint8_t val_raw = (idx % 2 == 0) ? (byte >> 4) : (byte & 0xF);
    val_raw &= 0xF;
    
    // E8M0 scale handling
    // val_raw is 4-bit, but for MXFP4 we interpret as signed 4-bit (2's comp)
    int8_t signed_val = static_cast<int8_t>(val_raw);
    if (signed_val >= 8) signed_val -= 16; // convert to signed 4-bit
    
    val = static_cast<float>(signed_val);
}

__device__ __forceinline__ void unpack_fp4_with_scale(
    const uint8_t* packed, int idx,
    const float* scale_ptr, int scale_idx,
    float& val) {
    float raw_val;
    float scale_val;
    unpack_fp4(packed, idx, raw_val, scale_val);
    scale_val = scale_ptr[scale_idx];
    val = raw_val * scale_val;
}

// E8M0 to float conversion (exponent only, no mantissa)
__device__ __forceinline__ float e8m0_to_float(uint8_t e8m0) {
    // E8M0: exponent only, implicit 1.0 mantissa
    // Map 8-bit exponent to float
    // Handle special cases: 0 -> 0, 255 -> inf (but we clamp to max float)
    if (e8m0 == 0) return 0.0f;
    if (e8m0 == 255) return 1e30f; // large value instead of inf
    return __int2float_ssat(static_cast<int>(e8m0) - 127, 24);
}

__global__ void gemm_fp4_a4w4_mxfp4_bf16(
    const bf16_t* __restrict__ A,
    const uint8_t* __restrict__ B_packed,
    const float* __restrict__ B_scale,
    const float* __restrict__ A_scale,
    bf16_t* __restrict__ C,
    int M, int N, int K
) {
    // Block indices
    int block_m = blockIdx.x;
    int block_n = blockIdx.y;
    int block_k = blockIdx.z;
    
    // Each block handles a M_BLOCK x N_BLOCK tile of output
    // with K_BLOCK partial sums across K dimension
    
    // Per-thread MFMA fragments
    using FragmentA = fragment<matrix_a, MFMA_SIZE, MFMA_SIZE, MFMA_TYPE, hip_bfloat16, row_major>;
    using FragmentB = fragment<matrix_b, MFMA_SIZE, MFMA_SIZE, MFMA_TYPE, uint8_t, col_major>;
    using FragmentC = fragment<accumulator, MFMA_SIZE, MFMA_SIZE, MFMA_TYPE, float>;
    
    FragmentA frag_a;
    FragmentB frag_b;
    FragmentC frag_c;
    
    // Initialize C fragment to zero
    init_matrix(frag_c, 0.0f);
    
    // K-block loop
    for (int k_block = 0; k_block < K; k_block += K_BLOCK) {
        // Load A tile (bf16)
        #pragma unroll
        for (int i = 0; i < MFMA_SIZE; ++i) {
            #pragma unroll
            for (int j = 0; j < MFMA_SIZE; ++j) {
                int a_row = block_m * MFMA_SIZE + i;
                int a_col = k_block + block_k * MFMA_SIZE + j;
                if (a_row < M && a_col < K) {
                    // Load A with scale
                    int scale_idx = a_col / SCALE_GROUP_SIZE;
                    float scale_val = e8m0_to_float(static_cast<uint8_t>(A_scale[scale_idx]));
                    frag_a.data[i * MFMA_SIZE + j] = static_cast<float>(A[a_row * K + a_col]) * scale_val;
                }
            }
        }
        
        // Load B tile (fp4 packed) with scale
        #pragma unroll
        for (int i = 0; i < MFMA_SIZE; ++i) {
            #pragma unroll
            for (int j = 0; j < MFMA_SIZE; ++j) {
                int b_row = k_block + block_k * MFMA_SIZE + i;
                int b_col = block_n * MFMA_SIZE + j;
                
                if (b_row < K && b_col < N) {
                    int packed_idx = (b_row * (N/2) + b_col/2);
                    int scale_idx = b_row / SCALE_GROUP_SIZE;
                    float scale_val = e8m0_to_float(static_cast<uint8_t>(B_scale[scale_idx]));
                    
                    float val;
                    unpack_fp4_with_scale(B_packed, b_row * (N/2) + b_col/2, 
                                        const_cast<float*>(B_scale), scale_idx, val);
                    
                    // B is transposed in layout (we compute A @ B^T)
                    frag_b.data[j * MFMA_SIZE + i] = val * scale_val;
                }
            }
        }
        
        // Perform MFMA multiply-accumulate
        matrix_sync(frag_a);
        matrix_sync(frag_b);
        matrix_mma(frag_a, frag_b, frag_c);
        matrix_wait(frag_c);
    }
    
    // Store result
    #pragma unroll
    for (int i = 0; i < MFMA_SIZE; ++i) {
        #pragma unroll
        for (int j = 0; j < MFMA_SIZE; ++j) {
            int c_row = block_m * MFMA_SIZE + i;
            int c_col = block_n * MFMA_SIZE + j;
            if (c_row < M && c_col < N) {
                C[c_row * N + c_col] = static_cast<bf16_t>(frag_c.data[i * MFMA_SIZE + j]);
            }
        }
    }
}

// FP8 dequant + GEMM kernel (optimized for MI355X)
__global__ void fp8_gemm_mxfp4_bf16(
    const bf16_t* __restrict__ A,
    const uint8_t* __restrict__ B_packed,
    const float* __restrict__ A_scale,
    const float* __restrict__ B_scale,
    bf16_t* __restrict__ C,
    int M, int N, int K
) {
    // Thread indices
    int tx = threadIdx.x;
    int ty = threadIdx.y;
    int tz = threadIdx.z;
    
    int block_m = blockIdx.x;
    int block_n = blockIdx.y;
    
    // Shared memory for tiles
    __shared__ bf16_t sA[M_BLOCK];
    __shared__ bf16_t sB[N_BLOCK];
    
    // Accumulator for this thread tile
    float acc[MFMA_SIZE * MFMA_SIZE] = {0};
    
    // K-block loop
    for (int k = 0; k < K; k += MFMA_SIZE) {
        // Load A tile (with FP8 dequant)
        if (block_m * MFMA_SIZE + ty < M && k + tx < K) {
            int a_idx = (block_m * MFMA_SIZE + ty) * K + (k + tx);
            int scale_idx = (k + tx) / SCALE_GROUP_SIZE;
            float scale_val = e8m0_to_float(static_cast<uint8_t>(A_scale[scale_idx]));
            sA[ty * MFMA_SIZE + tx] = static_cast<bf16_t>(
                static_cast<float>(A[a_idx]) * scale_val);
        }
        
        // Load B tile (with FP8 dequant)
        if (k + ty < K && block_n * MFMA_SIZE + tx < N) {
            int b_idx = (k + ty) * (N/2) + (block_n * MFMA_SIZE + tx)/2;
            int scale_idx = (k + ty) / SCALE_GROUP_SIZE;
            float scale_val = e8m0_to_float(static_cast<uint8_t>(B_scale[scale_idx]));
            
            float val;
            unpack_fp4_with_scale(B_packed, b_idx, const_cast<float*>(B_scale), scale_idx, val);
            sB[tx * MFMA_SIZE + ty] = static_cast<bf16_t>(val * scale_val);
        }
        
        __syncthreads();
        
        // Compute partial product
        #pragma unroll
        for (int i = 0; i < MFMA_SIZE; ++i) {
            #pragma unroll
            for (int j = 0; j < MFMA_SIZE; ++j) {
                acc[i * MFMA_SIZE + j] += 
                    static_cast<float>(sA[ty * MFMA_SIZE + i]) *
                    static_cast<float>(sB[tx * MFMA_SIZE + j]);
            }
        }
        
        __syncthreads();
    }
    
    // Store result
    if (block_m * MFMA_SIZE + ty < M && block_n * MFMA_SIZE + tx < N) {
        int c_idx = (block_m * MFMA_SIZE + ty) * N + (block_n * MFMA_SIZE + tx);
        C[c_idx] = static_cast<bf16_t>(acc[ty * MFMA_SIZE + tx]);
    }
}
'''

CPP_WRAPPER = r'''
#include <torch/extension.h>
#include <vector>

// FP8 GEMM kernel wrapper
torch::Tensor fp8_gemm_mxfp4_bf16(
    const torch::Tensor& A,
    const torch::Tensor& B_packed,
    const torch::Tensor& A_scale,
    const torch::Tensor& B_scale
) {
    auto options = torch::TensorOptions()
        .dtype(torch::kBFloat16)
        .device(A.device());
    
    int M = A.size(0);
    int K = A.size(1);
    int N = B_packed.size(0) * 2; // B_packed is [N, K/2] in packed form
    
    auto C = torch::empty({M, N}, options);
    
    // Launch kernel
    dim3 block(MFMA_SIZE, MFMA_SIZE, 1);
    dim3 grid((M + MFMA_SIZE - 1) / MFMA_SIZE, 
              (N + MFMA_SIZE - 1) / MFMA_SIZE, 
              1);
    
    hipLaunchKernelGGL(
        fp8_gemm_mxfp4_bf16,
        grid, block, 0, 0,
        A.data_ptr<hip_bfloat16>(),
        B_packed.data_ptr<uint8_t>(),
        A_scale.data_ptr<float>(),
        B_scale.data_ptr<float>(),
        C.data_ptr<hip_bfloat16>(),
        M, N, K
    );
    
    return C;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("fp8_gemm_mxfp4_bf16", &fp8_gemm_mxfp4_bf16, "FP8 GEMM (MI355X optimized)");
}
'''

# Load the custom HIP kernel
module = load_inline(
    name='fp8_mm',
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=['fp8_gemm_mxfp4_bf16'],
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20"],
)


def custom_kernel(data: input_t) -> output_t:
    """
    Custom HIP kernel for FP8 GEMM with MXFP4 weights.
    
    Args:
        data: Tuple of (A, B, B_q, B_shuffle, B_scale_sh)
    
    Returns:
        output_t: C matrix in bf16
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    
    m, k = A.shape
    n, _ = B.shape
    
    # Ensure contiguous
    A = A.contiguous()
    B_shuffle = B_shuffle.contiguous()
    B_scale_sh = B_scale_sh.contiguous()
    
    # Prepare A scales: per-1x32 MXFP4 quantization
    A_scale = torch.empty((m, k // SCALE_GROUP_SIZE), dtype=torch.float32, device=A.device)
    
    # Compute A scales using same logic as reference
    from aiter.utility import fp4_utils
    A_scale_np = A.view(m, k // SCALE_GROUP_SIZE, SCALE_GROUP_SIZE).abs().amax(dim=-1)
    A_scale_np = torch.ceil(A_scale_np).to(torch.float32)
    # Clamp to [1e-30, 1e30] to avoid inf
    A_scale_np = torch.clamp(A_scale_np, 1e-30, 1e30)
    A_scale.copy_(A_scale_np)
    
    # Prepare B scales (already in correct format)
    B_scale = B_scale_sh
    
    # Pack A as FP4 if needed (for consistency with kernel expectations)
    # But kernel expects A in bf16 with scale - no need for packing A
    
    # Use the custom HIP kernel
    C = module.fp8_gemm_mxfp4_bf16(A, B_shuffle, A_scale, B_scale)
    
    return C