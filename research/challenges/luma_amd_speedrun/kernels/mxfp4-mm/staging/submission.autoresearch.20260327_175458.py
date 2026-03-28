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

    # Quantize A using per-1x32 MXFP4 (same as reference)
    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale_sh = quant_func(A, shuffle=False)

    # Shuffle A to match B layout (16x16 tile coalesced)
    A_shuffle = shuffle_weight(A_q, layout=(16, 16))

    # Run optimized GEMM using gemm_a4w4
    C = aiter.gemm_a4w4(
        A_shuffle, B_shuffle,
        A_scale_sh, B_scale_sh,
        out_dtype=torch.bfloat16
    )

    # Ensure output is contiguous and correct shape
    return C.contiguous()