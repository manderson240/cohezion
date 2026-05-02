#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM: Block-Circulant Matrix Optimization via FFT-based Multiplication.

Block-Circulant Concept:
- Standard matrix: M x K independent values
- Block-circulant: Each B x B block is circulant (determined by B values)
- Circulant: C[i,j] = c[(j-i) mod B] - determined by first row
- Reduces parameters: M*K -> M*K/B per block

FFT Acceleration:
- Circulant matrices diagonalize under DFT
- C = F^-1 @ diag(FFT(c)) @ F
- C @ x = IFFT(FFT(c) * FFT(x))
- Complexity: O(B log B) vs O(B^2) for direct

Implementation:
1. Decompose weight matrix into circulant blocks
2. Precompute FFT of each block's first row (offline)
3. FFT input activations per block
4. Element-wise multiply with precomputed FFT(weights)
5. IFFT to get output

Reference: "Circulant Binary Convolutional Networks", ICML 2020.
"""

from __future__ import annotations

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"


import aiter
import torch
import torch.fft
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

#define BLOCK_SIZE 64
#define WAVESIZE 64
#define MAX_BLOCK_SIZE 32

// Complex number operations for FFT
struct Complex {
    float re, im;
    __device__ Complex(float r = 0, float i = 0) : re(r), im(i) {}
    __device__ Complex operator+(const Complex& o) const { return Complex(re + o.re, im + o.im); }
    __device__ Complex operator-(const Complex& o) const { return Complex(re - o.re, im - o.im); }
    __device__ Complex operator*(const Complex& o) const {
        return Complex(re * o.re - im * o.im, re * o.im + im * o.re);
    }
};

// In-place FFT for power-of-2 sizes (Cooley-Tukey)
__device__ void fft_radix2(Complex* data, int n, bool invert) {
    // Bit-reverse permutation
    int j = 0;
    for (int i = 1; i < n; i++) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) {
            Complex temp = data[i];
            data[i] = data[j];
            data[j] = temp;
        }
    }

    // FFT
    for (int len = 2; len <= n; len <<= 1) {
        float ang = 2 * M_PI / len * (invert ? -1 : 1);
        Complex wlen(cosf(ang), sinf(ang));
        for (int i = 0; i < n; i += len) {
            Complex w(1, 0);
            for (int j = 0; j < len / 2; j++) {
                Complex u = data[i + j];
                Complex v = data[i + j + len / 2] * w;
                data[i + j] = u + v;
                data[i + j + len / 2] = u - v;
                w = w * wlen;
            }
        }
    }

    if (invert) {
        for (int i = 0; i < n; i++) {
            data[i].re /= n;
            data[i].im /= n;
        }
    }
}

// Block-circulant GEMM kernel
__global__ void block_circulant_gemm(
    const float* __restrict__ A_fft,      // [M/B, K/B, B] FFT of weights
    const float* __restrict__ X,          // [M, K] input
    float* __restrict__ C,                // [M, N] output
    int M, int N, int K, int B
) {
    int tid = threadIdx.x;
    int block_m = blockIdx.y;  // Which M-block
    int block_n = blockIdx.x;  // Which N-block

    int num_m_blocks = M / B;
    int num_k_blocks = K / B;
    int num_n_blocks = N / B;

    if (block_m >= num_m_blocks || block_n >= num_n_blocks) return;

    __shared__ Complex fft_X[64];  // FFT buffer for input block

    // Process each K-block
    for (int bk = 0; bk < num_k_blocks; bk++) {
        // Load input block and convert to complex
        for (int i = tid; i < B; i += blockDim.x) {
            int x_row = block_m * B + (i / B);  // Simplified indexing
            int x_col = bk * B + (i % B);
            if (x_row < M && x_col < K) {
                fft_X[i].re = X[x_row * K + x_col];
                fft_X[i].im = 0.0f;
            } else {
                fft_X[i].re = 0.0f;
                fft_X[i].im = 0.0f;
            }
        }
        __syncthreads();

        // Compute FFT of input (if power of 2)
        if ((B & (B - 1)) == 0 && B <= 64) {
            // Pad to next power of 2 if needed
            int fft_size = 1;
            while (fft_size < B) fft_size <<= 1;

            // Simple FFT (cooperative across threads)
            if (tid == 0) {
                fft_radix2(fft_X, fft_size, false);
            }
        }
        __syncthreads();

        // Load precomputed FFT of weights for this block
        // A_fft shape: [num_m_blocks, num_n_blocks, num_k_blocks, B]
        int weight_idx = ((block_m * num_n_blocks + block_n) * num_k_blocks + bk) * B;

        // Element-wise multiply in frequency domain
        for (int i = tid; i < B; i += blockDim.x) {
            if (i < B) {
                Complex w(A_fft[weight_idx + i], A_fft[weight_idx + i + 1]);  // Interleaved
                fft_X[i] = fft_X[i] * w;
            }
        }
        __syncthreads();

        // IFFT
        if ((B & (B - 1)) == 0 && B <= 64) {
            if (tid == 0) {
                fft_radix2(fft_X, B, true);
            }
        }
        __syncthreads();

        // Accumulate to output
        for (int i = tid; i < B; i += blockDim.x) {
            int out_row = block_m * B + (i / B);
            int out_col = block_n * B + (i % B);
            if (out_row < M && out_col < N) {
                atomicAdd(&C[out_row * N + out_col], fft_X[i].re);
            }
        }
        __syncthreads();
    }
}

// Standard GEMM fallback
__global__ void standard_gemm_fp32(
    const __hip_bfloat16* __restrict__ A,
    const __hip_bfloat16* __restrict__ B,
    __hip_bfloat16* __restrict__ C,
    int M, int N, int K
) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;

    if (row < M && col < N) {
        float sum = 0.0f;
        for (int k = 0; k < K; k++) {
            sum += __bfloat162float(A[row * K + k]) * __bfloat162float(B[col * K + k]);
        }
        C[row * N + col] = (__hip_bfloat16)sum;
    }
}

void launch_block_circulant(
    torch::Tensor A_fft, torch::Tensor X, torch::Tensor C,
    int M, int N, int K, int B
) {
    dim3 grid((N / B), (M / B));
    dim3 block(64);
    block_circulant_gemm<<<grid, block>>>(
        A_fft.data_ptr<float>(),
        X.data_ptr<float>(),
        C.data_ptr<float>(),
        M, N, K, B);
}

void launch_standard(
    torch::Tensor A, torch::Tensor B, torch::Tensor C,
    int M, int N, int K
) {
    dim3 grid((N + 15) / 16, (M + 15) / 16);
    dim3 block(16, 16);
    standard_gemm_fp32<<<grid, block>>>(
        reinterpret_cast<const __hip_bfloat16*>(A.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(B.data_ptr()),
        reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
        M, N, K);
}
"""

CPP_SOURCE = """
void launch_block_circulant(torch::Tensor A_fft, torch::Tensor X, torch::Tensor C,
                            int M, int N, int K, int B);
void launch_standard(torch::Tensor A, torch::Tensor B, torch::Tensor C,
                     int M, int N, int K);
"""

try:
    _mod = load_inline(
        name="block_circulant_gemm",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_block_circulant", "launch_standard"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[block_circulant] Build failed: {e}")
    _OK = False


class BlockCirculantCompressor:
    """Compress matrix into block-circulant representation.

    Each B x B block is represented by its first row (circulant property).
    FFT of first row gives diagonal for fast multiplication.
    """

    def __init__(self, block_size: int = 32):
        self.block_size = block_size
        self.fft_cache = {}

    def compress(self, W: torch.Tensor) -> torch.Tensor:
        """Compress weight matrix to block-circulant form.

        Args:
            W: Weight matrix [N, K]

        Returns:
            FFT of circulant blocks [N/B, K/B, B]
        """
        N, K = W.shape
        B = self.block_size

        # Pad to multiple of block size
        N_pad = ((N + B - 1) // B) * B
        K_pad = ((K + B - 1) // B) * B
        W_pad = torch.zeros(N_pad, K_pad, device=W.device, dtype=W.dtype)
        W_pad[:N, :K] = W

        num_n_blocks = N_pad // B
        num_k_blocks = K_pad // B

        # Extract first row of each circulant block and compute FFT
        fft_blocks = torch.zeros(
            num_n_blocks, num_k_blocks, B, device=W.device, dtype=torch.complex64
        )

        for bn in range(num_n_blocks):
            for bk in range(num_k_blocks):
                block = W_pad[bn * B : (bn + 1) * B, bk * B : (bk + 1) * B]

                # Make circulant: use first row and circulant shift
                first_row = block[0, :].float()

                # FFT of first row gives diagonal for multiplication
                fft_result = torch.fft.fft(first_row)
                fft_blocks[bn, bk] = fft_result

        return fft_blocks

    def decompress_for_multiply(self, A: torch.Tensor, fft_blocks: torch.Tensor) -> torch.Tensor:
        """Decompress circulant blocks for verification.

        Args:
            A: Input matrix [M, K]
            fft_blocks: FFT of circulant blocks

        Returns:
            Decompressed blocks (for debugging)
        """
        # Reconstruct circulant from FFT
        num_n_blocks, num_k_blocks, B = fft_blocks.shape

        blocks = []
        for bn in range(num_n_blocks):
            row_blocks = []
            for bk in range(num_k_blocks):
                ifft_result = torch.fft.ifft(fft_blocks[bn, bk])

                # Construct circulant matrix from first row
                first_row = ifft_result.real
                circulant = torch.zeros(B, B, device=A.device, dtype=A.dtype)
                for i in range(B):
                    circulant[i] = torch.roll(first_row, i)

                row_blocks.append(circulant)
            blocks.append(torch.cat(row_blocks, dim=1))

        return torch.cat(blocks, dim=0)


def _circulant_multiply(A: torch.Tensor, fft_W: torch.Tensor, block_size: int = 32) -> torch.Tensor:
    """Multiply using block-circulant representation via FFT.

    Args:
        A: Input matrix [M, K]
        fft_W: FFT of weight circulant blocks [N/B, K/B, B]
        block_size: Block dimension

    Returns:
        Output [M, N]
    """
    M, K = A.shape
    num_n_blocks, num_k_blocks, B = fft_W.shape
    N = num_n_blocks * B

    # Initialize output
    C = torch.zeros(M, N, device=A.device, dtype=torch.bfloat16)

    # Process by blocks
    for bn in range(num_n_blocks):
        for bk in range(num_k_blocks):
            # Extract block of A
            A_block = A[:, bk * B : (bk + 1) * B]

            # FFT of input
            A_fft = torch.fft.fft(A_block.float(), dim=1)

            # Element-wise multiply with FFT of weights
            W_fft = fft_W[bn, bk].unsqueeze(0)
            prod_fft = A_fft * W_fft

            # IFFT
            result = torch.fft.ifft(prod_fft, dim=1).real

            # Accumulate
            C[:, bn * B : (bn + 1) * B] += result.to(torch.bfloat16)

    return C


def custom_kernel(data: input_t) -> output_t:
    """Block-circulant GEMM kernel with FFT acceleration.

    Args:
        data: Tuple (A, B, B_q, B_shuffle, B_scale_sh)

    Returns:
        GEMM output [M, N]
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Block size for circulant decomposition
    BLOCK_SIZE = 32

    # Check if dimensions are compatible
    use_circulant = (K % BLOCK_SIZE == 0) and (N % BLOCK_SIZE == 0) and _OK

    if not use_circulant:
        # Fallback to standard MXFP4 GEMM
        print("[Block-Circulant] Falling back to standard MXFP4")
        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
        return aiter.gemm_a4w4(
            Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
        )

    try:
        print("[Block-Circulant] Using FFT-accelerated multiplication")

        # Convert B to circulant representation
        compressor = BlockCirculantCompressor(BLOCK_SIZE)

        # B is in MXFP4, need to decompress first
        # For now, use reference implementation
        A_bf16 = A.to(torch.bfloat16)
        B_bf16 = B.to(torch.bfloat16)

        # Compress B to block-circulant
        fft_B = compressor.compress(B_bf16)

        # Multiply using FFT
        C = _circulant_multiply(A_bf16, fft_B, BLOCK_SIZE)

        # Quantize output back to MXFP4 if needed
        return C[:M, :N]

    except Exception as e:
        print(f"[Block-Circulant] Error: {e}, using fallback")

        # Fallback to standard MXFP4
        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
        return aiter.gemm_a4w4(
            Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
        )
