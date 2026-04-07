Thinking...
We are going to try multi-tile output (32x128) to increase data reuse of A.[2D[K
A.
 This means each block will compute a 32x128 tile of C, so we will have:
   grid.x = (M + 31) / 32
   grid.y = (N + 127) / 128
 Each block will have 64 threads (1 wavefront) and will compute 32x128 outp[4D[K
output using 4 MFMA tiles in the N dimension.

 We will load a 32x64 tile of A (same as before) and a 64x128 tile of B (in[3D[K
(in 4 parts of 64x32 each) to compute a 32x128 tile of C.

 However, note that the MFMA intrinsic 32x32x64_f8f6f4 produces a 32x32 til[3D[K
tile per thread. Since we have 64 threads, we can produce 32x32*2 = 32x64 p[1D[K
per wave?
 Wait, the intrinsic with 64 threads (one wave) produces a 32x32 tile. So t[1D[K
to get 32x128, we need to run 4 MFMA tiles in the N dimension.

 We can do this by having each thread compute 4 output columns (so 128 colu[4D[K
columns / 32 = 4 columns per thread? Actually 32x128 tile: 32 rows and 128 [K
columns.
 We have 64 threads, each thread can compute 2 rows and 2 columns? Let me t[1D[K
think.

 Alternatively, we can use the same MFMA intrinsic but with a different blo[3D[K
block size? Actually, the intrinsic is fixed at 32x32x64.

 We can break the 32x128 tile into four 32x32 tiles. Each 32x32 tile is com[3D[K
computed by one MFMA call. So we need to load 4 B tiles (each 32x64 in FP4,[4D[K
FP4, but note the B matrix is stored transposed? Actually B is [N, K] and w[1D[K
we are loading a column of B for each thread.

 In the original kernel, each thread loads a column of B (32x64 FP4 tile pe[2D[K
per thread? Actually, in the original kernel, each thread loads 16 bytes of[2D[K
of B (which is 32 FP4 elements, i.e., 32 values in K dimension) for a singl[5D[K
single column of B (since B is NxK). Then with 64 threads, we load 32 colum[5D[K
columns of B (since each thread is responsible for one column in the 32x32 [K
output tile). So for a 32x128 output tile, we need 128 columns of B, so we [K
need 4 times the number of B columns.

 We can have each thread load 4 B columns (so 4*16 = 64 bytes per thread fo[2D[K
for B) and then do 4 MFMA calls, each using a different B column and accumu[6D[K
accumulating to a different part of the accumulator.

 However, note that the accumulator is 16 floats per thread (for 32x32 outp[4D[K
output tile). For 32x128, we need 4 times that, so 64 floats per thread. We[2D[K
We can have 4 accumulator registers, one for each 32x32 subtile.

 Steps for the kernel:

   bm = blockIdx.x * 32
   bn = blockIdx.y * 128

   Each thread will compute:
      For 4 subtiles (j=0..3):
        B column index = bn + j*32 + (tid & 31)

   We load A tile as before (same as original, 16 bytes per thread, for 32 [K
rows and 64 K elements).

   We load B tile for 4 columns: each thread loads 4 columns of B, each col[3D[K
column is 16 bytes (for 64 K elements in FP4). So 64 bytes per thread for B[1D[K
B.

   We also load 4 scales for B (one for each column).

   Then in the K loop, we do 4 MFMA calls, one for each B column.

   We accumulate in 4 separate accumulator registers (c_reg0, c_reg1, c_reg[5D[K
c_reg2, c_reg3).

   After the K loop, we write out 4 sets of 16 floats (each set for a 32x32[5D[K
32x32 subtile) to the appropriate columns.

 However, note that the output layout per thread for the 32x32 tile is 16 f[1D[K
floats, arranged in a specific pattern (4 rows x 4 columns per thread? Actu[4D[K
Actually, in the original kernel, each thread writes 16 floats, which are 1[1D[K
16 rows of the same column? Let me check the original write pattern:

        int out_col = bn + (tid & 31);
        for (int r = 0; r < 16; r++) {
            int out_row = bm + (r & 3) + (r >> 2) * 8 + (tid >> 5) * 4;
            C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[r]);
        }

 So each thread writes to 16 rows of a single column (out_col). For 32x128,[7D[K
32x128, we want each thread to write to 16 rows of 4 columns (one column pe[2D[K
per subtile).

 So we can change the write to:

        for (int j = 0; j < 4; j++) {
            int out_col = bn + j*32 + (tid & 31);
            if (out_col < N) {
                for (int r = 0; r < 16; r++) {
                    int out_row = bm + (r & 3) + (r >> 2) * 8 + (tid >> 5) [K
* 4;
                    if (out_row < M) {
                        C[out_row * N + out_col] = (__hip_bfloat16)(c_reg_j[24D[K
(__hip_bfloat16)(c_reg_j[r]);
                    }
                }
            }
        }

 But note: we are loading 4 B columns per thread, so we have 4 accumulators[12D[K
accumulators. We can name them c_reg0, c_reg1, c_reg2, c_reg3.

 We also need to adjust the B pointer and B scale pointer for each j.

 However, note that the B matrix is stored in column-major? Actually B is [[1D[K
[N, K] and we are loading a column of B (so contiguous in K). So for each j[1D[K
j, the B column index is bn + j*32 + (tid & 31). So the offset in the B mat[3D[K
matrix (which is row-major in N, column-major in K) is (bn + j*32 + (tid & [K
31)) * K_half + k_byte_off.

 We can precompute the B pointers for each j at the beginning of the kernel[6D[K
kernel? Or compute on the fly.

 Alternatively, we can load all 4 B columns at once in a vectorized way (us[3D[K
(using uint4 for each column, so 4 uint4 = 64 bytes). But note that the B c[1D[K
columns for a given thread are not contiguous in memory (they are 32 column[6D[K
columns apart in the N dimension). So we cannot load them with a single vec[3D[K
vector load.

 We can load each column separately, but that would be 4 separate loads. We[2D[K
We can try to use vector loads for each column (16 bytes each) and hope tha[3D[K
that the compiler coalesces.

 However, note that the B matrix is stored in row-major (N rows, K columns)[8D[K
columns). So the columns of B that we want are 32*K_half bytes apart (becau[6D[K
(because each row is K_half bytes, and we jump 32 rows). So the addresses f[1D[K
for the 4 B columns for a thread are:

   B + (bn + j*32 + (tid & 31)) * K_half + k_byte_off

 for j=0..3.

 We can compute these addresses and then load each one with a uint4 load.

 We also need to load 4 B scales, one for each column.

 Let's restructure the kernel:

   Each thread:
      A tile: 16 bytes (same as before)
      B tile: 64 bytes (4 columns of 16 bytes each)
      A scale: 1 byte (same as before, but note we use the same A scale for[3D[K
for all 4 B columns)
      B scale: 4 bytes (one for each B column)

   Then in the K loop, for each kt, we load A, then load B for 4 columns, t[1D[K
then load 4 B scales, then do 4 MFMA calls.

   We can unroll the 4 MFMA calls to avoid extra loop.

   We must be careful with register pressure.

 Let's write the kernel accordingly.

 We'll change the grid and block:

   grid.x = (M + 31) / 32
   grid.y = (N + 127) / 128
   block = 64

 We'll also adjust the valid checks for A and B (now 4 B columns).

 We'll try to keep the same A loading and A scale loading as before.

 We'll change the B loading to load 4 columns.

 We'll change the MFMA to 4 accumulators.

 We'll change the write to write 4 columns.

 Let me write the kernel code accordingly.

 Note: We are using the same MFMA intrinsic, but now we are doing 4 of them[4D[K
them per K iteration.

 We are also loading 4 times the data for B per thread. This might increase[8D[K
increase memory bandwidth but also increase arithmetic intensity.

 We hope that by reusing A, we can achieve better performance.

 Let's code accordingly.
...done thinking.

#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MFMA GEMM v2 — Multi-tile 32x128x64 FP4 MFMA with A reuse.

Uses 32x128 output tile (4 MFMA tiles in N dimension) to reuse A data.
Each thread loads 4x B columns (64 bytes) and maintains 4 accumulators.
Grid: (M+31)//32 x (N+127)//128, block size 64 (1 wavefront).
"""

import os

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t


CPP_WRAPPER = """
void mxfp4_mfma_gemm_32x128(
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

__global__ void mxfp4_mfma_kernel_32x128(
    const uint8_t* __restrict__ A,    // [M, K/2] packed FP4
    const uint8_t* __restrict__ B,    // [N, K/2] packed FP4
    const uint8_t* __restrict__ As,   // [M, K/32] E8M0 scales
    const uint8_t* __restrict__ Bs,   // [N, K/32] E8M0 scales
    __hip_bfloat16* __restrict__ C,   // [M, N] output BF16
    int M, int N, int K
) {
    int bm = blockIdx.x * 32;   // block row start (32 rows)
    int bn = blockIdx.y * 128;  // block col start (128 cols)
    int tid = threadIdx.x;      // 0-63

    int K_half = K / 2;              // bytes per row
    int k_tiles = K / 64;            // MFMA tiles along K
    int k_scale_groups = K / 32;     // scale groups per row

    int a_row = bm + (tid & 31);     // which row of A this thread loads
    bool a_valid = (a_row < M);

    // 4 B columns this thread handles (32x128 tile → 4 MFMA tiles in N)
    int b_col[4];
    bool b_valid[4];
    for (int j = 0; j < 4; j++) {
        b_col[j] = bn + j * 32 + (tid & 31);
        b_valid[j] = (b_col[j] < N);
    }

    // 4 accumulators (one per 32x32 subtile)
    c_reg_t c_reg[4] = {};

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

        // === Load A scale (1 byte) ===
        int scale_idx = kt * 2 + (tid >> 5);
        int sa = a_valid ? (int)As[a_row * k_scale_groups + scale_idx] : 0;[2D[K
0;

        // === Load 4 B tiles (16 bytes each) ===
        b_reg_t b_reg[4] = {};
        int sb[4] = {0, 0, 0, 0};

        #pragma unroll
        for (int j = 0; j < 4; j++) {
            if (b_valid[j]) {
                int k_byte_off = kt * 32 + (tid >> 5) * 16;
                const uint8_t* src = B + b_col[j] * K_half + k_byte_off;
                uint8_t* dst = reinterpret_cast<uint8_t*>(&b_reg[j]);
                *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const ui[2D[K
uint4*>(src);
                sb[j] = (int)Bs[b_col[j] * k_scale_groups + scale_idx];
            }
        }

        // === 4 MFMA calls (reuse A tile) ===
        #pragma unroll
        for (int j = 0; j < 4; j++) {
            c_reg[j] = __builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(
                a_reg, b_reg[j], c_reg[j],
                4,     // cbsz = FP4 E2M1 for A
                4,     // blgp = FP4 E2M1 for B
                0, sa, // neg_a=0, scale_a
                0, sb[j]  // neg_b=0, scale_b
            );
        }
    }

    // === Write 4 output columns ===
    for (int j = 0; j < 4; j++) {
        int out_col = bn + j * 32 + (tid & 31);
        if (out_col < N) {
            for (int r = 0; r < 16; r++) {
                int out_row = bm + (r & 3) + (r >> 2) * 8 + (tid >> 5) * 4;[2D[K
4;
                if (out_row < M) {
                    C[out_row * N + out_col] = (__hip_bfloat16)(c_reg[j][r][28D[K
(__hip_bfloat16)(c_reg[j][r]);
                }
            }
        }
    }
}

void mxfp4_mfma_gemm_32x128(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    torch::Tensor C,
    int M, int N, int K
) {
    dim3 grid((M + 31) / 32, (N + 127) / 128);
    dim3 block(64);  // 1 wavefront per block

    mxfp4_mfma_kernel_32x128<<<grid, block>>>(
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
    name="mxfp4_mfma_32x128",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=["mxfp4_mfma_gemm_32x128"],
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
    """MXFP4 GEMM using MFMA 32x32x64 FP4 with 32x128 output tile."""
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

    # Use B_q (standard packed FP4), NOT B_shuffle
    A_packed = A_fp4.view(torch.uint8)
    B_packed = B_q.view(torch.uint8)

    # Output
    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    module.mxfp4_mfma_gemm_32x128(
        A_packed, B_packed, A_scale_bytes, B_scale_bytes, C,
        M, N, K
    )

    return C

