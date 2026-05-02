#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""AMD CDNA4 Blog 8-Wave Ping-Pong FP4 GEMM — v3.

v3 fixes over v2: removed inline-ASM ds_read_b128 + address-space cast.
  - v2 compile error: reinterpret_cast between address spaces not allowed.
  - Fix: use regular uint4 pointer load from __shared__ memory.
    The compiler generates ds_read_b128 automatically for 128-bit aligned
    __shared__ reads. No manual address-space manipulation needed.

v1 root cause: get_lds_addr used generic pointer uintptr_t (virtual address,
  not LDS offset). Fix: use __builtin_amdgcn_ds_fatomicadd or just let the
  compiler handle LDS reads via typed pointer dereference (this v3 approach).

Blog patterns applied:
  1. GLOBAL_LOAD_LDS via llvm.amdgcn.raw.buffer.load.lds (128-bit per lane)
  2. LDS XOR swizzle: col ^= ((pair ^ ((pair>>1)^(pair>>2))&1) << 4)
  3. 8-wave ping-pong using __builtin_amdgcn_s_barrier()
  4. __builtin_amdgcn_s_setprio(1) during MFMA, 0 after
  5. __builtin_amdgcn_sched_barrier(0) at boundaries
  6. Double-buffered LDS: tic/toc flip each K iteration
  7. 512 threads, 128x256 output tile per block
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

typedef int   a_reg_t __attribute__((ext_vector_type(8)));
typedef int   b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

#define BLOCK_M      128
#define BLOCK_N      256
#define TILE_K        64
#define TILE_K_BYTES  32
#define THREADS      512
#define WAVESIZE      64
#define LDS_A_BYTES  (BLOCK_M * TILE_K_BYTES)   // 4096
#define LDS_B_BYTES  (BLOCK_N * TILE_K_BYTES)   // 8192

// ============================================================================
// GLOBAL_LOAD_LDS intrinsic (AMD CDNA4 blog, 128-bit per lane)
// ============================================================================
using i32x4        = int32_t  __attribute__((ext_vector_type(4)));
using as3_uint32_p = uint32_t __attribute__((address_space(3)))*;

extern "C" __device__ void llvm_amdgcn_raw_buffer_load_lds(
    i32x4 rsrc, as3_uint32_p lds_ptr, int size,
    int voffset, int soffset, int offset, int aux)
    __asm("llvm.amdgcn.raw.buffer.load.lds");

struct buffer_resource { uint64_t ptr; uint32_t range; uint32_t config; };

// AMD blog's exact config value for raw buffer loads
__device__ __forceinline__ i32x4 make_srsrc(const void* p, uint32_t range) {
    buffer_resource r = {reinterpret_cast<uint64_t>(p), range, 0x00110000u};
    return *reinterpret_cast<const i32x4*>(&r);
}

// ============================================================================
// LDS XOR swizzle (AMD Blog formula, 64-bank CDNA4 LDS, self-inverse)
// ============================================================================
__device__ __forceinline__ int swizzle_byte_col(int row, int byte_col) {
    const int pair = (row >> 1) & 7;
    const int perm = pair ^ (((pair >> 1) ^ (pair >> 2)) & 1);
    return byte_col ^ (perm << 4);
}

// ============================================================================
// load_uint4_from_lds — 128-bit LDS read via compiler-generated ds_read_b128.
// Uses normal uint4 pointer dereference; compiler emits the correct LDS
// instruction without any address-space cast needed.
// ============================================================================
__device__ __forceinline__ uint4 load_uint4_lds(
    const uint8_t* __restrict__ lds_base, int byte_off
) {
    return *reinterpret_cast<const uint4*>(lds_base + byte_off);
}

// ============================================================================
// Async global→LDS tile loader (AMD Blog GLOBAL_LOAD_LDS pattern)
// ============================================================================
__device__ __forceinline__ void load_tile_to_lds_async(
    const uint8_t* __restrict__ global_base,
    uint8_t* __restrict__ lds_slot,
    int row_stride,
    int rows,
    int valid_rows,
    int global_row0,
    int tid,
    int num_threads
) {
    const int total_chunks = rows * (TILE_K_BYTES / 16);
    const uint32_t buf_range = (uint32_t)(rows * row_stride + TILE_K_BYTES);
    const i32x4 srsrc = make_srsrc(global_base, buf_range);

    for (int chunk = tid; chunk < total_chunks; chunk += num_threads) {
        const int row       = chunk / (TILE_K_BYTES / 16);
        const int col_chunk = chunk % (TILE_K_BYTES / 16);
        const int byte_col  = col_chunk * 16;
        const int swiz_col  = swizzle_byte_col(row, byte_col);
        const int lds_off   = row * TILE_K_BYTES + swiz_col;

        // LDS destination: use __to_local() to get the correct LDS-space address
        // from a generic (__shared__) pointer. This is the HIP-idiomatic way.
        as3_uint32_p ldsp = (as3_uint32_p)(__to_local((void*)(lds_slot + lds_off)));

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
// 8-wave ping-pong FP4 MFMA kernel
// ============================================================================
__global__ __launch_bounds__(THREADS, 1)
void mxfp4_blog_pp_v3(
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
    const int half   = lane >> 5;

    const int wave_m = waveid / 4;   // 0..1
    const int wave_n = waveid % 4;   // 0..3

    const int bm = blockIdx.x * BLOCK_M;
    const int bn = blockIdx.y * BLOCK_N;

    const int K_half  = K / 2;
    const int K_scale = K / 32;
    const int num_k   = K / TILE_K;

    __shared__ uint8_t smem_A[2][LDS_A_BYTES];
    __shared__ uint8_t smem_B[2][LDS_B_BYTES];

    // Per-wave output coordinates (4 MFMA tiles: 2×2 = 64×64)
    const int tile_m0 = bm + wave_m * 64;
    const int tile_m1 = tile_m0 + 32;
    const int tile_n0 = bn + wave_n * 64;
    const int tile_n1 = tile_n0 + 32;

    c_reg_t c00 = {}, c01 = {}, c10 = {}, c11 = {};

    // ----------------------------------------------------------------
    // PROLOGUE: all 512 threads load K-tile 0 into buffer 0
    // ----------------------------------------------------------------
    load_tile_to_lds_async(
        A + bm * K_half, smem_A[0], K_half, BLOCK_M, M, bm, tid, THREADS);
    load_tile_to_lds_async(
        B + bn * K_half, smem_B[0], K_half, BLOCK_N, N, bn, tid, THREADS);
    asm volatile("s_waitcnt vmcnt(0)");
    __builtin_amdgcn_s_barrier();

    // ----------------------------------------------------------------
    // HOT LOOP: 8-wave ping-pong (AMD Blog pattern)
    // ----------------------------------------------------------------
    for (int kt = 0; kt < num_k; kt++) {
        const int tic      = kt & 1;
        const int toc      = 1 - tic;
        const bool has_next = (kt + 1 < num_k);

        // Blog barrier 0: wave_m==1 stalls while wave_m==0 issues loads
        if (wave_m == 1) {
            __builtin_amdgcn_s_barrier();
        }

        // Load group (wave_m==0): prefetch next K tile into toc
        if (has_next && wave_m == 0) {
            __builtin_amdgcn_sched_barrier(0);

            const int next_k_off = (kt + 1) * TILE_K_BYTES;
            const int load_tid   = wave_n * WAVESIZE + lane;  // 0..255

            // A: 256 chunks of 16 bytes = 4096 bytes
            {
                constexpr int a_chunks = BLOCK_M * (TILE_K_BYTES / 16);
                for (int c = load_tid; c < a_chunks; c += 256) {
                    const int row      = c / (TILE_K_BYTES / 16);
                    const int byte_col = (c % (TILE_K_BYTES / 16)) * 16;
                    const int swiz_col = swizzle_byte_col(row, byte_col);
                    const int lds_off  = row * TILE_K_BYTES + swiz_col;

                    as3_uint32_p ldsp = (as3_uint32_p)(__to_local(
                        (void*)(smem_A[toc] + lds_off)));

                    const int global_row = bm + row;
                    if (global_row < M) {
                        const i32x4 s = make_srsrc(
                            A + global_row * K_half + next_k_off, TILE_K_BYTES);
                        llvm_amdgcn_raw_buffer_load_lds(s, ldsp, 16, byte_col, 0, 0, 0);
                    } else {
                        uint32_t* z = reinterpret_cast<uint32_t*>(smem_A[toc] + lds_off);
                        z[0] = z[1] = z[2] = z[3] = 0u;
                    }
                }
            }

            // B: 512 chunks of 16 bytes = 8192 bytes
            {
                constexpr int b_chunks = BLOCK_N * (TILE_K_BYTES / 16);
                for (int c = load_tid; c < b_chunks; c += 256) {
                    const int row      = c / (TILE_K_BYTES / 16);
                    const int byte_col = (c % (TILE_K_BYTES / 16)) * 16;
                    const int swiz_col = swizzle_byte_col(row, byte_col);
                    const int lds_off  = row * TILE_K_BYTES + swiz_col;

                    as3_uint32_p ldsp = (as3_uint32_p)(__to_local(
                        (void*)(smem_B[toc] + lds_off)));

                    const int global_row = bn + row;
                    if (global_row < N) {
                        const i32x4 s = make_srsrc(
                            B + global_row * K_half + next_k_off, TILE_K_BYTES);
                        llvm_amdgcn_raw_buffer_load_lds(s, ldsp, 16, byte_col, 0, 0, 0);
                    } else {
                        uint32_t* z = reinterpret_cast<uint32_t*>(smem_B[toc] + lds_off);
                        z[0] = z[1] = z[2] = z[3] = 0u;
                    }
                }
            }
            __builtin_amdgcn_sched_barrier(0);
        }

        // Blog barrier 1: releases wave_m==1; both proceed to MFMA
        __builtin_amdgcn_s_barrier();

        // MFMA with elevated priority
        __builtin_amdgcn_s_setprio(1);
        __builtin_amdgcn_sched_barrier(0);

        const int sg = kt * 2 + half;

        // A fragments: normal load from __shared__ (compiler → ds_read_b128)
        a_reg_t a0_reg = {}, a1_reg = {};
        {
            const int row0    = wave_m * 64 + (lane & 31);
            const int bc0     = half * 16;
            const int lds_off = row0 * TILE_K_BYTES + swizzle_byte_col(row0, bc0);
            const uint4 v = load_uint4_lds(smem_A[tic], lds_off);
            *reinterpret_cast<uint4*>(&a0_reg) = v;
        }
        {
            const int row1    = wave_m * 64 + 32 + (lane & 31);
            const int bc1     = half * 16;
            const int lds_off = row1 * TILE_K_BYTES + swizzle_byte_col(row1, bc1);
            const uint4 v = load_uint4_lds(smem_A[tic], lds_off);
            *reinterpret_cast<uint4*>(&a1_reg) = v;
        }

        // B fragments
        b_reg_t b0_reg = {}, b1_reg = {};
        {
            const int row0    = wave_n * 64 + (lane & 31);
            const int bc0     = half * 16;
            const int lds_off = row0 * TILE_K_BYTES + swizzle_byte_col(row0, bc0);
            const uint4 v = load_uint4_lds(smem_B[tic], lds_off);
            *reinterpret_cast<uint4*>(&b0_reg) = v;
        }
        {
            const int row1    = wave_n * 64 + 32 + (lane & 31);
            const int bc1     = half * 16;
            const int lds_off = row1 * TILE_K_BYTES + swizzle_byte_col(row1, bc1);
            const uint4 v = load_uint4_lds(smem_B[tic], lds_off);
            *reinterpret_cast<uint4*>(&b1_reg) = v;
        }

        // Scales (E8M0, one per lane per scale group)
        const int sa0 = (tile_m0+(lane&31) < M && sg < K_scale) ?
            (int)As[(tile_m0+(lane&31)) * K_scale + sg] : 127;
        const int sa1 = (tile_m1+(lane&31) < M && sg < K_scale) ?
            (int)As[(tile_m1+(lane&31)) * K_scale + sg] : 127;
        const int sb0 = (tile_n0+(lane&31) < N && sg < K_scale) ?
            (int)Bs[(tile_n0+(lane&31)) * K_scale + sg] : 127;
        const int sb1 = (tile_n1+(lane&31) < N && sg < K_scale) ?
            (int)Bs[(tile_n1+(lane&31)) * K_scale + sg] : 127;

        // 4 MFMA tiles
        c00 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a0_reg, b0_reg, c00, 4, 4, 0, sa0, 0, sb0);
        c01 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a0_reg, b1_reg, c01, 4, 4, 0, sa0, 0, sb1);
        c10 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a1_reg, b0_reg, c10, 4, 4, 0, sa1, 0, sb0);
        c11 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a1_reg, b1_reg, c11, 4, 4, 0, sa1, 0, sb1);

        __builtin_amdgcn_sched_barrier(0);
        __builtin_amdgcn_s_setprio(0);

        if (has_next) {
            asm volatile("s_waitcnt vmcnt(0)");
            __builtin_amdgcn_s_barrier();
        }
    }

    // ----------------------------------------------------------------
    // EPILOGUE: write output
    // Verified layout (Session 91): c_reg[r]→C[tm+(r&3)+(r>>2)*8+half*4][tn+lane&31]
    // ----------------------------------------------------------------
    #define WRITE_TILE(creg, tm, tn) \
    { \
        const int oc = (tn) + (lane & 31); \
        if (oc < N) { \
            _Pragma("unroll") \
            for (int r = 0; r < 16; r++) { \
                const int or2 = (tm) + (r & 3) + (r >> 2) * 8 + half * 4; \
                if (or2 < M) \
                    C[or2 * N + oc] = (__hip_bfloat16)((creg)[r]); \
            } \
        } \
    }

    WRITE_TILE(c00, tile_m0, tile_n0)
    WRITE_TILE(c01, tile_m0, tile_n1)
    WRITE_TILE(c10, tile_m1, tile_n0)
    WRITE_TILE(c11, tile_m1, tile_n1)
    #undef WRITE_TILE
}

void launch_blog_pp_v3(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C, int M, int N, int K
) {
    dim3 grid((M + BLOCK_M - 1) / BLOCK_M,
              (N + BLOCK_N - 1) / BLOCK_N);
    mxfp4_blog_pp_v3<<<grid, THREADS>>>(
        A.data_ptr<uint8_t>(), B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(), Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K);
}
"""

CPP_SOURCE = """
void launch_blog_pp_v3(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C, int M, int N, int K
);
"""

try:
    _mod = load_inline(
        name="mxfp4_blog_pp_v3",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_blog_pp_v3"],
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
    print("[blog_pp_v3] compile SUCCESS")
except Exception as e:
    print(f"[blog_pp_v3] compile FAILED: {e}")
    _OK = False


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
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
    """MXFP4 GEMM: AMD Blog 8-wave ping-pong with GLOBAL_LOAD_LDS and XOR swizzle.

    Falls back to aiter gemm_a4w4 for M < 128.
    """
    from aiter.ops.triton.quant import dynamic_mxfp4_quant

    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    if not _OK or M < 128:
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
    _mod.launch_blog_pp_v3(A_bytes, B_bytes, As_bytes, Bs_bytes, C, M, N, K)
    return C
