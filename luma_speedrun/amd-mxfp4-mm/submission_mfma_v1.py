#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MFMA GEMM v1 — Single-tile 32x32x64 FP4 MFMA via load_inline.

Uses __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4 (native FP4).
Register layouts verified in Session 91 (4/4 tests, max error 0.0).

Architecture:
  - 32×32 output tile per block, 64 threads (1 wavefront)
  - K loop: 64 FP4 elements per MFMA iteration
  - Scales passed as int args to intrinsic (per-thread)
  - Uses B_q (unshuffled) not B_shuffle
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t


CPP_WRAPPER = """
void mxfp4_mfma_gemm(
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

// MFMA register types (MUST be int vec8, NOT uint8_t!)
typedef int a_reg_t __attribute__((ext_vector_type(8)));
typedef int b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

__global__ void mxfp4_mfma_kernel(
    const uint8_t* __restrict__ A,    // [M, K/2] packed FP4
    const uint8_t* __restrict__ B,    // [N, K/2] packed FP4
    const uint8_t* __restrict__ As,   // [M, K/32] E8M0 scales (linear)
    const uint8_t* __restrict__ Bs,   // [N, K/32] E8M0 scales (linear)
    __hip_bfloat16* __restrict__ C,   // [M, N] output BF16
    int M, int N, int K
) {
    int bm = blockIdx.x * 32;   // block row start
    int bn = blockIdx.y * 32;   // block col start
    int tid = threadIdx.x;      // 0-63

    int K_half = K / 2;              // bytes per row
    int k_tiles = K / 64;            // MFMA tiles along K
    int k_scale_groups = K / 32;     // scale groups per row

    int a_row = bm + (tid & 31);     // which row of A this thread loads
    int b_col = bn + (tid & 31);     // which col of B this thread loads
    bool a_valid = (a_row < M);
    bool b_valid = (b_col < N);

    // Accumulator (zeroed)
    c_reg_t c_reg = {};

    for (int kt = 0; kt < k_tiles; kt++) {
        // === Load A tile (16 bytes per thread) ===
        a_reg_t a_reg = {};
        if (a_valid) {
            int k_byte_off = kt * 32 + (tid >> 5) * 16;
            const uint8_t* src = A + a_row * K_half + k_byte_off;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&a_reg);
            // Vectorized 16-byte load (128-bit)
            *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*>(src);
        }

        // === Load B tile (16 bytes per thread) ===
        b_reg_t b_reg = {};
        if (b_valid) {
            int k_byte_off = kt * 32 + (tid >> 5) * 16;
            const uint8_t* src = B + b_col * K_half + k_byte_off;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&b_reg);
            *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*>(src);
        }

        // === Load scales (1 byte per thread → int) ===
        int scale_idx = kt * 2 + (tid >> 5);
        int sa = a_valid ? (int)As[a_row * k_scale_groups + scale_idx] : 0;
        int sb = b_valid ? (int)Bs[b_col * k_scale_groups + scale_idx] : 0;

        // === MFMA: 32x32x64 FP4 with block scaling ===
        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg,
            4,     // cbsz = FP4 E2M1 for A
            4,     // blgp = FP4 E2M1 for B
            0, sa, // neg_a=0, scale_a
            0, sb  // neg_b=0, scale_b
        );
    }

    // === Write output (verified column-major per-thread pattern) ===
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

void mxfp4_mfma_gemm(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C,
    int M, int N, int K
) {
    dim3 grid((M + 31) / 32, (N + 31) / 32);
    dim3 block(64);  // 1 wavefront per block

    mxfp4_mfma_kernel<<<grid, block>>>(
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
    name="mxfp4_mfma_v1",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=["mxfp4_mfma_gemm"],
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
    """MXFP4 GEMM using MFMA 32x32x64 FP4 intrinsic via load_inline."""
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant

    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    k_scale_groups = K // 32

    # Quantize A on the fly
    A_fp4, A_scale_raw = dynamic_mxfp4_quant(A.contiguous())

    # A_scale: trim to valid region, keep as linear uint8
    A_scale_bytes = A_scale_raw[:M, :k_scale_groups].contiguous().view(torch.uint8)

    # B_scale: unshuffle from aiter format to linear [N, K/32]
    B_scale_sh_bytes = B_scale_sh.view(torch.uint8)
    # Get padded dimensions for unshuffle
    bs_m, bs_n = B_scale_sh_bytes.shape
    B_scale_bytes = e8m0_unshuffle(B_scale_sh_bytes, N, k_scale_groups)

    # Use B_q (standard packed FP4), NOT B_shuffle (CK-specific)
    A_packed = A_fp4.view(torch.uint8)
    B_packed = B_q.view(torch.uint8)

    # Output
    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    module.mxfp4_mfma_gemm(
        A_packed, B_packed, A_scale_bytes, B_scale_bytes, C,
        M, N, K
    )

    return C
