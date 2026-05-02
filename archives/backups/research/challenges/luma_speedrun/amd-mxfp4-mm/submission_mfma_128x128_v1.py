#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM: MFMA 128×128 8-wave ping-pong kernel.

Architecture:
- 512 threads = 8 wavefronts of 64 threads
- Output tile: 128×128 (4×4 grid of 32×32 MFMA tiles)
- K tile: 64 FP4 elements (32 bytes) per iteration
- Double-buffered LDS: 2 × (128×32 A + 128×32 B) = 16KB
- Wave ping-pong: Waves 0-3 compute while waves 4-7 load next tile
- Cooperative 128-bit global loads with XOR swizzle

Target: Beat aiter baseline 13.4µs across ranked shapes (M=4,16,32,64,256,4096)
"""

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


CPP_WRAPPER = """
void mxfp4_mfma_128x128_pingpong(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C,
    int M, int N, int K
);
"""

HIP_SRC = r"""
#include <hip/hip_runtime.h>
#include <hip/amd_detail/amd_hip_bf16.h>

// Tile dimensions
#define THREADS 512
#define WAVES 8
#define WAVESIZE 64
#define TILE_M 128
#define TILE_N 128
#define TILE_K 64
#define TILE_K_BYTES 32
#define MFMA_M 32
#define MFMA_N 32
#define MFMA_K 64

// MFMA tiles per output tile
#define MFMA_TILES_M 4
#define MFMA_TILES_N 4
#define MFMA_TILES_PER_WAVE 2  // Each wave handles 2 MFMA tiles along M or N

// MFMA register types
typedef int a_reg_t __attribute__((ext_vector_type(8)));
typedef int b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

// LDS layout: double-buffered
// Buffer A: 128 rows × 32 bytes per K-tile = 4KB per buffer
// Buffer B: 128 rows × 32 bytes per K-tile = 4KB per buffer
// Total per buffer: 8KB, Total: 16KB
#define LDS_BUF_SIZE 4096  // 128 * 32 bytes for A or B
#define LDS_A_OFFSET 0
#define LDS_B_OFFSET LDS_BUF_SIZE
#define LDS_BUF_TOTAL (2 * LDS_BUF_SIZE * 2)  // 2 buffers × (A + B)

// XOR swizzle pattern for LDS bank conflict avoidance
__device__ __forceinline__ int lds_swizzle(int row, int col) {
    return row ^ (col & 3);
}

__device__ __forceinline__ int e8m0_unshuffle(int idx, int N, int K_scale) {
    int row = idx / K_scale;
    int col = idx % K_scale;
    int i = row, j = col;
    return ((i/32)*32 + (j/8)*8 + (i%2)*4 + (j%8/4)*2 + (i%4/2)*1)*K_scale + (j%4);
}

__global__ __launch_bounds__(THREADS, 1)
void gemm_128x128_pingpong(
    const uint8_t* __restrict__ A,      // [M, K/2] packed FP4
    const uint8_t* __restrict__ B,      // [N, K/2] packed FP4
    const uint8_t* __restrict__ As,     // [M, K/32] E8M0 scales
    const uint8_t* __restrict__ Bs,     // [N, K/32] E8M0 scales
    __hip_bfloat16* __restrict__ C,     // [M, N] output
    int M, int N, int K
) {
    // Block coordinates
    int bm = blockIdx.y * TILE_M;
    int bn = blockIdx.x * TILE_N;
    int tid = threadIdx.x;
    int wave_id = tid / WAVESIZE;      // 0-7
    int lane_id = tid % WAVESIZE;      // 0-63

    // Dimensions
    int K_half = K / 2;
    int K_scale = K / 32;
    int num_k_tiles = K / TILE_K;

    // LDS base pointer (allocated dynamically)
    __shared__ uint8_t lds_mem[LDS_BUF_TOTAL];

    // Ping-pong buffer state (0 or 1)
    int ping_pong = 0;

    // LDS buffer offsets for current ping-pong state
    #define LDS_A(p) (lds_mem + (p) * LDS_BUF_SIZE * 2 + LDS_A_OFFSET)
    #define LDS_B(p) (lds_mem + (p) * LDS_BUF_SIZE * 2 + LDS_B_OFFSET)

    // Wave groups
    bool is_compute_wave = (wave_id < 4);  // Waves 0-3 compute
    bool is_load_wave = (wave_id >= 4);     // Waves 4-7 load

    int compute_wave_idx = wave_id;          // 0-3 within compute group
    int load_wave_idx = wave_id - 4;         // 0-3 within load group

    // Each compute wave handles a quadrant of the 4x4 MFMA grid
    // Wave 0: MFMA tiles (0,0), (0,1), (2,0), (2,1)
    // Wave 1: MFMA tiles (0,2), (0,3), (2,2), (2,3)
    // Wave 2: MFMA tiles (1,0), (1,1), (3,0), (3,1)
    // Wave 3: MFMA tiles (1,2), (1,3), (3,2), (3,3)
    int mfma_m_base = (compute_wave_idx / 2) * 2;  // 0 or 1, then scaled by 32
    int mfma_n_base = (compute_wave_idx % 2) * 2;  // 0 or 2

    // Accumulators: 4 per wave (2x2 tiles)
    c_reg_t c_reg_00 = {}, c_reg_01 = {};
    c_reg_t c_reg_10 = {}, c_reg_11 = {};
    for (int i = 0; i < 16; i++) {
        c_reg_00[i] = 0.0f; c_reg_01[i] = 0.0f;
        c_reg_10[i] = 0.0f; c_reg_11[i] = 0.0f;
    }

    // Scale accumulators
    int scale_00 = 0, scale_01 = 0;
    int scale_10 = 0, scale_11 = 0;

    // Initial load: all waves participate to load first K-tile
    // Cooperative load: 512 threads × 16 bytes = 8KB (fits 128×64 A and 128×64 B)
    #pragma unroll
    for (int load_iter = 0; load_iter < 2; load_iter++) {
        // Load A: 128 rows × 32 bytes
        // 512 threads load 8KB total
        int a_load_idx = tid + load_iter * THREADS;
        if (a_load_idx < TILE_M * TILE_K_BYTES) {
            int row = a_load_idx / TILE_K_BYTES;
            int col = a_load_idx % TILE_K_BYTES;
            int global_row = bm + row;
            int k_byte_off = col;

            // Swizzled LDS store
            int lds_row = lds_swizzle(row, col);
            if (global_row < M) {
                LDS_A(0)[lds_row * TILE_K_BYTES + col] = A[global_row * K_half + k_byte_off];
            } else {
                LDS_A(0)[lds_row * TILE_K_BYTES + col] = 0;
            }
        }

        // Load B: 128 rows × 32 bytes
        int b_load_idx = tid + load_iter * THREADS;
        if (b_load_idx < TILE_M * TILE_K_BYTES) {
            int row = b_load_idx / TILE_K_BYTES;
            int col = b_load_idx % TILE_K_BYTES;
            int global_col = bn + row;
            int k_byte_off = col;

            int lds_row = lds_swizzle(row, col);
            if (global_col < N) {
                LDS_B(0)[lds_row * TILE_K_BYTES + col] = B[global_col * K_half + k_byte_off];
            } else {
                LDS_B(0)[lds_row * TILE_K_BYTES + col] = 0;
            }
        }
    }

    __syncthreads();

    // Main K-loop with ping-pong
    for (int kt = 0; kt < num_k_tiles; kt++) {
        int next_kt = kt + 1;
        bool has_next = (next_kt < num_k_tiles);

        if (is_load_wave && has_next) {
            // Set priority high for loading
            __builtin_amdgcn_s_setprio(3);

            // Load next K-tile into ping_pong buffer
            // Each load wave handles part of the data
            int load_start = load_wave_idx * 128;  // 128 elements per wave

            #pragma unroll
            for (int i = 0; i < 128; i++) {
                int idx = load_start + i;
                if (idx < TILE_M * TILE_K_BYTES) {
                    int row = idx / TILE_K_BYTES;
                    int col = idx % TILE_K_BYTES;
                    int global_row = bm + row;
                    int k_byte_off = next_kt * TILE_K_BYTES + col;

                    int lds_row = lds_swizzle(row, col);
                    if (global_row < M && k_byte_off < K_half) {
                        LDS_A(ping_pong ^ 1)[lds_row * TILE_K_BYTES + col] =
                            A[global_row * K_half + k_byte_off];
                    } else {
                        LDS_A(ping_pong ^ 1)[lds_row * TILE_K_BYTES + col] = 0;
                    }
                }
            }

            // Load B similarly
            #pragma unroll
            for (int i = 0; i < 128; i++) {
                int idx = load_start + i;
                if (idx < TILE_M * TILE_K_BYTES) {
                    int row = idx / TILE_K_BYTES;
                    int col = idx % TILE_K_BYTES;
                    int global_col = bn + row;
                    int k_byte_off = next_kt * TILE_K_BYTES + col;

                    int lds_row = lds_swizzle(row, col);
                    if (global_col < N && k_byte_off < K_half) {
                        LDS_B(ping_pong ^ 1)[lds_row * TILE_K_BYTES + col] =
                            B[global_col * K_half + k_byte_off];
                    } else {
                        LDS_B(ping_pong ^ 1)[lds_row * TILE_K_BYTES + col] = 0;
                    }
                }
            }

            __builtin_amdgcn_s_setprio(0);
        }

        if (is_compute_wave) {
            // Set priority for compute
            __builtin_amdgcn_s_setprio(1);

            // Compute on current ping_pong buffer
            // Each compute wave does 4 MFMA tiles: (m,n) × (0,1) × (0,1)

            // Tile (mfma_m_base, mfma_n_base)
            {
                int a_row = mfma_m_base * MFMA_M + (lane_id % 32);
                int b_row = mfma_n_base * MFMA_N + (lane_id % 32);
                int k_half = (lane_id / 32) * 16;

                a_reg_t a_reg = {};
                b_reg_t b_reg = {};

                // Load from LDS
                uint8_t* a_ptr = LDS_A(ping_pong) + lds_swizzle(a_row, k_half) * TILE_K_BYTES + k_half;
                uint8_t* b_ptr = LDS_B(ping_pong) + lds_swizzle(b_row, k_half) * TILE_K_BYTES + k_half;

                #pragma unroll
                for (int i = 0; i < 16; i++) {
                    ((uint8_t*)&a_reg)[i] = a_ptr[i];
                    ((uint8_t*)&b_reg)[i] = b_ptr[i];
                }

                // Load scales
                int sg = kt * 2 + (lane_id / 32);
                int global_a_row = bm + a_row;
                int global_b_col = bn + mfma_n_base * MFMA_N + (lane_id % 32);
                int sa = (global_a_row < M && sg < K_scale) ?
                    (int)As[e8m0_unshuffle(global_a_row * K_scale + sg, M, K_scale)] : 127;
                int sb = (global_b_col < N && sg < K_scale) ?
                    (int)Bs[e8m0_unshuffle(global_b_col * K_scale + sg, N, K_scale)] : 127;

                // MFMA
                c_reg_00 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
                    a_reg, b_reg, c_reg_00, 4, 4, 0, sa, 0, sb);
            }

            // Tile (mfma_m_base, mfma_n_base + 1)
            {
                int a_row = mfma_m_base * MFMA_M + (lane_id % 32);
                int b_row = (mfma_n_base + 1) * MFMA_N + (lane_id % 32);
                int k_half = (lane_id / 32) * 16;

                a_reg_t a_reg = {};
                b_reg_t b_reg = {};

                uint8_t* a_ptr = LDS_A(ping_pong) + lds_swizzle(a_row, k_half) * TILE_K_BYTES + k_half;
                uint8_t* b_ptr = LDS_B(ping_pong) + lds_swizzle(b_row, k_half) * TILE_K_BYTES + k_half;

                #pragma unroll
                for (int i = 0; i < 16; i++) {
                    ((uint8_t*)&a_reg)[i] = a_ptr[i];
                    ((uint8_t*)&b_reg)[i] = b_ptr[i];
                }

                int sg = kt * 2 + (lane_id / 32);
                int global_a_row = bm + a_row;
                int global_b_col = bn + (mfma_n_base + 1) * MFMA_N + (lane_id % 32);
                int sa = (global_a_row < M && sg < K_scale) ?
                    (int)As[e8m0_unshuffle(global_a_row * K_scale + sg, M, K_scale)] : 127;
                int sb = (global_b_col < N && sg < K_scale) ?
                    (int)Bs[e8m0_unshuffle(global_b_col * K_scale + sg, N, K_scale)] : 127;

                c_reg_01 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
                    a_reg, b_reg, c_reg_01, 4, 4, 0, sa, 0, sb);
            }

            // Tile (mfma_m_base + 2, mfma_n_base)  - second pair
            {
                int a_row = (mfma_m_base + 2) * MFMA_M + (lane_id % 32);
                int b_row = mfma_n_base * MFMA_N + (lane_id % 32);
                int k_half = (lane_id / 32) * 16;

                a_reg_t a_reg = {};
                b_reg_t b_reg = {};

                uint8_t* a_ptr = LDS_A(ping_pong) + lds_swizzle(a_row, k_half) * TILE_K_BYTES + k_half;
                uint8_t* b_ptr = LDS_B(ping_pong) + lds_swizzle(b_row, k_half) * TILE_K_BYTES + k_half;

                #pragma unroll
                for (int i = 0; i < 16; i++) {
                    ((uint8_t*)&a_reg)[i] = a_ptr[i];
                    ((uint8_t*)&b_reg)[i] = b_ptr[i];
                }

                int sg = kt * 2 + (lane_id / 32);
                int global_a_row = bm + a_row;
                int global_b_col = bn + mfma_n_base * MFMA_N + (lane_id % 32);
                int sa = (global_a_row < M && sg < K_scale) ?
                    (int)As[e8m0_unshuffle(global_a_row * K_scale + sg, M, K_scale)] : 127;
                int sb = (global_b_col < N && sg < K_scale) ?
                    (int)Bs[e8m0_unshuffle(global_b_col * K_scale + sg, N, K_scale)] : 127;

                c_reg_10 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
                    a_reg, b_reg, c_reg_10, 4, 4, 0, sa, 0, sb);
            }

            // Tile (mfma_m_base + 2, mfma_n_base + 1)
            {
                int a_row = (mfma_m_base + 2) * MFMA_M + (lane_id % 32);
                int b_row = (mfma_n_base + 1) * MFMA_N + (lane_id % 32);
                int k_half = (lane_id / 32) * 16;

                a_reg_t a_reg = {};
                b_reg_t b_reg = {};

                uint8_t* a_ptr = LDS_A(ping_pong) + lds_swizzle(a_row, k_half) * TILE_K_BYTES + k_half;
                uint8_t* b_ptr = LDS_B(ping_pong) + lds_swizzle(b_row, k_half) * TILE_K_BYTES + k_half;

                #pragma unroll
                for (int i = 0; i < 16; i++) {
                    ((uint8_t*)&a_reg)[i] = a_ptr[i];
                    ((uint8_t*)&b_reg)[i] = b_ptr[i];
                }

                int sg = kt * 2 + (lane_id / 32);
                int global_a_row = bm + a_row;
                int global_b_col = bn + (mfma_n_base + 1) * MFMA_N + (lane_id % 32);
                int sa = (global_a_row < M && sg < K_scale) ?
                    (int)As[e8m0_unshuffle(global_a_row * K_scale + sg, M, K_scale)] : 127;
                int sb = (global_b_col < N && sg < K_scale) ?
                    (int)Bs[e8m0_unshuffle(global_b_col * K_scale + sg, N, K_scale)] : 127;

                c_reg_11 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
                    a_reg, b_reg, c_reg_11, 4, 4, 0, sa, 0, sb);
            }

            __builtin_amdgcn_s_setprio(0);
        }

        __syncthreads();

        // Swap ping-pong buffers
        ping_pong ^= 1;
    }

    // Write output
    if (is_compute_wave) {
        // Each wave writes 4 tiles of 32x32
        int tile_row_offsets[4] = {
            mfma_m_base * MFMA_M,
            mfma_m_base * MFMA_M,
            (mfma_m_base + 2) * MFMA_M,
            (mfma_m_base + 2) * MFMA_M
        };
        int tile_col_offsets[4] = {
            mfma_n_base * MFMA_N,
            (mfma_n_base + 1) * MFMA_N,
            mfma_n_base * MFMA_N,
            (mfma_n_base + 1) * MFMA_N
        };
        c_reg_t* c_regs[4] = {&c_reg_00, &c_reg_01, &c_reg_10, &c_reg_11};

        #pragma unroll
        for (int t = 0; t < 4; t++) {
            int out_col = bn + tile_col_offsets[t] + (lane_id % 32);
            if (out_col < N) {
                #pragma unroll
                for (int r = 0; r < 16; r++) {
                    int out_row = bm + tile_row_offsets[t] + (r % 4) + (r / 4) * 8 + (lane_id / 32) * 4;
                    if (out_row < M) {
                        C[out_row * N + out_col] = (__hip_bfloat16)((*c_regs[t])[r]);
                    }
                }
            }
        }
    }
}

void mxfp4_mfma_128x128_pingpong(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C,
    int M, int N, int K
) {
    dim3 grid((N + TILE_N - 1) / TILE_N, (M + TILE_M - 1) / TILE_M);
    dim3 block(THREADS);

    gemm_128x128_pingpong<<<grid, block>>>(
        (const uint8_t*)A_packed.data_ptr(),
        (const uint8_t*)B_packed.data_ptr(),
        (const uint8_t*)A_scale.data_ptr(),
        (const uint8_t*)B_scale.data_ptr(),
        (__hip_bfloat16*)C.data_ptr(),
        M, N, K
    );
}
"""

module = load_inline(
    name="mxfp4_mfma_128x128_pingpong",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=["mxfp4_mfma_128x128_pingpong"],
    verbose=False,
    extra_cuda_cflags=[
        "--offload-arch=gfx950",
        "-std=c++20",
        "-O3",
        "-mllvm",
        "-amdgpu-early-inline-all=true",
        "-mllvm",
        "-amdgpu-function-calls=false",
    ],
)


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
    """Reverse aiter's e8m0_shuffle to get linear [M, K/32] layout."""
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]


def custom_kernel(data: input_t) -> output_t:
    """MXFP4 GEMM using 128×128 8-wave ping-pong MFMA kernel."""
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    from aiter.utility.fp4_utils import e8m0_shuffle

    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    k_scale_groups = K // 32

    # Quantize A on the fly
    A_fp4, A_scale_raw = dynamic_mxfp4_quant(A.contiguous())

    # A_scale: trim to valid region, shuffle to match aiter format
    A_scale_trimmed = A_scale_raw[:M, :k_scale_groups].contiguous().view(dtypes.fp8_e8m0)
    A_scale_shuffled = e8m0_shuffle(A_scale_trimmed).view(torch.uint8)

    # B_scale: unshuffle from aiter format to linear [N, K/32]
    B_scale_sh_bytes = B_scale_sh.view(torch.uint8)
    bs_m, bs_n = B_scale_sh_bytes.shape
    B_scale_bytes = e8m0_unshuffle(B_scale_sh_bytes, N, k_scale_groups)

    # Use B_q (standard packed FP4), NOT B_shuffle
    A_packed = A_fp4.view(torch.uint8)
    B_packed = B_q.view(torch.uint8)

    # Output
    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    module.mxfp4_mfma_128x128_pingpong(
        A_packed, B_packed, A_scale_shuffled, B_scale_bytes, C, M, N, K
    )

    return C
