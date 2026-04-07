#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MFMA GEMM v3 — Shape-specialized dispatcher with 2-wavefront wide-N variant.

Two kernel variants dispatched by M:

1. standard kernel (M <= 64):  32×32 tile, 1 wavefront (identical to v1).
   Grid: (ceil(M/32), ceil(N/32)), 64 threads.
   Correct for all shapes; best for small M where block count is already minimal.

2. wide_n kernel  (M > 64):  32×64 tile, 2 wavefronts per block.
   Grid: (ceil(M/32), ceil(N/64)), 128 threads.
   Wave 0 → C[bm:bm+32, bn:bn+32]
   Wave 1 → C[bm:bm+32, bn+32:bn+64]
   Each wavefront independently loads its own A and B tiles (no LDS — avoids
   sync overhead that caused v2 regression). Halves N block count, reducing
   scheduler pressure for large M×N shapes like M=256,N=3072,K=1536.

Architecture notes (VERIFIED CORRECT from v1, Session 91):
  - Register types: int __attribute__((ext_vector_type(8))) for FP4 MFMA inputs
  - Output mapping: row = (r&3) + (r>>2)*8 + (tid>>5)*4,  col = tid&31
  - Scale index: kt*2 + (tid>>5)   — 2 scale groups per MFMA K-tile
  - Uses B_q (standard packed FP4), NOT B_shuffle (CK-specific layout)
  - Vectorized 128-bit loads (uint4) for A and B tiles
  - MFMA intrinsic: __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4
    cbsz=4 (FP4 E2M1 for A), blgp=4 (FP4 E2M1 for B)
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t


CPP_WRAPPER = """
void mxfp4_mfma_gemm_v3(
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

// MFMA register types (MUST be int vec, NOT uint8_t — verified correct in Session 91)
typedef int a_reg_t __attribute__((ext_vector_type(8)));
typedef int b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

// ─── Kernel 1: Standard — 32×32 tile, 1 wavefront (identical to v1) ────────
// Grid: (ceil(M/32), ceil(N/32)), 64 threads.
__global__ __launch_bounds__(64, 8)
void mxfp4_mfma_kernel_standard(
    const uint8_t* __restrict__ A,    // [M, K/2] packed FP4
    const uint8_t* __restrict__ B,    // [N, K/2] packed FP4
    const uint8_t* __restrict__ As,   // [M, K/32] E8M0 scales (linear layout)
    const uint8_t* __restrict__ Bs,   // [N, K/32] E8M0 scales (linear layout)
    __hip_bfloat16* __restrict__ C,   // [M, N] output BF16
    int M, int N, int K
) {
    int bm = blockIdx.x * 32;
    int bn = blockIdx.y * 32;
    int tid = threadIdx.x;  // 0..63

    int K_half = K / 2;
    int k_tiles = K / 64;
    int k_scale_groups = K / 32;

    // Per MFMA layout: thread tid loads row (tid&31) and K-half (tid>>5)
    int a_row = bm + (tid & 31);
    int b_col = bn + (tid & 31);
    bool a_valid = (a_row < M);
    bool b_valid = (b_col < N);

    c_reg_t c_reg = {};

    for (int kt = 0; kt < k_tiles; kt++) {
        a_reg_t a_reg = {};
        if (a_valid) {
            int k_byte_off = kt * 32 + (tid >> 5) * 16;
            const uint8_t* src = A + a_row * K_half + k_byte_off;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&a_reg);
            *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*>(src);
        }

        b_reg_t b_reg = {};
        if (b_valid) {
            int k_byte_off = kt * 32 + (tid >> 5) * 16;
            const uint8_t* src = B + b_col * K_half + k_byte_off;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&b_reg);
            *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*>(src);
        }

        int scale_idx = kt * 2 + (tid >> 5);
        int sa = a_valid ? (int)As[a_row * k_scale_groups + scale_idx] : 0;
        int sb = b_valid ? (int)Bs[b_col * k_scale_groups + scale_idx] : 0;

        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg,
            4, 4,
            0, sa,
            0, sb
        );
    }

    // Output mapping (verified correct in v1):
    //   c_reg[r] → C[bm + (r&3) + (r>>2)*8 + (tid>>5)*4][bn + (tid&31)]
    int out_col = bn + (tid & 31);
    if (out_col < N) {
        for (int r = 0; r < 16; r++) {
            int out_row = bm + (r & 3) + (r >> 2) * 8 + (tid >> 5) * 4;
            if (out_row < M) {
                C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
            }
        }
    }
}

// ─── Kernel 2: Wide-N — 32×64 tile, 2 wavefronts, no LDS ─────────────────
// Each block: 2 independent wavefronts computing adjacent 32×32 N-tiles.
// Wave 0 → C[bm:bm+32, bn:bn+32]
// Wave 1 → C[bm:bm+32, bn+32:bn+64]
// No shared memory — each wavefront loads its own A and B independently.
// This avoids the __syncthreads() overhead that caused v2 regression.
// Grid: (ceil(M/32), ceil(N/64)), 128 threads (2 wavefronts).
__global__ __launch_bounds__(128, 4)
void mxfp4_mfma_kernel_wide_n(
    const uint8_t* __restrict__ A,
    const uint8_t* __restrict__ B,
    const uint8_t* __restrict__ As,
    const uint8_t* __restrict__ Bs,
    __hip_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    int bm = blockIdx.x * 32;
    int bn = blockIdx.y * 64;  // 64 N-cols per block
    int tid = threadIdx.x;     // 0..127

    int wave_id = tid >> 6;    // 0 or 1
    int lane    = tid & 63;    // 0..63 within wavefront

    int K_half = K / 2;
    int k_tiles = K / 64;
    int k_scale_groups = K / 32;

    // Each wavefront is responsible for its own 32-col N slice
    int my_bn = bn + wave_id * 32;

    // Per MFMA layout: lane maps to row (lane&31) and K-half (lane>>5)
    int a_row = bm + (lane & 31);
    int b_col = my_bn + (lane & 31);
    bool a_valid = (a_row < M);
    bool b_valid = (b_col < N);

    c_reg_t c_reg = {};

    for (int kt = 0; kt < k_tiles; kt++) {
        a_reg_t a_reg = {};
        if (a_valid) {
            int k_byte_off = kt * 32 + (lane >> 5) * 16;
            const uint8_t* src = A + a_row * K_half + k_byte_off;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&a_reg);
            *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*>(src);
        }

        b_reg_t b_reg = {};
        if (b_valid) {
            int k_byte_off = kt * 32 + (lane >> 5) * 16;
            const uint8_t* src = B + b_col * K_half + k_byte_off;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&b_reg);
            *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*>(src);
        }

        int scale_idx = kt * 2 + (lane >> 5);
        int sa = a_valid ? (int)As[a_row * k_scale_groups + scale_idx] : 0;
        int sb = b_valid ? (int)Bs[b_col * k_scale_groups + scale_idx] : 0;

        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg,
            4, 4,
            0, sa,
            0, sb
        );
    }

    // Output: same mapping but use 'lane' for thread-local indices
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

// ─── Dispatcher ────────────────────────────────────────────────────────────
void mxfp4_mfma_gemm_v3(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C,
    int M, int N, int K
) {
    const uint8_t* Ap  = (const uint8_t*)A_packed.data_ptr();
    const uint8_t* Bp  = (const uint8_t*)B_packed.data_ptr();
    const uint8_t* Asc = (const uint8_t*)A_scale.data_ptr();
    const uint8_t* Bsc = (const uint8_t*)B_scale.data_ptr();
    __hip_bfloat16* Cp = (__hip_bfloat16*)C.data_ptr();

    if (M <= 64) {
        // Small-to-medium M: single wavefront 32×32 tiles
        dim3 grid((M + 31) / 32, (N + 31) / 32);
        mxfp4_mfma_kernel_standard<<<grid, 64, 0, 0>>>(Ap, Bp, Asc, Bsc, Cp, M, N, K);
    } else {
        // Large M: 2-wavefront 32×64 tiles, halve N block count
        dim3 grid((M + 31) / 32, (N + 63) / 64);
        mxfp4_mfma_kernel_wide_n<<<grid, 128, 0, 0>>>(Ap, Bp, Asc, Bsc, Cp, M, N, K);
    }
}
"""

module = load_inline(
    name="mxfp4_mfma_v3",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=["mxfp4_mfma_gemm_v3"],
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
    """MXFP4 GEMM with shape-specialized MFMA dispatch (v3)."""
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant

    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    k_scale_groups = K // 32

    # Quantize A on the fly
    A_fp4, A_scale_raw = dynamic_mxfp4_quant(A.contiguous())

    # Trim A scale to valid region and keep as linear uint8
    A_scale_bytes = A_scale_raw[:M, :k_scale_groups].contiguous().view(torch.uint8)

    # Unshuffle B scale from aiter format to linear [N, K/32]
    B_scale_sh_bytes = B_scale_sh.view(torch.uint8)
    B_scale_bytes = e8m0_unshuffle(B_scale_sh_bytes, N, k_scale_groups)

    # Use B_q (standard packed FP4), NOT B_shuffle (CK-specific layout)
    A_packed = A_fp4.view(torch.uint8)
    B_packed = B_q.view(torch.uint8)

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    module.mxfp4_mfma_gemm_v3(
        A_packed, B_packed, A_scale_bytes, B_scale_bytes, C,
        M, N, K
    )

    return C
