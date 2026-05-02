#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM: FP4 MFMA with EXACT register layouts from AMD calculator.

Key fix from Session 90: A and B loading patterns decoded from
amd_matrix_instruction_calculator output.

A loading: thread tid reads 16 sequential bytes from A[tid%32] row (simple)
B loading: thread tid reads 16 sequential bytes from B[tid%32] row
           (B is stored as B[N, K/2] — each row IS one N column's K data)
D output: row = (r%4) + (r/4)*8 + (tid/32)*4, col = tid%32
"""

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

// MFMA intrinsic requires 8×int (32 bytes) for A/B registers, regardless of element format.
// For FP4 (cbsz=4): only first 16 bytes per thread are used (rest zero).
typedef int a_reg_t __attribute__((ext_vector_type(8)));
typedef int b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

#define TILE_M 32
#define TILE_N 32
#define TILE_K 64
#define TILE_K_BYTES 32
#define WAVESIZE 64

__global__ void mxfp4_gemm_exact(
    const uint8_t* __restrict__ A,   // [M, K/2] row-major
    const uint8_t* __restrict__ B,   // [N, K/2] row-major
    const uint8_t* __restrict__ As,  // [M, K/32] E8M0
    const uint8_t* __restrict__ Bs,  // [N, K/32] E8M0
    __hip_bfloat16* __restrict__ C,  // [M, N]
    int M, int N, int K
) {
    int bm = blockIdx.y * TILE_M;
    int bn = blockIdx.x * TILE_N;
    int tid = threadIdx.x;

    int K_half = K / 2;
    int K_scale = K / 32;
    int num_k_tiles = K / TILE_K;

    c_reg_t c_reg = {};
    for (int i = 0; i < 16; i++) c_reg[i] = 0.0f;

    int a_row = bm + (tid % 32);
    int b_col = bn + (tid % 32);

    for (int kt = 0; kt < num_k_tiles; kt++) {
        a_reg_t a_reg = {};
        b_reg_t b_reg = {};
        for (int i = 0; i < 8; i++) { a_reg[i] = 0; b_reg[i] = 0; }

        // ─── A loading: 16 bytes per thread into int register ──
        // Lanes 0-31: K bytes [0:16], Lanes 32-63: K bytes [16:32]
        int a_k_byte = kt * TILE_K_BYTES + (tid / 32) * 16;
        if (a_row < M && a_k_byte + 16 <= K_half) {
            const uint8_t* a_ptr = A + a_row * K_half + a_k_byte;
            uint8_t* a_bytes = reinterpret_cast<uint8_t*>(&a_reg);
            for (int i = 0; i < 16; i++) a_bytes[i] = a_ptr[i];
        }

        // ─── B loading (TRANSPOSED): 16 bytes per thread ──────
        // B[N, K/2] row-major — row n has K data for column n
        int b_k_byte = kt * TILE_K_BYTES + (tid / 32) * 16;
        if (b_col < N && b_k_byte + 16 <= K_half) {
            const uint8_t* b_ptr = B + b_col * K_half + b_k_byte;
            uint8_t* b_bytes = reinterpret_cast<uint8_t*>(&b_reg);
            for (int i = 0; i < 16; i++) b_bytes[i] = b_ptr[i];
        }

        // ─── Scales (1 E8M0 per thread, zero-extended to int) ─
        int sg = kt * 2 + (tid / 32);
        int sa = (a_row < M && sg < K_scale) ?
            (int)As[a_row * K_scale + sg] : 127;
        int sb = (b_col < N && sg < K_scale) ?
            (int)Bs[b_col * K_scale + sg] : 127;

        // ─── MFMA (cbsz=4=FP4 for A, blgp=4=FP4 for B) ──────
        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg, 4, 4, 0, sa, 0, sb);
    }

    // ─── D output (from AMD calculator): ───────────────────
    // c_reg[r] → D[(r%4) + (r/4)*8 + (tid/32)*4][tid%32]
    int out_col = bn + (tid % 32);
    if (out_col < N) {
        for (int r = 0; r < 16; r++) {
            int out_row = bm + (r % 4) + (r / 4) * 8 + (tid / 32) * 4;
            if (out_row < M) {
                C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
            }
        }
    }
}

void launch(torch::Tensor A, torch::Tensor B,
            torch::Tensor As, torch::Tensor Bs, torch::Tensor C) {
    int M = A.size(0), K = A.size(1) * 2, N = B.size(0);
    dim3 grid((N + TILE_N - 1) / TILE_N, (M + TILE_M - 1) / TILE_M);
    mxfp4_gemm_exact<<<grid, WAVESIZE>>>(
        A.data_ptr<uint8_t>(), B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(), Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()), M, N, K);
}
"""

CPP_SOURCE = (
    "void launch(torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor);"
)

try:
    _mod = load_inline(
        name="fp4mfma_exact",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[fp4mfma_exact] {e}")
    _OK = False


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    ks = K // 32

    if not _OK:
        print("[GEMM] FALLBACK to aiter")
        import aiter

        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
        return aiter.gemm_a4w4(
            Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
        )

    print("[GEMM] CUSTOM FP4 MFMA exact")
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    A_bytes = Aq.view(torch.uint8)
    As_bytes = Asc[:M, :ks].contiguous().view(torch.uint8)

    # B: use raw B_q (not shuffled) — our kernel reads B row-major
    B_bytes = B_q.view(torch.uint8)
    # B scale: need unshuffled scale
    _, Bsc = dynamic_mxfp4_quant(B.contiguous())
    Bs_bytes = Bsc[:N, :ks].contiguous().view(torch.uint8)

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
    _mod.launch(A_bytes, B_bytes, As_bytes, Bs_bytes, C)
    return C
