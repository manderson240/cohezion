#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM v3: FP4 MFMA with int-level register loads (no cache).

v1 (byte loads, no cache): 4/4 pass, 20-66µs
v2 (+ B cache): 3/4 fail (cache poisoning)
v3: int loads (4x fewer mem ops), no cache
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

typedef int a_reg_t __attribute__((ext_vector_type(8)));
typedef int b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

#define TILE_M 32
#define TILE_N 32
#define TILE_K 64
#define TILE_K_BYTES 32
#define WAVESIZE 64

__global__ void mxfp4_gemm_v3(
    const uint8_t* __restrict__ A,
    const uint8_t* __restrict__ B,
    const uint8_t* __restrict__ As,
    const uint8_t* __restrict__ Bs,
    __hip_bfloat16* __restrict__ C,
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

    int a_row = bm + (tid & 31);
    int b_col = bn + (tid & 31);
    int half_id = tid >> 5;  // 0 or 1

    // Precompute base pointers
    const uint8_t* a_base = A + a_row * K_half;
    const uint8_t* b_base = B + b_col * K_half;
    const uint8_t* as_base = As + a_row * K_scale;
    const uint8_t* bs_base = Bs + b_col * K_scale;

    bool a_valid = (a_row < M);
    bool b_valid = (b_col < N);

    for (int kt = 0; kt < num_k_tiles; kt++) {
        a_reg_t a_reg = {};
        b_reg_t b_reg = {};

        int k_byte_off = kt * TILE_K_BYTES + half_id * 16;

        // ─── A: 4 × int32 load (16 bytes) ───────────────────
        if (a_valid && k_byte_off + 16 <= K_half) {
            const int* src = reinterpret_cast<const int*>(a_base + k_byte_off);
            a_reg[0] = src[0]; a_reg[1] = src[1];
            a_reg[2] = src[2]; a_reg[3] = src[3];
        }

        // ─── B: 4 × int32 load (16 bytes) ───────────────────
        if (b_valid && k_byte_off + 16 <= K_half) {
            const int* src = reinterpret_cast<const int*>(b_base + k_byte_off);
            b_reg[0] = src[0]; b_reg[1] = src[1];
            b_reg[2] = src[2]; b_reg[3] = src[3];
        }

        // ─── Scales ──────────────────────────────────────────
        int sg = kt * 2 + half_id;
        int sa = (a_valid && sg < K_scale) ? (int)as_base[sg] : 127;
        int sb = (b_valid && sg < K_scale) ? (int)bs_base[sg] : 127;

        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg, 4, 4, 0, sa, 0, sb);
    }

    // ─── D output ────────────────────────────────────────────
    int out_col = bn + (tid & 31);
    if (out_col < N) {
        for (int r = 0; r < 16; r++) {
            int out_row = bm + (r & 3) + (r >> 2) * 8 + half_id * 4;
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
    mxfp4_gemm_v3<<<grid, WAVESIZE>>>(
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
        name="fp4mfma_v3",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[fp4mfma_v3] {e}")
    _OK = False


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    ks = K // 32

    if not _OK:
        import aiter

        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
        return aiter.gemm_a4w4(
            Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
        )

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    A_bytes = Aq.view(torch.uint8)
    As_bytes = Asc[:M, :ks].contiguous().view(torch.uint8)

    B_bytes = B_q.view(torch.uint8)
    _, Bsc = dynamic_mxfp4_quant(B.contiguous())
    Bs_bytes = Bsc[:N, :ks].contiguous().view(torch.uint8)

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
    _mod.launch(A_bytes, B_bytes, As_bytes, Bs_bytes, C)
    return C
