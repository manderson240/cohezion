"""MXFP4 GEMM via tritonblas.matmul_fp4 — zero B re-quantization.

Reverses e8m0_shuffle to recover un-shuffled B_scale from B_scale_sh.
e8m0_shuffle:
  pad M→ceil(256), N→ceil(8)
  view(M//32, 2, 16, N//8, 2, 4)
  permute(0, 3, 5, 2, 4, 1)
  view(M_pad, N_pad)
Inverse:
  view(M//32, N//8, 4, 16, 2, 2)
  permute(0, 5, 3, 1, 4, 2)
  view(M_pad, N_pad)
  strip padding → [M_orig, N_orig]
"""
import torch
from task import input_t, output_t
from tritonblas import matmul_fp4
from aiter.ops.triton.quant import dynamic_mxfp4_quant


def e8m0_unshuffle(scale_shuffled: torch.Tensor, orig_m: int, orig_n: int) -> torch.Tensor:
    """Reverse e8m0_shuffle: recover original [orig_m, orig_n] scale."""
    sm, sn = scale_shuffled.shape
    # The shuffled tensor has padded dims: sm = ceil(orig_m/256)*256, sn = ceil(orig_n/8)*8
    # After shuffle, layout is: view(sm//32, sn//8, 4, 16, 2, 2) from permute(0,3,5,2,4,1)
    # Inverse permute of (0,3,5,2,4,1) is (0,5,3,1,4,2)
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    scale = scale.view(sm, sn)
    return scale[:orig_m, :orig_n]


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    m, k = A.shape
    n = B.shape[0]

    # Quantize A
    A_fp4, A_scale = dynamic_mxfp4_quant(A.contiguous())

    # B: reuse B_q data, UNSHUFFLE B_scale_sh to get un-shuffled scale
    # B_scale_sh is [N_padded, K_scale_padded] in e8m0 shuffled format
    # Original B_scale was [N, K//32] before shuffle
    k_scale = k // 32  # un-shuffled scale K dimension
    B_scale = e8m0_unshuffle(
        B_scale_sh.view(torch.uint8),
        orig_m=n,         # B_scale original M = N (number of rows in B)
        orig_n=k_scale,   # B_scale original N = K//32
    )

    C = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)

    matmul_fp4(
        A_fp4.view(torch.uint8),
        B_q.view(torch.uint8),
        C,
        A_scale.view(torch.uint8),
        B_scale,
    )

    return C
