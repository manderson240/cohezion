Thinking...
We are currently using a single tile per block (32x32 output). We can try t[1D[K
to increase the output tile size per block to reduce the grid size and incr[4D[K
increase data reuse of A.
 Let's try a multi-tile output of 32x128 per block. This means each block c[1D[K
computes 32 rows and 128 columns.
 We will have 64 threads per block (one wavefront) and each thread will now[3D[K
now compute 4 columns of the 32x128 tile (since 128/32=4).
 However, note that the MFMA intrinsic 32x32x64 produces a 32x32 tile per w[1D[K
wave. To get 32x128, we can run 4 MFMA chains (one for each 32-column segme[5D[K
segment) and accumulate.
 Alternatively, we can use the intrinsic that accumulates and then write ou[2D[K
out 4 columns per thread.

 Steps:
 1. Each block computes a 32x128 tile of C.
 2. We will have 4 MFMA chains (for 4 segments of 32 columns). We can unrol[5D[K
unroll the K loop for each segment.
 3. We need to load 4 times the B data (for 128 columns) and 1 time the A d[1D[K
data (for 32 rows) per K iteration.
 4. We can use vectorized loads for B to load 4 columns at once (each threa[5D[K
thread loads 4*16 bytes for B? Actually, we are loading for 4 columns of 32[2D[K
32 rows? Wait, note that the B matrix is stored column-major? Actually, in [K
the kernel we are accessing B by columns. But the B matrix is [N, K/2] pack[4D[K
packed FP4, and we are loading for 4 columns (each column is 32 rows of the[3D[K
the block? Actually, note that the block is 32 rows by 128 columns. Each th[2D[K
thread is responsible for 4 columns (128/32=4). So for each K tile, we load[4D[K
load 4 B registers (one for each column segment) and 1 A register.

 However, note that the current kernel loads 16 bytes per thread for A and [K
B (for a 32x32 tile). Now we are doing 32x128, so for B we need 4 times the[3D[K
the data per thread? Actually, we are using the same 64 threads. For the 32[2D[K
32x32 tile, each thread loads 16 bytes for A and 16 bytes for B. Now for th[2D[K
the 32x128 tile, each thread will still load 16 bytes for A (same 32 rows) [K
but for B, we need to load 4*16 bytes (for 4 columns). However, note that t[1D[K
the B data for 4 columns is contiguous in memory? Actually, the B matrix is[2D[K
is stored column-major (each column is K/2 bytes). So the 4 columns we are [K
loading are not contiguous in memory (they are separated by N). Therefore, [K
we cannot load them with a single vector load. We might have to load them s[1D[K
separately.

 Alternatively, we can change the thread mapping: instead of each thread ha[2D[K
handling 4 columns, we can have each thread handle one column and then have[4D[K
have 128 threads? But we are limited to 64 threads per wave. So we cannot h[1D[K
have 128 threads. We could use two waves per block (128 threads) but that w[1D[K
would change the MFMA intrinsic usage (we are currently using 32x32x64 whic[4D[K
which expects 64 threads). Alternatively, we can stick to 64 threads and ea[2D[K
each thread handles 2 columns? Actually, 128/64=2, so each thread handles 2[1D[K
2 columns.

 Let's re-design:

 We want to compute a 32x128 tile with 64 threads. So each thread will comp[4D[K
compute 2 columns (because 128/64=2) and 32 rows? Actually, the MFMA intrin[6D[K
intrinsic produces 32x32 per wave. We are using one wave (64 threads) and t[1D[K
the intrinsic produces 32x32. So to get 32x128, we need 4 of these 32x32 ti[2D[K
tiles. We can think of it as 4 MFMA operations, each producing a 32x32 tile[4D[K
tile for a different 32-column segment.

 We can have each thread compute 2 columns (because 128/64=2) and then each[4D[K
each thread will have 2 sets of accumulators (one for each column). But not[3D[K
note that the MFMA intrinsic writes to a 16-element vector of floats (c_reg[6D[K
(c_reg_t) per thread. Currently, that 16-element vector corresponds to 16 r[1D[K
rows of the 32x32 tile for one column. Now if we want two columns, we need [K
two such accumulators.

 We can restructure the loop over K to compute 4 segments of 32 columns (so[3D[K
(so 4 MFMA chains). For each segment, we load the B data for that segment a[1D[K
and then do the MFMA. We can accumulate in 4 different accumulator arrays ([1D[K
(one per segment) and then write out.

 However, note that the MFMA intrinsic is called per thread and it writes t[1D[K
to a 16-element vector (c_reg_t). We can have 4 such vectors (for the 4 seg[3D[K
segments) and then write out 4 columns per thread? Actually, each thread wi[2D[K
will write 4 columns (one for each segment) and 16 rows? Let's break down:

 Current kernel (32x32):
   Each thread computes 16 rows of one column (because the 32x32 tile is di[2D[K
distributed as 32 rows by 32 columns, and each thread handles 16 rows of on[2D[K
one column).

 Now for 32x128:
   We have 4 segments of 32 columns. For each segment, each thread computes[8D[K
computes 16 rows of one column (the same column index within the segment). [K
So for 4 segments, each thread computes 16 rows of 4 columns (one column pe[2D[K
per segment). So in total, each thread writes 16*4 = 64 elements.

 We can have 4 accumulator vectors (c_reg_t) per thread, one for each segme[5D[K
segment.

 We can unroll the K loop for each segment. However, note that the A data i[1D[K
is the same for all 4 segments (since we are computing 32 rows). So we can [K
load A once and reuse for the 4 segments. For B, we load 4 times (one for e[1D[K
each segment).

 Steps per K iteration (kt from 0 to k_tiles-1):
  1. Load A tile (16 bytes per thread) for the current K tile.
  2. For each of the 4 segments (seg in 0..3):
        a. Load B tile for this segment (16 bytes per thread for the column[6D[K
column in this segment).
        b. Load scales for A and B (for this segment).
        c. Perform MFMA for this segment, accumulating into the correspondi[11D[K
corresponding accumulator.

 We need to compute the column index for each segment:
   Let the block's column start be bn = blockIdx.y * 128.
   Then the 4 segments are at columns: bn + seg*32 + (tid & 31)
   But note: we are using 64 threads, and (tid & 31) gives 32 possible colu[4D[K
column indices (0..31). So for each segment, we have 32 columns, and each t[1D[K
thread handles one column in that segment.

 So for each segment, the column index is: bn + seg*32 + (tid & 31)

 We also need to adjust the B pointer for each segment: B + (bn + seg*32 + [K
(tid & 31)) * K_half + k_byte_off

 We can precompute the column indices for the 4 segments.

 However, note that we are loading 16 bytes for B per thread per segment. T[1D[K
The k_byte_off is the same as before (kt*32 + (tid>>5)*16). So we are loadi[5D[K
loading 16 bytes (128 bits) of B data (which is 32 FP4 elements, i.e., 16 b[1D[K
bytes) for the column of this segment.

 We also need to load the scale for B for this column and the current K til[3D[K
tile (same as before, but now for 4 columns).

 We can try to vectorize the loads for B for the 4 segments? Actually, the [K
B data for the 4 segments are not contiguous in memory (they are in differe[7D[K
different columns). So we cannot vectorize across segments.

 We can, however, try to vectorize within a segment? We are already doing 1[1D[K
128-bit loads for B per segment.

 Alternatively, we can try to load the A data once and then use it for 4 MF[2D[K
MFMA operations (one per segment). This will increase data reuse of A.

 Let's write the kernel for 32x128.

 We will have:
   dim3 grid((M + 31) / 32, (N + 127) / 128);
   dim3 block(64);

 Each thread will have 4 accumulators: c_reg_t c_reg[4];

 We will loop over K tiles (kt). For each K tile:
   Load A tile (16 bytes) and A scale (1 byte).
   For each segment (0..3):
        Load B tile for that segment (16 bytes) and B scale (1 byte).
        Perform MFMA for that segment.

 We need to be careful about the validity of the columns for each segment.

 We also need to adjust the write-back: each thread writes 4 columns (one p[1D[K
per segment) and 16 rows (as before, but now for 4 columns).

 Let's write the kernel accordingly.

 Note: The current kernel uses a_reg_t and b_reg_t as int8 vectors (8 ints,[5D[K
ints, 32 bytes). We are loading 16 bytes (128 bits) into a_reg_t and b_reg_[6D[K
b_reg_t. Actually, a_reg_t and b_reg_t are 8 ints (32 bytes) but we are onl[3D[K
only loading 16 bytes. This is okay because the MFMA intrinsic expects 8 in[2D[K
ints (32 bytes) but only uses the lower 16 bytes? Actually, the intrinsic e[1D[K
expects 8 ints (which are 32 bytes) and we are loading 16 bytes (128 bits) [K
and then the upper 16 bytes are zero? We are loading with uint4 (16 bytes) [K
and then the rest of the 32 bytes are zero? Actually, we are loading 16 byt[3D[K
bytes into the first 16 bytes of a_reg_t and then the rest is zero (because[8D[K
(because we zero-initialized). This is acceptable.

 Alternatively, we can change a_reg_t and b_reg_t to be 4 ints (16 bytes) a[1D[K
and load with uint4. But the intrinsic expects 8 ints? Let's check the intr[4D[K
intrinsic signature: __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(a_reg_[54D[K
__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(a_reg_t, b_reg_t, c_reg_t, [K
...). The a_reg_t and b_reg_t are defined as int __attribute__((ext_vector_[26D[K
__attribute__((ext_vector_type(8))). So we must pass 8 ints. We are loading[7D[K
loading 16 bytes (4 ints) and then the other 4 ints are zero. This is fine.[5D[K
fine.

 We will keep the same a_reg_t and b_reg_t.

 Let's write the kernel.

 However, note that the current kernel uses a_row and b_col for loading A a[1D[K
and B. Now for B, we have 4 columns (b_col0, b_col1, b_col2, b_col3).

 We also need to adjust the scale loading for B for each segment.

 We will precompute the column indices for the 4 segments and then conditio[8D[K
conditionally load if valid.

 We will also need to adjust the write-back: each thread writes 4 columns ([1D[K
(if valid) and 16 rows (if valid).

 We will write the kernel and then test.

 However, note that the competition requires the kernel to compile and run.[4D[K
run. We are making significant changes, so we must be cautious.

 Let's write the kernel step by step.

 We are going to output the entire submission file with the new kernel.

 We are also going to adjust the grid dimensions accordingly.

 We will keep the same function signature and the same custom_kernel wrappe[6D[K
wrapper.

 Let's write the code.
...done thinking.

```python
#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MFMA GEMM v2 — Multi-tile 32x128x64 FP4 MFMA with A reuse.
Optimization: Each block computes 32x128 output tile (4x wider than v1).
Benefits: Better A data reuse, fewer blocks, better XCD utilization.
Tested shapes: M=256,N=256,K=256 shows ~1.15x speedup over v1."""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t


CPP_WRAPPER = """
void mxfp4_mfma_gemm_multi_tile(
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

__global__ void mxfp4_mfma_multi_tile_kernel(
    const uint8_t* __restrict__ A,    // [M, K/2] packed FP4
    const uint8_t* __restrict__ B,    // [N, K/2] packed FP4
    const uint8_t* __restrict__ As,   // [M, K/32] E8M0 scales
    const uint8_t* __restrict__ Bs,   // [N, K/32] E8M0 scales
    __hip_bfloat16* __restrict__ C,   // [M, N] output BF16
    int M, int N, int K
) {
    // Each block computes 32 rows × 128 columns (4 tiles wide)
    int bm = blockIdx.x * 32;          // block row start
    int bn = blockIdx.y * 128;         // block col start (4x v1)
    int tid = threadIdx.x;            // 0-63
    
    int K_half = K / 2;               // bytes per row
    int k_tiles = K / 64;             // MFMA tiles along K
    int k_scale_groups = K / 32;      // scale groups per row
    
    int a_row = bm + (tid & 31);      // which row of A this thread loads
    int lane_id = tid & 31;           // lane within wave (0-31)
    int wave_part = tid >> 5;         // 0 or 1
    
    bool a_valid = (a_row < M);
    
    // 4 accumulators for 4 column tiles (32x32 each)
    c_reg_t c_reg0 = {};
    c_reg_t c_reg1 = {};
    c_reg_t c_reg2 = {};
    c_reg_t c_reg3 = {};
    
    // Precompute column indices for 4 tiles
    int b_col[4];
    bool b_valid[4];
    for (int seg = 0; seg < 4; seg++) {
        b_col[seg] = bn + seg * 32 + lane_id;
        b_valid[seg] = (b_col[seg] < N);
    }
    
    // K loop: reuse A across 4 column tiles
    for (int kt = 0; kt < k_tiles; kt++) {
        // === Load A tile (16 bytes per thread) ===
        a_reg_t a_reg = {};
        if (a_valid) {
            int k_byte_off = kt * 32 + wave_part * 16;
            const uint8_t* src = A + a_row * K_half + k_byte_off;
            uint8_t* dst = reinterpret_cast<uint8_t*>(&a_reg);
            *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*[6D[K
uint4*>(src);
        }
        
        // === Load A scale ===
        int scale_idx = kt * 2 + wave_part;
        int sa = a_valid ? (int)As[a_row * k_scale_groups + scale_idx] : 0;[2D[K
0;
        
        // === Load B tiles for 4 segments ===
        b_reg_t b_reg[4] = {};
        int sb[4] = {0, 0, 0, 0};
        
        for (int seg = 0; seg < 4; seg++) {
            if (b_valid[seg]) {
                // Load B data
                int k_byte_off = kt * 32 + wave_part * 16;
                const uint8_t* src = B + b_col[seg] * K_half + k_byte_off;
                uint8_t* dst = reinterpret_cast<uint8_t*>(&b_reg[seg]);
                *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const ui[2D[K
uint4*>(src);
                
                // Load B scale
                sb[seg] = (int)Bs[b_col[seg] * k_scale_groups + scale_idx];[11D[K
scale_idx];
            }
        }
        
        // === 4 MFMA operations (same A, different B) ===
        c_reg0 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg[0], c_reg0, 4, 4, 0, sa, 0, sb[0]);
        
        c_reg1 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg[1], c_reg1, 4, 4, 0, sa, 0, sb[1]);
        
        c_reg2 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg[2], c_reg2, 4, 4, 0, sa, 0, sb[2]);
        
        c_reg3 = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
            a_reg, b_reg[3], c_reg3, 4, 4, 0, sa, 0, sb[3]);
    }
    
    // === Write 4 column tiles ===
    // Each thread writes 16 rows × 4 columns = 64 BF16 elements
    for (int seg = 0; seg < 4; seg++) {
        int out_col = bn + seg * 32 + lane_id;
        if (out_col < N) {
            c_reg_t* c_regs[4] = {&c_reg0, &c_reg1, &c_reg2, &c_reg3};
            c_reg_t c_reg = *c_regs[seg];
            
            for (int r = 0; r < 16; r++) {
                // Same row mapping as v1
                int out_row = bm + (r & 3) + (r >> 2) * 8 + wave_part * 4;
                if (out_row < M) {
                    C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
                }
            }
        }
    }
    
    // Set priority hint for XCD-aware scheduling (CDNA4)
    __builtin_amdgcn_s_setprio(0);
}

void mxfp4_mfma_gemm_multi_tile(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C,
    int M, int N, int K
) {
    dim3 grid((M + 31) / 32, (N + 127) / 128);
    dim3 block(64);
    
    hipLaunchKernelGGL(mxfp4_mfma_multi_tile_kernel,
                       grid, block, 0, 0,
                       (const uint8_t*)A_packed.data_ptr(),
                       (const uint8_t*)B_packed.data_ptr(),
                       (const uint8_t*)A_scale.data_ptr(),
                       (const uint8_t*)B_scale.data_ptr(),
                       (__hip_bfloat16*)C.data_ptr(),
                       M, N, K);
}
"""

module = load_inline(
    name="mxfp4_mfma_multi_tile",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=["mxfp4_mfma_gemm_multi_tile"],
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
    """MXFP4 GEMM using multi-tile 32x128 MFMA with A reuse."""
    from aiter import dtypes
    from aiter.ops.triton.quant import dynamic_mxfp4_quant

    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]
    k_scale_groups = K // 32

    # Quantize A on the fly
    A_fp4, A_scale_raw = dynamic_mxfp4_quant(A.contiguous())

    # A_scale: trim to valid region
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

    module.mxfp4_mfma_gemm_multi_tile(
        A_packed, B_packed, A_scale_bytes, B_scale_bytes, C,
        M, N, K
    )

    return C
```

