"""GEMM submission template.

Parameters (JSON):
  kernel_table: dict mapping "M_N_K" -> {"kernel": str, "log2_ks": int}
                e.g. {"4_2880_512": {"kernel": "gemm_a4w4_asm", "log2_ks": 2}}
  default_kernel: str, fallback kernel name (default "gemm_a4w4")
  default_log2_ks: int, fallback split-K (default 0)
"""

TEMPLATE = """\
import torch
from task import input_t, output_t
from aiter import dtypes
import aiter
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle

_kt=$KERNEL_TABLE
_dk="$DEFAULT_KERNEL"
_dks=$DEFAULT_LOG2_KS

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
"""

DEFAULT_PARAMS = {
    "KERNEL_TABLE": {
        "4_2880_512": {"kernel": "gemm_a4w4", "log2_ks": 0},
        "16_2112_7168": {"kernel": "gemm_a4w4", "log2_ks": 0},
        "32_4096_512": {"kernel": "gemm_a4w4", "log2_ks": 0},
        "32_2880_512": {"kernel": "gemm_a4w4", "log2_ks": 0},
        "64_7168_2048": {"kernel": "gemm_a4w4", "log2_ks": 0},
        "256_3072_1536": {"kernel": "gemm_a4w4", "log2_ks": 0},
    },
    "DEFAULT_KERNEL": "gemm_a4w4",
    "DEFAULT_LOG2_KS": 0,
}

# Benchmark shapes from task.yml
SHAPES = [
    {"M": 4, "N": 2880, "K": 512},
    {"M": 16, "N": 2112, "K": 7168},
    {"M": 32, "N": 4096, "K": 512},
    {"M": 32, "N": 2880, "K": 512},
    {"M": 64, "N": 7168, "K": 2048},
    {"M": 256, "N": 3072, "K": 1536},
]
