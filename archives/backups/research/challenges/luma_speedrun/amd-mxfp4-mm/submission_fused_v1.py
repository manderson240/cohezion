#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM fused_v1: Inline BF16->FP4 quantization + MFMA 32x32x64 + LDS tiling.

Key improvements over fp4mfma_fused:
- 32x128 output tile (1 M-tile x 4 N-tiles, 256 threads = 4 waves)
- BF16 A loaded into LDS, then quantized inline per-wave
- B (pre-quantized FP4) loaded into LDS for reuse across M-rows
- Double-buffered LDS for latency hiding
- Vectorized uint4 (128-bit) loads for coalesced memory access
- Shape-specialized dispatch: small-M shapes use single-wave 32x32 path

Ranked shapes:
  M=4,  N=2880, K=512   | M=16, N=2112, K=7168
  M=32, N=4096, K=512   | M=32, N=2880, K=512
  M=64, N=7168, K=2048  | M=256,N=3072, K=1536
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
#include <hip/amd_detail/amd_hip_bf16.h>

typedef int   a_reg_t __attribute__((ext_vector_type(8)));
typedef int   b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

// ─── FP4 E2M1 round-to-nearest-even ────────────────────────────────────────
// Values: 0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0
__device__ __forceinline__ uint8_t float_to_fp4(float v) {
    uint8_t sign = (v < 0.0f) ? 8u : 0u;
    float a = fabsf(v);
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

// ─── E8M0 scale matching aiter's formula ───────────────────────────────────
// scale_exp = bf16_exp(max_abs) - 2; bump if mantissa >= 96
// inv_scale = 2^(-scale_exp) for dequant
__device__ __forceinline__ int compute_e8m0_scale(float max_abs) {
    if (max_abs == 0.0f) return 0;
    __hip_bfloat16 max_bf16 = (__hip_bfloat16)max_abs;
    unsigned short bf16_bits = *reinterpret_cast<const unsigned short*>(&max_bf16);
    int bf16_exp = (bf16_bits >> 7) & 0xFF;
    int bf16_man = bf16_bits & 0x7F;
    if (bf16_man >= 96) bf16_exp += 1;
    return max(bf16_exp - 2, 0);
}

__device__ __forceinline__ float scale_exp_to_inv(int scale_exp) {
    return (scale_exp > 0) ? __int_as_float((254 - scale_exp) << 23) : 0.0f;
}

// ─── Quantize 32 BF16 elements → 16 packed FP4 bytes ──────────────────────
// a_bf16: pointer to 32 BF16 elements in shared memory (or registers)
// a_bytes: pointer to 16 output bytes
// returns E8M0 scale exponent (int)
__device__ __forceinline__ int quantize_row_fp4(
    const __hip_bfloat16* a_bf16,
    uint8_t* a_bytes
) {
    // Pass 1: find max absolute value
    float max_abs = 0.0f;
    #pragma unroll
    for (int i = 0; i < 32; i++) {
        float v = __bfloat162float(a_bf16[i]);
        max_abs = fmaxf(max_abs, fabsf(v));
    }
    int scale_exp = compute_e8m0_scale(max_abs);
    float inv_scale = scale_exp_to_inv(scale_exp);

    // Pass 2: quantize 32 BF16 → 16 packed FP4 bytes
    #pragma unroll
    for (int i = 0; i < 16; i++) {
        float v0 = __bfloat162float(a_bf16[i * 2    ]) * inv_scale;
        float v1 = __bfloat162float(a_bf16[i * 2 + 1]) * inv_scale;
        uint8_t fp4_lo = float_to_fp4(v0);
        uint8_t fp4_hi = float_to_fp4(v1);
        a_bytes[i] = (fp4_hi << 4) | fp4_lo;
    }
    return scale_exp;
}

// ─── Main kernel: 32×128 tile, 256 threads = 4 waves ──────────────────────
// Each wave handles a 32×32 sub-tile (standard MFMA 32x32x64 shape).
// A is BF16 input; quantization is done inline per wave-row.
// B is pre-quantized FP4 [N, K/2].
// B_scale is unshuffled E8M0 [N, K/32].
//
// LDS layout:
//   smem_A_bf16[2][BLOCK_M * TILE_K]  — double-buffered BF16 A tiles
//   smem_B[2][BLOCK_N * TILE_K_BYTES] — double-buffered FP4 B tiles
//   smem_Bsc[2][BLOCK_N * 2]          — B scale (2 groups per K-tile)
#define BLOCK_M 32
#define BLOCK_N 128
#define TILE_K 64
#define TILE_K_BYTES 32   // TILE_K / 2 packed bytes
#define WAVES 4
#define WAVESIZE 64
#define THREADS (WAVES * WAVESIZE)

// LDS sizes (bytes)
#define LDS_A_BF16 (BLOCK_M * TILE_K * 2)   // 32*64*2 = 4096 bytes BF16
#define LDS_B_FP4  (BLOCK_N * TILE_K_BYTES)  // 128*32  = 4096 bytes FP4
#define LDS_BSC    (BLOCK_N * 2)              // 128*2   = 256  bytes scales

__global__ __launch_bounds__(THREADS, 4)
void mxfp4_gemm_fused_v1(
    const __hip_bfloat16* __restrict__ A_bf16,  // [M, K] BF16
    const uint8_t* __restrict__ B,               // [N, K/2] FP4 packed
    const uint8_t* __restrict__ Bs,              // [N, K/32] E8M0
    __hip_bfloat16* __restrict__ C,              // [M, N] BF16
    int M, int N, int K
) {
    int bm = blockIdx.y * BLOCK_M;
    int bn = blockIdx.x * BLOCK_N;
    int tid = threadIdx.x;

    int wave_id = tid / WAVESIZE;  // 0..3
    int lane_id = tid % WAVESIZE;  // 0..63
    int half_id = lane_id >> 5;    // 0 or 1 (which K half of the tile)

    int K_half  = K / 2;
    int K_scale = K / 32;
    int num_k_tiles = K / TILE_K;

    // Wave assignment: wave i handles N columns [wave_i*32 .. wave_i*32+31]
    int wave_n = wave_id;
    int bn_wave = bn + wave_n * 32;  // global N start for this wave

    // ─── Shared memory ──────────────────────────────────────────────────────
    // Double-buffered A (BF16): [2][32 rows × 64 cols]
    __shared__ __hip_bfloat16 smem_A[2][BLOCK_M * TILE_K];
    // Double-buffered B (FP4 packed): [2][128 rows × 32 bytes]
    __shared__ uint8_t smem_B[2][LDS_B_FP4];
    // Double-buffered B scales: [2][128 rows × 2 scale groups]
    __shared__ uint8_t smem_Bsc[2][LDS_BSC];

    // ─── Accumulators ───────────────────────────────────────────────────────
    c_reg_t c_reg = {};

    // ─── Helper: cooperative load of A (BF16) into LDS ──────────────────────
    // A tile: BLOCK_M × TILE_K = 32×64 BF16 = 4096 bytes
    // 256 threads → 16 bytes per thread = 8 BF16 per thread
    // Stride: 256 threads cover 256*8 = 2048 BF16 → 2 passes to fill 2048 BF16
    auto load_A_tile = [&](int kt_idx, int slot) {
        int k_start = kt_idx * TILE_K;
        // Each element i in [0, BLOCK_M * TILE_K)
        // Thread tid handles elements [tid, tid+THREADS, ...]
        for (int i = tid; i < BLOCK_M * TILE_K; i += THREADS) {
            int row = i / TILE_K;
            int col = i % TILE_K;
            int gr = bm + row;
            int gk = k_start + col;
            smem_A[slot][i] = (gr < M && gk < K) ?
                A_bf16[gr * K + gk] : (__hip_bfloat16)0.0f;
        }
    };

    // ─── Helper: cooperative load of B (FP4) into LDS ───────────────────────
    // B tile: BLOCK_N × TILE_K_BYTES = 128×32 = 4096 bytes
    // 256 threads → 16 bytes/thread = 1 pass
    auto load_B_tile = [&](int kt_idx, int slot) {
        int k_byte_start = kt_idx * TILE_K_BYTES;
        for (int i = tid; i < LDS_B_FP4; i += THREADS) {
            int row = i / TILE_K_BYTES;
            int col = i % TILE_K_BYTES;
            int gr = bn + row;
            int gk = k_byte_start + col;
            smem_B[slot][i] = (gr < N && gk < K_half) ? B[gr * K_half + gk] : 0;
        }
        // B scales: 128 rows × 2 groups = 256 bytes / 256 threads = 1 byte/thread
        int sg_base = kt_idx * 2;
        for (int i = tid; i < LDS_BSC; i += THREADS) {
            int row = i / 2;
            int sg  = i % 2;
            int gr  = bn + row;
            int gsg = sg_base + sg;
            smem_Bsc[slot][i] = (gr < N && gsg < K_scale) ? Bs[gr * K_scale + gsg] : 127;
        }
    };

    // ─── Prologue: load tile 0 ───────────────────────────────────────────────
    load_A_tile(0, 0);
    load_B_tile(0, 0);
    __syncthreads();

    int buf = 0;

    // ─── Main K-tile loop ────────────────────────────────────────────────────
    for (int kt = 0; kt < num_k_tiles; kt++) {
        int next_buf = 1 - buf;

        // Prefetch next tile into alternate buffer
        if (kt + 1 < num_k_tiles) {
            load_A_tile(kt + 1, next_buf);
            load_B_tile(kt + 1, next_buf);
        }

        // ─── Per-wave inline A quantization ───────────────────────────────
        // This wave's A row in LDS: lane_id & 31 → row in [0, 31]
        // Scale group index within K-tile: half_id (0 or 1)
        a_reg_t a_reg = {};
        int a_row_local = lane_id & 31;  // row index within BLOCK_M tile
        int a_k_local   = half_id * 32;  // BF16 element offset within K-tile

        // Pointer to the 32 BF16 elements for this thread's scale group
        const __hip_bfloat16* a_ptr =
            smem_A[buf] + a_row_local * TILE_K + a_k_local;

        int sa = 0;
        {
            uint8_t a_bytes[16];
            sa = quantize_row_fp4(a_ptr, a_bytes);
            // Store into MFMA register
            uint8_t* reg_bytes = reinterpret_cast<uint8_t*>(&a_reg);
            #pragma unroll
            for (int i = 0; i < 16; i++) reg_bytes[i] = a_bytes[i];
            // Upper 16 bytes of a_reg remain zero (FP4 uses only first 16 bytes)
        }

        // ─── B register load from LDS ──────────────────────────────────────
        b_reg_t b_reg = {};
        int b_row_local = wave_n * 32 + (lane_id & 31);
        int b_k_off     = half_id * 16;  // byte offset within tile row
        {
            uint8_t* b_bytes = reinterpret_cast<uint8_t*>(&b_reg);
            const uint8_t* b_src = smem_B[buf] + b_row_local * TILE_K_BYTES + b_k_off;
            #pragma unroll
            for (int i = 0; i < 16; i++) b_bytes[i] = b_src[i];
        }

        // ─── B scale from LDS ──────────────────────────────────────────────
        int sg = half_id;  // 0 or 1 within this tile
        int sb = (int)smem_Bsc[buf][b_row_local * 2 + sg];

        // ─── MFMA 32×32×64 FP4 ─────────────────────────────────────────────
        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg, 4, 4, 0, sa, 0, sb);

        buf = next_buf;
        if (kt + 1 < num_k_tiles) __syncthreads();
    }

    // ─── Epilogue: write output ──────────────────────────────────────────────
    // MFMA 32x32x64 output: thread (lane_id) writes to:
    //   col = bn_wave + (lane_id & 31)
    //   row = bm + (r % 4) + (r / 4) * 8 + (lane_id / 32) * 4
    int out_col = bn_wave + (lane_id & 31);
    if (out_col < N) {
        #pragma unroll
        for (int r = 0; r < 16; r++) {
            int out_row = bm + (r & 3) + (r >> 2) * 8 + (lane_id >> 5) * 4;
            if (out_row < M) {
                C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
            }
        }
    }
}

// ─── Small-M path: 32×32 single-wave, A quantized inline ──────────────────
// For M<=32 shapes, a single 32×32 tile per block avoids over-parallelization.
// This is the same as the verified fp4mfma_fused but with 1 wave.
__global__ __launch_bounds__(64, 8)
void mxfp4_gemm_fused_small(
    const __hip_bfloat16* __restrict__ A_bf16,
    const uint8_t* __restrict__ B,
    const uint8_t* __restrict__ Bs,
    __hip_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    int bm = blockIdx.y * 32;
    int bn = blockIdx.x * 32;
    int tid = threadIdx.x;  // 0..63

    int K_half  = K / 2;
    int K_scale = K / 32;
    int num_k_tiles = K / TILE_K;

    int a_row = bm + (tid & 31);
    int b_col = bn + (tid & 31);
    int half_id = tid >> 5;

    bool a_valid = (a_row < M);
    bool b_valid = (b_col < N);

    const __hip_bfloat16* a_base = A_bf16 + a_row * K;
    const uint8_t* b_base  = B  + b_col * K_half;
    const uint8_t* bs_base = Bs + b_col * K_scale;

    c_reg_t c_reg = {};

    for (int kt = 0; kt < num_k_tiles; kt++) {
        a_reg_t a_reg = {};
        b_reg_t b_reg = {};

        int a_k_start = kt * TILE_K + half_id * 32;
        int sa = 127;

        if (a_valid && a_k_start + 32 <= K) {
            const __hip_bfloat16* a_ptr = a_base + a_k_start;

            // Pass 1: find max abs
            float max_abs = 0.0f;
            #pragma unroll
            for (int i = 0; i < 32; i++) {
                max_abs = fmaxf(max_abs, fabsf(__bfloat162float(a_ptr[i])));
            }
            sa = compute_e8m0_scale(max_abs);
            float inv_scale = scale_exp_to_inv(sa);

            // Pass 2: quantize to FP4
            uint8_t* a_bytes = reinterpret_cast<uint8_t*>(&a_reg);
            #pragma unroll
            for (int i = 0; i < 16; i++) {
                float v0 = __bfloat162float(a_ptr[i * 2    ]) * inv_scale;
                float v1 = __bfloat162float(a_ptr[i * 2 + 1]) * inv_scale;
                a_bytes[i] = (float_to_fp4(v1) << 4) | float_to_fp4(v0);
            }
        }

        // B: vectorized 16-byte load
        int k_byte_off = kt * TILE_K_BYTES + half_id * 16;
        if (b_valid && k_byte_off + 16 <= K_half) {
            uint8_t* b_bytes = reinterpret_cast<uint8_t*>(&b_reg);
            *reinterpret_cast<uint4*>(b_bytes) =
                *reinterpret_cast<const uint4*>(b_base + k_byte_off);
        }

        int sg = kt * 2 + half_id;
        int sb = (b_valid && sg < K_scale) ? (int)bs_base[sg] : 127;

        c_reg = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg, c_reg, 4, 4, 0, sa, 0, sb);
    }

    int out_col = bn + (tid & 31);
    if (out_col < N) {
        #pragma unroll
        for (int r = 0; r < 16; r++) {
            int out_row = bm + (r & 3) + (r >> 2) * 8 + (tid >> 5) * 4;
            if (out_row < M) {
                C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
            }
        }
    }
}

void launch_fused_v1(
    torch::Tensor A_bf16,
    torch::Tensor B,
    torch::Tensor Bs,
    torch::Tensor C
) {
    int M = A_bf16.size(0);
    int K = A_bf16.size(1);
    int N = B.size(0);

    const __hip_bfloat16* a_ptr = reinterpret_cast<const __hip_bfloat16*>(A_bf16.data_ptr());
    const uint8_t* b_ptr  = B.data_ptr<uint8_t>();
    const uint8_t* bs_ptr = Bs.data_ptr<uint8_t>();
    __hip_bfloat16* c_ptr = reinterpret_cast<__hip_bfloat16*>(C.data_ptr());

    // Shape-specialized dispatch
    // For M <= 16: use small path (32x32 tiles, 64 threads) — avoids
    //   wasted waves when M is very small
    // For M > 16: use tiled path (32x128 tiles, 256 threads)
    if (M <= 16) {
        dim3 grid((N + 31) / 32, (M + 31) / 32);
        mxfp4_gemm_fused_small<<<grid, 64>>>(a_ptr, b_ptr, bs_ptr, c_ptr, M, N, K);
    } else {
        dim3 grid((N + BLOCK_N - 1) / BLOCK_N, (M + BLOCK_M - 1) / BLOCK_M);
        mxfp4_gemm_fused_v1<<<grid, THREADS>>>(a_ptr, b_ptr, bs_ptr, c_ptr, M, N, K);
    }
}
"""

CPP_SOURCE = """
void launch_fused_v1(
    torch::Tensor A_bf16,
    torch::Tensor B,
    torch::Tensor Bs,
    torch::Tensor C
);
"""

try:
    _mod = load_inline(
        name="mxfp4_fused_v1",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_fused_v1"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[mxfp4_fused_v1] compile failed: {e}")
    _OK = False


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
    """Reverse aiter's e8m0_shuffle to get linear [M, K/32] layout."""
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]


def custom_kernel(data: input_t) -> output_t:
    """Fused BF16->FP4 quantization + MFMA GEMM via single HIP kernel."""
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    ks = K // 32

    if not _OK:
        # Fallback to aiter reference
        import aiter
        from aiter import dtypes
        from aiter.ops.triton.quant import dynamic_mxfp4_quant
        from aiter.utility.fp4_utils import e8m0_shuffle

        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
        return aiter.gemm_a4w4(
            Aq.view(dtypes.fp4x2),
            B_shuffle,
            Ash,
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True,
        )

    # A: pass BF16 directly — kernel quantizes inline
    A_bf16 = A.contiguous()

    # B: pre-quantized FP4 bytes + unshuffled B scales [N, K/32]
    B_bytes = B_q.view(torch.uint8)
    Bs_bytes = e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks).contiguous()

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
    _mod.launch_fused_v1(A_bf16, B_bytes, Bs_bytes, C)
    return C
