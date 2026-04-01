"""
MXFP4 GEMM with optimal per-shape kernel selection.

Pre-warm all kernels before benchmarking and select optimal kernel for each shape.
"""

from __future__ import annotations

import os
import sys


# Enable HIP online tuning BEFORE importing aiter
os.environ["HIP_ONLINE_TUNING"] = "1"

import aiter
import torch
from aiter import QuantType, dtypes
from aiter.ops.shuffle import shuffle_weight
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


# Kernel names based on shape analysis
# M=4: 32x128 is good for small M
# M=16,32: 32x128 or 192x128 depending on N
# M=64+: 32x128 or 64x128 for larger N
KERNEL_32X128 = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"
KERNEL_192X128 = "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128E"
KERNEL_64X128 = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_64x128E"


def get_kernel_name(m, n, k):
    """Select optimal kernel based on shape."""
    if m <= 16:
        if n >= 4096:
            return KERNEL_192X128
        return KERNEL_32X128
    elif m <= 64:
        if n >= 7168:
            return KERNEL_64X128
        return KERNEL_32X128
    else:
        return KERNEL_32X128


def warm_all_kernels():
    """Pre-warm all kernels for benchmark shapes."""
    print("Pre-warming kernels...", file=sys.stderr, flush=True)
    
    shapes = [
        (4, 2880, 512),
        (16, 2112, 7168),
        (32, 4096, 512),
        (32, 2880, 512),
        (64, 7168, 2048),
        (256, 3072, 1536),
    ]
    
    kernels_to_warm = [KERNEL_32X128, KERNEL_192X128, KERNEL_64X128]
    
    for m, n, k in shapes:
        kernel = get_kernel_name(m, n, k)
        if kernel not in kernels_to_warm:
            kernels_to_warm.append(kernel)
    
    for kernel in kernels_to_warm:
        print(f"  Loading kernel: {kernel[:50]}...", file=sys.stderr, flush=True)
        try:
            A = torch.randn(16, 128, dtype=torch.bfloat16, device="cuda")
            B = torch.randn(128, 128, dtype=torch.bfloat16, device="cuda")
            quant_func = aiter.get_triton_quant(QuantType.per_1x32)
            A_q, A_scale = quant_func(A, shuffle=True)
            B_q, B_scale = quant_func(B, shuffle=True)
            B_shuffle = shuffle_weight(B_q, layout=(16, 16))
            
            out = torch.empty((16, 128), dtype=dtypes.bf16, device=A.device)
            aiter.gemm_a4w4_asm(
                A_q, B_shuffle, A_scale, B_scale, out,
                kernelName=kernel, bias=None, alpha=1.0, beta=0.0,
                bpreshuffle=True, log2_k_split=0,
            )
            del A, B, A_q, B_q, A_scale, B_scale, B_shuffle, out
            torch.cuda.empty_cache()
        except Exception as e:
            print(f"    Warning: {e}", file=sys.stderr, flush=True)
    
    print("Kernel pre-warming complete", file=sys.stderr, flush=True)


_warmed = False


def _ensure_warmed():
    global _warmed
    if not _warmed:
        _warmed = True
        warm_all_kernels()


def custom_kernel(data: input_t) -> output_t:
    _ensure_warmed()
    
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n = B_shuffle.shape[0]
    
    # Quantize A with MXFP4
    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A)
    A_q = x_fp4.view(dtypes.fp4x2)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)
    
    # Select optimal kernel
    kernel_name = get_kernel_name(m, n, k)
    
    # Pre-allocate output
    out = torch.empty((m, n), dtype=dtypes.bf16, device=A.device)
    
    # Call ASM path directly with optimal kernel
    aiter.gemm_a4w4_asm(
        A_q.view(m, k // 2),
        B_shuffle,
        A_scale_sh,
        B_scale_sh,
        out,
        kernelName=kernel_name,
        bias=None,
        alpha=1.0,
        beta=0.0,
        bpreshuffle=True,
        log2_k_split=0,
    )
    return out
