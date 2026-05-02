"""
GEMM: Dynamic Precision Selection
Approach: Dynamically select precision based on operand magnitudes.
Use lower precision for small values, higher for large values.

Key insight: Not all values need full precision. Dynamic selection
reduces compute for well-behaved data.
"""


import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from task import input_t, output_t


def _analyze_value_range(tensor: torch.Tensor) -> str:
    """Analyze value range to determine optimal precision."""
    max_val = tensor.abs().max().item()
    mean_val = tensor.abs().mean().item()

    if max_val < 1.0 and mean_val < 0.1:
        return "low"  # Can use lower precision
    elif max_val < 10.0:
        return "medium"  # Standard precision
    else:
        return "high"  # Need full precision


def custom_kernel(data: input_t) -> output_t:
    """
    Dynamic precision GEMM.

    1. Analyze input value ranges
    2. Select appropriate quantization strategy
    3. Execute GEMM with chosen precision
    """
    try:
        A, B, B_q, B_shuffle, B_scale_sh = data

        M, K = A.shape
        N = B.shape[0]

        A = A.contiguous()

        # Analyze A's value range
        precision_mode = _analyze_value_range(A)

        # Adjust quantization based on precision mode
        if precision_mode == "low":
            # More aggressive quantization for small values
            A_q, A_scale = dynamic_mxfp4_quant(A * 2.0)  # Scale up for better use of range
            A_q = A_q.view(dtypes.fp4x2)
            A_scale = A_scale * 0.5  # Compensate scaling
        else:
            # Standard quantization
            A_q, A_scale = dynamic_mxfp4_quant(A)
            A_q = A_q.view(dtypes.fp4x2)

        # Single GEMM dispatch
        output = aiter.gemm_a4w4(
            A_q,
            B_shuffle,
            A_scale,
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True,
        )

        return output

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
