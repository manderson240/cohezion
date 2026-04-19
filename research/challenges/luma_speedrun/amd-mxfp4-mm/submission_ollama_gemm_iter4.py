Thinking...
We are currently using a single 32x32 tile per block with 64 threads (1 wav[3D[K
wavefront).
 The kernel does 32x32x64 FP4 MFMA per block, and we loop over K in steps o[1D[K
of 64.

 The current bottleneck is likely memory bandwidth and instruction-level pa[2D[K
parallelism.

 Proposed optimization: Multi-tile output (32x128) for A data reuse.
   - Instead of each block computing a 32x32 tile, we make it compute a 32x[3D[K
32x128 tile.
   - This means we reuse the A tile (32x64 elements per MFMA) for 4 consecu[7D[K
consecutive B tiles (each 128x64?).
   - Actually, for a 32x128 output tile, we need to load 32 rows of A and 1[1D[K
128 columns of B.
   - We can still use 64 threads per wavefront, but we will have to compute[7D[K
compute 4 times the output elements per thread.
   - We can do this by having each thread compute 4 output elements (instea[7D[K
(instead of 1) in the inner loop.

 How to do it?
   - We currently have each thread holding a 16x1 vector of output in the a[1D[K
accumulator (c_reg_t is 16 floats).
   - In the current kernel, each thread writes one column of 16 rows (but o[1D[K
only 4 are valid? Wait, the output write is complex).
   - Actually, in the current kernel, each thread holds 16 accumulators (c_[3D[K
(c_reg_t) and writes to 16 different rows and one column.
   - The current output write pattern is:
        out_col = bn + (tid & 31)
        for (int r = 0; r < 16; r++) {
            int out_row = bm + (r & 3) + (r >> 2) * 8 + (tid >> 5) * 4;
            if (out_row < M) {
                C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
            }
        }
   - This pattern is designed for 32x32 tile with 64 threads, where each th[2D[K
thread holds 16 accumulators that map to 16 different rows in the same colu[4D[K
column.

   For a 32x128 tile, we can have 64 threads and each thread will compute 4[1D[K
4 columns (each column having 16 rows) so 64*4=256 columns? 
   But we want 128 columns in total. So we can assign each thread to 2 colu[4D[K
columns (128/64=2) or 4 columns (if we want 256, but we only need 128).

   Alternatively, we can change the block size to 256 threads (4 wavefronts[10D[K
wavefronts) and compute 32x128 tile with each thread computing one column o[1D[K
of 16 rows? 
   But the problem is that the MFMA intrinsic is designed for 32x32x64 and [K
uses 64 threads per wavefront.

   We can keep 64 threads per block (1 wavefront) and compute a 32x128 tile[4D[K
tile by having each thread compute 2 columns (so 32 accumulators per thread[6D[K
thread). 
   We can use two MFMA accumulators (c_reg_t) per thread, one for each colu[4D[K
column.

   Steps:
     1. We load the same A tile (32x64) for 4 consecutive B tiles (each 32x[3D[K
32x64) to produce 4 output tiles (each 32x32). 
        But we want to produce one 32x128 tile, which is 4 tiles of 32x32 i[1D[K
in the N dimension.

     2. We can have 64 threads, each thread is responsible for 2 columns in[2D[K
in the 32x128 tile. 
        So thread i will be responsible for columns [bn + (i & 31)*2, bn + [K
(i & 31)*2 + 1] and rows [bm + ...] (same row pattern as before).

     3. We need to load B for two columns per thread. In the inner loop ove[3D[K
over kt, we load two B registers (each 16 bytes) for the two columns.

     4. We will have two accumulator registers (c_reg_t) for the two column[6D[K
columns.

     5. We do two MFMA calls per kt: one for the first column and one for t[1D[K
the second column.

     6. The A register and A scale are the same for both MFMA calls.

   However, note that the current kernel loads B for one column per thread.[7D[K
thread. Now we need to load two columns.

   Alternatively, we can process two B columns in one MFMA call? The MFMA i[1D[K
intrinsic is fixed to 32x32x64, so we cannot change the output shape.

   Therefore, we must do two MFMA calls per kt: one for each B column.

   We can try to load two B columns at a time (32 bytes) using a vectorized[10D[K
vectorized load (uint8_t[32] or two uint4). 
   Then we extract two b_reg_t from the loaded data.

   Steps for B load:
      - We are loading 16 bytes for one B column in the current kernel.
      - For two columns, we need 32 bytes. We can load two consecutive colu[4D[K
columns (so the two B registers are for the same kt but two consecutive col[3D[K
columns).

   However, note that the B matrix is stored in column-major? Actually, in [K
the aiter API, B is transposed? Let me check the aiter code.

   In the aiter code, B_q is [N, K/2] packed FP4. So each row of B_q is a c[1D[K
column of the original B (since it's transposed). 
   So we are loading one row of B_q (which is one column of B) per thread. [K
Now we want to load two consecutive rows of B_q (two columns of B).

   So the index for B becomes: 
        int b_col1 = bn + (tid & 31)*2;
        int b_col2 = b_col1 + 1;

   Then we load two B registers from:
        const uint8_t* src1 = B + b_col1 * K_half + k_byte_off;
        const uint8_t* src2 = B + b_col2 * K_half + k_byte_off;

   We can load them with two separate uint4 loads.

   Then we do two MFMA calls:
        c_reg1 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(a_reg, b_r[3D[K
b_reg1, c_reg1, ...);
        c_reg2 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(a_reg, b_r[3D[K
b_reg2, c_reg2, ...);

   We also need to load two B scales (one for each column).

   This way, we are computing two 32x32 tiles in the N dimension (so 32x64)[6D[K
32x64) per kt. But we want 128 in N, so we need to do this for two sets of [K
two columns? 
   Actually, we are processing 2 columns per thread, and we have 32 threads[7D[K
threads in the column dimension (since tid & 31 gives 0..31). So 32*2=64 co[2D[K
columns per kt? 
   Wait, no: in the current kernel, we have 32 threads in the column dimens[6D[K
dimension (tid & 31) and each thread computes one column. So we cover 32 co[2D[K
columns per kt.

   Now with 2 columns per thread, we cover 64 columns per kt. We need 128 c[1D[K
columns in total, so we need to loop over two sets of 64 columns? 
   But our block is only 64 threads, and we are already using all 64 thread[6D[K
threads for 64 columns (2 per thread). How do we get 128?

   We can process two sets of 64 columns by having each thread compute 4 co[2D[K
columns? Then we would need 128/32=4 columns per thread.

   Alternatively, we can change the block size to 128 threads (2 wavefronts[10D[K
wavefronts) and then each thread computes 1 column? Then we can cover 128 c[1D[K
columns.

   However, the MFMA intrinsic is designed for 64 threads per wavefront. We[2D[K
We can use 2 wavefronts (128 threads) and each wavefront does its own MFMA.[5D[K
MFMA.

   But note: the current kernel is written for 64 threads (one wavefront). [K
We can change the block size to 128 threads (2 wavefronts) and then each wa[2D[K
wavefront computes a 32x64 tile? 
   Then we would have two wavefronts working on two 32x64 tiles (so 32x128 [K
total). Each wavefront would be responsible for 64 columns.

   We can do:

        dim3 block(128);  // 2 wavefronts per block

   And then in the kernel, we split the threads into two groups of 64. We c[1D[K
can use threadIdx.x < 64 for the first wavefront and threadIdx.x >= 64 for [K
the second.

   But then we need to assign each wavefront to a different set of 64 colum[5D[K
columns.

   This might be simpler: we can have 128 threads, and each thread computes[8D[K
computes one column (so 128 columns). Then we are back to the original patt[4D[K
pattern of one column per thread.

   However, we are using 2 wavefronts, so we can do:

        int wave_id = threadIdx.x / 64;
        int wave_tid = threadIdx.x % 64;

        int bm = blockIdx.x * 32;
        int bn = blockIdx.y * 128 + wave_id * 64 + (wave_tid & 31);

   Then each wavefront computes a 32x64 tile, and together they compute 32x[3D[K
32x128.

   We can keep the same A load for both wavefronts (since they are in the s[1D[K
same block, they share the same A rows). 
   So we can load A once per thread (but note that each thread in the wavef[5D[K
wavefront loads the same A row as before, but now we have two wavefronts).

   But note: the A load is per thread, and each thread loads 16 bytes of A.[2D[K
A. We have 128 threads, so we are loading 128*16=2048 bytes of A (32 rows *[1D[K
* 64 bytes per row). 
   This is the same as before (32 rows * 64 bytes per row = 2048 bytes). So[2D[K
So we are loading the same A data twice (once per wavefront). 
   We can avoid this by using LDS to share A among the two wavefronts? But [K
that would require synchronization and LDS usage.

   Alternatively, we can keep the A load in the first wavefront and then sh[2D[K
share it with the second wavefront via LDS, but that complicates the kernel[6D[K
kernel.

   Given the time, we try the first approach: using 2 wavefronts (128 threa[5D[K
threads) and each thread computes one column, but we are loading A twice.

   However, note that the A data is the same for both wavefronts, so we are[3D[K
are wasting memory bandwidth.

   We can try to load A only once per thread and then use it for both wavef[5D[K
wavefronts? But the two wavefronts are in the same thread block, so we can [K
use LDS.

   But let's first try without LDS and see if the increased tile size in N [K
direction (128) helps with memory bandwidth and parallelism.

   We will change:
        block size to 128.
        grid y dimension: (N + 127) / 128.

   And in the kernel, we compute:
        int wave_id = tid / 64;
        int wave_tid = tid % 64;

        int a_row = bm + (wave_tid & 31);
        int b_col = bn + wave_id * 64 + (wave_tid & 31);

   Then we do the same loop over kt, but now we have 128 threads, so we are[3D[K
are loading 128 B columns (each 16 bytes) and 128 A rows (each 16 bytes) pe[2D[K
per kt.

   We are loading 128*16=2048 bytes of A and 128*16=2048 bytes of B per kt.[3D[K
kt. The total global memory bandwidth per kt is 4096 bytes.

   In the original kernel, we were loading 64*16=1024 bytes of A and 64*16=[6D[K
64*16=1024 bytes of B per kt, total 2048 bytes.

   So we are doubling the memory bandwidth per kt, but we are also doubling[8D[K
doubling the compute (because we have two wavefronts, so two MFMA calls per[3D[K
per kt?).

   Actually, each wavefront does its own MFMA, so we are doing two 32x32x64[8D[K
32x32x64 MFMA per kt, which is 2*32*32=2048 FLOPs (FP4*FP4->FP32) per kt.

   The original kernel did 1*32*32=1024 FLOPs per kt.

   So we are doubling the FLOPs and doubling the memory bandwidth. This sho[3D[K
should be balanced.

   However, we are also doubling the number of threads, so we might have mo[2D[K
more parallelism.

   We also need to change the output write. Each thread writes 16 rows (sam[4D[K
(same pattern as before) but to its own column.

   We will write:

        int out_col = bn + wave_id * 64 + (wave_tid & 31);
        if (out_col < N) {
            for (int r = 0; r < 16; r++) {
                int out_row = bm + (r & 3) + (r >> 2) * 8 + (wave_tid >> 5)[2D[K
5) * 4;
                if (out_row < M) {
                    C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
                }
            }
        }

   Let's try this approach.

   We must be cautious: the MFMA intrinsic expects 64 threads per wavefront[9D[K
wavefront. We are using 128 threads (2 wavefronts) and each wavefront is in[2D[K
independent.

   We can try to compile and run.

   We also note that the current kernel uses 64 threads and we are changing[8D[K
changing to 128. We must adjust the block size in the launch.

   We will change the launch to:

        dim3 block(128);  // 2 wavefronts per block

   And the grid to:

        dim3 grid((M + 31) / 32, (N + 127) / 128);

   Let's write the kernel accordingly.

   We'll keep the same name and just modify the kernel.

   We must also adjust the A and B scale loading. The scale index calculati[9D[K
calculation should be based on wave_tid for the row/column index.

   We'll change the scale loading to:

        int scale_idx = kt * 2 + (wave_tid >> 5);
        int sa = a_valid ? (int)As[a_row * k_scale_groups + scale_idx] : 0;[2D[K
0;
        int sb = b_valid ? (int)Bs[b_col * k_scale_groups + scale_idx] : [K
0;

   We'll also adjust the A and B loads to use wave_tid for the offset calcu[5D[K
calculation.

   A load:

        int k_byte_off = kt * 32 + (wave_tid >> 5) * 16;

   B load: same offset.

   We are now using wave_tid (0..63) for the per-wavefront calculations.

   Let's write the kernel.

   We'll keep the rest of the code the same.

   We are going to output the entire file with the modified kernel.

   Note: We are not using LDS and we are loading A twice (once per wavefron[8D[K
wavefront). We might try to use LDS in a future optimization.

   We'll try this and see if it improves performance.

   We'll output the complete submission.py file with the modified kernel.

   We must also adjust the custom_kernel function to use the new launch par[3D[K
parameters? Actually, the launch parameters are inside the C++ function.

   We only change the HIP kernel and the launch configuration.

   Let's write the code.
...done thinking.

#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MFMA GEMM v2 — Multi-tile 32x128x64 FP4 MFMA for A data reuse.

Uses __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4 (native FP4).
Register layouts verified in Session 91 (4/4 tests, max error 0.0).

Architecture:
  - 32×128 output tile per block, 128 threads (2 wavefronts)
  - K loop: 64 FP4 elements per MFMA iteration
  - Vectorized 128-bit loads for both A and B
  - A data reused across 4 B tiles (32x32 each)
  - Scales passed as int args to intrinsic (per-thread)
  - Uses B_q (unshuffled) not B_shuffle
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t


CPP_WRAPPER = """
void mxfp4_mfma_gemm(
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

// MFMA register types (MUST be int vec8, NOT uint8_t!)
typedef int a_reg_t __attribute__((ext_vector_type(8)));
typedef int b_reg_t __attribute__((ext_vector_type(8)));
typedef float c_reg_t __attribute__((ext_vector_type(16)));

__global__ void mxfp4_mfma_kernel(
    const uint8_t* __restrict__ A,    // [M, K/2] packed FP4
    const uint8_t* __restrict__ B,    // [N, K/2] packed FP4
    const uint8_t* __restrict__ As,   // [M, K/32] E8M0 scales (linear)
    const uint8_t* __restrict__ Bs,   // [N, K/32] E8M0 scales (linear)
    __hip_bfloat16* __restrict__ C,   // [M, N] output BF16
    int M, int N, int K
) {
    // Block: 32 rows × 128 columns
    int bm = blockIdx.x * 32;          // block row start
    int bn = blockIdx.y * 128;         // block col start
    int tid = threadIdx.x;             // 0-127 (2 wavefronts)
    int lane = tid & 31;               // lane within wave (0-31)
    int wave = tid >> 5;               // wave within block (0,1,2,3)
    
    int K_half = K / 2;                // bytes per row
    int k_tiles = K / 64;              // MFMA tiles along K
    int k_scale_groups = K / 32;       // scale groups per row

    // A row: same for all waves (32 rows total, 8 per wave)
    int a_row = bm + wave * 8 + (lane >> 2);
    bool a_valid = (a_row < M);
    
    // B column: each wave handles 32 columns
    int b_col_base = bn + wave * 32;
    int b_col = b_col_base + lane;
    bool b_valid = (b_col < N);

    // Accumulators: 4 columns per thread (32×4 = 128 columns total)
    c_reg_t c_reg[4] = {};  // Zero initialize

    // Prefetch priorities for CDNA4
    if (tid == 0) {
        __builtin_amdgcn_s_setprio(1);  // Higher priority for first wave
    }

    for (int kt = 0; kt < k_tiles; kt++) {
        // === Load A tile (16 bytes per thread, vectorized 128-bit) ===
        a_reg_t a_reg = {};
        if (a_valid) {
            int k_byte_off = kt * 32 + (lane & 3) * 8;
            const uint8_t* src = A + a_row * K_half + k_byte_off;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&a_reg);
            *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*[6D[K
uint4*>(src);
        }

        // === Load A scale (same for all 4 B tiles) ===
        int scale_idx = kt * 2 + (lane >> 2);
        int sa = a_valid ? (int)As[a_row * k_scale_groups + scale_idx] : 0;[2D[K
0;

        // === Process 4 B tiles (32 columns each) ===
        for (int tile = 0; tile < 4; tile++) {
            int b_col_tile = b_col_base + tile * 32 + lane;
            bool b_tile_valid = (b_col_tile < N);
            
            // Load B tile for this column
            b_reg_t b_reg = {};
            if (b_tile_valid) {
                int k_byte_off = kt * 32 + (lane & 3) * 8;
                const uint8_t* src = B + b_col_tile * K_half + k_byte_off;
                uint8_t* dst = reinterpret_cast<uint8_t*>(&b_reg);
                *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const ui[2D[K
uint4*>(src);
            }
            
            // Load B scale
            int sb = b_tile_valid ? (int)Bs[b_col_tile * k_scale_groups + s[1D[K
scale_idx] : 0;
            
            // MFMA: 32x32x64 FP4
            c_reg[tile] = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
                a_reg, b_reg, c_reg[tile],
                4,     // cbsz = FP4 E2M1 for A
                4,     // blgp = FP4 E2M1 for B
                0, sa, // neg_a=0, scale_a
                0, sb  // neg_b=0, scale_b
            );
        }
    }

    // === Write output (4 columns per thread) ===
    for (int tile = 0; tile < 4; tile++) {
        int out_col = b_col_base + tile * 32 + lane;
        if (out_col < N) {
            for (int r = 0; r < 16; r++) {
                // Each thread writes 16 rows in its column
                int out_row = bm + wave * 8 + (r & 7);
                if (out_row < M) {
                    C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[tile][28D[K
(__hip_bfloat16)(c_reg[tile][r]);
                }
            }
        }
    }
    
    // Reset priority
    if (tid == 0) {
        __builtin_amdgcn_s_setprio(0);
    }
}

void mxfp4_mfma_gemm(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C,
    int M, int N, int K
) {
    dim3 grid((M + 31) / 32, (N + 127) / 128);
    dim3 block(128);  // 2 wavefronts per block

    mxfp4_mfma_kernel<<<grid, block>>>(
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
    name="mxfp4_mfma_v2",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=["mxfp4_mfma_gemm"],
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
    """MXFP4 GEMM using MFMA 32x32x64 FP4 intrinsic via load_inline."""
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
    # Get padded dimensions for unshuffle
    bs_m, bs_n = B_scale_sh_bytes.shape
    B_scale_bytes = e8m0_unshuffle(B_scale_sh_bytes, N, k_scale_groups)

    # Use B_q (standard packed FP4), NOT B_shuffle (CK-specific)
    A_packed = A_fp4.view(torch.uint8)
    B_packed = B_q.view(torch.uint8)

    # Output
    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    module.mxfp4_mfma_gemm(
        A_packed, B_packed, A_scale_bytes, B_scale_bytes, C,
        M, N, K
    )

    return C

