"""
MXFP4 GEMM optimized submission for AMD MI355X.

Approach: Shape-dependent routing between CK gemm_a4w4 and Triton gemm_afp4wfp4.
For large M (>=256), the Triton GEMM may be faster despite B re-quantization overhead.
For small M (<256), CK path with cached quant_func is optimal.

The benchmark times the ENTIRE custom_kernel() including A quantization.
"""
from task import input_t, output_t
import torch
import aiter
from aiter import QuantType, dtypes

# Cache quant functions at module level (avoids per-call lookup)
_quant_shuffled = aiter.get_triton_quant(QuantType.per_1x32)

# Probe for Triton GEMM at import time
_triton_gemm = None
try:
    from aiter.ops.triton.gemm.basic.gemm_afp4wfp4 import gemm_afp4wfp4 as _triton_gemm
except ImportError:
    pass

# Also try to get non-shuffled quant for Triton path
_quant_raw = None
try:
    _quant_raw = aiter.get_triton_quant(QuantType.per_1x32)
except Exception:
    pass


def _ck_path(A, B_shuffle, B_scale_sh):
    """CK-based gemm_a4w4 — proven, uses pre-shuffled B."""
    A_q, A_scale_sh = _quant_shuffled(A, shuffle=True)
    return aiter.gemm_a4w4(
        A_q, B_shuffle, A_scale_sh, B_scale_sh,
        dtype=dtypes.bf16, bpreshuffle=True,
    )


def _triton_path(A, B):
    """Triton-based gemm_afp4wfp4 — requires raw (non-shuffled) quant."""
    A_q, A_scale = _quant_raw(A, shuffle=False)
    B_q, B_scale = _quant_raw(B, shuffle=False)
    return _triton_gemm(A_q, B_q, A_scale, B_scale, dtype=dtypes.bf16)


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()

    # For now: use CK path (proven correct, minimal risk)
    # Triton path requires B re-quantization which adds overhead.
    # TODO: After remote benchmarking, enable Triton for shapes where it wins.
    return _ck_path(A, B_shuffle, B_scale_sh)
