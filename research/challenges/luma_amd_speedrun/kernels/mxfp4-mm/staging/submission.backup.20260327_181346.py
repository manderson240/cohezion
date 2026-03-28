import torch
import aiter
from aiter import QuantType, dtypes
from aiter.ops.shuffle import shuffle_weight
from task import input_t, output_t
from utils import make_match_reference

SCALE_GROUP_SIZE = 32


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    B = B.contiguous()
    m, k = A.shape
    n, _ = B.shape

    # Per-1x32 MXFP4 quant on A (same as reference)
    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale = quant_func(A, shuffle=False)

    # Use gemm_a4w4 kernel with shuffled B (already prepared in input)
    # B_shuffle: [n, k//2] in fp4x2 layout, B_scale_sh: [n, k//32] in e8m0
    C = aiter.gemm_a4w4(A_q, B_shuffle, A_scale, B_scale_sh, out_dtype=dtypes.bf16)

    # Ensure output shape [m, n] and contiguous
    C = C[:m, :n].contiguous()
    return C