#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""AMD CDNA4 Blog 8-Wave Ping-Pong FP4 GEMM — v1.

Applies every pattern from the ROCm CDNA4 GEMM blog
(https://rocm.blogs.amd.com/software-tools-optimization/cdna4-gemm-kernels/README.html)
to our verified FP4 MFMA kernel.

Patterns extracted from the blog (FP8 → adapted to FP4):
  1. GLOBAL_LOAD_LDS via llvm.amdgcn.raw.buffer.load.lds (128-bit per lane)
  2. LDS XOR swizzle: col ^= ((pair ^ ((pair>>1)^(pair>>2))&1) << 4)
  3. 8-wave ping-pong using __builtin_amdgcn_s_barrier() (NOT __syncthreads)
  4. __builtin_amdgcn_s_setprio(1) for MFMA waves, setprio(0) for load waves
  5. __builtin_amdgcn_sched_barrier(0) at load/compute boundaries
  6. Double-buffered LDS: tic/toc flip each K iteration
  7. 512 threads (8 waves), 256×256 output tile per block
     (blog's best config: 256x256_t512, 2288 TFLOPS/s for FP8)
     Adapted: 128×256 output tile (4 waves × 2 MFMA cols = 8 MFMA tiles)

FP4 adaptation from FP8:
  - Replace 16x16x128 FP8 MFMA with 32x32x64 FP4 scaled MFMA
  - K tile: 64 FP4 elements = 32 bytes (fits the 128-bit buffer load: 16B per half)
  - A in [M, K/2] uint8 row-major, B in [N, K/2] uint8 row-major
  - Scales: [M, K/32] and [N, K/32] linear E8M0 uint8

Fallback: aiter gemm_a4w4 for M < 128 (small-M shapes not worth large tile overhead).
"""

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


# ---------------------------------------------------------------------------
# HIP kernel: AMD Blog 8-wave ping-pong with GLOBAL_LOAD_LDS + XOR swizzle
# ---------------------------------------------------------------------------
HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

// ============================================================================
// MFMA register types — MUST be int vec8 (verified gfx950, Session 91)
// ============================================================================
typedef int   a_reg_t __attribute__((ext_vector_type(8)));
typedef int   b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

// ============================================================================
// Tile geometry
// ============================================================================
// 8 waves, 512 threads. Blog's 256x256_t512 config but adapted for FP4 tiles.
// Each wave handles a 32x64 C sub-tile (two 32x32 MFMA side by side).
// Wave layout: wave_m = waveid/4 (0-1 → M rows), wave_n = waveid%4 (0-3 → N cols)
// Full block tile: 2*32=64 rows in M, 4*64=256 cols in N → 64×256 per block.
//
// To get closer to the blog's 256×256 tile while keeping register pressure
// manageable for FP4, each wave now computes 4 MFMA tiles (2 in M, 2 in N):
//   wave_m → rows [wave_m*64 .. wave_m*64+63] (2 consecutive 32-row chunks)
//   wave_n → cols [wave_n*64 .. wave_n*64+63] (2 consecutive 32-col chunks)
// Full block tile: 2*64=128 rows, 4*64=256 cols = 128×256 per block.
#define BLOCK_M     128
#define BLOCK_N     256
#define TILE_K       64   // FP4 elements consumed per K step (1 scale group = 32 FP4)
#define TILE_K_BYTES 32   // packed bytes (2 FP4 per byte)
#define THREADS     512   // 8 waves × 64 threads
#define WAVESIZE     64

// LDS bytes for one buffer slot
// A: BLOCK_M rows × TILE_K_BYTES bytes/row = 128 × 32 = 4096 bytes
// B: BLOCK_N rows × TILE_K_BYTES bytes/row = 256 × 32 = 8192 bytes
// Two buffers (tic/toc) → 2*(4096+8192) = 24 KB (well within 160 KB)
#define LDS_A_BYTES  (BLOCK_M * TILE_K_BYTES)   // 4096
#define LDS_B_BYTES  (BLOCK_N * TILE_K_BYTES)   // 8192

// ============================================================================
// GLOBAL_LOAD_LDS via llvm.amdgcn.raw.buffer.load.lds (AMD Blog pattern)
// 128-bit per lane — CDNA4 can move 16 bytes/lane direct global->LDS.
// ============================================================================
using i32x4 = int32_t __attribute__((ext_vector_type(4)));
using as3_uint32_ptr = uint32_t __attribute__((address_space(3)))*;

extern "C" __device__ void llvm_amdgcn_raw_buffer_load_lds(
    i32x4 rsrc, as3_uint32_ptr lds_ptr, int size,
    int voffset, int soffset, int offset, int aux)
    __asm("llvm.amdgcn.raw.buffer.load.lds");

struct buffer_resource {
    uint64_t ptr;
    uint32_t range;
    uint32_t config;
};

__device__ __forceinline__ i32x4 make_srsrc(const void* ptr, uint32_t range_bytes) {
    buffer_resource rsrc = {
        reinterpret_cast<uint64_t>(ptr),
        range_bytes,
        // 0x00110000 = AMD Blog's exact config for raw byte buffer loads
        // NUM_FORMAT=1 (UNORM), DATA_FORMAT=1 (8-bit), stride=0
        0x00110000u
    };
    return *reinterpret_cast<const i32x4*>(&rsrc);
}

// Return the flat LDS byte address suitable for ds_read_b128 VGPR argument.
__device__ __forceinline__ uint32_t lds_byte_addr(const void* lds_ptr) {
    return static_cast<uint32_t>(reinterpret_cast<uintptr_t>(lds_ptr));
}

// ============================================================================
// LDS XOR swizzle — AMD Blog formula for 64-bank CDNA4 LDS
//
// For a tile with rows indexed [0..R) and 16-byte aligned column chunks:
//   pair      = (row >> 1) & 7
//   perm      = pair ^ (((pair >> 1) ^ (pair >> 2)) & 1)
//   mask      = perm << 4           (shifts 16-byte chunks)
//   swiz_col  = byte_col ^ mask     (XOR in units of bytes)
//
// Applied when writing to LDS; the same formula recovers original col on read.
// ============================================================================
__device__ __forceinline__ int swizzle_byte_col(int row, int byte_col) {
    const int pair = (row >> 1) & 7;
    const int perm = pair ^ (((pair >> 1) ^ (pair >> 2)) & 1);
    return byte_col ^ (perm << 4);
}

// ============================================================================
// Cooperative GLOBAL_LOAD_LDS tile loader
//
// Loads a [ROWS × TILE_K_BYTES] tile from global memory into LDS using the
// 128-bit buffer load instruction. Each of the 'num_threads' threads in the
// cooperative group loads 16 bytes. We distribute work in round-robin over
// the available threads, applying XOR swizzle to the LDS write offset.
//
// Parameters:
//   global_base : pointer to row 0 of the tile in global memory
//   lds_base    : pointer to slot start in LDS (uint8_t*, address_space(3))
//   global_stride : stride between rows in global memory (K_half bytes)
//   rows        : number of rows in this tile (BLOCK_M or BLOCK_N)
//   valid_rows  : actual valid global rows (for bounds check, 0=pad)
//   global_row0 : first global row index (for bounds check)
//   tid         : flat thread index [0..num_threads)
//   num_threads : total cooperating threads
// ============================================================================
__device__ __forceinline__ void load_tile_global_to_lds(
    const uint8_t* __restrict__ global_base,
    uint8_t* __restrict__ lds_base,
    int global_stride,
    int rows,
    int valid_rows,
    int global_row0,
    int tid,
    int num_threads
) {
    // Total 16-byte chunks in the tile
    const int total_chunks = rows * (TILE_K_BYTES / 16);  // 16 bytes per chunk
    // Build srsrc covering the full relevant global buffer range.
    // voffset = row * global_stride + byte_col (max = (rows-1)*global_stride + 16).
    // Use a generous range to avoid OOB clamp for any row in [0..rows).
    const uint32_t buf_range = static_cast<uint32_t>(rows) * global_stride + TILE_K_BYTES;
    const i32x4 srsrc = make_srsrc(global_base, buf_range);

    for (int chunk = tid; chunk < total_chunks; chunk += num_threads) {
        const int row       = chunk / (TILE_K_BYTES / 16);
        const int col_chunk = chunk % (TILE_K_BYTES / 16);   // 0 or 1 for 32-byte K
        const int byte_col  = col_chunk * 16;

        // XOR swizzle on the LDS write column
        const int swiz_col = swizzle_byte_col(row, byte_col);
        const int lds_off  = row * TILE_K_BYTES + swiz_col;

        as3_uint32_ptr lds_ptr = (as3_uint32_ptr)(
            reinterpret_cast<uintptr_t>(lds_base + lds_off));

        // voffset: byte offset of this chunk within global buffer
        const int voffset = row * global_stride + byte_col;

        if (global_row0 + row < valid_rows) {
            // 128-bit direct global→LDS transfer (CDNA4 GLOBAL_LOAD_LDS)
            llvm_amdgcn_raw_buffer_load_lds(srsrc, lds_ptr, 16, voffset, 0, 0, 0);
        } else {
            // Out-of-bounds: zero-fill LDS (scalar store, no async needed)
            uint32_t* z = reinterpret_cast<uint32_t*>(lds_base + lds_off);
            z[0] = z[1] = z[2] = z[3] = 0u;
        }
    }
}

// ============================================================================
// 8-wave ping-pong FP4 MFMA kernel — AMD CDNA4 Blog pattern
// ============================================================================
__global__ __launch_bounds__(THREADS, 1)
void mxfp4_blog_pingpong(
    const uint8_t* __restrict__ A,    // [M, K/2] packed FP4
    const uint8_t* __restrict__ B,    // [N, K/2] packed FP4
    const uint8_t* __restrict__ As,   // [M, K/32] E8M0 linear (NOT shuffled)
    const uint8_t* __restrict__ Bs,   // [N, K/32] E8M0 linear (NOT shuffled)
    __hip_bfloat16* __restrict__ C,   // [M, N] BF16 output
    int M, int N, int K
) {
    // ------------------------------------------------------------------
    // Thread/wave identity
    // ------------------------------------------------------------------
    const int tid     = threadIdx.x;
    const int waveid  = tid / WAVESIZE;   // 0..7
    const int lane    = tid % WAVESIZE;   // 0..63
    const int half    = lane >> 5;        // 0=lanes 0-31, 1=lanes 32-63

    // Blog's wave decomposition:
    //   wave_m = waveid / 4  → selects M-half of block (0=rows 0-63, 1=rows 64-127)
    //   wave_n = waveid % 4  → selects N-quarter (0-3 → cols 0-63,64-127,128-191,192-255)
    const int wave_m = waveid / 4;   // 0 or 1
    const int wave_n = waveid % 4;   // 0..3

    // Block origin
    const int bm = blockIdx.x * BLOCK_M;
    const int bn = blockIdx.y * BLOCK_N;

    // K dimensions
    const int K_half   = K / 2;
    const int K_scale  = K / 32;
    const int num_k    = K / TILE_K;   // K tiles in the loop

    // ------------------------------------------------------------------
    // Double-buffered LDS (tic/toc pattern from blog)
    // ------------------------------------------------------------------
    __shared__ uint8_t smem_A[2][LDS_A_BYTES];
    __shared__ uint8_t smem_B[2][LDS_B_BYTES];

    // ------------------------------------------------------------------
    // Per-wave output tile coordinates
    //   Each wave computes a 64×64 C region using 4 MFMA tiles (2×2):
    //     c00 = MFMA(A[m0..m0+31], B[n0..n0+31])
    //     c01 = MFMA(A[m0..m0+31], B[n1..n1+31])
    //     c10 = MFMA(A[m1..m1+31], B[n0..n0+31])
    //     c11 = MFMA(A[m1..m1+31], B[n1..n1+31])
    // ------------------------------------------------------------------
    const int tile_m0 = bm + wave_m * 64;           // first  M row for this wave
    const int tile_m1 = bm + wave_m * 64 + 32;      // second M row for this wave
    const int tile_n0 = bn + wave_n * 64;            // first  N col for this wave
    const int tile_n1 = bn + wave_n * 64 + 32;      // second N col for this wave

    // ------------------------------------------------------------------
    // Accumulators: 4 MFMA tiles per wave
    // ------------------------------------------------------------------
    c_reg_t c00 = {}, c01 = {}, c10 = {}, c11 = {};

    // ------------------------------------------------------------------
    // Blog's ping-pong identity:
    //   wave_m == 0 (waves 0-3): "group A"
    //   wave_m == 1 (waves 4-7): "group B"
    // ------------------------------------------------------------------

    // ------------------------------------------------------------------
    // PROLOGUE: load first K tile (tic=0) using all 512 threads
    // Blog: issue all 8 async buffer loads, then wait vmcnt down to 0.
    // ------------------------------------------------------------------
    {
        // All threads cooperate on the prologue load
        load_tile_global_to_lds(
            A + bm * K_half,                  // A global base for this block
            smem_A[0],
            K_half,
            BLOCK_M,
            M,
            bm,
            tid,
            THREADS
        );
        load_tile_global_to_lds(
            B + bn * K_half,                  // B global base for this block
            smem_B[0],
            K_half,
            BLOCK_N,
            N,
            bn,
            tid,
            THREADS
        );
        // Wait for all VMEM loads to LDS to complete
        asm volatile("s_waitcnt vmcnt(0)");
        // Synchronize all waves so LDS is fully written before compute
        __builtin_amdgcn_s_barrier();
    }

    // ------------------------------------------------------------------
    // HOT LOOP — blog pattern:
    //   if (wave_m == 1) stall with s_barrier  [blog: "barrier 0"]
    //   (load group loads next tile)
    //   s_barrier                               [blog: "barrier 1"]
    //   (compute group does MFMA)
    // ------------------------------------------------------------------
    for (int kt = 0; kt < num_k; kt++) {
        const int tic = kt & 1;
        const int toc = 1 - tic;
        const bool has_next = (kt + 1 < num_k);

        // ------------------------------------------------------------
        // Blog barrier 0: wave_m==1 stalls here; wave_m==0 runs ahead
        // to issue async loads for the next tile into toc buffer.
        // ------------------------------------------------------------
        if (wave_m == 1) {
            __builtin_amdgcn_s_barrier();  // barrier 0: waves 4-7 stall
        }

        // ------------------------------------------------------------
        // LOAD GROUP (wave_m == 0, waves 0-3): issue async loads for next tile
        // ------------------------------------------------------------
        if (has_next && wave_m == 0) {
            __builtin_amdgcn_sched_barrier(0);

            const int next_k_off = (kt + 1) * TILE_K_BYTES;  // byte offset in row

            // Each of the 4 load-group waves handles a strip of A and B.
            // Waves 0-3 collectively have 4×64=256 threads.
            // We load BLOCK_M*TILE_K_BYTES = 4096 bytes for A → 16 bytes/thread
            // and BLOCK_N*TILE_K_BYTES = 8192 bytes for B → 32 bytes/thread
            const int load_wave_idx = wave_n;  // 0..3 within the load group
            const int load_tid = load_wave_idx * WAVESIZE + lane;  // 0..255

            // A tile: 4096 bytes, 256 threads, 16 bytes each = 1 chunk/thread
            {
                const int a_total_chunks = BLOCK_M * (TILE_K_BYTES / 16);  // 256 chunks
                for (int chunk = load_tid; chunk < a_total_chunks; chunk += 256) {
                    const int row = chunk / (TILE_K_BYTES / 16);
                    const int col_chunk = chunk % (TILE_K_BYTES / 16);
                    const int byte_col = col_chunk * 16;
                    const int swiz_col = swizzle_byte_col(row, byte_col);
                    const int lds_off = row * TILE_K_BYTES + swiz_col;

                    as3_uint32_ptr lds_ptr = (as3_uint32_ptr)(
                        reinterpret_cast<uintptr_t>(smem_A[toc] + lds_off));

                    const int global_row = bm + row;
                    if (global_row < M) {
                        const i32x4 srsrc = make_srsrc(
                            A + global_row * K_half + next_k_off, TILE_K_BYTES);
                        llvm_amdgcn_raw_buffer_load_lds(srsrc, lds_ptr, 16, byte_col, 0, 0, 0);
                    } else {
                        uint32_t* z = reinterpret_cast<uint32_t*>(smem_A[toc] + lds_off);
                        z[0] = z[1] = z[2] = z[3] = 0u;
                    }
                }
            }

            // B tile: 8192 bytes, 256 threads, 32 bytes each = 2 chunks/thread
            {
                const int b_total_chunks = BLOCK_N * (TILE_K_BYTES / 16);  // 512 chunks
                for (int chunk = load_tid; chunk < b_total_chunks; chunk += 256) {
                    const int row = chunk / (TILE_K_BYTES / 16);
                    const int col_chunk = chunk % (TILE_K_BYTES / 16);
                    const int byte_col = col_chunk * 16;
                    const int swiz_col = swizzle_byte_col(row, byte_col);
                    const int lds_off = row * TILE_K_BYTES + swiz_col;

                    as3_uint32_ptr lds_ptr = (as3_uint32_ptr)(
                        reinterpret_cast<uintptr_t>(smem_B[toc] + lds_off));

                    const int global_row = bn + row;
                    if (global_row < N) {
                        const i32x4 srsrc = make_srsrc(
                            B + global_row * K_half + next_k_off, TILE_K_BYTES);
                        llvm_amdgcn_raw_buffer_load_lds(srsrc, lds_ptr, 16, byte_col, 0, 0, 0);
                    } else {
                        uint32_t* z = reinterpret_cast<uint32_t*>(smem_B[toc] + lds_off);
                        z[0] = z[1] = z[2] = z[3] = 0u;
                    }
                }
            }
            __builtin_amdgcn_sched_barrier(0);
        }

        // ------------------------------------------------------------
        // Blog barrier 1: load group (wave_m==0) reaches here after issuing
        // loads; this releases the stalled compute group (wave_m==1).
        // Both groups then proceed to MFMA.
        // ------------------------------------------------------------
        __builtin_amdgcn_s_barrier();  // barrier 1

        // ------------------------------------------------------------
        // COMPUTE: all 8 waves execute MFMA on tic buffer
        // Blog: s_setprio(1) during MFMA, setprio(0) after
        // ------------------------------------------------------------
        __builtin_amdgcn_s_setprio(1);
        __builtin_amdgcn_sched_barrier(0);

        // Scale group index (2 scale groups per 64-element K tile)
        const int sg = kt * 2 + half;

        // ---- Load A fragments from LDS (de-swizzle on read) ----
        // Thread reads row (wave_m*64 + {0..31} + half*32) depending on m-sub
        // For m0 sub-tile: a_local_row = wave_m*64 + (lane&31)
        // For m1 sub-tile: a_local_row = wave_m*64 + 32 + (lane&31)
        a_reg_t a0_reg = {}, a1_reg = {};
        {
            // m0 row (used for c00 and c01)
            const int a_local_row = wave_m * 64 + (lane & 31);
            const int byte_col    = half * 16;
            const int swiz_col    = swizzle_byte_col(a_local_row, byte_col);
            const int lds_off     = a_local_row * TILE_K_BYTES + swiz_col;
            // ds_read_b128 takes flat LDS byte address in a VGPR (uint32)
            const uint32_t addr   = lds_byte_addr(smem_A[tic] + lds_off);
            uint8_t* dst = reinterpret_cast<uint8_t*>(&a0_reg);
            using u32x4_t = uint32_t __attribute__((ext_vector_type(4)));
            asm volatile("ds_read_b128 %0, %1\n"
                : "=v"(*reinterpret_cast<u32x4_t*>(dst))
                : "v"(addr) : "memory");
        }
        {
            // m1 row (used for c10 and c11)
            const int a_local_row = wave_m * 64 + 32 + (lane & 31);
            const int byte_col    = half * 16;
            const int swiz_col    = swizzle_byte_col(a_local_row, byte_col);
            const int lds_off     = a_local_row * TILE_K_BYTES + swiz_col;
            const uint32_t addr   = lds_byte_addr(smem_A[tic] + lds_off);
            uint8_t* dst = reinterpret_cast<uint8_t*>(&a1_reg);
            using u32x4_t = uint32_t __attribute__((ext_vector_type(4)));
            asm volatile("ds_read_b128 %0, %1\n"
                : "=v"(*reinterpret_cast<u32x4_t*>(dst))
                : "v"(addr) : "memory");
        }

        // ---- Load B fragments from LDS ----
        b_reg_t b0_reg = {}, b1_reg = {};
        {
            // n0 col (first 32 cols of this wave's N strip)
            const int b_local_row = wave_n * 64 + (lane & 31);
            const int byte_col    = half * 16;
            const int swiz_col    = swizzle_byte_col(b_local_row, byte_col);
            const int lds_off     = b_local_row * TILE_K_BYTES + swiz_col;
            const uint32_t addr   = lds_byte_addr(smem_B[tic] + lds_off);
            uint8_t* dst = reinterpret_cast<uint8_t*>(&b0_reg);
            using u32x4_t = uint32_t __attribute__((ext_vector_type(4)));
            asm volatile("ds_read_b128 %0, %1\n"
                : "=v"(*reinterpret_cast<u32x4_t*>(dst))
                : "v"(addr) : "memory");
        }
        {
            // n1 col (second 32 cols of this wave's N strip)
            const int b_local_row = wave_n * 64 + 32 + (lane & 31);
            const int byte_col    = half * 16;
            const int swiz_col    = swizzle_byte_col(b_local_row, byte_col);
            const int lds_off     = b_local_row * TILE_K_BYTES + swiz_col;
            const uint32_t addr   = lds_byte_addr(smem_B[tic] + lds_off);
            uint8_t* dst = reinterpret_cast<uint8_t*>(&b1_reg);
            using u32x4_t = uint32_t __attribute__((ext_vector_type(4)));
            asm volatile("ds_read_b128 %0, %1\n"
                : "=v"(*reinterpret_cast<u32x4_t*>(dst))
                : "v"(addr) : "memory");
        }

        // Wait for all LDS reads to complete before MFMA
        asm volatile("s_waitcnt lgkmcnt(0)");

        // ---- Scales ----
        const int a0_gr = tile_m0 + (lane & 31);
        const int a1_gr = tile_m1 + (lane & 31);
        const int b0_gr = tile_n0 + (lane & 31);
        const int b1_gr = tile_n1 + (lane & 31);

        const int sa0 = (a0_gr < M && sg < K_scale) ? (int)As[a0_gr * K_scale + sg] : 127;
        const int sa1 = (a1_gr < M && sg < K_scale) ? (int)As[a1_gr * K_scale + sg] : 127;
        const int sb0 = (b0_gr < N && sg < K_scale) ? (int)Bs[b0_gr * K_scale + sg] : 127;
        const int sb1 = (b1_gr < N && sg < K_scale) ? (int)Bs[b1_gr * K_scale + sg] : 127;

        // ---- 4 MFMA tiles (A reused across N, B reused across M) ----
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

        // Wait for the async VMEM loads (issued by wave_m==0) to finish
        // before the next iteration's reads from toc.
        if (has_next) {
            asm volatile("s_waitcnt vmcnt(0)");
            __builtin_amdgcn_s_barrier();
        }
    }

    // ------------------------------------------------------------------
    // EPILOGUE: write outputs
    // Verified register layout (Session 91 SKILL.md):
    //   c_reg[r] -> C[tile_m + (r&3) + (r>>2)*8 + half*4][tile_n + (lane&31)]
    // ------------------------------------------------------------------
    #define WRITE_TILE(c_reg, tm, tn) \
    { \
        const int oc = (tn) + (lane & 31); \
        if (oc < N) { \
            _Pragma("unroll") \
            for (int r = 0; r < 16; r++) { \
                const int or_ = (tm) + (r & 3) + (r >> 2) * 8 + half * 4; \
                if (or_ < M) \
                    C[or_ * N + oc] = (__hip_bfloat16)((c_reg)[r]); \
            } \
        } \
    }

    WRITE_TILE(c00, tile_m0, tile_n0)
    WRITE_TILE(c01, tile_m0, tile_n1)
    WRITE_TILE(c10, tile_m1, tile_n0)
    WRITE_TILE(c11, tile_m1, tile_n1)
    #undef WRITE_TILE
}

// ============================================================================
// C++ launcher
// ============================================================================
void launch_blog_pingpong(
    torch::Tensor A,   // [M, K/2] uint8
    torch::Tensor B,   // [N, K/2] uint8
    torch::Tensor As,  // [M, K/32] uint8
    torch::Tensor Bs,  // [N, K/32] uint8
    torch::Tensor C,   // [M, N] bfloat16
    int M, int N, int K
) {
    dim3 grid((M + BLOCK_M - 1) / BLOCK_M,
              (N + BLOCK_N - 1) / BLOCK_N);
    dim3 block(THREADS);

    mxfp4_blog_pingpong<<<grid, block>>>(
        A.data_ptr<uint8_t>(),
        B.data_ptr<uint8_t>(),
        As.data_ptr<uint8_t>(),
        Bs.data_ptr<uint8_t>(),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K
    );
}
"""

CPP_SOURCE = """
void launch_blog_pingpong(
    torch::Tensor A,
    torch::Tensor B,
    torch::Tensor As,
    torch::Tensor Bs,
    torch::Tensor C,
    int M, int N, int K
);
"""

try:
    _mod = load_inline(
        name="mxfp4_blog_pingpong_v1",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_blog_pingpong"],
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
    _BLOG_OK = True
    print("[blog_pingpong] compile SUCCESS")
except Exception as e:
    print(f"[blog_pingpong] compile FAILED: {e}")
    _BLOG_OK = False


# ---------------------------------------------------------------------------
# Scale utilities (verified Session 91)
# ---------------------------------------------------------------------------
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
    """Use aiter gemm_a4w4 as fallback for small M or compile failure."""
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
    """MXFP4 GEMM using AMD Blog 8-wave ping-pong with GLOBAL_LOAD_LDS + XOR swizzle.

    Applies the exact CDNA4 blog patterns (buffer load, XOR swizzle, s_barrier
    ping-pong, s_setprio, sched_barrier) to our verified FP4 MFMA kernel.

    Falls back to aiter gemm_a4w4 for M < 128.
    """
    from aiter.ops.triton.quant import dynamic_mxfp4_quant

    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    if not _BLOG_OK or M < 128:
        return _aiter_fallback(data)

    ks = K // 32

    # Quantize A (aiter fast Triton kernel)
    A_q, A_sc = dynamic_mxfp4_quant(A.contiguous())
    A_bytes = A_q.view(torch.uint8)
    As_bytes = A_sc[:M, :ks].contiguous().view(torch.uint8)

    # B uses pre-quantized B_q (row-major, NOT shuffled)
    B_bytes = B_q.view(torch.uint8)

    # Unshuffle B scale once per unique allocation
    cache_key = (B_scale_sh.data_ptr(), N, ks)
    if cache_key not in _bs_cache:
        _bs_cache.clear()
        _bs_cache[cache_key] = (
            e8m0_unshuffle(B_scale_sh.view(torch.uint8), N, ks).contiguous().view(torch.uint8)
        )
    Bs_bytes = _bs_cache[cache_key]

    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    _mod.launch_blog_pingpong(A_bytes, B_bytes, As_bytes, Bs_bytes, C, M, N, K)
    return C
