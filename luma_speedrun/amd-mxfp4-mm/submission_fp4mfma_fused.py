#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM fused: Inline BF16→FP4 quantization + MFMA.

Eliminates ALL Python-side A quantization:
- Reads BF16 A directly in the kernel
- Quantizes to FP4 E2M1 in registers (per-32-element E8M0 scale)
- Feeds FP4 data to MFMA intrinsic

B uses pre-quantized B_q + unshuffled B scale.
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
#define TILE_K 64       // FP4 elements per K tile
#define TILE_K_BYTES 32 // = TILE_K / 2
#define WAVESIZE 64

// FP4 E2M1: map normalized float to 4-bit code with round-to-nearest-even.
// Values: 0, 0.5, 1, 1.5, 2, 3, 4, 6
// At midpoints: round toward even mantissa (mantissa LSB = 0).
// Even codes: 0(0.0), 2(1.0), 4(2.0), 6(4.0)  — mantissa bit = 0
// Odd codes:  1(0.5), 3(1.5), 5(3.0), 7(6.0)  — mantissa bit = 1
__device__ __forceinline__ uint8_t float_to_fp4(float v) {
    uint8_t sign = (v < 0.0f) ? 8u : 0u;
    float a = fabsf(v);
    uint8_t code;
    if      (a <= 0.25f) code = 0;  // midpoint 0.25 → even=0.0
    else if (a <  0.75f) code = 1;
    else if (a <= 1.25f) code = 2;  // midpoint 0.75→1.0(even), 1.25→1.0(even)
    else if (a <  1.75f) code = 3;
    else if (a <= 2.5f)  code = 4;  // midpoint 1.75→2.0(even), 2.5→2.0(even)
    else if (a <  3.5f)  code = 5;
    else if (a <= 5.0f)  code = 6;  // midpoint 3.5→4.0(even), 5.0→4.0(even)
    else                  code = 7;
    return sign | code;
}

__global__ void mxfp4_gemm_fused(
    const __hip_bfloat16* __restrict__ A_bf16,  // [M, K] bf16
    const uint8_t* __restrict__ B,               // [N, K/2] fp4x2
    const uint8_t* __restrict__ Bs,              // [N, K/32] E8M0
    __hip_bfloat16* __restrict__ C,              // [M, N]
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

    bool a_valid = (a_row < M);
    bool b_valid = (b_col < N);

    // B base pointers (pre-quantized FP4)
    const uint8_t* b_base = B + b_col * K_half;
    const uint8_t* bs_base = Bs + b_col * K_scale;

    // A base pointer (BF16 — we quantize inline)
    const __hip_bfloat16* a_base = A_bf16 + a_row * K;

    for (int kt = 0; kt < num_k_tiles; kt++) {
        a_reg_t a_reg = {};
        b_reg_t b_reg = {};

        // ─── A: Read 32 BF16 values → quantize to 16 FP4 bytes inline ───
        int a_k_start = kt * TILE_K + half_id * 32;  // FP4 element offset
        int sa = 0;

        if (a_valid && a_k_start + 32 <= K) {
            const __hip_bfloat16* a_ptr = a_base + a_k_start;

            // Pass 1: find max absolute value across 32 elements
            float max_abs = 0.0f;
            for (int i = 0; i < 32; i++) {
                float v = __bfloat162float(a_ptr[i]);
                max_abs = fmaxf(max_abs, fabsf(v));
            }

            // E8M0 scale: match aiter's BF16-exponent-based formula.
            // Formula: scale_exp = bf16_exp - 2 + (mantissa >= 96 ? 1 : 0)
            int scale_exp;
            float inv_scale;
            if (max_abs == 0.0f) {
                scale_exp = 0;
                inv_scale = 0.0f;
            } else {
                __hip_bfloat16 max_bf16 = (__hip_bfloat16)max_abs;
                unsigned short bf16_bits =
                    *reinterpret_cast<const unsigned short*>(&max_bf16);
                int bf16_exp = (bf16_bits >> 7) & 0xFF;
                int bf16_man = bf16_bits & 0x7F;
                if (bf16_man >= 96) bf16_exp += 1;
                scale_exp = max(bf16_exp - 2, 0);
                inv_scale = (scale_exp > 0) ?
                    __int_as_float((254 - scale_exp) << 23) : 0.0f;
            }
            sa = scale_exp;

            // Pass 2: quantize 32 BF16 → 16 packed FP4 bytes
            uint8_t* a_bytes = reinterpret_cast<uint8_t*>(&a_reg);
            for (int i = 0; i < 32; i += 2) {
                float v0 = __bfloat162float(a_ptr[i]) * inv_scale;
                float v1 = __bfloat162float(a_ptr[i+1]) * inv_scale;
                uint8_t fp4_0 = float_to_fp4(v0);
                uint8_t fp4_1 = float_to_fp4(v1);
                a_bytes[i >> 1] = (fp4_1 << 4) | fp4_0;
            }
        } else {
            sa = 127; // neutral scale for zero data
        }

        // ─── B: Load pre-quantized FP4 (same as v4) ────────────────────
        int k_byte_off = kt * TILE_K_BYTES + half_id * 16;
        int sb;

        if (b_valid && k_byte_off + 16 <= K_half) {
            uint8_t* b_bytes = reinterpret_cast<uint8_t*>(&b_reg);
            const uint8_t* b_ptr = b_base + k_byte_off;
            for (int i = 0; i < 16; i++) b_bytes[i] = b_ptr[i];
        }

        int sg = kt * 2 + half_id;
        sb = (b_valid && sg < K_scale) ? (int)bs_base[sg] : 127;

        // ─── MFMA ───────────────────────────────────────────────────────
        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg, 4, 4, 0, sa, 0, sb);
    }

    // ─── D output ────────────────────────────────────────────────────────
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

void launch(torch::Tensor A_bf16, torch::Tensor B,
            torch::Tensor Bs, torch::Tensor C) {
    int M = A_bf16.size(0), K = A_bf16.size(1), N = B.size(0);
    dim3 grid((N + TILE_N - 1) / TILE_N, (M + TILE_M - 1) / TILE_M);
    mxfp4_gemm_fused<<<grid, WAVESIZE>>>(
        reinterpret_cast<const __hip_bfloat16*>(A_bf16.data_ptr()),
        B.data_ptr<uint8_t>(),
        Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()), M, N, K);
}
"""

CPP_SOURCE = "void launch(torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor);"

try:
    _mod = load_inline(
        name="fp4mfma_fused",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[fp4mfma_fused] {e}")
    _OK = False


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]


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

    # A: pass BF16 directly (kernel quantizes inline!)
    A_bf16 = A.contiguous()

    # B: pre-quantized FP4 + unshuffled scale
    B_bytes = B_q.view(torch.uint8)
    Bs_unshuffled = e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks)
    Bs_bytes = Bs_unshuffled.contiguous().view(torch.uint8)

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
    _mod.launch(A_bf16, B_bytes, Bs_bytes, C)
    return C
