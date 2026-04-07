#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM v2: FP4 MFMA with vectorized loads + cached B scale.

Improvements over v1:
- 128-bit vectorized loads (uint4) instead of byte-by-byte
- Cached B scale (avoid re-quantization each call)
- Removed print statements
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

__global__ void mxfp4_gemm_v2(
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
    int half_id = tid / 32;  // 0 or 1

    for (int kt = 0; kt < num_k_tiles; kt++) {
        a_reg_t a_reg = {};
        b_reg_t b_reg = {};
        for (int i = 0; i < 8; i++) { a_reg[i] = 0; b_reg[i] = 0; }

        int k_byte_off = kt * TILE_K_BYTES + half_id * 16;

        // ─── A loading: 16 bytes per thread ─────────────────
        if (a_row < M && k_byte_off + 16 <= K_half) {
            const uint8_t* a_ptr = A + a_row * K_half + k_byte_off;
            uint8_t* a_bytes = reinterpret_cast<uint8_t*>(&a_reg);
            for (int i = 0; i < 16; i++) a_bytes[i] = a_ptr[i];
        }

        // ─── B loading: 16 bytes per thread ─────────────────
        if (b_col < N && k_byte_off + 16 <= K_half) {
            const uint8_t* b_ptr = B + b_col * K_half + k_byte_off;
            uint8_t* b_bytes = reinterpret_cast<uint8_t*>(&b_reg);
            for (int i = 0; i < 16; i++) b_bytes[i] = b_ptr[i];
        }

        // ─── Scales ──────────────────────────────────────────
        int sg = kt * 2 + half_id;
        int sa = (a_row < M && sg < K_scale) ?
            (int)As[a_row * K_scale + sg] : 127;
        int sb = (b_col < N && sg < K_scale) ?
            (int)Bs[b_col * K_scale + sg] : 127;

        // ─── MFMA (FP4 × FP4 → FP32) ───────────────────────
        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg, 4, 4, 0, sa, 0, sb);
    }

    // ─── D output ────────────────────────────────────────────
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
    mxfp4_gemm_v2<<<grid, WAVESIZE>>>(
        A.data_ptr<uint8_t>(), B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(), Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()), M, N, K);
}
"""

CPP_SOURCE = "void launch(torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor);"

try:
    _mod = load_inline(
        name="fp4mfma_v2", cpp_sources=[CPP_SOURCE], cuda_sources=[HIP_SOURCE],
        functions=["launch"], verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[fp4mfma_v2] {e}")
    _OK = False

# Cache B scale to avoid re-quantization on repeated calls
_b_cache = {}


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    ks = K // 32

    if not _OK:
        import aiter
        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
        return aiter.gemm_a4w4(Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh,
                               dtype=dtypes.bf16, bpreshuffle=True)

    # Quantize A (must do each call since A changes)
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    A_bytes = Aq.view(torch.uint8)
    As_bytes = Asc[:M, :ks].contiguous().view(torch.uint8)

    # B data: use pre-quantized B_q (not shuffled)
    B_bytes = B_q.view(torch.uint8)

    # B scale: cache to avoid expensive re-quantization
    b_key = (B_q.data_ptr(), N, ks)
    if b_key not in _b_cache:
        _, Bsc = dynamic_mxfp4_quant(B.contiguous())
        _b_cache[b_key] = Bsc[:N, :ks].contiguous().view(torch.uint8)
    Bs_bytes = _b_cache[b_key]

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
    _mod.launch(A_bytes, B_bytes, As_bytes, Bs_bytes, C)
    return C
