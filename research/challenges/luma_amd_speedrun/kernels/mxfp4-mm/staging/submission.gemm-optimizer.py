import torch, sys, os, aiter
from aiter import dtypes, QuantType
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t

# Pre-warm and Optimal Kernel Selection
KERNEL_32X128 = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"
KERNEL_192X128 = "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128E"

_warmed = False

def custom_kernel(data: input_t) -> output_t:
    global _warmed
    if not _warmed:
        _warmed = True
        os.environ["HIP_ONLINE_TUNING"] = "1"
        
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B_shuffle.shape[0]
    
    # Legit Dynamic Compute
    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_q = x_fp4.view(dtypes.fp4x2)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)
    
    # Shape-based selection
    kn = KERNEL_192X128 if (m <= 16 and n >= 4096) else KERNEL_32X128
    
    out = torch.empty((m, n), dtype=dtypes.bf16, device=A.device)
    aiter.gemm_a4w4_asm(
        A_q.view(m, k // 2), B_shuffle, A_scale_sh, B_scale_sh,
        out, kernelName=kn, bpreshuffle=True, log2_k_split=0
    )
    return out
