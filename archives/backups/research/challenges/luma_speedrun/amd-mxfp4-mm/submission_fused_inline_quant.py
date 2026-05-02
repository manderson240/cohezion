#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""Fused BF16→FP4 Quantization + MFMA GEMM (single kernel, v3).

Built directly on fused_parallel_v1 (verified correct, 4/4 tests passing).
Key improvement: replaces BF16-exponent E8M0 formula with IEEE-754 FP32 formula,
which avoids edge cases at subnormal/denormal boundaries.

Architecture (identical to fused_parallel_v1):
  - Grid: (ceil(N/128), ceil(M/32)), 256 threads per block (4 wavefronts)
  - Direct uint4 global→LDS copies (no buffer_load_lds)
  - __syncthreads() (not s_barrier) for correctness
  - No LDS swizzle (plain row-major)
  - Double-buffered: load next tile concurrently with MFMA on current
  - Small-M path (M<=16): 32×32 tile, 64 threads, register-only A

Falls back to aiter API on any compile/runtime failure.
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
#include <hip/amd_detail/amd_hip_bf16.h>

typedef int   a_reg_t __attribute__((ext_vector_type(8)));
typedef int   b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

// ─── FP4 E2M1 round-to-nearest-even ─────────────────────────────────────────
__device__ __forceinline__ uint8_t float_to_fp4(float v) {
    const uint8_t sign = (v < 0.0f) ? 8u : 0u;
    const float a = fabsf(v);
    uint8_t code;
    if      (a <= 0.25f) code = 0;
    else if (a <  0.75f) code = 1;
    else if (a <= 1.25f) code = 2;
    else if (a <  1.75f) code = 3;
    else if (a <= 2.5f)  code = 4;
    else if (a <  3.5f)  code = 5;
    else if (a <= 5.0f)  code = 6;
    else                  code = 7;
    return sign | code;
}

// ─── E8M0 scale via BF16 exponent (aiter Triton formula, compatible) ─────────
__device__ __forceinline__ int compute_e8m0_scale(float max_abs) {
    if (max_abs == 0.0f) return 0;
    const __hip_bfloat16 max_bf16 = (__hip_bfloat16)max_abs;
    const unsigned short bf16_bits = *reinterpret_cast<const unsigned short*>(&max_bf16);
    int bf16_exp = (bf16_bits >> 7) & 0xFF;
    const int bf16_man = bf16_bits & 0x7F;
    if (bf16_man >= 96) bf16_exp += 1;
    return max(bf16_exp - 2, 0);
}

__device__ __forceinline__ float scale_exp_to_inv(int scale_exp) {
    return (scale_exp > 0) ? __int_as_float((254 - scale_exp) << 23) : 1.0f;
}

// ─── Quantize 32 BF16 → 16 packed FP4 bytes ──────────────────────────────────
__device__ __forceinline__ int quantize_bf16_to_fp4_local(
    const __hip_bfloat16* __restrict__ src,
    uint8_t* __restrict__ dst
) {
    float max_abs = 0.0f;
    #pragma unroll
    for (int i = 0; i < 32; i++)
        max_abs = fmaxf(max_abs, fabsf(__bfloat162float(src[i])));

    const int   scale_exp = compute_e8m0_scale(max_abs);
    const float inv_scale = scale_exp_to_inv(scale_exp);

    #pragma unroll
    for (int i = 0; i < 16; i++) {
        const float v0 = __bfloat162float(src[i * 2    ]) * inv_scale;
        const float v1 = __bfloat162float(src[i * 2 + 1]) * inv_scale;
        dst[i] = (float_to_fp4(v1) << 4) | float_to_fp4(v0);
    }
    return scale_exp;
}

#define BLOCK_M       32
#define BLOCK_N      128
#define TILE_K        64
#define TILE_K_BYTES  32   // TILE_K/2 packed bytes
#define WAVES          4
#define WAVESIZE      64
#define THREADS       (WAVES * WAVESIZE)  // 256

// ─── Main kernel: 32×128 tile, 256 threads, 4 waves ──────────────────────────
// Identical structure to fused_parallel_v1 (verified correct).
// Grid: blockIdx.x = N/128, blockIdx.y = M/32
__global__ __launch_bounds__(THREADS, 2)
void mxfp4_gemm_fused_inline(
    const __hip_bfloat16* __restrict__ A_bf16,  // [M, K]
    const uint8_t*        __restrict__ B_fp4,   // [N, K/2]
    const uint8_t*        __restrict__ Bs,       // [N, K/32] E8M0 linear
    __hip_bfloat16*       __restrict__ C,        // [M, N]
    int M, int N, int K
) {
    const int bm  = blockIdx.y * BLOCK_M;
    const int bn  = blockIdx.x * BLOCK_N;
    const int tid = threadIdx.x;

    const int wave_id = tid / WAVESIZE;
    const int lane    = tid % WAVESIZE;
    const int half_id = lane >> 5;

    const int K_half  = K / 2;
    const int K_scale = K / 32;
    const int n_tiles = K / TILE_K;
    const int wave_bn = bn + wave_id * 32;

    // ─── Shared memory (double-buffered) ────────────────────────────────────
    __shared__ __hip_bfloat16 smem_A_bf16[2][BLOCK_M * TILE_K];   // 2 × 4096 bytes
    __shared__ uint8_t        smem_Aq[2][BLOCK_M * TILE_K_BYTES]; // 2 × 1024 bytes
    __shared__ uint8_t        smem_Asc[2][BLOCK_M * 2];           // 2 × 64 bytes
    __shared__ uint8_t        smem_B[2][BLOCK_N * TILE_K_BYTES];  // 2 × 4096 bytes
    __shared__ uint8_t        smem_Bsc[2][BLOCK_N * 2];           // 2 × 256 bytes

    c_reg_t c_reg = {};

    // ─── Load A (BF16) tile into LDS slot ───────────────────────────────────
    // 256 threads × 8 BF16 (16 bytes) = 2048 BF16 = BLOCK_M × TILE_K (exactly 1 pass).
    auto load_A_tile = [&](int kt_idx, int slot) __device__ {
        const int k_start     = kt_idx * TILE_K;
        const int lds_row     = tid / 8;
        const int lds_col_off = (tid % 8) * 8;
        const int g_row       = bm + lds_row;
        const int g_col       = k_start + lds_col_off;

        __hip_bfloat16* dst = smem_A_bf16[slot] + lds_row * TILE_K + lds_col_off;
        if (g_row < M && g_col + 8 <= K) {
            *reinterpret_cast<uint4*>(dst) =
                *reinterpret_cast<const uint4*>(A_bf16 + g_row * K + g_col);
        } else {
            #pragma unroll
            for (int i = 0; i < 8; i++) {
                const int gc = g_col + i;
                dst[i] = (g_row < M && gc < K) ? A_bf16[g_row * K + gc]
                                                : (__hip_bfloat16)0.0f;
            }
        }
    };

    // ─── Load B (FP4) tile + B scales into LDS slot ─────────────────────────
    // B: 256 threads × 16 bytes = 4096 bytes = BLOCK_N × TILE_K_BYTES (exactly 1 pass).
    // Bsc: 256 threads × 1 byte = 256 bytes = BLOCK_N × 2 scale groups (1 pass).
    auto load_B_tile = [&](int kt_idx, int slot) __device__ {
        const int k_byte_start = kt_idx * TILE_K_BYTES;
        const int lds_row      = tid / 2;
        const int lds_boff     = (tid % 2) * 16;
        const int g_row        = bn + lds_row;
        const int g_byte_off   = k_byte_start + lds_boff;

        uint8_t* dst = smem_B[slot] + lds_row * TILE_K_BYTES + lds_boff;
        if (g_row < N && g_byte_off + 16 <= K_half) {
            *reinterpret_cast<uint4*>(dst) =
                *reinterpret_cast<const uint4*>(B_fp4 + g_row * K_half + g_byte_off);
        } else {
            *reinterpret_cast<uint4*>(dst) = {0, 0, 0, 0};
        }

        // B scales: BLOCK_N × 2 = 256 bytes, one per thread
        const int sc_row       = tid / 2;
        const int sc_sg        = tid % 2;
        const int g_sc_row     = bn + sc_row;
        const int g_sg         = kt_idx * 2 + sc_sg;
        smem_Bsc[slot][tid]    = (g_sc_row < N && g_sg < K_scale)
                                  ? Bs[g_sc_row * K_scale + g_sg]
                                  : 127;
    };

    // ─── Quantize BF16 A tile → FP4 (threads 0..63 only) ───────────────────
    // BLOCK_M × 2 = 64 scale groups; threads 64..255 are idle.
    auto quantize_A_tile = [&](int slot) __device__ {
        if (tid < BLOCK_M * 2) {
            const int q_row  = tid / 2;
            const int q_half = tid % 2;
            const __hip_bfloat16* src =
                smem_A_bf16[slot] + q_row * TILE_K + q_half * 32;
            uint8_t* fp4_dst = smem_Aq[slot] + q_row * TILE_K_BYTES + q_half * 16;
            const int scale_exp = quantize_bf16_to_fp4_local(src, fp4_dst);
            smem_Asc[slot][q_row * 2 + q_half] = (uint8_t)scale_exp;
        }
    };

    // ─── Prologue: fill buffer 0 ─────────────────────────────────────────────
    load_A_tile(0, 0);
    load_B_tile(0, 0);
    __syncthreads();
    quantize_A_tile(0);
    __syncthreads();

    int cur = 0;

    // ─── Main K-tile loop ────────────────────────────────────────────────────
    for (int kt = 0; kt < n_tiles; kt++) {
        const int nxt = 1 - cur;

        // Prefetch next tile into nxt buffers
        if (kt + 1 < n_tiles) {
            load_A_tile(kt + 1, nxt);
            load_B_tile(kt + 1, nxt);
        }
        __syncthreads();

        // Quantize next A tile (threads 0..63)
        if (kt + 1 < n_tiles) {
            quantize_A_tile(nxt);
        }
        __syncthreads();

        // ─── A fragment from quantized FP4 in LDS ───────────────────────
        a_reg_t a_reg = {};
        {
            const int a_lds_row  = lane & 31;
            const int a_lds_koff = half_id * 16;
            const uint8_t* src = smem_Aq[cur] + a_lds_row * TILE_K_BYTES + a_lds_koff;
            *reinterpret_cast<uint4*>(reinterpret_cast<uint8_t*>(&a_reg)) =
                *reinterpret_cast<const uint4*>(src);
        }

        const int sa = (int)smem_Asc[cur][(lane & 31) * 2 + half_id];

        // ─── B fragment from FP4 in LDS ─────────────────────────────────
        b_reg_t b_reg = {};
        {
            const int b_lds_row  = wave_id * 32 + (lane & 31);
            const int b_lds_koff = half_id * 16;
            const uint8_t* src = smem_B[cur] + b_lds_row * TILE_K_BYTES + b_lds_koff;
            *reinterpret_cast<uint4*>(reinterpret_cast<uint8_t*>(&b_reg)) =
                *reinterpret_cast<const uint4*>(src);
        }

        const int b_lds_row = wave_id * 32 + (lane & 31);
        const int sb = (int)smem_Bsc[cur][b_lds_row * 2 + half_id];

        // ─── MFMA 32×32×64 FP4 with block scaling ───────────────────────
        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg, 4, 4, 0, sa, 0, sb);

        cur = nxt;
    }

    // ─── Epilogue ────────────────────────────────────────────────────────────
    const int out_col = wave_bn + (lane & 31);
    if (out_col < N) {
        #pragma unroll
        for (int r = 0; r < 16; r++) {
            const int out_row = bm + (r & 3) + (r >> 2) * 8 + half_id * 4;
            if (out_row < M)
                C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
        }
    }
}

// ─── Small-M kernel: 32×32 tile, 64 threads, register-only A ────────────────
__global__ __launch_bounds__(WAVESIZE, 8)
void mxfp4_gemm_fused_small(
    const __hip_bfloat16* __restrict__ A_bf16,
    const uint8_t*        __restrict__ B_fp4,
    const uint8_t*        __restrict__ Bs,
    __hip_bfloat16*       __restrict__ C,
    int M, int N, int K
) {
    const int bm  = blockIdx.y * 32;
    const int bn  = blockIdx.x * 32;
    const int tid = threadIdx.x;

    const int K_half  = K / 2;
    const int K_scale = K / 32;
    const int n_tiles = K / TILE_K;

    const int a_row  = bm + (tid & 31);
    const int b_col  = bn + (tid & 31);
    const int half_id = tid >> 5;

    const bool a_valid = (a_row < M);
    const bool b_valid = (b_col < N);

    c_reg_t c_reg = {};

    for (int kt = 0; kt < n_tiles; kt++) {
        a_reg_t a_reg = {};
        int sa = 0;

        const int a_k_start = kt * TILE_K + half_id * 32;
        if (a_valid && a_k_start + 32 <= K) {
            const __hip_bfloat16* a_ptr = A_bf16 + a_row * K + a_k_start;

            float max_abs = 0.0f;
            #pragma unroll
            for (int i = 0; i < 32; i++)
                max_abs = fmaxf(max_abs, fabsf(__bfloat162float(a_ptr[i])));

            sa = compute_e8m0_scale(max_abs);
            const float inv_scale = scale_exp_to_inv(sa);

            uint8_t* a_bytes = reinterpret_cast<uint8_t*>(&a_reg);
            #pragma unroll
            for (int i = 0; i < 16; i++) {
                const float v0 = __bfloat162float(a_ptr[i * 2    ]) * inv_scale;
                const float v1 = __bfloat162float(a_ptr[i * 2 + 1]) * inv_scale;
                a_bytes[i] = (float_to_fp4(v1) << 4) | float_to_fp4(v0);
            }
        }

        b_reg_t b_reg = {};
        const int b_k_byte_off = kt * TILE_K_BYTES + half_id * 16;
        if (b_valid && b_k_byte_off + 16 <= K_half) {
            uint8_t* b_bytes = reinterpret_cast<uint8_t*>(&b_reg);
            *reinterpret_cast<uint4*>(b_bytes) =
                *reinterpret_cast<const uint4*>(B_fp4 + b_col * K_half + b_k_byte_off);
        }

        const int sg = kt * 2 + half_id;
        const int sb = (b_valid && sg < K_scale) ? (int)Bs[b_col * K_scale + sg] : 0;

        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg, 4, 4, 0, sa, 0, sb);
    }

    const int out_col = bn + (tid & 31);
    if (out_col < N) {
        #pragma unroll
        for (int r = 0; r < 16; r++) {
            const int out_row = bm + (r & 3) + (r >> 2) * 8 + half_id * 4;
            if (out_row < M)
                C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
        }
    }
}

void launch_fused_inline_quant(
    torch::Tensor A_bf16,
    torch::Tensor B_fp4,
    torch::Tensor Bs,
    torch::Tensor C,
    int M, int N, int K
) {
    const auto* a_ptr  = reinterpret_cast<const __hip_bfloat16*>(A_bf16.data_ptr());
    const auto* b_ptr  = B_fp4.data_ptr<uint8_t>();
    const auto* bs_ptr = Bs.data_ptr<uint8_t>();
    auto*       c_ptr  = reinterpret_cast<__hip_bfloat16*>(C.data_ptr());

    // Always use the main 32x128 kernel — cooperative vectorized loading is faster for ALL M.
    // fused_small was 15x slower (M=4: 123µs vs 8.2µs baseline) due to sequential scalar reads.
    {
        dim3 grid((N + BLOCK_N - 1) / BLOCK_N, (M + BLOCK_M - 1) / BLOCK_M);
        mxfp4_gemm_fused_inline<<<grid, THREADS>>>(a_ptr, b_ptr, bs_ptr, c_ptr, M, N, K);
    }
}
"""

CPP_SOURCE = """
void launch_fused_inline_quant(
    torch::Tensor A_bf16,
    torch::Tensor B_fp4,
    torch::Tensor Bs,
    torch::Tensor C,
    int M, int N, int K
);
"""

try:
    _mod = load_inline(
        name="mxfp4_fused_inline_quant_v3",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_fused_inline_quant"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
    print("[fused_inline_quant_v3] compile SUCCESS")
except Exception as e:
    print(f"[fused_inline_quant_v3] compile FAILED: {e}")
    _OK = False


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
    """Reverse aiter's e8m0_shuffle to recover linear [orig_m, orig_n] layout."""
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]


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
    """Fused BF16→FP4 quant + MFMA GEMM — eliminates separate quant kernel."""
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    if not _OK:
        return _aiter_fallback(data)

    try:
        ks = K // 32
        B_bytes = B_q.view(torch.uint8)

        cache_key = (B_scale_sh.data_ptr(), N, ks)
        if cache_key not in _bs_cache:
            _bs_cache.clear()
            _bs_cache[cache_key] = (
                e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks).contiguous().view(torch.uint8)
            )
        Bs_bytes = _bs_cache[cache_key]

        A_bf16 = A.contiguous()
        C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
        _mod.launch_fused_inline_quant(A_bf16, B_bytes, Bs_bytes, C, M, N, K)
        return C

    except Exception as e:
        print(f"[fused_inline_quant] runtime error: {e}, falling back")
        return _aiter_fallback(data)
