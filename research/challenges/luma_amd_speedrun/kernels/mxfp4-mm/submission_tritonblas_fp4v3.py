"""MXFP4 GEMM via tritonblas.matmul_fp4 — persistent Triton kernel with Origami scheduling.

tritonblas uses tl.dot_scaled internally with chiplet-aware thread scheduling.
Expected layout:
  A: [M, K//2] uint8 (packed fp4)
  B: [N, K//2] uint8 (packed fp4, NOT transposed)
  A_scales: [M, K//32] uint8 (e8m0)
  B_scales: [N, K//32] uint8 (e8m0, un-shuffled)
  C: [M, N] bf16 (pre-allocated output)
"""
import torch
from task import input_t, output_t
from tritonblas import matmul_fp4
from aiter.ops.triton.quant import dynamic_mxfp4_quant


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    m, k = A.shape
    n = B.shape[0]

    # Quantize A (un-shuffled fp4 + e8m0 scale)
    A_fp4, A_scale = dynamic_mxfp4_quant(A.contiguous())

    # B: reuse B_q data, re-compute un-shuffled scale
    _, B_scale = dynamic_mxfp4_quant(B.contiguous())

    # Pre-allocate output
    C = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)

    # All tensors as uint8 for tritonblas
    matmul_fp4(
        A_fp4.view(torch.uint8),      # [M, K//2]
        B_q.view(torch.uint8),         # [N, K//2]
        C,                             # [M, N] bf16
        A_scale.view(torch.uint8),     # [M, K//32]
        B_scale.view(torch.uint8),     # [N, K//32]
    )

    return C
