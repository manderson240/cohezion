"""MXFP4 GEMM via tritonblas.matmul_fp4 — fast B scale computation.

Skip full B re-quantization (expensive fp4 packing) — compute only E8M0 scale.
E8M0 scale = floor(log2(amax per 32 elements)) + 127, as uint8.
"""
import torch
from task import input_t, output_t
from tritonblas import matmul_fp4
from aiter.ops.triton.quant import dynamic_mxfp4_quant


def _compute_e8m0_scale(tensor: torch.Tensor) -> torch.Tensor:
    """Compute E8M0 block-32 scale from bf16/fp16/fp32 tensor.

    For each group of 32 elements along the last dimension,
    compute floor(log2(amax)) + 127 as uint8.
    """
    n, k = tensor.shape
    groups = tensor.view(n, k // 32, 32)
    amax = groups.float().abs().amax(dim=-1)  # [N, K//32]
    # E8M0: exponent-only float8 with bias 127
    # log2(amax) + 127, floored, clamped to [0, 254]
    # amax=0 maps to scale=0 (special case)
    log2_amax = torch.where(
        amax > 0,
        torch.floor(torch.log2(amax)) + 127,
        torch.zeros_like(amax),
    )
    return log2_amax.clamp(0, 254).to(torch.uint8)  # [N, K//32]


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    m, k = A.shape
    n = B.shape[0]

    # Quantize A (full quant needed — both data and scale)
    A_fp4, A_scale = dynamic_mxfp4_quant(A.contiguous())

    # B: reuse B_q data, compute ONLY scale (skip expensive fp4 packing)
    B_scale = _compute_e8m0_scale(B)  # [N, K//32] uint8

    # Pre-allocate output
    C = torch.empty(m, n, dtype=torch.bfloat16, device=A.device)

    matmul_fp4(
        A_fp4.view(torch.uint8),
        B_q.view(torch.uint8),
        C,
        A_scale.view(torch.uint8),
        B_scale,
    )

    return C
