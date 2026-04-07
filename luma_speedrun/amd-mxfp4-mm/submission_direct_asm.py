#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""GEMM: Direct ASM dispatch + HIP quant, matching leader pattern.

Optimizations over baseline:
1. per_1x32_f4_quant_hip(shuffle=True): single HIP kernel for quant+shuffle
2. Direct gemm_a4w4_asm call: skip config lookup, explicit splitK=0
3. Pre-allocated output tensor: reuse across calls
4. Explicit 32x128 ASM kernel: known optimal for all 6 competition shapes

All 6 competition shapes confirmed to use 32x128 ASM kernel with splitK=0.
"""

import torch
from aiter import dtypes
from aiter.ops.gemm_op_a4w4 import gemm_a4w4_asm
from task import input_t, output_t

# Try HIP quant path (single kernel for quant + shuffle)
_hip_quant = None
try:
    from aiter.ops.quant import per_1x32_f4_quant_hip

    _hip_quant = per_1x32_f4_quant_hip
except ImportError:
    pass

# Fallback imports
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle

_fp4x2 = dtypes.fp4x2
_e8m0 = dtypes.fp8_e8m0
_bf16 = dtypes.bf16

# The 32x128 ASM kernel — optimal for ALL 6 competition shapes (verified from CSV)
_KERNEL_NAME = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"

# Output tensor cache (keyed by (m_padded, n))
_out_cache: dict[tuple[int, int], torch.Tensor] = {}


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Quantize A: prefer HIP single-call, fallback to Triton two-call
    if _hip_quant is not None:
        try:
            Aq, Ash = _hip_quant(A.contiguous(), shuffle=True)
            Ash_view = Ash.view(_e8m0)
        except Exception:
            Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
            Ash_view = e8m0_shuffle(Asc).view(_e8m0)
    else:
        Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
        Ash_view = e8m0_shuffle(Asc).view(_e8m0)

    m = A.numel() // A.shape[-1]
    n = B_shuffle.shape[0]
    k_half = Aq.shape[-1]  # K/2 in fp4x2 packed format
    m_padded = (m + 31) // 32 * 32

    # Get or allocate padded output
    cache_key = (m_padded, n)
    out = _out_cache.get(cache_key)
    if out is None or out.device != A.device:
        out = torch.empty((m_padded, n), dtype=_bf16, device=A.device)
        _out_cache[cache_key] = out

    # Direct ASM dispatch: skip config lookup, explicit splitK=0
    gemm_a4w4_asm(
        Aq.view(m, k_half).view(_fp4x2),
        B_shuffle,
        Ash_view,
        B_scale_sh,
        out,
        _KERNEL_NAME,
        None,  # bias
        1.0,  # alpha
        0.0,  # beta
        True,  # bpreshuffle
        log2_k_split=0,
    )
    return out[:m].view(*A.shape[:-1], n)
