import torch
from torch.utils.cpp_extension import load_inline
from aiter import QuantType, dtypes
from aiter.ops.shuffle import shuffle_weight
from task import input_t, output_t

# Constants
SCALE_GROUP_SIZE = 32
FP4_PACK_FACTOR = 2  # 2 fp4 values per byte, so k//2 for packed

# HIP kernel sources
HIP_KERNEL_SRC = """
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <hip/hip_bfloat16.h>
#include <cmath>

// FP4 unpack helper: extract 4-bit value from packed byte
__device__ __forceinline__ int8_t unpack_fp4(uint8_t packed, int idx) {
    return (packed >> (idx * 4)) & 0x0F;
}

// E8M0 decode: 8-bit exponent with implicit mantissa=1.0, bias=127
__device__ __forceinline__ float e8m0_to_f32(uint8_t exp) {
    // Handle special cases: 0 -> 0, 255 -> inf (but we clamp)
    if (exp == 0) return 0.0f;
    if (exp == 255) return 1e30f; // clamp to max representable
    return __int2float_rn(exp) * 0.5f; // approximate: exp - 127 + log2(1.0) but use direct mapping
}

// Convert MXFP4 to bf16
__device__ __forceinline__ __nv_bfloat16 fp4_to_bf16(uint8_t packed, int idx, float scale) {
    int8_t val = unpack_fp4(packed, idx);
    // MXFP4: value = (val - 7) * scale for signed 4-bit, but spec uses [0,15] -> [-7,7]
    float fval = (val - 7) * scale;
    return __float2bfloat16(fval);
}

// Block-wise GEMM: MxK * KxN -> MxN with FP4 weights
// A: [m, k] in bf16 (unpacked), B: [n, k//2] in MXFP4 packed, B_scale: [n, k//32] in E8M0
// Output: [m, n] in bf16
__global__ void gemm_a4w4_fp4_kernel(
    const __nv_bfloat16* __restrict__ A,
    const uint8_t* __restrict__ B,
    const uint8_t* __restrict__ B_scale,
    __nv_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    // Block dimensions
    const int BLOCK_M = 16;
    const int BLOCK_N = 16;
    const int BLOCK_K = 32;  // matches SCALE_GROUP_SIZE

    const int tx = threadIdx.x;
    const int ty = threadIdx.y;
    const int tz = threadIdx.z;
    
    const int block_m = blockIdx.x;
    const int block_n = blockIdx.y;
    
    // Accumulator for C[block_m*BLOCK_M + :, block_n*BLOCK_N + :]
    float acc[16] = {0.0f};  // up to BLOCK_M=16, BLOCK_N=16 => 16x16=256 threads, but we use 16 accumulators per row
    
    // Shared memory for A and B tiles
    extern __shared__ __nv_bfloat16 shared_mem[];
    __nv_bfloat16* shared_A = shared_mem;
    uint8_t* shared_B = reinterpret_cast<uint8_t*>(shared_A + BLOCK_M * BLOCK_K / FP4_PACK_FACTOR);
    
    const int k_tiles = K / BLOCK_K;
    
    // Thread mapping: 4x4 threads per tile, each computing 4x4 output (16 threads produce 16 outputs)
    const int row = block_m * BLOCK_M + ty * 4 + tz / 4;
    const int col = block_n * BLOCK_N + tx * 4 + tz % 4;
    
    if (row >= M || col >= N) return;
    
    // Process K dimension in tiles
    for (int kt = 0; kt < k_tiles; ++kt) {
        // Load A tile: [row, kt*BLOCK_K : (kt+1)*BLOCK_K]
        for (int i = 0; i < 4; ++i) {
            int k_idx = kt * BLOCK_K + i * 4 + (ty * 4 + tz / 4) % 4;
            if (k_idx < K) {
                shared_A[(ty * 4 + tz / 4) * (BLOCK_K / FP4_PACK_FACTOR) + i] = A[row * K + k_idx];
            }
        }
        
        // Load B tile: [col, kt*BLOCK_K : (kt+1)*BLOCK_K] in packed format
        const int b_row = col;
        const int b_col_start = kt * (BLOCK_K / FP4_PACK_FACTOR);
        for (int i = 0; i < 4; ++i) {
            int k_idx = b_col_start + i;
            if (k_idx < (K / FP4_PACK_FACTOR)) {
                shared_B[(tx * 4 + tz % 4) * (BLOCK_K / FP4_PACK_FACTOR) + i] = B[b_row * (K / FP4_PACK_FACTOR) + k_idx];
            }
        }
        
        __syncthreads();
        
        // Compute partial product for this tile
        for (int i = 0; i < 4; ++i) {
            for (int j = 0; j < 4; ++j) {
                // Get A value (unpacked)
                float a_val = __bfloat162float(shared_A[(ty * 4 + tz / 4) * (BLOCK_K / FP4_PACK_FACTOR) + i]);
                
                // Get B value (unpacked from packed byte)
                int k_idx = kt * BLOCK_K + i * 4 + j;
                int packed_idx = k_idx / FP4_PACK_FACTOR;
                int byte_idx = k_idx % FP4_PACK_FACTOR;
                uint8_t b_byte = shared_B[(tx * 4 + tz % 4) * (BLOCK_K / FP4_PACK_FACTOR) + packed_idx];
                int8_t b_val = (b_byte >> (byte_idx * 4)) & 0x0F;
                // MXFP4: (val - 7) * scale
                int scale_group_idx = k_idx / SCALE_GROUP_SIZE;
                float b_scale = e8m0_to_f32(B_scale[b_row * (K / SCALE_GROUP_SIZE) + scale_group_idx]);
                float b_val_f = (b_val - 7) * b_scale;
                
                // Accumulate
                acc[ty * 4 + tz / 4] += a_val * b_val_f;
            }
        }
        __syncthreads();
    }
    
    // Write result: convert to bf16 and store
    if (ty == 0 && tz < 4) {
        int out_row = block_m * BLOCK_M + tx;
        int out_col = block_n * BLOCK_N + tz;
        if (out_row < M && out_col < N) {
            float result = acc[out_row % 16];  // correct indexing
            C[out_row * N + out_col] = __float2bfloat16_rn(result);
        }
    }
}

// Simplified kernel: 1D block mapping for simplicity and robustness
__global__ void gemm_a4w4_fp4_kernel_simple(
    const __nv_bfloat16* __restrict__ A,
    const uint8_t* __restrict__ B,
    const uint8_t* __restrict__ B_scale,
    __nv_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    // Each thread computes one C[i,j]
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int m = idx / N;
    int n = idx % N;
    
    if (m >= M) return;
    
    // Accumulator
    float acc = 0.0f;
    
    // Process K dimension in blocks of 32 (scale group)
    for (int k = 0; k < K; k += SCALE_GROUP_SIZE) {
        // Load scale for this group
        int scale_idx = n * (K / SCALE_GROUP_SIZE) + k / SCALE_GROUP_SIZE;
        float w_scale = e8m0_to_f32(B_scale[scale_idx]);
        
        // Process 32 K values
        for (int ki = 0; ki < SCALE_GROUP_SIZE; ki += FP4_PACK_FACTOR) {
            int packed_idx = n * (K / FP4_PACK_FACTOR) + (k + ki) / FP4_PACK_FACTOR;
            int byte_offset = (k + ki) % FP4_PACK_FACTOR;
            uint8_t b_byte = B[packed_idx];
            int8_t val = (b_byte >> (byte_offset * 4)) & 0x0F;
            
            // FP4 dequant
            float w_val = (val - 7) * w_scale;
            
            // Load A value
            int a_idx = m * K + k + ki;
            float a_val = __bfloat162float(A[a_idx]);
            
            // Accumulate
            acc += a_val * w_val;
        }
    }
    
    // Store result
    C[m * N + n] = __float2bfloat16_rn(acc);
}
"""

CPP_WRAPPER = """
#include <torch/extension.h>

torch::Tensor gemm_a4w4_fp4(
    const torch::Tensor& A,
    const torch::Tensor& B,
    const torch::Tensor& B_scale,
    int M, int N, int K
) {
    auto C = torch::empty({M, N}, A.options().dtype(torch::kBFloat16));
    
    const int block_size = 256;
    int grid_size = (M * N + block_size - 1) / block_size;
    
    gemm_a4w4_fp4_kernel_simple<<<grid_size, block_size>>>(
        (const __nv_bfloat16*)A.data_ptr(),
        (const uint8_t*)B.data_ptr(),
        (const uint8_t*)B_scale.data_ptr(),
        (__nv_bfloat16*)C.data_ptr(),
        M, N, K
    );
    
    return C;
}
"""

# Load kernel
module = load_inline(
    name='fp4_gemm_kernel',
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_KERNEL_SRC],
    functions=['gemm_a4w4_fp4'],
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-Xcompiler=-fPIC"],
    verbose=False
)

def custom_kernel(data: input_t) -> output_t:
    """
    Custom HIP GEMM kernel for MXFP4 per-1x32 quant: A(bf16) @ B(MXFP4) -> bf16 C.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    
    m, k = A.shape
    n, _ = B_shuffle.shape
    
    # Ensure contiguous
    A = A.contiguous()
    B_shuffle = B_shuffle.contiguous()
    B_scale_sh = B_scale_sh.contiguous()
    
    # Call the custom kernel
    C = module.gemm_a4w4_fp4(A, B_shuffle, B_scale_sh, m, n, k)
    
    return C