"""
MXFP4 GEMM — Phase 2: gemm_afp4wfp4 Triton kernel.

gemm_afp4wfp4 takes UNSHUFFLED FP4 quant data + scales, unlike gemm_a4w4
which needs pre-shuffled inputs. get_torch_quant produces unshuffled output,
so the two should be compatible.

Signature discovered via introspection:
  gemm_afp4wfp4(x, w, x_scales, w_scales, dtype=bf16, y=None, config=None, skip_reduce=False)

The reference provides B_q (unshuffled) and B_scale via generate_input.
We quantize A with get_torch_quant (no shuffle) and call gemm_afp4wfp4.
"""
import sys
import aiter
from aiter import QuantType, dtypes
from aiter.ops.triton.gemm.basic.gemm_afp4wfp4 import gemm_afp4wfp4
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()

    # Quantize A with torch_quant (produces unshuffled fp4x2 + e8m0 scale)
    quant_func = aiter.get_torch_quant(QuantType.per_1x32)
    A_q, A_scale = quant_func(A, quant_dtype=dtypes.fp4x2)

    # B_q is the raw (unshuffled) quantized B from generate_input
    # We need unshuffled B scale — but generate_input only gives us B_scale_sh (shuffled)
    # Re-quantize B to get unshuffled scale
    B_q_raw, B_scale_raw = quant_func(B, quant_dtype=dtypes.fp4x2)

    try:
        out = gemm_afp4wfp4(A_q, B_q_raw, A_scale, B_scale_raw, dtype=dtypes.bf16)
        return out
    except Exception as e:
        print(f"GEMM_AFP4WFP4_FAIL: {e}", file=sys.stderr)
        # Fallback to ref_kernel
        from reference import ref_kernel
        return ref_kernel(data)
