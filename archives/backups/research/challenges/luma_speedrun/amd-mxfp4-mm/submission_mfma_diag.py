#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MFMA diagnostic: determine exact register→output mapping.

Strategy: Use the MFMA with known inputs where the output pattern reveals
the register mapping. Feed A=identity-like and B=identity-like, then check
which output positions get non-zero values.

The key trick: set ALL A and B data to a known value (e.g., all FP4=1.0)
with identity scales (127). Then each output C[i,j] should equal K (the
dot product of K ones). By checking which c_reg indices map to which
output positions, we can reverse-engineer the layout.

BUT: we can't inspect c_reg directly — we can only see the final output.
So instead: make each thread write a UNIQUE identifier to its output
positions, using the accumulator as a marker.

Approach: Don't use MFMA at all for the diagnostic. Just write thread ID
patterns to output to determine what the CORRECT output should look like
for the standard aiter path, then compare.

Actually, simplest approach: use the MFMA with c_reg initialized to
thread-specific values (not zero), and A/B = 0. Then the output IS c_reg,
revealing the exact mapping.
"""

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

typedef short v4s __attribute__((ext_vector_type(4)));
typedef float v4f __attribute__((ext_vector_type(4)));

__device__ __forceinline__ v4f bf16_mfma(v4s a, v4s b, v4f c) {
    return __builtin_amdgcn_mfma_f32_16x16x16bf16_1k(a, b, c, 0, 0, 0);
}

// Diagnostic kernel: initialize c_reg to known values, feed zero A/B
// Output reveals the exact c_reg → output position mapping
__global__ void mfma_diag(
    __hip_bfloat16* __restrict__ C,
    int M, int N
) {
    int bm = blockIdx.y * 16;
    int bn = blockIdx.x * 16;
    int tid = threadIdx.x;

    // Initialize c_reg with unique values per thread
    // c_reg[j] = tid * 4 + j (gives values 0-255 for 64 threads × 4 values)
    v4f c_reg;
    for (int j = 0; j < 4; j++) {
        ((float*)&c_reg)[j] = (float)(tid * 4 + j);
    }

    // Feed zero data through MFMA — output should be c_reg (0 + c_reg = c_reg)
    v4s zero_a = {0, 0, 0, 0};
    v4s zero_b = {0, 0, 0, 0};
    c_reg = bf16_mfma(zero_a, zero_b, c_reg);

    // Write output — try EVERY possible mapping pattern
    // Pattern 1: row = tid % 16, cols = (tid/16)*4 + j
    // Pattern 2: row = (tid/16)*4 + j, col = tid % 16
    // We'll use Pattern 1 first and see what the reference expects

    // Actually, just write the value and its position as a tag
    // For a 16x16 output tile, write c_reg[j] to position determined by mapping
    // TRY: row = tid % 16, col_base = (tid / 16) * 4
    int row = bm + (tid % 16);
    int col_base = bn + (tid / 16) * 4;

    if (row < M) {
        for (int j = 0; j < 4; j++) {
            int col = col_base + j;
            if (col < N) {
                C[row * N + col] = (__hip_bfloat16)(((float*)&c_reg)[j]);
            }
        }
    }
}

void mfma_diag_launch(torch::Tensor C, int M, int N) {
    dim3 grid((N + 15) / 16, (M + 15) / 16);
    dim3 block(64);
    mfma_diag<<<grid, block>>>(
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N);
}
"""

CPP_SOURCE = "void mfma_diag_launch(torch::Tensor C, int M, int N);"

try:
    _mod = load_inline(
        name="mfma_diag",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["mfma_diag_launch"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[mfma_diag] {e}")
    _OK = False


def custom_kernel(data: input_t) -> output_t:
    """Diagnostic: write MFMA output mapping pattern, compare with reference."""
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    if _OK and M <= 16 and N <= 16:
        # For small shapes, use diagnostic to dump the mapping
        C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)
        _mod.mfma_diag_launch(C, M, N)
        # Print the output pattern for debugging
        vals = C.float().cpu()
        print(f"[DIAG] M={M} N={N} output[0,:8]={vals[0, : min(8, N)].tolist()}")
        if M > 1:
            print(f"[DIAG] output[1,:8]={vals[1, : min(8, N)].tolist()}")

    # Always use reference for correctness
    import aiter

    A_q, A_scale = dynamic_mxfp4_quant(A.contiguous())
    A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        A_q.view(dtypes.fp4x2),
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
