"""
MXFP4 GEMM — Phase 3: Wrapper module bypass for callsite sensitivity.

Since gemm_a4w4_asm is callsite-sensitive (fails from submission.py),
we call it through gemm_wrapper.py where the DIRECT caller is the wrapper
module (not submission.py), bypassing the JIT dispatch sensitivity.

This approach also caches get_triton_quant at module level in gemm_wrapper.py.
"""
from task import input_t, output_t
from gemm_wrapper import quant_and_gemm


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    return quant_and_gemm(A, B_shuffle, B_scale_sh)
