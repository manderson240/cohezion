"""
MXFP4 GEMM — Phase 1 fallback: get_torch_quant + gemm_a4w4.

Fallback to pure-PyTorch quantization if get_hip_quant scale format
is incompatible with gemm_a4w4. get_torch_quant is verified to produce
the correct format (probe showed it works with shuffle=True).
"""
import aiter
from aiter import QuantType, dtypes
from task import input_t, output_t

_quant_func = None


def custom_kernel(data: input_t) -> output_t:
    global _quant_func
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    if _quant_func is None:
        _quant_func = aiter.get_torch_quant(QuantType.per_1x32)
    A_q, A_scale_sh = _quant_func(A, shuffle=True)
    return aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        dtype=dtypes.bf16,
        bpreshuffle=True,
    )
