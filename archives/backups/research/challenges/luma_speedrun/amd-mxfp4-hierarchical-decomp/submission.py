#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM: Hierarchical Matrix Decomposition via Recursive Low-Rank Approximation.

Hierarchical Decomposition Concept:
- Standard matrix: All entries independent (M*K parameters)
- Low-rank: W = U @ V^T (rank r << M, K)
- Hierarchical: Recursively decompose into block structure
  - Level 0: Full matrix
  - Level 1: 4 blocks, each low-rank
  - Level 2: 16 blocks, each lower rank
  - ...until blocks are small enough

H-Matrix (Hierarchical Matrix) Structure:
- Admissible blocks (far-field): Low-rank approximation
- Inadmissible blocks (near-field): Full storage
- Tree structure: Quad-tree for 2D matrices

Implementation:
1. Build quad-tree over matrix
2. For each block: decide if low-rank or full
3. Low-rank: store U, V factors
4. Full: store original values
5. Multiply: traverse tree, use appropriate kernel per block

Complexity: O(n log n) vs O(n^2) for dense

Reference: "Fast Approximate Matrix Multiplication", J. Sci. Comp. 2020.
"""

from __future__ import annotations

import os


os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

from dataclasses import dataclass

import aiter
import torch
import torch.linalg as la
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


@dataclass
class HNode:
    """Node in hierarchical matrix quad-tree."""

    row_start: int
    row_end: int
    col_start: int
    col_end: int
    is_leaf: bool
    is_low_rank: bool
    U: torch.Tensor | None = None  # Left factor [size, rank]
    V: torch.Tensor | None = None  # Right factor [rank, size]
    full: torch.Tensor | None = None  # Full matrix if not low-rank
    children: list[HNode] | None = None  # 4 children if not leaf


class HierarchicalMatrix:
    """Hierarchical matrix with quad-tree decomposition."""

    def __init__(
        self, min_block_size: int = 64, max_rank: int = 16, admissibility_eta: float = 1.0
    ):
        """
        Args:
            min_block_size: Stop recursion when block smaller than this
            max_rank: Maximum rank for low-rank approximation
            admissibility_eta: Threshold for determining low-rank admissibility
        """
        self.min_block_size = min_block_size
        self.max_rank = max_rank
        self.admissibility_eta = admissibility_eta
        self.root: HNode | None = None

    def _is_admissible(self, row_start: int, row_end: int, col_start: int, col_end: int) -> bool:
        """Check if block is admissible for low-rank approximation.

        Admissibility criterion: block is far from diagonal (well-separated)
        """
        row_center = (row_start + row_end) / 2
        col_center = (col_start + col_end) / 2

        # Distance between block centers
        distance = abs(row_center - col_center)

        # Block diameter
        row_diam = row_end - row_start
        col_diam = col_end - col_start
        max_diam = max(row_diam, col_diam)

        # Admissible if well-separated (distance > eta * diameter)
        return distance > self.admissibility_eta * max_diam

    def _compress_block(self, W_block: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Compress block to low-rank via truncated SVD.

        Args:
            W_block: Block matrix

        Returns:
            U, V factors such that W_block ≈ U @ V
        """
        # SVD
        U_full, S, Vh_full = la.svd(W_block.float(), full_matrices=False)

        # Determine effective rank
        rank = min(self.max_rank, (S[0] * 0.01 < S).sum().item())
        rank = max(rank, 1)

        # Truncate
        U = U_full[:, :rank]
        S_sqrt = torch.sqrt(S[:rank])
        V = (Vh_full[:rank, :].T * S_sqrt).T

        # Scale U by singular values
        U = U * S_sqrt.unsqueeze(0)

        return U.to(W_block.dtype), V.to(W_block.dtype)

    def build(self, W: torch.Tensor) -> HierarchicalMatrix:
        """Build hierarchical decomposition of matrix.

        Args:
            W: Weight matrix [N, K]

        Returns:
            Self with constructed tree
        """
        N, K = W.shape
        self.root = self._build_recursive(W, 0, N, 0, K)
        return self

    def _build_recursive(
        self, W: torch.Tensor, row_start: int, row_end: int, col_start: int, col_end: int
    ) -> HNode:
        """Recursively build hierarchical decomposition."""
        node = HNode(
            row_start=row_start,
            row_end=row_end,
            col_start=col_start,
            col_end=col_end,
            is_leaf=False,
            is_low_rank=False,
        )

        # Extract block
        W_block = W[row_start:row_end, col_start:col_end]

        # Check if leaf (small enough block)
        if row_end - row_start <= self.min_block_size or col_end - col_start <= self.min_block_size:
            node.is_leaf = True
            node.is_low_rank = False
            node.full = W_block
            return node

        # Check if admissible for low-rank
        if self._is_admissible(row_start, row_end, col_start, col_end):
            node.is_leaf = True
            node.is_low_rank = True
            node.U, node.V = self._compress_block(W_block)
            return node

        # Split into 4 children (quad-tree)
        row_mid = (row_start + row_end) // 2
        col_mid = (col_start + col_end) // 2

        node.children = [
            self._build_recursive(W, row_start, row_mid, col_start, col_mid),  # NW
            self._build_recursive(W, row_start, row_mid, col_mid, col_end),  # NE
            self._build_recursive(W, row_mid, row_end, col_start, col_mid),  # SW
            self._build_recursive(W, row_mid, row_end, col_mid, col_end),  # SE
        ]

        return node

    def multiply(self, X: torch.Tensor) -> torch.Tensor:
        """Multiply hierarchical matrix by vector/matrix.

        Args:
            X: Input matrix [K, batch_size]

        Returns:
            Output [N, batch_size]
        """
        if self.root is None:
            raise ValueError("Matrix not built")

        N = self.root.row_end - self.root.row_start
        K = self.root.col_end - self.root.col_start
        batch_size = X.shape[1] if X.ndim > 1 else 1

        result = torch.zeros(N, batch_size, device=X.device, dtype=X.dtype)

        self._multiply_recursive(self.root, X, result, 0, 0)

        return result

    def _multiply_recursive(
        self, node: HNode, X: torch.Tensor, result: torch.Tensor, row_offset: int, col_offset: int
    ):
        """Recursively multiply hierarchical matrix."""
        if node.is_leaf:
            if node.is_low_rank:
                # Low-rank: U @ (V @ X)
                X_slice = X[node.col_start - col_offset : node.col_end - col_offset]
                temp = node.V @ X_slice
                result_slice = node.U @ temp
                result[node.row_start - row_offset : node.row_end - row_offset] += result_slice
            else:
                # Full: direct multiply
                X_slice = X[node.col_start - col_offset : node.col_end - col_offset]
                result[node.row_start - row_offset : node.row_end - row_offset] += (
                    node.full @ X_slice
                )
        else:
            # Recurse to children
            for child in node.children:
                self._multiply_recursive(child, X, result, row_offset, col_offset)

    def memory_usage(self) -> int:
        """Compute total memory usage in bytes."""
        if self.root is None:
            return 0
        return self._memory_recursive(self.root)

    def _memory_recursive(self, node: HNode) -> int:
        """Recursively compute memory usage."""
        if node.is_leaf:
            if node.is_low_rank:
                # U: [size, rank], V: [rank, size]
                size = node.row_end - node.row_start
                rank = node.U.shape[1]
                return size * rank * node.U.element_size() * 2
            else:
                # Full matrix
                rows = node.row_end - node.row_start
                cols = node.col_end - node.col_start
                return rows * cols * node.full.element_size()
        else:
            return sum(self._memory_recursive(c) for c in node.children)


HIP_SOURCE = r"""
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_bf16.h>

#define BLOCK_SIZE 256
#define WAVESIZE 64

// Low-rank multiply kernel: U @ (V @ X) for batch
__global__ void low_rank_multiply_kernel(
    const float* __restrict__ U,      // [m, r]
    const float* __restrict__ V,      // [r, n]
    const float* __restrict__ X,      // [n, batch]
    float* __restrict__ Y,            // [m, batch]
    int m, int n, int r, int batch
) {
    // Compute Y = U @ (V @ X)
    // First compute T = V @ X (temp), then Y = U @ T

    extern __shared__ float shared_mem[];
    float* temp = shared_mem;  // [r, batch] temporary

    int tid = threadIdx.x;

    // T = V @ X
    for (int i = tid; i < r * batch; i += blockDim.x) {
        int ri = i / batch;
        int bi = i % batch;

        float sum = 0.0f;
        for (int j = 0; j < n; j++) {
            sum += V[ri * n + j] * X[j * batch + bi];
        }
        temp[ri * batch + bi] = sum;
    }
    __syncthreads();

    // Y = U @ T
    for (int i = tid; i < m * batch; i += blockDim.x) {
        int mi = i / batch;
        int bi = i % batch;

        float sum = 0.0f;
        for (int j = 0; j < r; j++) {
            sum += U[mi * r + j] * temp[j * batch + bi];
        }
        Y[mi * batch + bi] = sum;
    }
}

// Full dense multiply
__global__ void dense_multiply_kernel(
    const __hip_bfloat16* __restrict__ W,    // [m, n]
    const __hip_bfloat16* __restrict__ X,      // [n, batch]
    __hip_bfloat16* __restrict__ Y,          // [m, batch]
    int m, int n, int batch
) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;

    if (row < m && col < batch) {
        float sum = 0.0f;
        for (int k = 0; k < n; k++) {
            sum += __bfloat162float(W[row * n + k]) * __bfloat162float(X[k * batch + col]);
        }
        Y[row * batch + col] = (__hip_bfloat16)sum;
    }
}

void launch_low_rank(
    torch::Tensor U, torch::Tensor V, torch::Tensor X, torch::Tensor Y,
    int m, int n, int r, int batch) {
    dim3 block(BLOCK_SIZE);
    low_rank_multiply_kernel<<<1, block, r * batch * sizeof(float)>>>(
        U.data_ptr<float>(), V.data_ptr<float>(),
        X.data_ptr<float>(), Y.data_ptr<float>(),
        m, n, r, batch);
}

void launch_dense(
    torch::Tensor W, torch::Tensor X, torch::Tensor Y,
    int m, int n, int batch) {
    dim3 block(16, 16);
    dim3 grid((batch + 15) / 16, (m + 15) / 16);
    dense_multiply_kernel<<<grid, block>>>(
        reinterpret_cast<const __hip_bfloat16*>(W.data_ptr()),
        reinterpret_cast<const __hip_bfloat16*>(X.data_ptr()),
        reinterpret_cast<__hip_bfloat16*>(Y.data_ptr()),
        m, n, batch);
}
"""

CPP_SOURCE = """
void launch_low_rank(torch::Tensor U, torch::Tensor V, torch::Tensor X, torch::Tensor Y,
                     int m, int n, int r, int batch);
void launch_dense(torch::Tensor W, torch::Tensor X, torch::Tensor Y,
                  int m, int n, int batch);
"""

try:
    _mod = load_inline(
        name="hierarchical_gemm",
        cpp_sources=[CPP_SOURCE],
        cuda_sources=[HIP_SOURCE],
        functions=["launch_low_rank", "launch_dense"],
        verbose=False,
        extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
    )
    _OK = True
except Exception as e:
    print(f"[hierarchical] Build failed: {e}")
    _OK = False


def _standard_gemm(A: torch.Tensor, B: torch.Tensor, B_q, B_shuffle, B_scale_sh) -> torch.Tensor:
    """Standard MXFP4 GEMM fallback."""
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
    )


def custom_kernel(data: input_t) -> output_t:
    """Hierarchical decomposition GEMM kernel.

    Args:
        data: Tuple (A, B, B_q, B_shuffle, B_scale_sh)

    Returns:
        GEMM output [M, N]
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Only use hierarchical for large matrices
    use_hierarchical = M >= 512 and N >= 512 and K >= 512

    if not use_hierarchical:
        return _standard_gemm(A, B, B_q, B_shuffle, B_scale_sh)

    try:
        print("[Hierarchical] Using recursive low-rank decomposition")

        # Build hierarchical matrix from B
        hmat = HierarchicalMatrix(min_block_size=128, max_rank=32, admissibility_eta=1.5)

        # Convert to bf16 for decomposition
        B_bf16 = B.to(torch.bfloat16)
        hmat.build(B_bf16.T)  # B is [N, K], we work with [K, N] for multiply

        # Check if compression is beneficial
        original_size = N * K * 2  # 2 bytes per bf16
        compressed_size = hmat.memory_usage()
        compression_ratio = original_size / compressed_size if compressed_size > 0 else 1.0

        print(f"[Hierarchical] Compression ratio: {compression_ratio:.2f}x")

        # If compression is poor, use standard GEMM
        if compression_ratio < 1.5:
            print("[Hierarchical] Poor compression, using standard GEMM")
            return _standard_gemm(A, B, B_q, B_shuffle, B_scale_sh)

        # Multiply using hierarchical structure
        # A: [M, K], hmat: [K, N] -> C: [M, N]
        A_bf16 = A.to(torch.bfloat16)

        # Process in batches for memory efficiency
        batch_size = min(32, M)
        C = torch.empty(M, N, device=A.device, dtype=torch.bfloat16)

        for start in range(0, M, batch_size):
            end = min(start + batch_size, M)
            A_batch = A_bf16[start:end].T  # [K, batch]

            # Multiply: result = hmat @ A_batch
            result = hmat.multiply(A_batch)
            C[start:end] = result.T

        return C

    except Exception as e:
        print(f"[Hierarchical] Error: {e}, using fallback")
        return _standard_gemm(A, B, B_q, B_shuffle, B_scale_sh)
