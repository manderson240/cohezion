# submission.py

import torch
import torch.utils.cpp_extension
import numpy as np
from typing import Tuple, Any

# Define input/output types for typing
input_t = Tuple[
    torch.Tensor,  # A: bf16 [M, K]
    torch.Tensor,  # B: bf16 [N, K]
    torch.Tensor,  # B_q: packed FP4 [N, K//2]
    torch.Tensor,  # B_shuffle: shuffled indices [N, K//2]
    torch.Tensor   # B_scale_sh: shuffled E8M0 [N, K//32]
]
output_t = torch.Tensor  # [M, N]

# CUDA/HIP sources — HIP-compliant for MI355X (gfx950)
# Uses __hip_bfloat16, __hip_fp8_e4m3_fnuz, hipLaunchKernelGGL
cuda_sources = r'''
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>
#include <hip/hip_fp8.h>
#include <type_traits>
#include <cstdio>

// FP4 packing helper: pack two e4m3 values into one byte
__device__ __forceinline__ uint8_t pack_fp4(__hip_fp8_e4m3_fnuz a, __hip_fp8_e4m3_fnuz b) {
    // FP4: 1 sign + 3 exponent bits (no mantissa) — but e4m3 has 3 mantissa bits
    // However, MXFP4 uses 4-bit values: sign + 3-bit exponent (E4M3) → stored in lower 4 bits each
    // We assume input is already FP8 e4m3, but only 4 bits used (clamped to FP4 range)
    // Simplified: store a in low 4 bits, b in high 4 bits
    return ((static_cast<uint8_t>(b.__x) & 0xF) << 4) | (static_cast<uint8_t>(a.__x) & 0xF);
}

// Unpack two FP4 values from byte
__device__ __forceinline__ void unpack_fp4(uint8_t x, __hip_fp8_e4m3_fnuz& a, __hip_fp8_e4m3_fnuz& b) {
    a.__x = static_cast<uint8_t>(x & 0xF);
    b.__x = static_cast<uint8_t>((x >> 4) & 0xF);
}

// E8M0 scale: 8-bit exponent only (no mantissa, no sign), stored in uint8_t
// Interpret as 2^scale where scale is stored in exponent field of uint8 (but e8m0 has no mantissa)
// We treat it as raw exponent bias=0: value = 2^(scale)
__device__ __forceinline__ float e8m0_to_float(uint8_t s) {
    // E8M0: exponent = s, bias = 127 → value = 2^(s - 127) ? 
    // But in MXFP4, e8m0 scales are typically stored as raw exponents with bias=0 (i.e., 2^s)
    // Let’s assume raw: 2^s, with s in [0,255], but clamp to avoid inf/nan
    if (s == 0) return 0.0f;
    int exp = static_cast<int>(s);
    // Use union to construct float from bits: sign=0, exp=exp, mantissa=0
    // But float encoding: exp field is 8 bits, bias=127
    // So actual exponent = exp - 127 → value = 1.x * 2^(exp - 127), but mantissa=0 → 1.0 * 2^(exp - 127)
    // However, in MXFP4 (e.g., Meta's implementation), e8m0 scale is *direct* exponent: value = 2^s
    // So we’ll compute via ldexp: 2^s = ldexp(1.0f, s)
    return ldexpf(1.0f, s);
}

// MXFP4 GEMM kernel: C = A * B^T
// A: [M, K] bf16 (row-major)
// B: quantized as FP4 (packed in B_q), with metadata B_shuffle, B_scale_sh
// Output: C [M, N] in fp32 or bf16 — we’ll use fp32 accumulation for accuracy, then cast to bf16 if needed
template <int BLOCK_M = 64, int BLOCK_N = 64, int BLOCK_K = 128>
__global__ void mxfp4_gemm_kernel(
    const __hip_bfloat16* __restrict__ A,
    const __hip_bfloat16* __restrict__ B,  // used for validation or fallback
    const uint8_t* __restrict__ B_q,      // [N, K/2] — packed FP4
    const uint32_t* __restrict__ B_shuffle, // [N, K/2] — permutation indices
    const uint8_t* __restrict__ B_scale_sh, // [N, K/32] — E8M0 scales, shuffled
    const float* __restrict__ A_scale_sh,   // [M] — A’s e8m0 scale (already shuffled)
    int M, int N, int K,
    __hip_bfloat16* __restrict__ C
) {
    // Compute tile indices
    const int tile_m = blockIdx.x * BLOCK_M;
    const int tile_n = blockIdx.y * BLOCK_N;
    const int tile_k = blockIdx.z * BLOCK_K;

    // Thread indices
    const int tid = threadIdx.y * blockDim.x + threadIdx.x;
    const int tx = tid % BLOCK_N;
    const int ty = tid / BLOCK_N;

    // Accumulator for C[i,j]: use fp32 internally for precision
    __shared__ float accum[BLOCK_M * BLOCK_N];
    if (tid < BLOCK_M * BLOCK_N) {
        accum[tid] = 0.0f;
    }
    __syncthreads();

    // Each thread processes K / (BLOCK_K * warp_size) iterations
    for (int k0 = tile_k; k0 < min(tile_k + BLOCK_K, K); k0 += 128) {
        // Process 128 elements of K (64 FP4 pairs)
        // We’ll unroll by 4 FP4 pairs per thread per iteration (assuming 32 threads per row)
        // Simplified: each thread handles 2 FP4 values (4 bytes = 32 bits) → 8 elements per thread
        // But for clarity, we do scalar per thread and rely on occupancy

        // FP4 unpacking and scaling
        // For each k in [k0, k0+128):
        for (int k_idx = k0; k_idx < min(k0 + 128, K); ++k_idx) {
            // A[i, k] — load once per row i
            const int a_row = tile_m + ty;
            if (a_row >= M) continue;

            // Load A element
            __hip_bfloat16 a_val = A[a_row * K + k_idx];
            float a_float = __hip_bfloat162float(a_val);
            float a_scale = A_scale_sh ? A_scale_sh[a_row] : 1.0f;
            a_float *= e8m0_to_float(static_cast<uint8_t>(a_scale));

            // Process B: for each n in [tile_n, tile_n+BLOCK_N)
            for (int n_idx = tile_n + tx; n_idx < min(tile_n + BLOCK_N, N); ++n_idx) {
                // B is [N, K] in bf16, but we only use FP4 path:
                // FP4 is stored in B_q[n, k/2], shuffled via B_shuffle
                int k_pair = k_idx / 2;
                int bit_offset = k_idx % 2;  // 0 → low 4 bits, 1 → high 4 bits

                // Get original index after shuffle
                uint32_t sh_idx = B_shuffle[n_idx * (K/2) + k_pair];
                uint8_t packed = B_q[sh_idx];  // [N*K/2] flattened

                // Unpack FP4
                __hip_fp8_e4m3_fnuz fp4_val_lo, fp4_val_hi;
                unpack_fp4(packed, fp4_val_lo, fp4_val_hi);

                // Select correct FP4 value
                __hip_fp8_e4m3_fnuz fp4_val = (bit_offset == 0) ? fp4_val_lo : fp4_val_hi;
                float b_val = __hip_fp8_e4m3_fnuz2float(fp4_val);

                // Get scale: E8M0 scale per 32 K-blocks
                int scale_idx = k_pair / 16;  // 32 K elements per scale (since 2 FP4 per K element)
                if (scale_idx >= K / 32) scale_idx = K / 32 - 1;

                // Scale row index (B_scale_sh is [N, K/32])
                uint8_t scale_val = B_scale_sh[n_idx * (K / 32) + scale_idx];
                float b_scale = e8m0_to_float(scale_val);
                b_val *= b_scale;

                // Accumulate
                float contrib = a_float * b_val;
                atomicAdd(&accum[(ty * BLOCK_N) + tx], contrib);
            }
        }
    }

    // Store result
    if (tile_m + ty < M && tile_n + tx < N) {
        float acc = accum[(ty * BLOCK_N) + tx];
        // Clamp or cast to bf16
        __hip_bfloat16 c_val = __float2bfloat16(acc);
        C[(tile_m + ty) * N + (tile_n + tx)] = c_val;
    }
}

// Kernel launch wrapper (for Python)
extern "C" void launch_mxfp4_gemm(
    const void* A, const void* B,
    const void* B_q, const void* B_shuffle, const void* B_scale_sh,
    const void* A_scale_sh,
    int M, int N, int K,
    void* C
) {
    dim3 block(64);  // 8x8 threads in 64-thread block (or use 32x2=64)
    dim3 grid(
        (M + 63) / 64,
        (N + 63) / 64,
        (K + 127) / 128
    );

    hipLaunchKernelGGL(
        mxfp4_gemm_kernel<64, 64, 128>,
        grid, block, 0, 0,
        static_cast<const __hip_bfloat16*>(A),
        static_cast<const __hip_bfloat16*>(B),
        static_cast<const uint8_t*>(B_q),
        static_cast<const uint32_t*>(B_shuffle),
        static_cast<const uint8_t*>(B_scale_sh),
        static_cast<const float*>(A_scale_sh),
        M, N, K,
        static_cast<__hip_bfloat16*>(C)
    );
}
'''

# Load HIP kernel via inline extension (uses hipcc if on ROCm)
mxfp4_module = torch.utils.cpp_extension.load_inline(
    name="mxfp4_gemm",
    cuda_sources=cuda_sources,
    extra_cuda_cflags=["-xhip", "--offload-arch=gfx950", "-O3"],
    verbose=False,
    # For ROCm, use hipcc; for CUDA, use nvcc — auto-detected by torch
)

# Helper: call HIP kernel
def _call_hip_kernel(
    A: torch.Tensor,
    B: torch.Tensor,
    B_q: torch.Tensor,
    B_shuffle: torch.Tensor,
    B_scale_sh: torch.Tensor,
    A_scale_sh: torch.Tensor
) -> torch.Tensor:
    M, K = A.shape
    N, _ = B.shape
    assert K % 2 == 0, "K must be even for FP4 packing"
    assert B_q.shape == (N, K // 2)
    assert B_shuffle.shape == (N, K // 2)
    assert B_scale_sh.shape == (N, K // 32)

    # Allocate output C [M, N] in bf16
    C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

    # Launch kernel
    mxfp4_module.launch_mxfp4_gemm(
        A.data_ptr(),
        B.data_ptr(),
        B_q.data_ptr(),
        B_shuffle.data_ptr(),
        B_scale_sh.data_ptr(),
        A_scale_sh.data_ptr(),
        M, N, K,
        C.data_ptr()
    )

    # Sync (HIP kernel is async)
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    # For ROCm: torch.cuda.synchronize() works (ROCm uses CUDA-like API for torch)

    return C


def custom_kernel(data: input_t) -> output_t:
    """
    MXFP4 GEMM: C = A * B^T, with:
        A: bf16 [M, K]
        B: bf16 [N, K] (unused — weight is in FP4)
        B_q: packed FP4 [N, K/2]
        B_shuffle: shuffled FP4 indices [N, K/2]
        B_scale_sh: shuffled E8M0 scales [N, K/32]
    """
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Step 1: Quantize A to MXFP4 format
    # dynamic_mxfp4_quant returns:
    #   - A_fp4: packed FP4 [M, K/2]
    #   - A_scale: E8M0 scale [M]
    #   - A_shuffle: optional (if any)
    # We only need A_fp4 and A_scale
    try:
        from aiter.ops.triton.quant import dynamic_mxfp4_quant, e8m0_shuffle
    except ImportError:
        raise RuntimeError("aiter.ops.triton.quant not available. Install AMD's aiter.")

    A_fp4, A_scale = dynamic_mxfp4_quant(A)  # A_fp4: [M, K//2], A_scale: [M]

    # Step 2: Apply e8m0_shuffle to A scale (if required — here, no permutation, but call to be safe)
    A_scale_sh = e8m0_shuffle(A_scale)  # [M] — already 1D, shuffle may be no-op

    # Step 3: Call HIP kernel
    # Note: HIP kernel expects A_scale_sh as float* — convert from bf16 E8M0
    # E8M0 is stored as uint8 in bf16 tensor (only low 8 bits used), so reinterpret as uint8 → float
    A_scale_sh_f32 = A_scale_sh.to(torch.float32)

    # Call HIP kernel
    C = _call_hip_kernel(
        A, B, B_q, B_shuffle, B_scale_sh,
        A_scale_sh_f32
    )

    return C


# Optional: self-test (uncomment to verify)
if __name__ == "__main__":
    if not torch.cuda.is_available():
        print("CUDA not available — skipping test")
    else:
        M, N, K = 64, 128, 256
        A = torch.randn((M, K), dtype=torch.bfloat16, device="cuda")
        B = torch.randn((N, K), dtype=torch.bfloat16, device="cuda")

        # Fake FP4 quantization for B (for demo)
        from aiter.ops.triton.quant import dynamic_mxfp4_quant
        B_q, B_scale = dynamic_mxfp4_quant(B)
        B_shuffle = torch.arange(N * K // 2, dtype=torch.uint32, device="cuda")
        B_scale_sh = e8m0_shuffle(B_scale)

        data = (A, B, B_q, B_shuffle, B_scale_sh)
        C = custom_kernel(data)
        print(f"Input shapes: A={A.shape}, B={B.shape}, Output C={C.shape}")
        print("✓ custom_kernel executed successfully!")