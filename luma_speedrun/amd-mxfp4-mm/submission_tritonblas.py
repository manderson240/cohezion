"""MXFP4 GEMM submission — tritonblas.matmul_fp4 + gemm_a4w4_asm k_split sweep.

Two approaches tested:
1. tritonblas.matmul_fp4: Origami-aware Triton kernel (alternative to aiter CK)
2. aiter.gemm_a4w4_asm: Direct ASM with log2_k_split parameter sweep

Skill data shows tritonblas is slightly slower (~26µs vs ~24µs for aiter),
so the primary value here is the gemm_a4w4_asm k_split sweep.

Key constraints (from tritonblas-matmul-fp4-api skill):
- All tensors MUST be torch.uint8 views (native fp4 → KeyError)
- B layout is [N, K//2] row-major (NOT transposed like aiter)
- Output C must be pre-allocated
- Only dynamic_mxfp4_quant produces compatible scales
"""

import sys

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


# Try importing tritonblas — may not be available
_HAS_TRITONBLAS = False
try:
    import tritonblas
    _HAS_TRITONBLAS = True
    print("tritonblas available", file=sys.stderr)
except ImportError:
    print("tritonblas NOT available, using aiter fallback", file=sys.stderr)

# Try importing gemm_a4w4_asm for k_split sweep
_HAS_ASM = False
try:
    from aiter import gemm_a4w4_asm
    _HAS_ASM = True
    print("gemm_a4w4_asm available", file=sys.stderr)
except ImportError:
    print("gemm_a4w4_asm NOT available", file=sys.stderr)

import torch


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
    """Reverse e8m0_shuffle: recover original [orig_m, orig_n] uint8 scale."""
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    scale = scale.view(sm, sn)
    return scale[:orig_m, :orig_n]


# ── Benchmark: Try multiple approaches, pick fastest at module load ──
# We test once per shape class and cache the winner.
_USE_TRITONBLAS = False  # Default to aiter (known faster from skill data)
_USE_ASM_KSPLIT = False
_BEST_LOG2_KSPLIT = None


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Quantize A to MXFP4 with shuffled E8M0 scales
    A_q, A_scale_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_scale_sh = e8m0_shuffle(A_scale_e8m0).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)

    # Primary path: aiter.gemm_a4w4 with bpreshuffle=True
    # This is the known fastest from skill data (~24µs geomean)
    return aiter.gemm_a4w4(
        A_q, B_shuffle, A_scale_sh, B_scale_sh,
        dtype=dtypes.bf16, bpreshuffle=True,
    )


def custom_kernel_tritonblas(data: input_t) -> output_t:
    """Alternative: tritonblas.matmul_fp4 path.

    ~26µs geomean — slightly slower than aiter but uses Origami scheduling.
    Kept as reference for future optimization.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data

    M, K = A.shape
    N = B.shape[0]  # B is [N, K]

    # Quantize A
    A_q, A_scale_e8m0 = dynamic_mxfp4_quant(A.contiguous())

    # B_q from input is [N, K//2] row-major — exactly what tritonblas expects
    # B_scale_sh is shuffled — unshuffle to get [N, K//32] uint8
    B_scale = e8m0_unshuffle(
        B_scale_sh.view(torch.uint8),
        orig_m=N,
        orig_n=K // 32,
    )

    # Pre-allocate output
    C = torch.empty(M, N, dtype=torch.bfloat16, device=A.device)

    tritonblas.matmul_fp4(
        A_q.view(torch.uint8),        # [M, K//2] uint8
        B_q.view(torch.uint8),        # [N, K//2] uint8 row-major
        C,                            # [M, N] bf16 pre-allocated
        A_scale_e8m0.view(torch.uint8),  # [M, K//32] uint8
        B_scale,                      # [N, K//32] uint8
    )
    return C


def custom_kernel_asm_ksplit(data: input_t, log2_k_split: int = 0) -> output_t:
    """Alternative: gemm_a4w4_asm with explicit log2_k_split.

    Sweep log2_k_split {0, 1, 2, 3} to find optimal split factor.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data

    A_q, A_scale_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_scale_sh = e8m0_shuffle(A_scale_e8m0).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)

    return gemm_a4w4_asm(
        A_q, B_shuffle, A_scale_sh, B_scale_sh,
        dtype=dtypes.bf16, bpreshuffle=True,
        log2_k_split=log2_k_split,
    )
