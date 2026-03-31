import math

import torch
import torch.nn.functional as F
from aiter import ActivationType, QuantType, dtypes
from aiter.fused_moe import fused_moe
from aiter.ops.shuffle import shuffle_weight
from aiter.utility import fp4_utils
from task import input_t, output_t


# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────
MXFP4_BLOCK_SIZE = 32
PAD_ALIGN = 256
CK_BLOCK_GEMM = 1  # Enable block GEMM dispatch


def _pad_to(x: int, align: int) -> int:
    return (x + align - 1) // align * align


def _adaptive_ksplit(n_experts: int) -> int:
    # Adaptive KSPLIT: sparse (>200 experts) → 4, else 2
    return 4 if n_experts > 200 else 2


def custom_kernel(data: input_t) -> output_t:
    # ── Unpack inputs ────────────────────────────────────────────────────
    hidden_states = data.hidden_states  # [M, d_hidden]
    router_logits = data.router_logits  # [M, n_routed_experts]
    w13_list = data.w13_list  # list of [d_expert_pad, d_hidden_pad] experts
    w2_list = data.w2_list     # list of [d_hidden_pad, d_expert_pad] experts
    n_routed_experts = len(w13_list)
    n_shared_experts = data.n_shared_experts
    n_experts_per_token = data.n_experts_per_token
    d_hidden = data.d_hidden
    d_expert = data.d_expert

    # ── Compute router scores and top-k indices ──────────────────────────
    scores = F.softmax(router_logits, dim=-1)
    topk_weights, topk_ids = torch.topk(scores, k=n_experts_per_token, dim=-1, sorted=False)
    topk_weights = topk_weights.to(torch.float32)
    topk_ids = topk_ids.to(torch.int32)

    # ── Append shared experts (always selected, weight=1.0) ──────────────
    M = hidden_states.size(0)
    if n_shared_experts > 0:
        # Create shared expert indices [M, n_shared_experts]
        shared_ids = torch.arange(
            n_routed_experts, n_routed_experts + n_shared_experts,
            device=topk_ids.device, dtype=topk_ids.dtype
        ).unsqueeze(0).expand(M, -1)
        # Concatenate
        topk_ids = torch.cat([topk_ids, shared_ids], dim=1)
        # Shared expert weights = 1.0
        shared_weights = torch.ones(M, n_shared_experts, dtype=torch.float32, device=topk_ids.device)
        topk_weights = torch.cat([topk_weights, shared_weights], dim=1)

    # ── Determine block GEMM and KSPLIT strategy ────────────────────────
    total_top_k = topk_ids.size(1)  # including shared experts
    # Use adaptive KSPLIT based on total number of experts involved
    n_active_experts = n_routed_experts + n_shared_experts
    ks = _adaptive_ksplit(n_active_experts)

    # ── Pad dimensions (required for MXFP4 and alignment) ────────────────
    d_hidden_pad = _pad_to(d_hidden, PAD_ALIGN)
    d_expert_pad = _pad_to(d_expert, PAD_ALIGN)

    # ── Prepare expert weights: pad and convert to MXFP4 format ──────────
    # Convert w13/w2 to MXFP4 format and pad
    w13_fp4_list = []
    w2_fp4_list = []

    for w13 in w13_list:
        # Pad and convert to MXFP4: [d_expert, d_hidden] -> [d_expert_pad, d_hidden_pad]
        padded = torch.zeros(d_expert_pad, d_hidden_pad, dtype=torch.bfloat16, device=w13.device)
        padded[:d_expert, :d_hidden] = w13.to(torch.bfloat16)
        # Convert to MXFP4: [N, K//2] where N=d_expert_pad, K=d_hidden_pad
        fp4_tensor = fp4_utils.pack_bf16_to_mxfp4(padded, block_size=MXFP4_BLOCK_SIZE)
        w13_fp4_list.append(fp4_tensor)

    for w2 in w2_list:
        # Pad and convert to MXFP4: [d_hidden, d_expert] -> [d_hidden_pad, d_expert_pad]
        padded = torch.zeros(d_hidden_pad, d_expert_pad, dtype=torch.bfloat16, device=w2.device)
        padded[:d_hidden, :d_expert] = w2.to(torch.bfloat16)
        # Convert to MXFP4: [N, K//2] where N=d_hidden_pad, K=d_expert_pad
        fp4_tensor = fp4_utils.pack_bf16_to_mxfp4(padded, block_size=MXFP4_BLOCK_SIZE)
        w2_fp4_list.append(fp4_tensor)

    # ── Run fused MoE kernel with block GEMM and adaptive KSPLIT ─────────
    # Use fused_moe with block GEMM enabled (CK_BLOCK_GEMM=1)
    # KSPLIT is set via aiter config (KSPLIT=ks)
    torch.cuda.synchronize()
    output = fused_moe(
        hidden_states,
        topk_ids,
        topk_weights,
        w13_fp4_list,
        w2_fp4_list,
        activation=ActivationType.GELU,
        quant_type=QuantType.MXFP4,
        block_size=MXFP4_BLOCK_SIZE,
        block_gemm=CK_BLOCK_GEMM,
        ks=ks,
        # Additional config for stability
        use_fp4=True,
        use_mxfp4=True,
    )

    # Ensure output shape and dtype match expectations
    assert output.shape == (M, d_hidden), f"Output shape mismatch: {output.shape}"
    assert output.dtype == torch.bfloat16, f"Output dtype mismatch: {output.dtype}"

    return output_t(output=output)