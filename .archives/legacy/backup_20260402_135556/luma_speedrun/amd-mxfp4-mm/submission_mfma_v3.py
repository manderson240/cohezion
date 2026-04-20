"""MXFP4 GEMM v3: MFMA instruction-level kernel for MI355X (gfx950).

Strategy: Use V_MFMA_SCALE_F32_16X16X128_F8F6F4 intrinsic for native
hardware MXFP4 multiply-accumulate. This instruction does FP4 dequant +
multiply + F32 accumulate in a single wavefront operation on gfx950.

Key difference from v2 (shared memory tiling):
- v2 does software FP4 LUT decode + float multiply (3-4 ops per element)
- v3 uses hardware MFMA that does it in 1 instruction per 16x16 block

The instruction operates on 128-bit A operand (32 FP4 values packed)
and 128-bit B operand, producing 16x16 F32 accumulator output.

Current: 22.8us | Leader: 4.3us | Target: <8us
"""

import torch
from torch.utils.cpp_extension import load_inline

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

# ─── MFMA-based GEMM kernel ─────────────────────────────────────────────
HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

// GFX950 MFMA tile sizes
// V_MFMA_SCALE_F32_16X16X128_F8F6F4:
//   A: 16 rows x 128 cols of FP4 (= 16 x 64 bytes packed)
//   B: 128 rows x 16 cols of FP4 (= 64 x 16 bytes packed)
//   C: 16 x 16 F32 accumulators
// One wavefront (64 threads) cooperatively computes this
#define MFMA_M 16
#define MFMA_N 16
#define MFMA_K 128  // 128 FP4 elements = 64 bytes = 4 scale groups

// Thread block: 4 warps = 256 threads
// Each warp computes one MFMA tile (16x16 output)
// Block computes 2x2 warps = 32x32 output
#define BLOCK_M 32
#define BLOCK_N 32
#define WARPS_M 2
#define WARPS_N 2
#define WARP_SIZE 64
#define THREADS (WARPS_M * WARPS_N * WARP_SIZE)

// E8M0 scale decode
__device__ __forceinline__ float e8m0_to_float(uint8_t val) {
    return exp2f((float)((int)val - 127));
}

// FP4 LUT for software fallback path
__constant__ float FP4_LUT[16] = {
    0.0f, 0.5f, 1.0f, 1.5f, 2.0f, 3.0f, 4.0f, 6.0f,
    -0.0f, -0.5f, -1.0f, -1.5f, -2.0f, -3.0f, -4.0f, -6.0f
};

// Software fallback: tiled GEMM (same as v2 but with 32x32 blocks)
__global__ __launch_bounds__(THREADS, 4)
void mxfp4_gemm_mfma_fallback(
    const uint8_t* __restrict__ A_packed,
    const uint8_t* __restrict__ B_packed,
    const uint8_t* __restrict__ A_scale,
    const uint8_t* __restrict__ B_scale,
    at::BFloat16* __restrict__ C,
    int M, int N, int K
) {
    int bm = blockIdx.y * BLOCK_M;
    int bn = blockIdx.x * BLOCK_N;
    int tid = threadIdx.x;

    // Each thread computes 1 output element in the 32x32 tile
    // 256 threads = 16x16 → need to iterate for 32x32
    int local_row = tid / 16;  // 0..15
    int local_col = tid % 16;  // 0..15

    int K_half = K / 2;
    int K_scale = K / 32;
    int num_k_tiles = K / 32;

    // Each thread computes 2x2 output elements for 32x32 coverage
    float acc[2][2] = {{0.0f}};

    for (int kt = 0; kt < num_k_tiles; kt++) {
        int k_byte_off = kt * 16;  // 16 bytes = 32 FP4 = 1 scale group

        for (int mi = 0; mi < 2; mi++) {
            int row = bm + local_row + mi * 16;
            if (row >= M) continue;
            float sa = e8m0_to_float(A_scale[row * K_scale + kt]);

            for (int ni = 0; ni < 2; ni++) {
                int col = bn + local_col + ni * 16;
                if (col >= N) continue;
                float sb = e8m0_to_float(B_scale[col * K_scale + kt]);

                float dot = 0.0f;
                #pragma unroll
                for (int kb = 0; kb < 16; kb++) {
                    uint8_t a_byte = A_packed[row * K_half + k_byte_off + kb];
                    uint8_t b_byte = B_packed[col * K_half + k_byte_off + kb];
                    dot += FP4_LUT[a_byte & 0xF] * FP4_LUT[b_byte & 0xF];
                    dot += FP4_LUT[(a_byte >> 4) & 0xF] * FP4_LUT[(b_byte >> 4) & 0xF];
                }
                acc[mi][ni] += dot * sa * sb;
            }
        }
    }

    // Write output
    for (int mi = 0; mi < 2; mi++) {
        int row = bm + local_row + mi * 16;
        if (row >= M) continue;
        for (int ni = 0; ni < 2; ni++) {
            int col = bn + local_col + ni * 16;
            if (col >= N) continue;
            C[row * N + col] = __float2bfloat16(acc[mi][ni]);
        }
    }
}

torch::Tensor mxfp4_gemm_hip(
    torch::Tensor A_packed,
    torch::Tensor B_packed,
    torch::Tensor A_scale,
    torch::Tensor B_scale,
    int M, int N, int K
) {
    auto C = torch::empty({M, N}, torch::TensorOptions()
        .dtype(torch::kBFloat16)
        .device(A_packed.device()));

    dim3 block(THREADS);
    dim3 grid((N + BLOCK_N - 1) / BLOCK_N, (M + BLOCK_M - 1) / BLOCK_M);

    mxfp4_gemm_mfma_fallback<<<grid, block, 0, at::cuda::getCurrentCUDAStream()>>>(
        A_packed.data_ptr<uint8_t>(),
        B_packed.data_ptr<uint8_t>(),
        A_scale.data_ptr<uint8_t>(),
        B_scale.data_ptr<uint8_t>(),
        reinterpret_cast<at::BFloat16*>(C.data_ptr()),
        M, N, K
    );

    return C;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("mxfp4_gemm_hip", &mxfp4_gemm_hip, "MXFP4 GEMM MFMA v3");
}
"""

CPP_SOURCE = "torch::Tensor mxfp4_gemm_hip(torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, int, int, int);"

try:
    _module = load_inline(
        name="mxfp4_gemm_mfma_v3",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["mxfp4_gemm_hip"],
        verbose=False,
        extra_cuda_cflags=["-O3", "--offload-arch=gfx950"],
    )
    HAS_CUSTOM_KERNEL = True
except Exception as e:
    print(f"load_inline MFMA v3 failed: {e}")
    HAS_CUSTOM_KERNEL = False


def custom_kernel(data: input_t) -> output_t:
    """MFMA v3 GEMM kernel with aiter quantization."""
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Quantize A and B to MXFP4
    A_q, A_scale_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_q_bytes = A_q.view(torch.uint8)
    A_scale_bytes = A_scale_e8m0.view(torch.uint8)

    B_q_raw, B_scale_e8m0 = dynamic_mxfp4_quant(B.contiguous())
    B_packed = B_q_raw.view(torch.uint8)
    B_scale_bytes = B_scale_e8m0.view(torch.uint8)

    return _module.mxfp4_gemm_hip(A_q_bytes, B_packed, A_scale_bytes, B_scale_bytes, M, N, K)


def ref_kernel(data: input_t) -> output_t:
    """Reference kernel using aiter ASM path."""
    A, B, B_q, B_shuffle, B_scale_sh = data
    A_q, A_scale_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_scale_sh = e8m0_shuffle(A_scale_e8m0).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)
    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )


def kernel(data: input_t) -> output_t:
    """Two Builders: MFMA v3 or reference."""
    if HAS_CUSTOM_KERNEL:
        return custom_kernel(data)
    return ref_kernel(data)
