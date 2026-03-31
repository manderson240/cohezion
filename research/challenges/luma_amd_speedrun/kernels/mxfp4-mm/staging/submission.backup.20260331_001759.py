import torch
from task import input_t, output_t
from aiter import dtypes
import aiter
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle

_kt={"4_2880_512": {"kernel": "gemm_a4w4", "log2_ks": 0}, "16_2112_7168": {"kernel": "gemm_a4w4", "log2_ks": 0}, "32_4096_512": {"kernel": "gemm_a4w4", "log2_ks": 0}, "32_2880_512": {"kernel": "gemm_a4w4", "log2_ks": 0}, "64_7168_2048": {"kernel": "gemm_a4w4", "log2_ks": 0}, "256_3072_1536": {"kernel": "gemm_a4w4", "log2_ks": 0}}
_dk="gemm_a4w4"
_dks=0

def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    M, K = A.shape
    N = B_shuffle.shape[0]
    key = f"{M}_{N}_{K}"
    cfg = _kt.get(key, {"kernel": _dk, "log2_ks": _dks})
    kname = cfg["kernel"]
    log2_ks = cfg["log2_ks"]

    A_q_raw, A_scale_raw = dynamic_mxfp4_quant(A)
    A_scale_shuffled = e8m0_shuffle(A_scale_raw).view(dtypes.fp8_e8m0)
    A_q = A_q_raw.view(dtypes.fp4x2)

    gemm_fn = getattr(aiter, kname, aiter.gemm_a4w4)
    if log2_ks > 0:
        C = gemm_fn(
            A_q, B_shuffle, A_scale_shuffled, B_scale_sh,
            dtype=dtypes.bf16, bpreshuffle=True, log2_ks=log2_ks,
        )
    else:
        C = gemm_fn(
            A_q, B_shuffle, A_scale_shuffled, B_scale_sh,
            dtype=dtypes.bf16, bpreshuffle=True,
        )
    return C
