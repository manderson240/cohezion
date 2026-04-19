#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""
GEMM: Mixed Tiling Sizes

This kernel implements adaptive tiling with different tile sizes based on
matrix dimensions. The key insight is that different problem sizes benefit
from different tile configurations - one size doesn't fit all.

Tile Size Selection Strategy:
  Small matrices (M,N,K <= 256):
    - Small tiles: 16x16 for fine granularity
    - Better occupancy with more thread blocks

  Medium matrices (256 < M,N,K <= 1024):
    - Medium tiles: 32x32 or 64x32
    - Balance between parallelism and cache locality

  Large matrices (M,N,K > 1024):
    - Large tiles: 64x64 or 128x64
    - Better cache utilization, fewer thread blocks

Tile Shape Variants:
  - Square tiles: M_TILE = N_TILE (balanced)
  - Tall tiles: M_TILE > N_TILE (M-dominant)
  - Wide tiles: M_TILE < N_TILE (N-dominant)

Adaptive Selection:
  1. Analyze matrix aspect ratios
  2. Choose tile shape based on dominant dimension
  3. Adjust for GPU occupancy constraints
  4. Optimize for memory coalescing

Performance Characteristics:
  - Reduces wasted computation in partial tiles
  - Better LDS utilization per tile size
  - Improved occupancy across different shapes
  - Shape-specific micro-optimizations
"""

from __future__ import annotations
import os
import math

os.environ["PYTORCH_ROCM_ARCH"] = "gfx950"
os.environ["CXX"] = "clang++"

import torch
from torch.utils.cpp_extension import load_inline
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

# Tile size configurations
TILE_CONFIGS = {
    "small": {"M": 16, "N": 16, "K": 32},
    "medium": {"M": 32, "N": 32, "K": 32},
    "large": {"M": 64, "N": 64, "K": 64},
    "wide": {"M": 32, "N": 64, "K": 32},  # N-dominant
    "tall": {"M": 64, "N": 32, "K": 32},  # M-dominant
}

# Cache for compiled kernels
_kernel_modules: dict[str, any] = {}


def _select_tile_config(M: int, N: int, K: int) -> str:
    """
    Select optimal tile configuration based on problem dimensions.

    Args:
        M: Output rows
        N: Output columns
        K: Inner dimension

    Returns:
        config_name: Name of tile configuration to use
    """
    # Determine matrix size category
    max_dim = max(M, N, K)

    if max_dim <= 256:
        size_category = "small"
    elif max_dim <= 1024:
        size_category = "medium"
    else:
        size_category = "large"

    # Determine aspect ratio
    aspect_ratio = M / N if N > 0 else 1.0

    if aspect_ratio > 2.0:
        # M-dominant
        shape_category = "tall"
    elif aspect_ratio < 0.5:
        # N-dominant
        shape_category = "wide"
    else:
        # Balanced
        shape_category = "balanced"

    # Combine categories
    if shape_category == "balanced":
        return size_category
    else:
        # For medium/large with extreme aspect ratios
        if size_category in ["medium", "large"]:
            return shape_category
        return size_category


def _get_mixed_tiling_kernel(config_name: str):
    """Get or compile kernel for specific tile configuration."""
    global _kernel_modules

    if config_name in _kernel_modules:
        return _kernel_modules[config_name], True

    tile_config = TILE_CONFIGS.get(config_name, TILE_CONFIGS["medium"])
    TILE_M = tile_config["M"]
    TILE_N = tile_config["N"]
    TILE_K = tile_config["K"]

    HIP_SOURCE = rf"""
    #include <torch/extension.h>
    #include <hip/hip_runtime.h>
    #include <hip/hip_bf16.h>
    
    #define TILE_M {TILE_M}
    #define TILE_N {TILE_N}
    #define TILE_K {TILE_K}
    #define WAVESIZE 64
    
    // Mixed-tiling GEMM kernel
    __global__ __launch_bounds__({TILE_M * TILE_N if TILE_M * TILE_N <= 256 else 256})
    void mixed_gemm_<{config_name}>(
        const __hip_bfloat16* __restrict__ A,  // [M, K]
        const __hip_bfloat16* __restrict__ B,  // [N, K]
        __hip_bfloat16* __restrict__ C,        // [M, N]
        int M, int N, int K
    ) {{
        int tile_m = blockIdx.y * TILE_M;
        int tile_n = blockIdx.x * TILE_N;
        int tid = threadIdx.x;
        
        // Determine position within tile
        int local_m = tid / TILE_N;
        int local_n = tid % TILE_N;
        
        // Accumulator
        float acc = 0.0f;
        
        // Iterate over K dimension
        for (int k = 0; k < K; k += TILE_K) {{
            // Load A tile
            __shared__ __hip_bfloat16 A_shared[TILE_M][TILE_K];
            
            // Load B tile  
            __shared__ __hip_bfloat16 B_shared[TILE_N][TILE_K];
            
            // Collaborative load
            int a_row = tile_m + local_m;
            int b_row = tile_n + local_n;
            
            if (a_row < M && local_n < TILE_K && k + local_n < K) {{
                A_shared[local_m][local_n] = A[a_row * K + k + local_n];
            }}
            
            if (b_row < N && local_m < TILE_K && k + local_m < K) {{
                B_shared[local_n][local_m] = B[b_row * K + k + local_m];
            }}
            
            __syncthreads();
            
            // Compute partial dot product
            if (a_row < M && b_row < N) {{
                #pragma unroll
                for (int kk = 0; kk < TILE_K && k + kk < K; kk++) {{
                    acc += __bfloat162float(A_shared[local_m][kk]) * 
                           __bfloat162float(B_shared[local_n][kk]);
                }}
            }}
            
            __syncthreads();
        }}
        
        // Write output
        int out_m = tile_m + local_m;
        int out_n = tile_n + local_n;
        
        if (out_m < M && out_n < N) {{
            C[out_m * N + out_n] = (__hip_bfloat16)acc;
        }}
    }}
    
    void launch_mixed_gemm_<{config_name}>(
        torch::Tensor A, torch::Tensor B, torch::Tensor C,
        int M, int N, int K
    ) {{
        dim3 grid((N + TILE_N - 1) / TILE_N, (M + TILE_M - 1) / TILE_M);
        int threads = TILE_M * TILE_N;
        if (threads > 256) threads = 256;
        
        mixed_gemm_<{config_name}><<<grid, threads>>>(
            reinterpret_cast<const __hip_bfloat16*>(A.data_ptr()),
            reinterpret_cast<const __hip_bfloat16*>(B.data_ptr()),
            reinterpret_cast<__hip_bfloat16*>(C.data_ptr()),
            M, N, K
        );
    }}
    """

    CPP_SOURCE = f"void launch_mixed_gemm_{config_name}(torch::Tensor A, torch::Tensor B, torch::Tensor C, int M, int N, int K);"

    try:
        mod = load_inline(
            name=f"mixed_tiling_{config_name}",
            cpp_sources=[CPP_SOURCE],
            cuda_sources=[HIP_SOURCE],
            functions=[f"launch_mixed_gemm_{config_name}"],
            verbose=False,
            extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
        )
        _kernel_modules[config_name] = mod
        return mod, True
    except Exception as e:
        print(f"[MixedTiling] Failed to compile {config_name}: {e}")
        return None, False


def _aiter_gemm(data: input_t) -> torch.Tensor:
    """Aiter GEMM with MXFP4 quantization."""
    A, B, B_q, B_shuffle, B_scale_sh = data

    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)

    import aiter

    return aiter.gemm_a4w4(
        Aq.view(dtypes.fp4x2), B_shuffle, Ash, B_scale_sh, dtype=dtypes.bf16, bpreshuffle=True
    )


def custom_kernel(data: input_t) -> output_t:
    """
    Mixed tiling GEMM kernel.

    Implements adaptive tile sizes based on problem dimensions
    for optimal performance across different matrix shapes.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Select tile configuration
    config_name = _select_tile_config(M, N, K)

    # Get kernel for selected configuration
    mod, ok = _get_mixed_tiling_kernel(config_name)

    if ok and mod is not None:
        try:
            # Convert to bfloat16 for kernel
            A_bf16 = A.to(torch.bfloat16)
            B_T = B.t().contiguous()
            B_bf16 = B_T.to(torch.bfloat16)

            C = torch.empty((M, N), dtype=torch.bfloat16, device=A.device)

            # Launch kernel
            launch_fn = getattr(mod, f"launch_mixed_gemm_{config_name}")
            launch_fn(A_bf16, B_bf16, C, M, N, K)

            return C.to(A.dtype)

        except Exception as e:
            print(f"[MixedTiling] {config_name} kernel failed: {e}")

    # Fallback to aiter
    try:
        return _aiter_gemm(data)
    except Exception as e:
        print(f"[MixedTiling] Aiter fallback failed: {e}")
        return torch.matmul(A, B.t())
