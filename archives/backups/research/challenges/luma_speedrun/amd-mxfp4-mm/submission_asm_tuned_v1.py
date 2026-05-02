#!POPCORN leaderboard amd-mxfp4-mm
#!POPCORN gpu MI355X

"""MXFP4 GEMM: Force specific pre-compiled .co kernels per shape.

The runner has these pre-compiled ASM kernels at /home/runner/aiter/hsa/gfx950/f4gemm/:
  - f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128.co  (tile_M=32, tile_N=128)
  - f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128.co (tile_M=192, tile_N=128)

Kernel selection strategy (from a4w4_blockscale_tuned_gemm.csv, cu_num=256):
  M=4,  N=2880, K=512  → 32x128 (no tuned entry; 32x128 is universal small-M choice)
  M=16, N=2112, K=7168 → 32x128, log2_k_split=1 (K=7168 is large; 2-way K-split may help)
  M=32, N=4096, K=512  → 32x128 (no tuned entry; K small, no split)
  M=32, N=2880, K=512  → 32x128 (no tuned entry; K small, no split)
  M=64, N=7168, K=2048 → 32x128, splitK=0 (directly tuned: 6.81µs)
  M=256,N=3072, K=1536 → 32x128, splitK=0 (directly tuned: 6.18µs)

Output tensor must be padded to ceil(M/32)*32 per gemm_a4w4_asm requirement.

Note: 192x128 kernel only wins for M ∈ {192, 384, 512, 768, 1024, 1152} — never for our
benchmark shapes (max M=256 at N=3072 uses 32x128 per tuning data).
"""

import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


# Kernel mangled names — match exactly what's in the .co files
_KERNEL_32x128 = "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"
_KERNEL_192x128 = "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128E"


def _select_kernel(M: int, K: int) -> tuple[str, int]:
    """Return (kernel_name, log2_k_split) for the given shape.

    Strategy based on a4w4_blockscale_tuned_gemm.csv (cu_num=256):
    - 192x128 kernel wins only when M is a multiple of 192 (192, 384, 512...).
      None of our 6 benchmark shapes have such M, so always use 32x128.
    - For M <= 32 with K >= 4096 (specifically M=16, K=7168): try log2_k_split=1
      to double the number of CU-resident tiles, improving GPU occupancy.
    - All other shapes: 32x128, no K-split (matches tuned data).
    """
    # For M=16 with large K (the hardest benchmark shape at ~20.8µs), K-splitting
    # may improve CU utilisation: K=7168 → 2 splits of K=3584 each.
    if M <= 32 and K >= 4096:
        return _KERNEL_32x128, 1
    return _KERNEL_32x128, 0


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    M, K = A.shape
    N = B.shape[0]

    # Quantize A: produces fp4x2 data and E8M0 scales
    Aq, Asc = dynamic_mxfp4_quant(A.contiguous())
    Ash = e8m0_shuffle(Asc).view(dtypes.fp8_e8m0)
    Aq_fp4 = Aq.view(dtypes.fp4x2)

    # gemm_a4w4_asm requires out.shape[0] % 32 == 0
    M_padded = ((M + 31) // 32) * 32
    out = torch.empty((M_padded, N), dtype=torch.bfloat16, device=A.device)

    kernel_name, log2_ksplit = _select_kernel(M, K)

    try:
        aiter.gemm_a4w4_asm(
            Aq_fp4,
            B_shuffle,
            Ash,
            B_scale_sh,
            out,
            kernel_name,
            None,  # bias
            1.0,  # alpha
            0.0,  # beta
            True,  # bpreshuffle
            log2_ksplit,
        )
        # Slice to exact [M, N] — avoids returning padded rows
        return out[:M]
    except Exception as e:
        # Fall back to standard gemm_a4w4 if ASM dispatch fails
        print(f"[asm_tuned_v1] ASM fallback M={M} N={N} K={K}: {e}")
        return aiter.gemm_a4w4(
            Aq_fp4,
            B_shuffle,
            Ash,
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True,
        )
