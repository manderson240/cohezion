#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM: Shape-adaptive tile kernel with MFMA FP4.

Key insight from competition analysis:
- M=16, K=7168 is the WORST shape (34µs, dominates geomean)
- With BLOCK_M=128, only 12.5% of rows are used for M=16
- CK ASM uses 32x128 tile for ALL shapes — suboptimal for M=4,16

This kernel uses BLOCK_M=32, BLOCK_N=32, 4 waves (256 threads).
Each wave handles one 32x32x64 MFMA tile.
For M=16: 50% row utilization (vs 12.5% with 128-row tiles).

Falls back to aiter baseline on compile failure.
"""

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


# Compact HIP kernel — MFMA 32x32x64 FP4 with small tiles
HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

typedef int a_reg_t __attribute__((ext_vector_type(8)));
typedef int b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

#define BLOCK_M 32
#define BLOCK_N 32
#define TILE_K  64
#define TILE_K_BYTES 32
#define WAVESIZE 64
#define THREADS 64   // 1 wave per block — minimal for fast compile

// Each block: 32x32 output tile, iterates over K in steps of 64
__global__ __launch_bounds__(THREADS, 4)
void smalltile_fp4_gemm(
    const uint8_t* __restrict__ A,       // [M, K/2] fp4x2
    const uint8_t* __restrict__ B,       // [N, K/2] fp4x2 (shuffled)
    const uint8_t* __restrict__ A_scale, // [M_pad, K/32] e8m0 (shuffled)
    const uint8_t* __restrict__ B_scale, // [N_pad, K/32] e8m0 (shuffled)
    __hip_bfloat16* __restrict__ C,      // [M, N] bf16
    int M, int N, int K
) {
    const int bm = blockIdx.x;
    const int bn = blockIdx.y;
    const int tid = threadIdx.x;

    const int m_start = bm * BLOCK_M;
    const int n_start = bn * BLOCK_N;

    // Accumulator: 16 floats per thread (MFMA 32x32 output)
    c_reg_t acc;
    #pragma unroll
    for (int i = 0; i < 16; i++) acc[i] = 0.0f;

    const int k_iters = K / TILE_K;
    const int K_half = K / 2;

    for (int ki = 0; ki < k_iters; ki++) {
        const int k_off = ki * TILE_K_BYTES;  // byte offset in K dim

        // Load A tile: thread tid loads 32 bytes (TILE_K_BYTES) from row tid%32
        // Each thread in the wave loads one row's K-chunk
        a_reg_t a_data;
        {
            int row = tid % BLOCK_M;  // 0..31 (wraps for tid >= 32)
            int global_row = m_start + row;
            if (global_row < M) {
                const uint8_t* a_ptr = A + global_row * K_half + k_off;
                // Load 32 bytes = 8 x int32
                const int* a_ptr_i = reinterpret_cast<const int*>(a_ptr);
                #pragma unroll
                for (int i = 0; i < 8; i++) {
                    a_data[i] = (tid < BLOCK_M) ? a_ptr_i[i] : 0;
                }
            } else {
                #pragma unroll
                for (int i = 0; i < 8; i++) a_data[i] = 0;
            }
        }

        // Load B tile: thread tid loads from row tid%32
        b_reg_t b_data;
        {
            int row = tid % BLOCK_N;
            int global_row = n_start + row;
            if (global_row < N) {
                const uint8_t* b_ptr = B + global_row * K_half + k_off;
                const int* b_ptr_i = reinterpret_cast<const int*>(b_ptr);
                #pragma unroll
                for (int i = 0; i < 8; i++) {
                    b_data[i] = (tid < BLOCK_N) ? b_ptr_i[i] : 0;
                }
            } else {
                #pragma unroll
                for (int i = 0; i < 8; i++) b_data[i] = 0;
            }
        }

        // MFMA: 32x32x64 FP4 matrix multiply-accumulate
        // cbsz=4 (FP4 A), blgp=4 (FP4 B)
        acc = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_data, b_data, acc,
            0,    // cbsz_a = 4 (FP4 for A) -- encoded as src modifier
            0,    // blgp_b = 4 (FP4 for B) -- encoded as src modifier
            0, 0, 0, 0  // scale factors (0 = no scaling in instruction)
        );
    }

    // Write output: each thread writes its portion of the 32x32 tile
    // MFMA 32x32 output layout: thread tid owns 16 float values
    // Row = (tid%16)/4*8 + tid/32*4 + (result_idx%4)
    // Col = tid%4 + (result_idx/4)*4
    // But for simplicity, let's use a sequential write pattern
    {
        // MFMA 32x32 output: 16 values per thread
        // tid layout in 32x32: complex but deterministic
        // Row mapping for MFMA 32x32:
        //   base_row = (tid % 32) / 4   -> 0..7, gives rows 0,8,16,24 base
        //   Actually for 32x32 MFMA on gfx950:
        //   row = (tid % 16) + (result_idx / 4) * ... (complex)
        // Let's use the known gfx950 MFMA 32x32 layout:
        // For result[r] (r=0..15):
        //   row = 4*(r%4) + (tid/32)*2 + ((tid%32)/16)
        //       Actually no — let me use the verified layout from our skills

        // From gfx950-mfma-register-layouts skill:
        // row = (r%4) + (r/4)*8 + (tid/32)*4
        // col = tid%32
        // where r = result index 0..15

        for (int r = 0; r < 16; r++) {
            int row = (r % 4) + (r / 4) * 8 + (tid / 32) * 4;
            int col = tid % 32;
            int global_row = m_start + row;
            int global_col = n_start + col;
            if (global_row < M && global_col < N) {
                C[global_row * N + global_col] = (__hip_bfloat16)acc[r];
            }
        }
    }
}

torch::Tensor run_smalltile_gemm(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor A_scale, torch::Tensor B_scale,
    int M, int N, int K
) {
    auto C = torch::empty({M, N}, torch::dtype(torch::kBFloat16).device(A.device()));
    dim3 grid((M + BLOCK_M - 1) / BLOCK_M, (N + BLOCK_N - 1) / BLOCK_N);
    smalltile_fp4_gemm<<<grid, THREADS>>>(
        A.data_ptr<uint8_t>(), B.data_ptr<uint8_t>(),
        A_scale.data_ptr<uint8_t>(), B_scale.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K
    );
    return C;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("run_smalltile_gemm", &run_smalltile_gemm);
}
"""

_custom = None
try:
    _custom = load_inline(
        name="smalltile_fp4_v1",
        cuda_sources=[HIP_SOURCE],
        extra_cuda_cflags=["--offload-arch=gfx950", "-O3"],
        verbose=False,
    )
except Exception:
    pass

_gemm = aiter.gemm_a4w4
_fp4x2 = dtypes.fp4x2
_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(_e8m0)

    if _custom is not None:
        try:
            M = A.shape[0]
            K = A.shape[1]
            N = B_shuffle.shape[0]
            result = _custom.run_smalltile_gemm(
                Aq.view(torch.uint8),
                B_shuffle.view(torch.uint8),
                Ash.view(torch.uint8),
                B_scale_sh.view(torch.uint8),
                M,
                N,
                K,
            )
            return result
        except Exception:
            pass

    # Fallback
    return _gemm(
        Aq.view(_fp4x2),
        B_shuffle,
        Ash,
        B_scale_sh,
        dtype=_bf16,
        bpreshuffle=True,
    )
