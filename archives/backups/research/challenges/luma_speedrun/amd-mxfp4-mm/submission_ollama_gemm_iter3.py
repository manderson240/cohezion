Thinking...
We are given a single-tile MFMA kernel that computes a 32x32 tile per block[5D[K
block (one wavefront) using the FP4 MFMA instruction.
 The goal is to improve performance to reach a geomean of <13µs (current be[2D[K
best is 13.425µs, aiter baseline is 11.5µs).
 We are to propose one specific optimization and output the entire modified[8D[K
modified submission.

 After analyzing the current kernel, note that:
   - It uses a single 32x32 output tile per block.
   - The K loop is unrolled and uses MFMA with scaling.
   - The global loads are 128-bit (16 bytes) per thread, which is good for [K
coalescing.
   - However, the kernel is memory-bound and the arithmetic intensity is lo[2D[K
low.

 One of the suggested optimizations is to use multi-tile output (e.g., 32x1[4D[K
32x128) to reuse A data.
 This would increase the work per block and reduce the number of blocks, wh[2D[K
which can improve occupancy and reduce global memory traffic for A.

 Let's design a kernel that computes a 32x128 tile per block. This means ea[2D[K
each block will compute 4 consecutive 32x32 tiles in the N dimension.
 We'll still have 64 threads (one wavefront) per block, but each thread wil[3D[K
will now compute 4 columns of the 32x32 tile (so 4x the output elements).

 Steps:
  1. Each thread will load its A data once and reuse it for 4 B tiles (each[5D[K
(each B tile is 32 columns wide).
  2. We'll loop over K tiles (64 elements per MFMA) as before, but for each[4D[K
each K tile we load 4 B tiles (each 32 columns wide) and perform 4 MFMA ins[3D[K
instructions.
  3. We'll accumulate 4 sets of C registers (each set is 16 floats for the [K
32x32 tile, but now each thread has 4 sets).

 However, note that the MFMA instruction we are using (32x32x64) produces a[1D[K
a 32x32 tile per instruction. So for 32x128, we need 4 MFMA instructions pe[2D[K
per K tile.

 We can restructure the kernel as follows:
   - Each thread is responsible for 4 output columns (each column has 32 ro[2D[K
rows, but the thread only holds 16 rows of each column due to the MFMA layo[4D[K
layout).
   - The thread loads its A data (same as before, 16 bytes per K tile) and [K
then loads 4 B tiles (each 16 bytes per thread per B tile) and does 4 MFMA [K
calls.

 We must adjust the memory loads for B to load 4 consecutive 32-column tile[4D[K
tiles. This means the B matrix is now accessed with a stride of N (which is[2D[K
is the same as before, but now we load 4 consecutive columns per thread per[3D[K
per K tile).

 However, note that the B matrix is packed as FP4 and has shape [N, K/2]. W[1D[K
We are loading 4 consecutive columns (each column is K/2 bytes) but with a [K
step of 32 columns per tile.

 Let's define:
   - bn = blockIdx.y * 128   (since we are doing 128 columns per block)
   - Then we have 4 tiles: tile0: columns [bn, bn+31], tile1: [bn+32, bn+63[5D[K
bn+63], tile2: [bn+64, bn+95], tile3: [bn+96, bn+127].

 Each thread will load B data for 4 columns (one from each tile). The threa[5D[K
thread's column index within the tile is (tid & 31). So the global column i[1D[K
index for tile j is:
   b_col = bn + j*32 + (tid & 31)

 We must also adjust the scale loading for B: we now have 4 scale values pe[2D[K
per K scale group (one for each tile).

 We'll accumulate 4 sets of C registers (each set is 16 floats). We can rep[3D[K
represent them as 4 vectors of 16 floats, or a 2D array.

 We'll write out 4 columns per thread, each column with 16 rows (as before,[7D[K
before, but now 4 columns).

 Implementation plan:
   - Use a_reg_t and b_reg_t as before for A and B data.
   - Use c_reg_t for the accumulator, but now we have 4 of them (one per ti[2D[K
tile).
   - In the K loop, load A once, then for each of the 4 tiles:
        Load B for that tile, load the scale for that tile, and perform MFM[3D[K
MFMA into the corresponding accumulator.

   - After the K loop, write out the 4 columns (each with 16 rows) to the a[1D[K
appropriate positions.

 We must be careful with the memory accesses for B and scales to ensure coa[3D[K
coalescing.

 Let's code accordingly.

 Note: We are using the same MFMA intrinsic, but now we call it 4 times per[3D[K
per K iteration (once per tile).

 We also need to adjust the grid: the number of blocks in the y dimension b[1D[K
becomes (N+127)/128.

 We'll keep the same number of threads per block (64).

 Let's write the kernel accordingly.
...done thinking.

#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MFMA GEMM v2 — Multi-tile 32x128x64 FP4 MFMA with A data reuse.

Optimization: Process 4 consecutive 32x32 tiles in N dimension (32x128 tota[4D[K
total)
to reuse A data across multiple B columns. Reduces A memory traffic by 4x
within block, improves arithmetic intensity.

Architecture:
  - 32×128 output tile per block (4× wider)
  - 64 threads (1 wavefront), each handles 4 output columns
  - K loop loads A once, processes 4 B tiles sequentially
  - MFMA 32x32x64 called 4× per K iteration
  - Column-major writeback with proper coalescing
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t


CPP_WRAPPER = """
void mxfp4_mfma_gemm_multi(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C,
    int M, int N, int K
);
"""

HIP_SRC = r"""
#include <hip/hip_runtime.h>
#include <hip/amd_detail/amd_hip_bf16.h>

// MFMA register types
typedef int a_reg_t __attribute__((ext_vector_type(8)));
typedef int b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

__global__ void mxfp4_mfma_kernel_multi(
    const uint8_t* __restrict__ A,    // [M, K/2] packed FP4
    const uint8_t* __restrict__ B,    // [N, K/2] packed FP4
    const uint8_t* __restrict__ As,   // [M, K/32] E8M0 scales
    const uint8_t* __restrict__ Bs,   // [N, K/32] E8M0 scales
    __hip_bfloat16* __restrict__ C,   // [M, N] output BF16
    int M, int N, int K
) {
    int bm = blockIdx.x * 32;          // block row start (always 32)
    int bn = blockIdx.y * 128;         // block col start (4 tiles wide)
    int tid = threadIdx.x;             // 0-63

    int K_half = K / 2;                // bytes per row
    int k_tiles = K / 64;              // MFMA tiles along K
    int k_scale_groups = K / 32;       // scale groups per row

    int a_row = bm + (tid & 31);       // which row of A this thread loads
    bool a_valid = (a_row < M);

    // Accumulators for 4 tiles (tile0, tile1, tile2, tile3)
    c_reg_t c_reg0 = {};
    c_reg_t c_reg1 = {};
    c_reg_t c_reg2 = {};
    c_reg_t c_reg3 = {};

    for (int kt = 0; kt < k_tiles; kt++) {
        // === Load A tile (16 bytes per thread) ===
        a_reg_t a_reg = {};
        if (a_valid) {
            int k_byte_off = kt * 32 + (tid >> 5) * 16;
            const uint8_t* src = A + a_row * K_half + k_byte_off;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&a_reg);
            *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*[6D[K
uint4*>(src);
        }

        // Load A scale once per K iteration
        int scale_idx = kt * 2 + (tid >> 5);
        int sa = a_valid ? (int)As[a_row * k_scale_groups + scale_idx] : 0;[2D[K
0;

        // === Process 4 B tiles sequentially ===
        for (int tile = 0; tile < 4; tile++) {
            int b_col = bn + tile * 32 + (tid & 31);
            bool b_valid = (b_col < N);

            // Load B tile
            b_reg_t b_reg = {};
            if (b_valid) {
                int k_byte_off = kt * 32 + (tid >> 5) * 16;
                const uint8_t* src = B + b_col * K_half + k_byte_off;
                uint8_t* dst = reinterpret_cast<uint8_t*>(&b_reg);
                *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const ui[2D[K
uint4*>(src);
            }

            // Load B scale for this tile
            int sb = b_valid ? (int)Bs[b_col * k_scale_groups + scale_idx] [K
: 0;

            // MFMA into corresponding accumulator
            switch (tile) {
                case 0:
                    c_reg0 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f[46D[K
__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
                        a_reg, b_reg, c_reg0, 4, 4, 0, sa, 0, sb);
                    break;
                case 1:
                    c_reg1 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f[46D[K
__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
                        a_reg, b_reg, c_reg1, 4, 4, 0, sa, 0, sb);
                    break;
                case 2:
                    c_reg2 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f[46D[K
__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
                        a_reg, b_reg, c_reg2, 4, 4, 0, sa, 0, sb);
                    break;
                case 3:
                    c_reg3 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f[46D[K
__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
                        a_reg, b_reg, c_reg3, 4, 4, 0, sa, 0, sb);
                    break;
            }
        }
    }

    // === Write 4 output columns (each with 16 rows) ===
    int out_col_base = bn + (tid & 31);
    for (int tile = 0; tile < 4; tile++) {
        int out_col = out_col_base + tile * 32;
        if (out_col >= N) break;
        
        c_reg_t* c_reg;
        switch (tile) {
            case 0: c_reg = &c_reg0; break;
            case 1: c_reg = &c_reg1; break;
            case 2: c_reg = &c_reg2; break;
            case 3: c_reg = &c_reg3; break;
        }
        
        for (int r = 0; r < 16; r++) {
            int out_row = bm + (r & 3) + (r >> 2) * 8 + (tid >> 5) * 4;
            if (out_row < M) {
                C[out_row * N + out_col] = (__hip_bfloat16)((*c_reg)[r]);
            }
        }
    }
}

void mxfp4_mfma_gemm_multi(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C,
    int M, int N, int K
) {
    dim3 grid((M + 31) / 32, (N + 127) / 128);
    dim3 block(64);  // 1 wavefront per block

    mxfp4_mfma_kernel_multi<<<grid, block>>>(
        (const uint8_t*)A_packed.data_ptr(),
        (const uint8_t*)B_packed.data_ptr(),
        (const uint8_t*)A_scale.data_ptr(),
        (const uint8_t*)B_scale.data_ptr(),
        (__hip_bfloat16*)C.data_ptr(),
        M, N, K
    );
}
"""

module = load_inline(
    name="mxfp4_mfma_multi",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=["mxfp4_mfma_gemm_multi"],
    verbose=False,
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
)


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) [K
-> torch.Tensor:
    """Reverse aiter's e8m0_shuffle to get linear [M, K/32] layout."""
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    return scale.view(sm, sn)[:orig_m, :orig_n]


def custom_kernel(data: input_t) -> output_t:
    """MXFP4 GEMM using multi-tile MFMA 32x128x64."""
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant

    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    k_scale_groups = K // 32

    # Quantize A on the fly
    A_fp4, A_scale_raw = dynamic_mxfp4_quant(A.contiguous())

    # A_scale: trim to valid region, keep as linear uint8
    A_scale_bytes = A_scale_raw[:M, :k_scale_groups].contiguous().view(torc[39D[K
:k_scale_groups].contiguous().view(torch.uint8)

    # B_scale: unshuffle from aiter format to linear [N, K/32]
    B_scale_sh_bytes = B_scale_sh.view(torch.uint8)
    bs_m, bs_n = B_scale_sh_bytes.shape
    B_scale_bytes = e8m0_unshuffle(B_scale_sh_bytes, N, k_scale_groups)

    # Use B_q (standard packed FP4)
    A_packed = A_fp4.view(torch.uint8)
    B_packed = B_q.view(torch.uint8)

    # Output
    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    module.mxfp4_mfma_gemm_multi(
        A_packed, B_packed, A_scale_bytes, B_scale_bytes, C,
        M, N, K
    )

    return C

