TEMPLATE = """\
import torch
import sys
import aiter
from aiter import QuantType, dtypes
from reference import ref_kernel

def custom_kernel(data):
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    
    # Legit Dynamic Compute
    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale_sh = quant_func(A, shuffle=True)
    
    # KERNEL_TABLE substitution
    kernel_table = $KERNEL_TABLE
    M, N, K = A.shape[0], B.shape[0], A.shape[1]
    shape_key = f"{M}_{N}_{K}"
    config = kernel_table.get(shape_key, {"kernel": "gemm_a4w4", "log2_ks": 0})
    
    out = torch.empty((M, N), dtype=dtypes.bf16, device=A.device)
    
    if config["kernel"] == "gemm_a4w4_asm":
        aiter.gemm_a4w4_asm(
            A_q, B_shuffle, A_scale_sh, B_scale_sh,
            out, bpreshuffle=True, log2_k_split=config["log2_ks"]
        )
    else:
        # Fallback to unified
        out = aiter.gemm_a4w4(
            A_q, B_shuffle, A_scale_sh, B_scale_sh,
            dtype=dtypes.bf16, bpreshuffle=True
        )
    return out
"""

DEFAULT_PARAMS = {
    "KERNEL_TABLE": {
        "4_2880_512": {"kernel": "gemm_a4w4", "log2_ks": 0},
        "16_2112_7168": {"kernel": "gemm_a4w4", "log2_ks": 0},
        "32_4096_512": {"kernel": "gemm_a4w4", "log2_ks": 0},
        "32_2880_512": {"kernel": "gemm_a4w4", "log2_ks": 0},
        "64_7168_2048": {"kernel": "gemm_a4w4", "log2_ks": 0},
        "256_3072_1536": {"kernel": "gemm_a4w4", "log2_ks": 0},
    }
}
