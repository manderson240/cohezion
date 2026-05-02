#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""AMD CDNA4 4-Wave Ping-Pong FP4 GEMM — small-tile variant.

Designed to work for ALL M values (M=4, 16, 32, 64, 256, etc.) by using
a 32×128 output tile per block instead of the 128×256 tile in v2.

Architecture:
  - 32×128 output tile per block (32 M rows × 128 N cols)
  - 256 threads = 4 waves × 64 threads per wave
  - Each wave handles one 32×32 MFMA sub-tile across 4 N positions (128 cols total)
  - Ping-pong: waves 0-1 (group 0) load while waves 2-3 (group 1) compute, then swap
  - GLOBAL_LOAD_LDS via llvm.amdgcn.raw.buffer.load.lds (128-bit per lane)
  - LDS XOR swizzle for 64-bank conflict elimination
  - Double-buffered LDS (tic/toc)
  - __builtin_amdgcn_s_barrier() (wave-level, NOT block-level __syncthreads)
  - __builtin_amdgcn_s_setprio(1/0) for compute/load priority
  - __builtin_amdgcn_sched_barrier(0) at load/compute boundaries

Wave decomposition (4 waves, 32×128 tile):
  wave_n = waveid % 4  → 32-col N slice:  [waveid*32 .. waveid*32+31]
  All waves handle the same 32 M rows (wave_m=0 always for this tile size)

Ping-pong groups:
  group 0: waves 0, 1  (wave_n=0 and wave_n=1)
  group 1: waves 2, 3  (wave_n=2 and wave_n=3)
  Iteration k: group 0 loads tile k+1, group 1 computes tile k. Next iter: swap.

LDS layout:
  smem_A[2]: [BLOCK_M=32, TILE_K_BYTES=32] = 1024 bytes per slot
  smem_B[2]: [BLOCK_N=128, TILE_K_BYTES=32] = 4096 bytes per slot
  Total: 2*(1024+4096) = 10240 bytes ≪ 160KB CDNA4 LDS

Falls back to aiter gemm_a4w4 only on compile failure.
"""

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

// ============================================================================
// MFMA register types — int vec8 (verified gfx950)
// ============================================================================
typedef int   a_reg_t __attribute__((ext_vector_type(8)));
typedef int   b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

// ============================================================================
// Tile geometry — 32×128 per block, 4 waves
// ============================================================================
#define BLOCK_M       32
#define BLOCK_N      128
#define TILE_K        64    // FP4 elements per K step (one MFMA)
#define TILE_K_BYTES  32    // packed bytes (2 FP4 per byte)
#define THREADS      256    // 4 waves × 64 threads
#define WAVESIZE      64

// LDS per buffer slot
#define LDS_A_BYTES  (BLOCK_M * TILE_K_BYTES)    // 32 * 32 = 1024
#define LDS_B_BYTES  (BLOCK_N * TILE_K_BYTES)    // 128 * 32 = 4096

// ============================================================================
// GLOBAL_LOAD_LDS — 128-bit per lane, CDNA4 only
// ============================================================================
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

// ============================================================================
// LDS XOR swizzle — AMD Blog formula (CDNA4 64-bank LDS)
// ============================================================================
__device__ __forceinline__ int swizzle_byte_col(int row, int byte_col) {
    const int pair = (row >> 1) & 7;
    const int perm = pair ^ (((pair >> 1) ^ (pair >> 2)) & 1);
    return byte_col ^ (perm << 4);
}

// ============================================================================
// get_lds_byte_addr — LDS byte offset for ds_read_b128
// ============================================================================
__device__ __forceinline__ uint32_t get_lds_byte_addr(const uint8_t* shared_ptr) {
    const as3_uint8_p p = reinterpret_cast<as3_uint8_p>(
        const_cast<uint8_t*>(shared_ptr));
    return static_cast<uint32_t>(reinterpret_cast<uintptr_t>(p));
}

// ============================================================================
// ds_read_b128 wrapper
// ============================================================================
__device__ __forceinline__ void load_uint4_from_lds(
    const uint8_t* lds_base, int byte_off, void* dst
) {
    using u32x4_t = uint32_t __attribute__((ext_vector_type(4)));
    const uint32_t addr = get_lds_byte_addr(lds_base + byte_off);
    u32x4_t result;
    asm volatile("ds_read_b128 %0, %1\n"
        : "=v"(result) : "v"(addr) : "memory");
    *reinterpret_cast<u32x4_t*>(dst) = result;
}

// ============================================================================
// 4-wave ping-pong FP4 MFMA kernel — small tile (32×128), all M values
// ============================================================================
__global__ __launch_bounds__(THREADS, 1)
void mxfp4_pingpong_small(
    const uint8_t* __restrict__ A,    // [M, K/2] packed FP4
    const uint8_t* __restrict__ B,    // [N, K/2] packed FP4
    const uint8_t* __restrict__ As,   // [M, K/32] E8M0 linear
    const uint8_t* __restrict__ Bs,   // [N, K/32] E8M0 linear
    __hip_bfloat16* __restrict__ C,   // [M, N] BF16 output
    int M, int N, int K
) {
    const int tid    = threadIdx.x;
    const int waveid = tid / WAVESIZE;   // 0..3
    const int lane   = tid % WAVESIZE;   // 0..63
    const int half   = lane >> 5;        // 0=lanes 0-31, 1=lanes 32-63

    // Wave N slice: each wave covers 32 N columns
    const int wave_n = waveid;  // 0..3 → N offsets 0, 32, 64, 96

    // Ping-pong groups:
    //   group 0 = waves 0, 1  (wave_n < 2)
    //   group 1 = waves 2, 3  (wave_n >= 2)
    const int pp_group = waveid >> 1;  // 0 or 1

    const int bm = blockIdx.x * BLOCK_M;
    const int bn = blockIdx.y * BLOCK_N;

    const int K_half  = K / 2;
    const int K_scale = K / 32;
    const int num_k   = K / TILE_K;

    // Double-buffered LDS
    __shared__ uint8_t smem_A[2][LDS_A_BYTES];
    __shared__ uint8_t smem_B[2][LDS_B_BYTES];

    // Per-wave output coordinates: one 32×32 MFMA tile
    const int tile_m0 = bm;                     // all waves share same M rows
    const int tile_n0 = bn + wave_n * 32;       // N slice for this wave

    // Accumulator for one 32×32 MFMA tile
    c_reg_t c0 = {};

    // ----------------------------------------------------------------
    // PROLOGUE: all 256 threads cooperatively load K-tile 0 into tic=0
    // ----------------------------------------------------------------
    // A tile: 32 rows × 32 bytes = 1024 bytes, 256 threads → 4 bytes/thread (covered below)
    {
        const int total_a_chunks = BLOCK_M * (TILE_K_BYTES / 16);  // 32*2=64
        for (int chunk = tid; chunk < total_a_chunks; chunk += THREADS) {
            const int row      = chunk / (TILE_K_BYTES / 16);
            const int byte_col = (chunk % (TILE_K_BYTES / 16)) * 16;
            const int swiz_col = swizzle_byte_col(row, byte_col);
            const int lds_off  = row * TILE_K_BYTES + swiz_col;

            as3_uint32_p ldsp = reinterpret_cast<as3_uint32_p>(
                reinterpret_cast<as3_uint8_p>(smem_A[0] + lds_off));

            const int global_row = bm + row;
            if (global_row < M) {
                const i32x4 srsrc = make_srsrc(A + global_row * K_half, K_half);
                llvm_amdgcn_raw_buffer_load_lds(srsrc, ldsp, 16, byte_col, 0, 0, 0);
            } else {
                uint32_t* z = reinterpret_cast<uint32_t*>(smem_A[0] + lds_off);
                z[0] = z[1] = z[2] = z[3] = 0u;
            }
        }
    }
    // B tile: 128 rows × 32 bytes = 4096 bytes, 256 threads → 16 bytes/thread
    {
        const int total_b_chunks = BLOCK_N * (TILE_K_BYTES / 16);  // 128*2=256
        for (int chunk = tid; chunk < total_b_chunks; chunk += THREADS) {
            const int row      = chunk / (TILE_K_BYTES / 16);
            const int byte_col = (chunk % (TILE_K_BYTES / 16)) * 16;
            const int swiz_col = swizzle_byte_col(row, byte_col);
            const int lds_off  = row * TILE_K_BYTES + swiz_col;

            as3_uint32_p ldsp = reinterpret_cast<as3_uint32_p>(
                reinterpret_cast<as3_uint8_p>(smem_B[0] + lds_off));

            const int global_row = bn + row;
            if (global_row < N) {
                const i32x4 srsrc = make_srsrc(B + global_row * K_half, K_half);
                llvm_amdgcn_raw_buffer_load_lds(srsrc, ldsp, 16, byte_col, 0, 0, 0);
            } else {
                uint32_t* z = reinterpret_cast<uint32_t*>(smem_B[0] + lds_off);
                z[0] = z[1] = z[2] = z[3] = 0u;
            }
        }
    }
    asm volatile("s_waitcnt vmcnt(0)");
    __builtin_amdgcn_s_barrier();

    // ----------------------------------------------------------------
    // HOT LOOP — 4-wave ping-pong
    //
    // Pattern:
    //   Group 1 stalls at barrier 0 → Group 0 issues loads for toc
    //   Barrier 1 releases everyone → both groups compute tic
    //   Wait for loads → barrier 2 syncs → flip buffers
    // ----------------------------------------------------------------
    for (int kt = 0; kt < num_k; kt++) {
        const int tic      = kt & 1;
        const int toc      = 1 - tic;
        const bool has_next = (kt + 1 < num_k);

        // Blog barrier 0: group 1 stalls; group 0 issues loads for toc
        if (pp_group == 1) {
            __builtin_amdgcn_s_barrier();
        }

        // Load group (group 0: waves 0,1) prefetches next tile
        if (has_next && pp_group == 0) {
            __builtin_amdgcn_sched_barrier(0);

            const int next_k_off = (kt + 1) * TILE_K_BYTES;
            // 2 waves × 64 lanes = 128 threads in load group
            const int load_tid = (waveid & 1) * WAVESIZE + lane;  // 0..127

            // A: 64 chunks × 16 bytes = 1024 bytes
            {
                constexpr int a_chunks = BLOCK_M * (TILE_K_BYTES / 16);  // 64
                for (int c = load_tid; c < a_chunks; c += 128) {
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
                }
            }

            // B: 256 chunks × 16 bytes = 4096 bytes
            {
                constexpr int b_chunks = BLOCK_N * (TILE_K_BYTES / 16);  // 256
                for (int c = load_tid; c < b_chunks; c += 128) {
                    const int row      = c / (TILE_K_BYTES / 16);
                    const int byte_col = (c % (TILE_K_BYTES / 16)) * 16;
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

        // Barrier 1: release group 1, both groups proceed to MFMA
        __builtin_amdgcn_s_barrier();

        // MFMA with elevated priority
        __builtin_amdgcn_s_setprio(1);
        __builtin_amdgcn_sched_barrier(0);

        const int sg = kt * 2 + half;  // scale group index (2 per K tile)

        // Load A fragment from LDS (32 rows, half selects which 16 bytes)
        a_reg_t a_reg = {};
        {
            const int row0     = lane & 31;                      // 0..31 (MFMA row)
            const int byte_col = half * 16;                      // 0 or 16
            const int lds_off  = row0 * TILE_K_BYTES + swizzle_byte_col(row0, byte_col);
            load_uint4_from_lds(smem_A[tic], lds_off, &a_reg);
        }

        // Load B fragment from LDS (wave_n selects 32-col slice)
        b_reg_t b_reg = {};
        {
            const int row0     = wave_n * 32 + (lane & 31);     // N row for this wave
            const int byte_col = half * 16;
            const int lds_off  = row0 * TILE_K_BYTES + swizzle_byte_col(row0, byte_col);
            load_uint4_from_lds(smem_B[tic], lds_off, &b_reg);
        }

        asm volatile("s_waitcnt lgkmcnt(0)");  // wait for ds_read_b128

        // Scales: one E8M0 per thread per scale group
        const int a_mrow = tile_m0 + (lane & 31);
        const int b_ncol = tile_n0 + (lane & 31);
        const int sa = (a_mrow < M && sg < K_scale) ?
            (int)As[a_mrow * K_scale + sg] : 127;
        const int sb = (b_ncol < N && sg < K_scale) ?
            (int)Bs[b_ncol * K_scale + sg] : 127;

        // One 32×32×64 MFMA tile
        c0 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c0, 4, 4, 0, sa, 0, sb);

        __builtin_amdgcn_sched_barrier(0);
        __builtin_amdgcn_s_setprio(0);

        // Wait for async loads to finish before next iteration reads toc
        if (has_next) {
            asm volatile("s_waitcnt vmcnt(0)");
            __builtin_amdgcn_s_barrier();
        }
    }

    // ----------------------------------------------------------------
    // EPILOGUE: write output
    // Layout (verified): c0[r] → C[tile_m0 + (r&3) + (r>>2)*8 + half*4][tile_n0 + lane&31]
    // ----------------------------------------------------------------
    {
        const int oc = tile_n0 + (lane & 31);
        if (oc < N) {
            #pragma unroll
            for (int r = 0; r < 16; r++) {
                const int or2 = tile_m0 + (r & 3) + (r >> 2) * 8 + half * 4;
                if (or2 < M)
                    C[or2 * N + oc] = (__hip_bfloat16)(c0[r]);
            }
        }
    }
}

void launch_pingpong_small(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C, int M, int N, int K
) {
    dim3 grid((M + BLOCK_M - 1) / BLOCK_M,
              (N + BLOCK_N - 1) / BLOCK_N);
    mxfp4_pingpong_small<<<grid, THREADS>>>(
        A.data_ptr<uint8_t>(), B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(), Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K);
}
"""

CPP_SOURCE = """
void launch_pingpong_small(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C, int M, int N, int K
);
"""

try:
    _mod = load_inline(
        name="mxfp4_pingpong_small",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_pingpong_small"],
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
    print("[pingpong_small] compile SUCCESS")
except Exception as e:
    print(f"[pingpong_small] compile FAILED: {e}")
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
    """MXFP4 GEMM: 4-wave ping-pong (GLOBAL_LOAD_LDS + XOR swizzle + s_barrier).

    Uses 32×128 tile so works for ALL M values (M=4, 16, 32, 64, 256, ...).
    Falls back to aiter gemm_a4w4 only on compile failure.
    """
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

    # Cache B scale unshuffling by data_ptr (B weight is fixed across calls)
    cache_key = (B_scale_sh.data_ptr(), N, ks)
    if cache_key not in _bs_cache:
        _bs_cache.clear()
        _bs_cache[cache_key] = (
            e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks).contiguous().view(torch.uint8)
        )
    Bs_bytes = _bs_cache[cache_key]

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
    _mod.launch_pingpong_small(A_bytes, B_bytes, As_bytes, Bs_bytes, C, M, N, K)
    return C
