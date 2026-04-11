#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM — Small-M tile: BLOCK_M=32, BLOCK_N=128, 4 waves (256 threads).

Targets small-M shapes (M=4,16,32) where the 128x256 tile wastes most CUs.
A 32x128 tile creates ceil(M/32)*ceil(N/128) blocks → better occupancy for small M.

Wave decomposition (4 waves, 256 threads):
  BLOCK_M=32, BLOCK_N=128 → 1 M-row × 4 N-cols of 32×32 MFMA tiles
  wave 0 → tile_n = bn + 0
  wave 1 → tile_n = bn + 32
  wave 2 → tile_n = bn + 64
  wave 3 → tile_n = bn + 96
  Each wave computes one 32×32 output tile (1 MFMA accumulator).

Within each MFMA 32x32x64 call:
  - 32 rows of A: lanes 0-31 → row base, lanes 32-63 → row base (half=0 vs half=1 selects K half)
  - 32 rows of B (cols): lane & 31 selects the output column
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

typedef int   a_reg_t __attribute__((ext_vector_type(8)));
typedef int   b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

#define BLOCK_M      32
#define BLOCK_N      128
#define TILE_K        64
#define TILE_K_BYTES  32
#define THREADS      256   // 4 waves x 64 threads
#define WAVESIZE      64

// LDS: A=1024B, B=4096B, 2 slots = 10 KB total
#define LDS_A_BYTES  (BLOCK_M * TILE_K_BYTES)   // 1024
#define LDS_B_BYTES  (BLOCK_N * TILE_K_BYTES)   // 4096

using i32x4        = int32_t  __attribute__((ext_vector_type(4)));
using as3_uint32_t = uint32_t __attribute__((address_space(3)));
using as3_uint32_p = as3_uint32_t*;
using as3_uint8_t  = uint8_t  __attribute__((address_space(3)));
using as3_uint8_p  = as3_uint8_t*;

extern "C" __device__ void llvm_amdgcn_raw_buffer_load_lds(
    i32x4 rsrc, as3_uint32_p lds_ptr, int size,
    int voffset, int soffset, int offset, int aux)
    __asm("llvm.amdgcn.raw.buffer.load.lds");

struct buffer_resource { uint64_t ptr; uint32_t range; uint32_t config; };

__device__ __forceinline__ i32x4 make_srsrc(const void* ptr, uint32_t range) {
    buffer_resource r = {reinterpret_cast<uint64_t>(ptr), range, 0x00110000u};
    return *reinterpret_cast<const i32x4*>(&r);
}

__device__ __forceinline__ int swizzle_byte_col(int row, int byte_col) {
    const int pair = (row >> 1) & 7;
    const int perm = pair ^ (((pair >> 1) ^ (pair >> 2)) & 1);
    return byte_col ^ (perm << 4);
}

__device__ __forceinline__ uint32_t get_lds_byte_addr(const uint8_t* shared_ptr) {
    const as3_uint8_p p = reinterpret_cast<as3_uint8_p>(
        const_cast<uint8_t*>(shared_ptr));
    return static_cast<uint32_t>(reinterpret_cast<uintptr_t>(p));
}

__device__ __forceinline__ void load_uint4_from_lds(
    const uint8_t* lds_base, int byte_off, void* dst
) {
    using u32x4_t = uint32_t __attribute__((ext_vector_type(4)));
    const uint32_t addr = get_lds_byte_addr(lds_base + byte_off);
    u32x4_t result;
    asm volatile("ds_read_b128 %0, %1\n" : "=v"(result) : "v"(addr) : "memory");
    *reinterpret_cast<u32x4_t*>(dst) = result;
}

__device__ __forceinline__ void load_tile_global_to_lds(
    const uint8_t* __restrict__ global_base,
    uint8_t* __restrict__ lds_slot,
    int row_stride, int rows, int valid_rows, int global_row0,
    int tid, int num_threads
) {
    const int total_chunks = rows * (TILE_K_BYTES / 16);
    const uint32_t buf_range = (uint32_t)(rows * row_stride + TILE_K_BYTES);
    const i32x4 srsrc = make_srsrc(global_base, buf_range);

    for (int chunk = tid; chunk < total_chunks; chunk += num_threads) {
        const int row       = chunk / (TILE_K_BYTES / 16);
        const int byte_col  = (chunk % (TILE_K_BYTES / 16)) * 16;
        const int swiz_col  = swizzle_byte_col(row, byte_col);
        const int lds_off   = row * TILE_K_BYTES + swiz_col;
        as3_uint32_p ldsp = reinterpret_cast<as3_uint32_p>(
            reinterpret_cast<as3_uint8_p>(lds_slot + lds_off));
        const int voffset = row * row_stride + byte_col;
        if (global_row0 + row < valid_rows) {
            llvm_amdgcn_raw_buffer_load_lds(srsrc, ldsp, 16, voffset, 0, 0, 0);
        } else {
            uint32_t* z = reinterpret_cast<uint32_t*>(lds_slot + lds_off);
            z[0] = z[1] = z[2] = z[3] = 0u;
        }
    }
}

// ============================================================================
// 4-wave kernel: BLOCK_M=32, BLOCK_N=128
// Each wave owns 1 MFMA tile (32x32 output region):
//   wave 0→N cols [bn+0..31], wave 1→[bn+32..63],
//   wave 2→[bn+64..95],       wave 3→[bn+96..127]
// All 4 waves share the same BLOCK_M=32 row range.
// ============================================================================
__global__ __launch_bounds__(THREADS, 2)
void mxfp4_tile32x128(
    const uint8_t* __restrict__ A,
    const uint8_t* __restrict__ B,
    const uint8_t* __restrict__ As,
    const uint8_t* __restrict__ Bs,
    __hip_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    const int tid    = threadIdx.x;
    const int waveid = tid / WAVESIZE;
    const int lane   = tid % WAVESIZE;
    const int half   = lane >> 5;   // 0=lanes 0-31, 1=lanes 32-63

    const int bm = blockIdx.x * BLOCK_M;
    const int bn = blockIdx.y * BLOCK_N;

    const int K_half  = K / 2;
    const int K_scale = K / 32;
    const int num_k   = K / TILE_K;

    __shared__ uint8_t smem_A[2][LDS_A_BYTES];
    __shared__ uint8_t smem_B[2][LDS_B_BYTES];

    // Each wave handles 1 N-tile of 32 columns
    const int tile_m = bm;                    // all waves: same M start
    const int tile_n = bn + waveid * 32;      // wave 0/1/2/3 → 0/32/64/96

    // 1 accumulator per wave (32×32 MFMA output)
    c_reg_t c00 = {};

    // Prologue: load K-tile 0
    load_tile_global_to_lds(
        A + bm * K_half, smem_A[0], K_half, BLOCK_M, M, bm, tid, THREADS);
    load_tile_global_to_lds(
        B + bn * K_half, smem_B[0], K_half, BLOCK_N, N, bn, tid, THREADS);
    asm volatile("s_waitcnt vmcnt(0)");
    __builtin_amdgcn_s_barrier();

    for (int kt = 0; kt < num_k; kt++) {
        const int tic      = kt & 1;
        const int toc      = 1 - tic;
        const bool has_next = (kt + 1 < num_k);

        // ALL waves cooperatively prefetch next K-tile (4x faster than wave-0 only)
        if (has_next) {
            __builtin_amdgcn_sched_barrier(0);
            const int next_k_off = (kt + 1) * TILE_K_BYTES;

            // A+B combined: 64+256=320 chunks, 256 threads → ~1.25 chunks/thread
            constexpr int a_chunks = BLOCK_M * (TILE_K_BYTES / 16);   // 64
            constexpr int b_chunks = BLOCK_N * (TILE_K_BYTES / 16);   // 256
            constexpr int total_chunks = a_chunks + b_chunks;          // 320

            for (int c = tid; c < total_chunks; c += THREADS) {
                if (c < a_chunks) {
                    // Load A chunk
                    const int row      = c / (TILE_K_BYTES / 16);
                    const int byte_col = (c % (TILE_K_BYTES / 16)) * 16;
                    const int swiz_col = swizzle_byte_col(row, byte_col);
                    const int lds_off  = row * TILE_K_BYTES + swiz_col;
                    as3_uint32_p ldsp = reinterpret_cast<as3_uint32_p>(
                        reinterpret_cast<as3_uint8_p>(smem_A[toc] + lds_off));
                    const int global_row = bm + row;
                    if (global_row < M) {
                        const i32x4 srsrc = make_srsrc(
                            A + global_row * K_half + next_k_off, TILE_K_BYTES);
                        llvm_amdgcn_raw_buffer_load_lds(srsrc, ldsp, 16, byte_col, 0, 0, 0);
                    } else {
                        uint32_t* z = reinterpret_cast<uint32_t*>(smem_A[toc] + lds_off);
                        z[0] = z[1] = z[2] = z[3] = 0u;
                    }
                } else {
                    // Load B chunk
                    const int bc       = c - a_chunks;
                    const int row      = bc / (TILE_K_BYTES / 16);
                    const int byte_col = (bc % (TILE_K_BYTES / 16)) * 16;
                    const int swiz_col = swizzle_byte_col(row, byte_col);
                    const int lds_off  = row * TILE_K_BYTES + swiz_col;
                    as3_uint32_p ldsp = reinterpret_cast<as3_uint32_p>(
                        reinterpret_cast<as3_uint8_p>(smem_B[toc] + lds_off));
                    const int global_row = bn + row;
                    if (global_row < N) {
                        const i32x4 srsrc = make_srsrc(
                            B + global_row * K_half + next_k_off, TILE_K_BYTES);
                        llvm_amdgcn_raw_buffer_load_lds(srsrc, ldsp, 16, byte_col, 0, 0, 0);
                    } else {
                        uint32_t* z = reinterpret_cast<uint32_t*>(smem_B[toc] + lds_off);
                        z[0] = z[1] = z[2] = z[3] = 0u;
                    }
                }
            }
            __builtin_amdgcn_sched_barrier(0);
        }

        __builtin_amdgcn_s_barrier();
        __builtin_amdgcn_s_setprio(1);
        __builtin_amdgcn_sched_barrier(0);

        const int sg = kt * 2 + half;

        // A fragment: all waves use all 32 rows of smem_A
        // lane & 31 selects row within the 32-row MFMA tile
        a_reg_t a0_reg = {};
        {
            const int row      = lane & 31;   // 0..31 (row within BLOCK_M=32)
            const int byte_col = half * 16;
            const int lds_off  = row * TILE_K_BYTES + swizzle_byte_col(row, byte_col);
            load_uint4_from_lds(smem_A[tic], lds_off, &a0_reg);
        }

        // B fragment: each wave loads from its 32-col slice
        b_reg_t b0_reg = {};
        {
            // waveid*32 is the B-row (N dimension) base for this wave
            const int b_row    = waveid * 32 + (lane & 31);
            const int byte_col = half * 16;
            const int lds_off  = b_row * TILE_K_BYTES + swizzle_byte_col(b_row, byte_col);
            load_uint4_from_lds(smem_B[tic], lds_off, &b0_reg);
        }

        asm volatile("s_waitcnt lgkmcnt(0)");

        const int a_row = tile_m + (lane & 31);
        const int b_row = tile_n + (lane & 31);
        const int sa0 = (a_row < M && sg < K_scale) ?
            (int)As[a_row * K_scale + sg] : 127;
        const int sb0 = (b_row < N && sg < K_scale) ?
            (int)Bs[b_row * K_scale + sg] : 127;

        c00 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a0_reg, b0_reg, c00, 4, 4, 0, sa0, 0, sb0);

        __builtin_amdgcn_sched_barrier(0);
        __builtin_amdgcn_s_setprio(0);

        if (has_next) {
            asm volatile("s_waitcnt vmcnt(0)");
            __builtin_amdgcn_s_barrier();
        }
    }

    // Epilogue: write 32x32 tile
    // Layout: c_reg[r] → C[(tm) + (r&3) + (r>>2)*8 + half*4][(tn) + lane&31]
    {
        const int oc = tile_n + (lane & 31);
        if (oc < N) {
            #pragma unroll
            for (int r = 0; r < 16; r++) {
                const int or2 = tile_m + (r & 3) + (r >> 2) * 8 + half * 4;
                if (or2 < M)
                    C[or2 * N + oc] = (__hip_bfloat16)(c00[r]);
            }
        }
    }
}

void launch_tile32x128(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C, int M, int N, int K
) {
    dim3 grid((M + BLOCK_M - 1) / BLOCK_M,
              (N + BLOCK_N - 1) / BLOCK_N);
    mxfp4_tile32x128<<<grid, THREADS>>>(
        A.data_ptr<uint8_t>(), B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(), Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K);
}
"""

CPP_SOURCE = """
void launch_tile32x128(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C, int M, int N, int K
);
"""

try:
    _mod = load_inline(
        name="mxfp4_tile32x128",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_tile32x128"],
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
    _OK = True
    print("[tile32x128] compile SUCCESS")
except Exception as e:
    print(f"[tile32x128] compile FAILED: {e}")
    _OK = False


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
    """Reverse aiter's e8m0_shuffle to get linear [M, K/32] uint8 layout."""
    sm, sn = scale_shuffled.shape
    return (
        scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
        .permute(0, 5, 3, 1, 4, 2)
        .contiguous()
        .view(sm, sn)[:orig_m, :orig_n]
    )


_bs_cache: dict = {}


def _aiter_fallback(data: input_t) -> output_t:
    import aiter
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    from aiter.utility.fp4_utils import e8m0_shuffle

    A, B, B_q, B_shuffle, B_scale_sh = data
    A_q, A_scale_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_scale_sh = e8m0_shuffle(A_scale_e8m0).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        A_q.view(dtypes.fp4x2),
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )


def custom_kernel(data: input_t) -> output_t:
    """MXFP4 GEMM with BLOCK_M=32, BLOCK_N=128 — targets small-M shapes."""
    from aiter.ops.triton.quant import dynamic_mxfp4_quant

    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    if not _OK:
        return _aiter_fallback(data)

    ks = K // 32

    A_q, A_sc = dynamic_mxfp4_quant(A.contiguous())
    A_bytes = A_q.view(torch.uint8)
    As_bytes = A_sc[:M, :ks].contiguous().view(torch.uint8)
    B_bytes = B_q.view(torch.uint8)

    cache_key = (B_scale_sh.data_ptr(), N, ks)
    if cache_key not in _bs_cache:
        _bs_cache.clear()
        _bs_cache[cache_key] = (
            e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks).contiguous().view(torch.uint8)
        )
    Bs_bytes = _bs_cache[cache_key]

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
    _mod.launch_tile32x128(A_bytes, B_bytes, As_bytes, Bs_bytes, C, M, N, K)
    return C
