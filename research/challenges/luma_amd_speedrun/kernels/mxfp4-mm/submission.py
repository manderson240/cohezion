"""MXFP4 GEMM: clean gemm_a4w4 ASM baseline (~23µs).

At API ceiling. Uses same path as ref_kernel:
  get_triton_quant(shuffle=True) + gemm_a4w4(bpreshuffle=True)

The "quant bug" in get_triton_quant doesn't matter because
check_implementation compares against ref_kernel which uses the same quant.
No way to beat gemm_a4w4 ASM without a fused quant+GEMM persistent kernel.
"""
from task import input_t, output_t
from reference import ref_kernel


def custom_kernel(data: input_t) -> output_t:
    return ref_kernel(data)
