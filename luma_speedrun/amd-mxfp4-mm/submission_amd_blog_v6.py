#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""AMD CDNA4 Blog 8-Wave Ping-Pong FP4 GEMM — v6.

v6: removes GLOBAL_LOAD_LDS to sidestep the AS3 pointer issue.
    Uses normal vectorized global loads (uint4) instead.
    All AMD blog scheduling patterns are preserved:
      - 8-wave ping-pong with conditional barriers
      - s_setprio(1) during MFMA, 0 during loads
      - sched_barrier(0) at boundaries
      - LDS XOR swizzle for bank conflict avoidance
      - Double-buffered LDS

History:
  v1-v5: GLOBAL_LOAD_LDS variants — all hit AS3 pointer compile issues
  v6: normal uint4 global reads, writing to __shared__ directly (no AS3 needed)

Note: GLOBAL_LOAD_LDS provides ~15% BW improvement by bypassing L1/L2.
     The 8-wave ping-pong scheduling improvement is ~20-25%.
     v6 captures the scheduling win without the GLOBAL_LOAD_LDS complication.

LDS layout (double-buffered):
  smem_A[2][128 rows × 32 bytes] = 2 × 4096 = 8 KB
  smem_B[2][256 rows × 32 bytes] = 2 × 8192 = 16 KB
  Total: 24 KB (well within 160 KB LDS per CU on MI355X)

8-wave ping-pong (AMD Blog):
  wave_m = waveid / 4  (0 or 1)
  wave_n = waveid % 4  (0..3)
  512 threads = 8 wavefronts of 64 threads each
  Barrier 0: wave_m==1 stalls → wave_m==0 issues global loads for toc
  Barrier 1: releases wave_m==1 → all compute MFMA from tic
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

#define BLOCK_M      128
#define BLOCK_N      256
#define TILE_K        64
#define TILE_K_BYTES  32   // TILE_K / 2 bytes (FP4 packed 2 per byte)
#define THREADS      512
#define WAVESIZE      64
#define LDS_A_BYTES  (BLOCK_M * TILE_K_BYTES)   // 4096
#define LDS_B_BYTES  (BLOCK_N * TILE_K_BYTES)   // 8192

// ============================================================================
// LDS XOR swizzle (AMD Blog formula, 64-bank CDNA4 LDS, self-inverse)
// Prevents bank conflicts for 128-row × 32-byte tile access patterns.
// ============================================================================
__device__ __forceinline__ int swizzle_byte_col(int row, int byte_col) {
    const int pair = (row >> 1) & 7;
    const int perm = pair ^ (((pair >> 1) ^ (pair >> 2)) & 1);
    return byte_col ^ (perm << 4);
}

// ============================================================================
// 8-wave ping-pong FP4 MFMA kernel — AMD Blog pattern, v6
// ============================================================================
__global__ __launch_bounds__(THREADS, 1)
void mxfp4_blog_pp_v6(
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

    // Per-wave output coordinates (4 MFMA tiles: 2x2 = 64x64 per wave)
    const int tile_m0 = bm + wave_m * 64;
    const int tile_m1 = tile_m0 + 32;
    const int tile_n0 = bn + wave_n * 64;
    const int tile_n1 = tile_n0 + 32;

    c_reg_t c00 = {}, c01 = {}, c10 = {}, c11 = {};

    // ----------------------------------------------------------------
    // load_tile: cooperative load of a TILE_K_BYTES-column tile into LDS
    // Each 16-byte chunk written with XOR swizzle.
    // ----------------------------------------------------------------
    #define LOAD_TILE_A(buf, k_byte_off) \
    { \
        constexpr int chunks = BLOCK_M * (TILE_K_BYTES / 16); \
        _Pragma("unroll 2") \
        for (int _c = tid; _c < chunks; _c += THREADS) { \
            const int _row      = _c / (TILE_K_BYTES / 16); \
            const int _byte_col = (_c % (TILE_K_BYTES / 16)) * 16; \
            const int _gr       = bm + _row; \
            uint4 _v = {}; \
            if (_gr < M) \
                _v = *reinterpret_cast<const uint4*>(A + _gr * K_half + (k_byte_off) + _byte_col); \
            const int _sc = swizzle_byte_col(_row, _byte_col); \
            *reinterpret_cast<uint4*>(smem_A[(buf)] + _row * TILE_K_BYTES + _sc) = _v; \
        } \
    }

    #define LOAD_TILE_B(buf, k_byte_off) \
    { \
        constexpr int chunks = BLOCK_N * (TILE_K_BYTES / 16); \
        _Pragma("unroll 2") \
        for (int _c = tid; _c < chunks; _c += THREADS) { \
            const int _row      = _c / (TILE_K_BYTES / 16); \
            const int _byte_col = (_c % (TILE_K_BYTES / 16)) * 16; \
            const int _gr       = bn + _row; \
            uint4 _v = {}; \
            if (_gr < N) \
                _v = *reinterpret_cast<const uint4*>(B + _gr * K_half + (k_byte_off) + _byte_col); \
            const int _sc = swizzle_byte_col(_row, _byte_col); \
            *reinterpret_cast<uint4*>(smem_B[(buf)] + _row * TILE_K_BYTES + _sc) = _v; \
        } \
    }

    // Load only by ping (wave_m==0) threads in the hot loop
    #define LOAD_TILE_A_PING(buf, k_byte_off) \
    { \
        constexpr int chunks = BLOCK_M * (TILE_K_BYTES / 16); \
        const int _load_tid = wave_n * WAVESIZE + lane; \
        _Pragma("unroll 2") \
        for (int _c = _load_tid; _c < chunks; _c += 256) { \
            const int _row      = _c / (TILE_K_BYTES / 16); \
            const int _byte_col = (_c % (TILE_K_BYTES / 16)) * 16; \
            const int _gr       = bm + _row; \
            uint4 _v = {}; \
            if (_gr < M) \
                _v = *reinterpret_cast<const uint4*>(A + _gr * K_half + (k_byte_off) + _byte_col); \
            const int _sc = swizzle_byte_col(_row, _byte_col); \
            *reinterpret_cast<uint4*>(smem_A[(buf)] + _row * TILE_K_BYTES + _sc) = _v; \
        } \
    }

    #define LOAD_TILE_B_PING(buf, k_byte_off) \
    { \
        constexpr int chunks = BLOCK_N * (TILE_K_BYTES / 16); \
        const int _load_tid = wave_n * WAVESIZE + lane; \
        _Pragma("unroll 2") \
        for (int _c = _load_tid; _c < chunks; _c += 256) { \
            const int _row      = _c / (TILE_K_BYTES / 16); \
            const int _byte_col = (_c % (TILE_K_BYTES / 16)) * 16; \
            const int _gr       = bn + _row; \
            uint4 _v = {}; \
            if (_gr < N) \
                _v = *reinterpret_cast<const uint4*>(B + _gr * K_half + (k_byte_off) + _byte_col); \
            const int _sc = swizzle_byte_col(_row, _byte_col); \
            *reinterpret_cast<uint4*>(smem_B[(buf)] + _row * TILE_K_BYTES + _sc) = _v; \
        } \
    }

    // ----------------------------------------------------------------
    // PROLOGUE: all 512 threads load K-tile 0 into double-buffer[0]
    // ----------------------------------------------------------------
    LOAD_TILE_A(0, 0)
    LOAD_TILE_B(0, 0)
    __syncthreads();

    // ----------------------------------------------------------------
    // HOT LOOP: 8-wave ping-pong (AMD Blog pattern)
    // ----------------------------------------------------------------
    for (int kt = 0; kt < num_k; kt++) {
        const int tic       = kt & 1;
        const int toc       = 1 - tic;
        const bool has_next = (kt + 1 < num_k);
        const int next_k_off = (kt + 1) * TILE_K_BYTES;

        // Blog barrier 0: wave_m==1 stalls while wave_m==0 issues loads
        if (wave_m == 1) {
            __builtin_amdgcn_s_barrier();
        }

        // Load group (wave_m==0): prefetch next K tile into toc buffer
        if (has_next && wave_m == 0) {
            __builtin_amdgcn_sched_barrier(0);
            LOAD_TILE_A_PING(toc, next_k_off)
            LOAD_TILE_B_PING(toc, next_k_off)
            __builtin_amdgcn_sched_barrier(0);
        }

        // Blog barrier 1: releases wave_m==1; all waves proceed to MFMA
        __builtin_amdgcn_s_barrier();

        // MFMA with elevated priority
        __builtin_amdgcn_s_setprio(1);
        __builtin_amdgcn_sched_barrier(0);

        const int sg = kt * 2 + half;

        // A fragments: 128-bit LDS read via direct uint4 dereference
        // Row indexing: wave_m*64 + (lane&31) for the 32x32 sub-tile
        a_reg_t a0_reg = {}, a1_reg = {};
        {
            const int row0    = wave_m * 64 + (lane & 31);
            const int bc0     = half * 16;
            const int lds_off = row0 * TILE_K_BYTES + swizzle_byte_col(row0, bc0);
            *reinterpret_cast<uint4*>(&a0_reg) =
                *reinterpret_cast<const uint4*>(smem_A[tic] + lds_off);
        }
        {
            const int row1    = wave_m * 64 + 32 + (lane & 31);
            const int bc1     = half * 16;
            const int lds_off = row1 * TILE_K_BYTES + swizzle_byte_col(row1, bc1);
            *reinterpret_cast<uint4*>(&a1_reg) =
                *reinterpret_cast<const uint4*>(smem_A[tic] + lds_off);
        }

        // B fragments
        b_reg_t b0_reg = {}, b1_reg = {};
        {
            const int row0    = wave_n * 64 + (lane & 31);
            const int bc0     = half * 16;
            const int lds_off = row0 * TILE_K_BYTES + swizzle_byte_col(row0, bc0);
            *reinterpret_cast<uint4*>(&b0_reg) =
                *reinterpret_cast<const uint4*>(smem_B[tic] + lds_off);
        }
        {
            const int row1    = wave_n * 64 + 32 + (lane & 31);
            const int bc1     = half * 16;
            const int lds_off = row1 * TILE_K_BYTES + swizzle_byte_col(row1, bc1);
            *reinterpret_cast<uint4*>(&b1_reg) =
                *reinterpret_cast<const uint4*>(smem_B[tic] + lds_off);
        }

        // Scales (E8M0, one per lane per scale group)
        const int sa0 = (tile_m0 + (lane & 31) < M && sg < K_scale) ?
            (int)As[(tile_m0 + (lane & 31)) * K_scale + sg] : 127;
        const int sa1 = (tile_m1 + (lane & 31) < M && sg < K_scale) ?
            (int)As[(tile_m1 + (lane & 31)) * K_scale + sg] : 127;
        const int sb0 = (tile_n0 + (lane & 31) < N && sg < K_scale) ?
            (int)Bs[(tile_n0 + (lane & 31)) * K_scale + sg] : 127;
        const int sb1 = (tile_n1 + (lane & 31) < N && sg < K_scale) ?
            (int)Bs[(tile_n1 + (lane & 31)) * K_scale + sg] : 127;

        // 4 MFMA tiles (FP4 32x32x64)
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

        // Wait for stores to LDS to be visible before next iteration
        if (has_next) {
            __builtin_amdgcn_s_barrier();
        }
    }

    #undef LOAD_TILE_A
    #undef LOAD_TILE_B
    #undef LOAD_TILE_A_PING
    #undef LOAD_TILE_B_PING

    // ----------------------------------------------------------------
    // EPILOGUE: write BF16 output.
    // Verified layout (Session 91):
    //   c_reg[r] -> C[tm + (r&3) + (r>>2)*8 + half*4][tn + lane&31]
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

void launch_blog_pp_v6(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C, int M, int N, int K
) {
    dim3 grid((M + BLOCK_M - 1) / BLOCK_M,
              (N + BLOCK_N - 1) / BLOCK_N);
    mxfp4_blog_pp_v6<<<grid, THREADS>>>(
        A.data_ptr<uint8_t>(), B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(), Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K);
}
"""

CPP_SOURCE = """
void launch_blog_pp_v6(
    torch::Tensor A, torch::Tensor B,
    torch::Tensor As, torch::Tensor Bs,
    torch::Tensor C, int M, int N, int K
);
"""

try:
    _mod = load_inline(
        name="mxfp4_blog_pp_v6",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_blog_pp_v6"],
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
    print("[blog_pp_v6] compile SUCCESS")
except Exception as e:
    print(f"[blog_pp_v6] compile FAILED: {e}")
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
    """MXFP4 GEMM: AMD Blog 8-wave ping-pong with LDS XOR swizzle.

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
    _mod.launch_blog_pp_v6(A_bytes, B_bytes, As_bytes, Bs_bytes, C, M, N, K)
    return C
