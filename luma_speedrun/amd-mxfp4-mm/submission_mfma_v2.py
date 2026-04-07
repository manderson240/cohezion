#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MFMA GEMM v2 — Multi-tile 32x64 with LDS double-buffering.

Upgrades from v1:
  - 32×64 output tile (2 MFMA 32×32 sub-tiles per K iteration)
  - A data reused across 2 N-tiles (2x A bandwidth reduction)
  - LDS for coalesced A loads + bank-conflict-free redistribution
  - 128 threads (2 wavefronts) for 32×64 output
  - Vectorized 128-bit global loads

Architecture:
  - Grid: (ceil(M/32), ceil(N/64)), 128 threads per block
  - Each block: 2 wavefronts, each computing one 32×32 MFMA tile
  - Wavefront 0: C[bm:bm+32, bn:bn+32]
  - Wavefront 1: C[bm:bm+32, bn+32:bn+64]
  - Both wavefronts share A data via LDS
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t


CPP_WRAPPER = """
void mxfp4_mfma_gemm_v2(
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

typedef int a_reg_t __attribute__((ext_vector_type(8)));
typedef int b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

// LDS: 32 rows × 32 bytes = 1024 bytes for A tile (reused by both wavefronts)
// Double-buffer: 2 × 1024 = 2048 bytes
#define LDS_A_SIZE 1024
#define A_BUF_SIZE (2 * LDS_A_SIZE)

__global__ __launch_bounds__(128, 4)
void mxfp4_mfma_kernel_v2(
    const uint8_t* __restrict__ A,
    const uint8_t* __restrict__ B,
    const uint8_t* __restrict__ As,
    const uint8_t* __restrict__ Bs,
    __hip_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    int bm = blockIdx.x * 32;
    int bn = blockIdx.y * 64;  // 64 columns per block
    int tid = threadIdx.x;      // 0-127

    // Which wavefront am I? (0 or 1)
    int wave_id = tid / 64;     // 0 or 1
    int lane = tid % 64;        // 0-63 within wavefront

    int K_half = K / 2;
    int k_tiles = K / 64;
    int k_scale_groups = K / 32;

    // This wavefront's N offset: wave 0 → bn, wave 1 → bn+32
    int my_bn = bn + wave_id * 32;

    // A row for this lane
    int a_row = bm + (lane & 31);
    bool a_valid = (a_row < M);

    // B column for this lane
    int b_col = my_bn + (lane & 31);
    bool b_valid = (b_col < N);

    // LDS for A tile (shared between wavefronts)
    __shared__ uint8_t lds_a[A_BUF_SIZE];

    c_reg_t c_reg = {};

    for (int kt = 0; kt < k_tiles; kt++) {
        int buf = (kt & 1) * LDS_A_SIZE;

        // === Cooperative A load into LDS ===
        // 128 threads load 32 rows × 32 bytes = 1024 bytes
        // Each thread loads 8 bytes (1024/128 = 8)
        {
            int load_idx = tid;  // 0-127
            // Map thread to (row, byte_offset): 32 rows × 32 bytes
            // Each row has 32 bytes for this K tile
            // thread 0-3 → row 0, bytes 0-7,8-15,16-23,24-31
            // thread 4-7 → row 1, etc.
            int load_row = load_idx / 4;  // 0-31
            int load_byte_off = (load_idx % 4) * 8;  // 0, 8, 16, 24

            int global_row = bm + load_row;
            int global_k_off = kt * 32 + load_byte_off;

            if (global_row < M && load_byte_off < 32) {
                const uint8_t* src = A + global_row * K_half + global_k_off;
                uint8_t* dst = lds_a + buf + load_row * 32 + load_byte_off;
                // 8-byte load (64-bit)
                *reinterpret_cast<uint2*>(dst) = *reinterpret_cast<const uint2*>(src);
            } else {
                uint8_t* dst = lds_a + buf + load_row * 32 + load_byte_off;
                *reinterpret_cast<uint2*>(dst) = {0, 0};
            }
        }
        __syncthreads();

        // === Load A from LDS into registers ===
        a_reg_t a_reg = {};
        {
            int lds_row = lane & 31;
            int lds_k_off = (lane >> 5) * 16;  // lanes 0-31→bytes 0-15, lanes 32-63→bytes 16-31
            const uint8_t* src = lds_a + buf + lds_row * 32 + lds_k_off;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&a_reg);
            *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*>(src);
        }

        // === Load B directly from global (each wavefront loads its own B tile) ===
        b_reg_t b_reg = {};
        if (b_valid) {
            int k_byte_off = kt * 32 + (lane >> 5) * 16;
            const uint8_t* src = B + b_col * K_half + k_byte_off;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&b_reg);
            *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*>(src);
        }

        // === Load scales ===
        int scale_idx = kt * 2 + (lane >> 5);
        int sa = a_valid ? (int)As[a_row * k_scale_groups + scale_idx] : 0;
        int sb = b_valid ? (int)Bs[b_col * k_scale_groups + scale_idx] : 0;

        // === MFMA 32x32x64 FP4 ===
        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg,
            4, 4,
            0, sa,
            0, sb
        );

        __syncthreads();  // Ensure LDS can be overwritten next iteration
    }

    // === Write output ===
    int out_col = my_bn + (lane & 31);
    if (out_col < N) {
        for (int r = 0; r < 16; r++) {
            int out_row = bm + (r & 3) + (r >> 2) * 8 + (lane >> 5) * 4;
            if (out_row < M) {
                C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
            }
        }
    }
}

void mxfp4_mfma_gemm_v2(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C,
    int M, int N, int K
) {
    dim3 grid((M + 31) / 32, (N + 63) / 64);
    dim3 block(128);

    mxfp4_mfma_kernel_v2<<<grid, block>>>(
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
    name="mxfp4_mfma_v2",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=["mxfp4_mfma_gemm_v2"],
    verbose=False,
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
)


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
    """Reverse aiter's e8m0_shuffle to get linear [M, K/32] layout."""
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]


def custom_kernel(data: input_t) -> output_t:
    """MXFP4 GEMM using MFMA v2 with LDS and multi-tile."""
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant

    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    k_scale_groups = K // 32

    A_fp4, A_scale_raw = dynamic_mxfp4_quant(A.contiguous())
    A_scale_bytes = A_scale_raw[:M, :k_scale_groups].contiguous().view(torch.uint8)

    B_scale_sh_bytes = B_scale_sh.view(torch.uint8)
    B_scale_bytes = e8m0_unshuffle(B_scale_sh_bytes, N, k_scale_groups)

    A_packed = A_fp4.view(torch.uint8)
    B_packed = B_q.view(torch.uint8)

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    module.mxfp4_mfma_gemm_v2(
        A_packed, B_packed, A_scale_bytes, B_scale_bytes, C,
        M, N, K
    )

    return C
