#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM — Shape-aware dispatch.

Compiles two custom kernels:
  - Kernel A: BLOCK_M=32,  BLOCK_N=128,  4 waves  → M<=32 shapes
  - Kernel B: BLOCK_M=128, BLOCK_N=256,  8 waves  → M>32  shapes (the v2 blog kernel)

Dispatch logic in custom_kernel():
  M <= 32 → Kernel A (32x128, 4 waves, 256 threads)
  M >  32 → Kernel B (128x256, 8 waves, 512 threads)
  Either fails → aiter.gemm_a4w4 fallback

Benchmark shapes and expected routing:
  M=4,   N=2880,  K=512  → Kernel A
  M=16,  N=2112,  K=7168 → Kernel A  (worst shape, key target)
  M=32,  N=4096,  K=512  → Kernel A
  M=32,  N=2880,  K=512  → Kernel A
  M=64,  N=7168,  K=2048 → Kernel B
  M=256, N=3072,  K=1536 → Kernel B
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

# ============================================================================
# Shared HIP utilities (inlined into both kernels via preprocessor)
# ============================================================================
_COMMON_HIP = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

typedef int   a_reg_t __attribute__((ext_vector_type(8)));
typedef int   b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

#define TILE_K        64
#define TILE_K_BYTES  32
#define WAVESIZE      64

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

// Generic tile loader (all threads cooperate)
template<int ROWS, int NTHREADS>
__device__ __forceinline__ void load_tile_to_lds(
    const uint8_t* __restrict__ global_base,
    uint8_t* __restrict__ lds_slot,
    int row_stride, int valid_rows, int global_row0, int tid
) {
    constexpr int total_chunks = ROWS * (TILE_K_BYTES / 16);
    const uint32_t buf_range = (uint32_t)(ROWS * row_stride + TILE_K_BYTES);
    const i32x4 srsrc = make_srsrc(global_base, buf_range);

    for (int chunk = tid; chunk < total_chunks; chunk += NTHREADS) {
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
"""

# ============================================================================
# Kernel A: BLOCK_M=32, BLOCK_N=128, 4 waves — targets M<=32
# Each wave owns 1 MFMA 32x32 output tile:
#   wave 0→N cols [bn+0..31], wave 1→[bn+32..63]
#   wave 2→[bn+64..95],       wave 3→[bn+96..127]
# Wave 0 is the load wave; waves 1-3 stall at a barrier while it prefetches.
# ============================================================================
_KERNEL_A_HIP = (
    _COMMON_HIP
    + r"""
#define BM_A  32
#define BN_A  128
#define THREADS_A  256

__global__ __launch_bounds__(THREADS_A, 1)
void mxfp4_small_m(
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

    const int bm = blockIdx.x * BM_A;
    const int bn = blockIdx.y * BN_A;

    const int K_half  = K / 2;
    const int K_scale = K / 32;
    const int num_k   = K / TILE_K;

    __shared__ uint8_t smem_A[2][BM_A * TILE_K_BYTES];
    __shared__ uint8_t smem_B[2][BN_A * TILE_K_BYTES];

    // Each wave owns 32 contiguous N-columns
    const int tile_m = bm;
    const int tile_n = bn + waveid * 32;

    c_reg_t c00 = {};

    load_tile_to_lds<BM_A, THREADS_A>(
        A + bm * K_half, smem_A[0], K_half, M, bm, tid);
    load_tile_to_lds<BN_A, THREADS_A>(
        B + bn * K_half, smem_B[0], K_half, N, bn, tid);
    asm volatile("s_waitcnt vmcnt(0)");
    __builtin_amdgcn_s_barrier();

    for (int kt = 0; kt < num_k; kt++) {
        const int tic      = kt & 1;
        const int toc      = 1 - tic;
        const bool has_next = (kt + 1 < num_k);

        // Wave 0 is load master; waves 1-3 stall
        if (waveid != 0) {
            __builtin_amdgcn_s_barrier();
        }

        if (has_next && waveid == 0) {
            __builtin_amdgcn_sched_barrier(0);
            const int next_k_off = (kt + 1) * TILE_K_BYTES;

            constexpr int a_chunks = BM_A * (TILE_K_BYTES / 16);
            for (int c = lane; c < a_chunks; c += WAVESIZE) {
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

            constexpr int b_chunks = BN_A * (TILE_K_BYTES / 16);
            for (int c = lane; c < b_chunks; c += WAVESIZE) {
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
            __builtin_amdgcn_sched_barrier(0);
        }

        __builtin_amdgcn_s_barrier();
        __builtin_amdgcn_s_setprio(1);
        __builtin_amdgcn_sched_barrier(0);

        const int sg = kt * 2 + half;

        a_reg_t a0_reg = {};
        {
            const int row      = lane & 31;
            const int byte_col = half * 16;
            load_uint4_from_lds(smem_A[tic],
                row * TILE_K_BYTES + swizzle_byte_col(row, byte_col), &a0_reg);
        }

        b_reg_t b0_reg = {};
        {
            const int b_row    = waveid * 32 + (lane & 31);
            const int byte_col = half * 16;
            load_uint4_from_lds(smem_B[tic],
                b_row * TILE_K_BYTES + swizzle_byte_col(b_row, byte_col), &b0_reg);
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

void launch_small_m(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C, int M, int N, int K
) {
    dim3 grid((M + BM_A - 1) / BM_A, (N + BN_A - 1) / BN_A);
    mxfp4_small_m<<<grid, THREADS_A>>>(
        A.data_ptr<uint8_t>(), B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(), Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K);
}
"""
)

# ============================================================================
# Kernel B: BLOCK_M=128, BLOCK_N=256, 8 waves — targets M>32 (blog v2)
# Identical to submission_amd_blog_v2.py but combined in one load_inline call.
# ============================================================================
_KERNEL_B_HIP = (
    _COMMON_HIP
    + r"""
#define BM_B      128
#define BN_B      256
#define THREADS_B 512

__global__ __launch_bounds__(THREADS_B, 1)
void mxfp4_large_m(
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

    const int wave_m = waveid / 4;
    const int wave_n = waveid % 4;

    const int bm = blockIdx.x * BM_B;
    const int bn = blockIdx.y * BN_B;

    const int K_half  = K / 2;
    const int K_scale = K / 32;
    const int num_k   = K / TILE_K;

    __shared__ uint8_t smem_A[2][BM_B * TILE_K_BYTES];
    __shared__ uint8_t smem_B[2][BN_B * TILE_K_BYTES];

    const int tile_m0 = bm + wave_m * 64;
    const int tile_m1 = tile_m0 + 32;
    const int tile_n0 = bn + wave_n * 64;
    const int tile_n1 = tile_n0 + 32;

    c_reg_t c00 = {}, c01 = {}, c10 = {}, c11 = {};

    load_tile_to_lds<BM_B, THREADS_B>(
        A + bm * K_half, smem_A[0], K_half, M, bm, tid);
    load_tile_to_lds<BN_B, THREADS_B>(
        B + bn * K_half, smem_B[0], K_half, N, bn, tid);
    asm volatile("s_waitcnt vmcnt(0)");
    __builtin_amdgcn_s_barrier();

    for (int kt = 0; kt < num_k; kt++) {
        const int tic      = kt & 1;
        const int toc      = 1 - tic;
        const bool has_next = (kt + 1 < num_k);

        if (wave_m == 1) {
            __builtin_amdgcn_s_barrier();
        }

        if (has_next && wave_m == 0) {
            __builtin_amdgcn_sched_barrier(0);
            const int next_k_off = (kt + 1) * TILE_K_BYTES;
            const int load_tid = wave_n * WAVESIZE + lane;

            {
                constexpr int a_chunks = BM_B * (TILE_K_BYTES / 16);
                for (int c = load_tid; c < a_chunks; c += 256) {
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
            {
                constexpr int b_chunks = BN_B * (TILE_K_BYTES / 16);
                for (int c = load_tid; c < b_chunks; c += 256) {
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

        __builtin_amdgcn_s_barrier();
        __builtin_amdgcn_s_setprio(1);
        __builtin_amdgcn_sched_barrier(0);

        const int sg = kt * 2 + half;

        a_reg_t a0_reg = {}, a1_reg = {};
        {
            const int row0     = wave_m * 64 + (lane & 31);
            const int byte_col = half * 16;
            load_uint4_from_lds(smem_A[tic],
                row0 * TILE_K_BYTES + swizzle_byte_col(row0, byte_col), &a0_reg);
        }
        {
            const int row1     = wave_m * 64 + 32 + (lane & 31);
            const int byte_col = half * 16;
            load_uint4_from_lds(smem_A[tic],
                row1 * TILE_K_BYTES + swizzle_byte_col(row1, byte_col), &a1_reg);
        }

        b_reg_t b0_reg = {}, b1_reg = {};
        {
            const int row0     = wave_n * 64 + (lane & 31);
            const int byte_col = half * 16;
            load_uint4_from_lds(smem_B[tic],
                row0 * TILE_K_BYTES + swizzle_byte_col(row0, byte_col), &b0_reg);
        }
        {
            const int row1     = wave_n * 64 + 32 + (lane & 31);
            const int byte_col = half * 16;
            load_uint4_from_lds(smem_B[tic],
                row1 * TILE_K_BYTES + swizzle_byte_col(row1, byte_col), &b1_reg);
        }

        asm volatile("s_waitcnt lgkmcnt(0)");

        const int sa0 = (tile_m0+(lane&31) < M && sg < K_scale) ?
            (int)As[(tile_m0+(lane&31)) * K_scale + sg] : 127;
        const int sa1 = (tile_m1+(lane&31) < M && sg < K_scale) ?
            (int)As[(tile_m1+(lane&31)) * K_scale + sg] : 127;
        const int sb0 = (tile_n0+(lane&31) < N && sg < K_scale) ?
            (int)Bs[(tile_n0+(lane&31)) * K_scale + sg] : 127;
        const int sb1 = (tile_n1+(lane&31) < N && sg < K_scale) ?
            (int)Bs[(tile_n1+(lane&31)) * K_scale + sg] : 127;

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

void launch_large_m(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C, int M, int N, int K
) {
    dim3 grid((M + BM_B - 1) / BM_B, (N + BN_B - 1) / BN_B);
    mxfp4_large_m<<<grid, THREADS_B>>>(
        A.data_ptr<uint8_t>(), B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(), Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K);
}
"""
)

_CPP_SMALL = """
void launch_small_m(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C, int M, int N, int K
);
"""

_CPP_LARGE = """
void launch_large_m(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C, int M, int N, int K
);
"""

_CFLAGS = [
    "--offload-arch=gfx950",
    "-std=c++20",
    "-O3",
    "-mllvm",
    "-amdgpu-early-inline-all=true",
    "-mllvm",
    "-amdgpu-function-calls=false",
]

_mod_small = None
_mod_large = None
_OK_SMALL = False
_OK_LARGE = False

try:
    _mod_small = load_inline(
        name="mxfp4_small_m_dispatch",
        cpp_sources=[_CPP_SMALL],
        cuda_sources=[_KERNEL_A_HIP],
        functions=["launch_small_m"],
        verbose=False,
        extra_cuda_cflags=_CFLAGS,
    )
    _OK_SMALL = True
    print("[shape_dispatch] small-M kernel compile SUCCESS")
except Exception as e:
    print(f"[shape_dispatch] small-M kernel compile FAILED: {e}")

try:
    _mod_large = load_inline(
        name="mxfp4_large_m_dispatch",
        cpp_sources=[_CPP_LARGE],
        cuda_sources=[_KERNEL_B_HIP],
        functions=["launch_large_m"],
        verbose=False,
        extra_cuda_cflags=_CFLAGS,
    )
    _OK_LARGE = True
    print("[shape_dispatch] large-M kernel compile SUCCESS")
except Exception as e:
    print(f"[shape_dispatch] large-M kernel compile FAILED: {e}")


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
    """Shape-aware MXFP4 GEMM: 32x128 tile for M<=32, 128x256 for M>32."""
    from aiter.ops.triton.quant import dynamic_mxfp4_quant

    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    use_small = M <= 32

    if use_small and not _OK_SMALL:
        return _aiter_fallback(data)
    if not use_small and not _OK_LARGE:
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

    if use_small:
        _mod_small.launch_small_m(A_bytes, B_bytes, As_bytes, Bs_bytes, C, M, N, K)
    else:
        _mod_large.launch_large_m(A_bytes, B_bytes, As_bytes, Bs_bytes, C, M, N, K)

    return C
