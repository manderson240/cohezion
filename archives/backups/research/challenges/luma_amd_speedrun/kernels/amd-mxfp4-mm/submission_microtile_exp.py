#!/usr/bin/env python3
"""
EXPERIMENTAL: Warp-Level Micro-Tiling for Small GEMM Shapes
===========================================================

HYPOTHESIS:
Standard GEMM implementations use block-level tiling (256 threads or more) with
shared memory for data reuse. For small M/N shapes (M,N < 128), the synchronization
overhead and shared memory latency dominate. Warp-level micro-tiling (64 threads)
eliminates __syncthreads() and uses register-level accumulation for lower latency.

APPROACH:
1. One warp (64 threads) = one output tile
2. No shared memory - direct global loads with register accumulation
3. MFMA 32x32x64 for the compute (maximizing register usage)
4. Each warp processes multiple tiles sequentially to amortize overhead
5. No inter-warp synchronization needed

EXPERIMENTAL RISK: MEDIUM-HIGH
- Without shared memory, we rely on L2 cache for bandwidth
- Strided access patterns may hurt coalescing
- Limited to shapes where register pressure allows 64-thread warps
- May be memory-bound for very small K

OPTIMAL SHAPES: Small M,N (32-128) with moderate K (256-1024)

FALLBACK: aiter.gemm_a4w4 for general cases

Author: Experimental Kernel Collection
Date: April 2026
"""

from __future__ import annotations

import os
import sys


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from reference import ref_kernel
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


# =============================================================================
# HIP Kernel: Warp-Level Micro-Tiling
# =============================================================================

HIP_SRC = r"""
#include <hip/hip_runtime.h>
#include <hip/amd_detail/amd_hip_bf16.h>

// FP4 E2M1 unpacking
__device__ inline float fp4_to_f32(uint8_t fp4) {
    float vals[16] = {0.0f, 0.5f, 1.0f, 1.5f, 2.0f, 3.0f, 4.0f, 6.0f,
                      -0.0f, -0.5f, -1.0f, -1.5f, -2.0f, -3.0f, -4.0f, -6.0f};
    return vals[fp4 & 0xF];
}

__device__ inline float unpack_fp4(uint8_t packed, int idx) {
    uint8_t nibble = (idx == 0) ? (packed & 0xF) : ((packed >> 4) & 0xF);
    return fp4_to_f32(nibble);
}

// E8M0 scale conversion
__device__ inline float e8m0_to_f32(uint8_t e8m0) {
    if (e8m0 == 0 || e8m0 == 255) return 0.0f;
    return exp2f((float)((int)e8m0 - 127));
}

// MFMA 32x32x64 for FP4 E2M1
__device__ inline void mfma_32x32x64_fp4(
    int* a_reg,      // 8 x int32 = 32 bytes (16 FP4 values used)
    int* b_reg,
    float* c_reg,    // 16 floats output
    int sa,          // Scale for A (E8M0 as int)
    int sb           // Scale for B (E8M0 as int)
) {
    typedef int a_vec_t __attribute__((ext_vector_type(8)));
    typedef int b_vec_t __attribute__((ext_vector_type(8)));
    typedef float c_vec_t __attribute__((ext_vector_type(16)));

    a_vec_t a_vec, b_vec;
    c_vec_t c_vec;

    // Load registers
    #pragma unroll
    for (int i = 0; i < 8; i++) {
        ((int*)&a_vec)[i] = a_reg[i];
        ((int*)&b_vec)[i] = b_reg[i];
    }
    #pragma unroll
    for (int i = 0; i < 16; i++) {
        c_vec[i] = c_reg[i];
    }

    // MFMA intrinsic - FP4 E2M1
    c_vec = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
        a_vec, b_vec, c_vec,
        4,    // cbsz = FP4 E2M1
        4,    // blgp = FP4 E2M1
        0, sa, 0, sb
    );

    // Store back
    #pragma unroll
    for (int i = 0; i < 16; i++) {
        c_reg[i] = c_vec[i];
    }
}

// Warp-level micro-tiling kernel
// Each warp (64 threads) handles a 32x32 output tile
// No shared memory, no synchronization, pure register-based accumulation
__global__ void warp_microtile_gemm(
    const uint8_t* __restrict__ A_q,      // [M, K/2] packed FP4
    const uint8_t* __restrict__ B_q,      // [N, K/2] packed FP4 (row-major)
    const uint8_t* __restrict__ A_scale,   // [M, K/32] E8M0
    const uint8_t* __restrict__ B_scale,   // [N, K/32] E8M0
    __hip_bfloat16* __restrict__ C,        // [M, N] output
    int M, int N, int K
) {
    // Grid: each block has multiple warps, each warp is independent
    const int tid = threadIdx.x;      // 0-63 within warp
    const int wid = threadIdx.y;      // warp index within block
    const int warps_per_block = blockDim.y;

    // Global warp ID
    int global_warp = blockIdx.x * warps_per_block + wid;
    int total_warps = gridDim.x * warps_per_block;

    // Tiles are 32x32, each warp handles one tile
    int tiles_m = (M + 31) / 32;
    int tiles_n = (N + 31) / 32;
    int total_tiles = tiles_m * tiles_n;

    // Each warp processes multiple tiles in round-robin fashion
    for (int tile_id = global_warp; tile_id < total_tiles; tile_id += total_warps) {
        int tile_m = tile_id / tiles_n;
        int tile_n = tile_id % tiles_n;

        int m_start = tile_m * 32;
        int n_start = tile_n * 32;
        int m_size = min(32, M - m_start);
        int n_size = min(32, N - n_start);

        // Thread position within MFMA tile
        // Lane mapping for MFMA 32x32x64 output
        int lane_row = (tid >> 5) * 4 + (tid & 3) + ((tid >> 2) & 7) * 4;
        int lane_col = tid & 31;

        // Accumulator in registers (16 floats per thread for 32x32 output)
        float accum[16];
        #pragma unroll
        for (int i = 0; i < 16; i++) accum[i] = 0.0f;

        // K-dimension tiles (64 FP4 elements = 32 bytes = 1 scale group)
        int k_tiles = K / 64;

        // Register buffers for A and B
        int a_reg[8];
        int b_reg[8];

        for (int kt = 0; kt < k_tiles; kt++) {
            int k_start = kt * 64;

            // Load A tile (32 rows x 64 K)
            // Thread loads its portion based on lane id
            int a_row = m_start + (tid & 31);
            int a_k_off = k_start / 2 + (tid >> 5) * 16;

            // Zero registers first
            #pragma unroll
            for (int i = 0; i < 8; i++) a_reg[i] = 0;

            // Load FP4 data
            if (a_row < m_start + m_size) {
                const uint8_t* a_ptr = A_q + a_row * (K / 2) + a_k_off;
                uint8_t* a_bytes = (uint8_t*)a_reg;
                #pragma unroll
                for (int i = 0; i < 16; i++) {
                    if (a_k_off + i < K / 2) {
                        a_bytes[i] = a_ptr[i];
                    }
                }
            }

            // Load B tile (32 cols x 64 K)
            // B is stored as [N, K/2] row-major
            int b_col = n_start + (tid & 31);
            int b_k_off = k_start / 2 + (tid >> 5) * 16;

            #pragma unroll
            for (int i = 0; i < 8; i++) b_reg[i] = 0;

            if (b_col < n_start + n_size) {
                const uint8_t* b_ptr = B_q + b_col * (K / 2) + b_k_off;
                uint8_t* b_bytes = (uint8_t*)b_reg;
                #pragma unroll
                for (int i = 0; i < 16; i++) {
                    if (b_k_off + i < K / 2) {
                        b_bytes[i] = b_ptr[i];
                    }
                }
            }

            // Load scales
            // A scale: [M, K/32], each group of 32 K values shares 1 scale
            // B scale: [N, K/32]
            int scale_k = kt * 2 + (tid >> 5);
            int sa = 127;  // Default scale = 1.0
            int sb = 127;

            if (a_row < M && scale_k < K / 32) {
                sa = A_scale[a_row * (K / 32) + scale_k];
            }
            if (b_col < N && scale_k < K / 32) {
                sb = B_scale[b_col * (K / 32) + scale_k];
            }

            // Execute MFMA
            mfma_32x32x64_fp4(a_reg, b_reg, accum, sa, sb);
        }

        // Write output using MFMA output mapping
        // c_reg[r] -> D[row][col] where:
        //   col = tid % 32
        //   row = (r % 4) + (r / 4) * 8 + (tid / 32) * 4
        #pragma unroll
        for (int r = 0; r < 16; r++) {
            int out_row = m_start + (r & 3) + (r >> 2) * 8 + (tid >> 5) * 4;
            int out_col = n_start + (tid & 31);

            if (out_row < M && out_col < N) {
                C[out_row * N + out_col] = (__hip_bfloat16)accum[r];
            }
        }
    }
}

// Entry point
void launch_microtile_gemm(
    torch::Tensor A_q,
    torch::Tensor B_q,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C,
    int M, int N, int K
) {
    // Launch configuration
    int warps_per_block = 8;  // 8 warps = 512 threads per block
    int num_blocks = 128;      // Sufficient for MI355X

    dim3 threads(64, warps_per_block);  // 64 threads per warp
    dim3 blocks(num_blocks);

    warp_microtile_gemm<<<blocks, threads>>>(
        A_q.data_ptr<uint8_t>(),
        B_q.data_ptr<uint8_t>(),
        A_scale.data_ptr<uint8_t>(),
        B_scale.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K
    );
}
"""

CPP_WRAPPER = """
void launch_microtile_gemm(
    torch::Tensor A_q,
    torch::Tensor B_q,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C,
    int M, int N, int K
);
"""

# Module cache
_microtile_module = None


def get_microtile_module():
    global _microtile_module
    if _microtile_module is None:
        _microtile_module = load_inline(
            name="warp_microtile_gemm",
            cpp_sources=[CPP_WRAPPER],
            cuda_sources=[HIP_SRC],
            functions=["launch_microtile_gemm"],
            extra_cuda_cflags=[
                "--offload-arch=gfx950",
                "-std=c++20",
                "-O3",
                "-ffast-math",
                "-funroll-loops",
            ],
            verbose=False,
        )
    return _microtile_module


# =============================================================================
# Experimental Kernel Entry Point
# =============================================================================


def custom_kernel(data: input_t) -> output_t:
    """
    Experimental warp-level micro-tiling GEMM.

    Hypothesis: Eliminating block-level synchronization via warp-level
    micro-tiling reduces overhead for small M,N shapes.

    Optimal shapes: M,N in [32, 128], K in [256, 1024]
    Risk: Memory-bound without shared memory caching for large K
    """
    A_bf16, B_bf16, B_q, B_shuffle, B_scale = data

    M = A_bf16.shape[0]
    N = B_bf16.shape[0]
    K = A_bf16.shape[1]

    # ====================================================================
    # EXPERIMENTAL GUARD: Only for small shapes where micro-tiling helps
    # ====================================================================
    if M > 256 or N > 256:
        # Large shapes need shared memory blocking
        return _optimized_baseline(data)

    if K % 64 != 0:
        # Our MFMA kernel requires K divisible by 64
        return _optimized_baseline(data)

    try:
        return _experimental_microtile_kernel(data)
    except Exception as e:
        print(f"[EXPERIMENTAL] Microtile kernel failed: {e}, using fallback", file=sys.stderr)
        return _optimized_baseline(data)


def _experimental_microtile_kernel(data):
    """Internal micro-tiling implementation."""
    import aiter

    A_bf16, B_bf16, B_q, B_shuffle, B_scale = data

    M = A_bf16.shape[0]
    N = B_bf16.shape[0]
    K = A_bf16.shape[1]

    device = A_bf16.device

    # Quantize A to FP4
    A_q, A_scale = aiter.dynamic_mxfp4_quant(A_bf16)

    # Prepare output
    C = torch.empty((M, N), dtype=torch.bfloat16, device=device)

    # Launch experimental kernel
    module = get_microtile_module()
    module.launch_microtile_gemm(A_q, B_q, A_scale, B_scale, C, M, N, K)

    return C


def _optimized_baseline(data):
    """Optimized baseline using aiter.gemm_a4w4."""
    import aiter

    A_bf16, B_bf16, B_q, B_shuffle, B_scale = data

    # Quantize A
    A_q, A_scale = aiter.dynamic_mxfp4_quant(A_bf16)

    # Use optimized API
    return aiter.gemm_a4w4(A_q, B_shuffle, A_scale, B_scale)


# Keep baseline accessible
baseline_kernel = ref_kernel


if __name__ == "__main__":
    print("=" * 70)
    print("EXPERIMENTAL: Warp-Level Micro-Tiling for Small GEMM Shapes")
    print("=" * 70)
    print("\nHypothesis: 64-thread warp tiles eliminate __syncthreads overhead")
    print("Optimal: M,N in [32, 128], K divisible by 64")
    print("Expected: Medium risk - may be memory-bound without LDS")
    print("Fallback: aiter.gemm_a4w4 with optimized parameters")
    print("=" * 70)
