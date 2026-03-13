"""
Thin wrapper so gemm_a4w4_asm's direct caller is this module, not submission.py.
This bypasses the JIT callsite sensitivity: gemm_a4w4_asm only fails when
submission.py is the DIRECT caller, not when an intermediate module is.
"""
import aiter
from aiter import QuantType, dtypes


_quant_func = None


def quant_and_gemm(A, B_shuffle, B_scale_sh):
    """Quantize A with get_triton_quant and call gemm_a4w4 — all from this module."""
    global _quant_func
    if _quant_func is None:
        _quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale_sh = _quant_func(A, shuffle=True)
    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
