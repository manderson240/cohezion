import math
import torch
import torch.nn.functional as F
import aiter
from aiter.fused_moe import fused_moe
from aiter import dtypes
from task import input_t, output_t
from utils import make_match_reference


# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────
MXFP4_BLOCK_SIZE = 32
PAD_ALIGN = 256


def _pad_to(x: int, align: int) -> int:
    return (x + align - 1) // align * align


# ──────────────────────────────────────────────────────────────────────
# Optimized MoE kernel for MI355X (gfx950) with KSPLIT=6 heuristic
# ──────────────────────────────────────────────────────────────────────
def custom_kernel(data: input_t) -> output_t:
    # ── Unpack input ──
    hidden_states = data.hidden_states  # [M, d_hidden]
    w1 = data.w1  # [E, d_expert, d_hidden]
    w2 = data.w2  # [E, d_hidden, d_expert]
    router_logits = data.router_logits  # [M, E_routed]
    routed_weights = data.routed_weights  # [M, top_k_routed]
    routed_ids = data.routed_ids  # [M, top_k_routed]
    n_routed_experts = data.n_routed_experts
    n_shared_experts = data.n_shared_experts
    n_experts_per_token = data.n_experts_per_token
    d_hidden = data.d_hidden
    d_expert = data.d_expert
    d_hidden_pad = data.d_hidden_pad
    d_expert_pad = data.d_expert_pad
    total_top_k = data.total_top_k

    M = hidden_states.size(0)
    # Effective M for expert dispatch (routed only, shared handled separately)
    est_m = M * n_experts_per_token

    # ── KSPLIT selection per strategy ──
    # KSPLIT=6 for est_m<5 heuristic (OpenCode Kimi v16)
    # For MI355X, higher KSPLIT helps very small effective M
    KSPLIT = 6 if est_m < 5 else 4

    # ── Prepare expert weights (padded) ──
    E_total = n_routed_experts + n_shared_experts
    w1_padded = torch.zeros((E_total, d_expert_pad, d_hidden_pad), 
                            dtype=dtypes.fp4, device=hidden_states.device)
    w2_padded = torch.zeros((E_total, d_hidden_pad, d_expert_pad), 
                            dtype=dtypes.fp4, device=hidden_states.device)

    # Copy actual weights to padded views (only first d_expert/d_hidden slices)
    w1_padded[:n_routed_experts, :d_expert, :d_hidden] = w1.to(dtypes.fp4)
    w2_padded[:n_routed_experts, :d_hidden, :d_expert] = w2.to(dtypes.fp4)

    # Handle shared experts: identity-like weights (no quant, no scaling)
    if n_shared_experts > 0:
        shared_idx = n_routed_experts
        for i in range(n_shared_experts):
            e_idx = shared_idx + i
            # Shared expert: linear pass-through (identity mapping)
            w1_padded[e_idx, :d_hidden, :d_hidden] = torch.eye(d_hidden, 
                dtype=torch.bfloat16, device=hidden_states.device).to(dtypes.fp4)
            w2_padded[e_idx, :d_hidden, :d_hidden] = torch.eye(d_hidden, 
                dtype=torch.bfloat16, device=hidden_states.device).to(dtypes.fp4)

    # ── Build expert dispatch order ──
    # Combine routed and shared experts
    # routed_ids: [M, top_k_routed], routed_weights: [M, top_k_routed]
    # shared: indices [n_routed_experts, ..., n_routed_experts + n_shared_experts - 1]
    # weights = 1.0 for shared, routed_weights for routed

    # Expand routed_ids to full expert indices for all tokens
    all_expert_ids = routed_ids.clone()  # [M, top_k_routed]
    all_weights = routed_weights.clone()  # [M, top_k_routed]

    # Append shared experts: one per token, always active, weight=1.0
    if n_shared_experts > 0:
        shared_ids = torch.full((M, n_shared_experts), 
                                n_routed_experts, 
                                dtype=routed_ids.dtype, 
                                device=routed_ids.device)
        # Increment for multiple shared experts if needed
        for i in range(1, n_shared_experts):
            shared_ids[:, i] += i
        shared_weights = torch.ones((M, n_shared_experts), 
                                    dtype=routed_weights.dtype, 
                                    device=routed_weights.device)
        all_expert_ids = torch.cat([all_expert_ids, shared_ids], dim=1)  # [M, total_top_k]
        all_weights = torch.cat([all_weights, shared_weights], dim=1)    # [M, total_top_k]

    # Flatten for fused_moe: [M * total_top_k]
    flat_expert_ids = all_expert_ids.flatten()  # [M * total_top_k]
    flat_weights = all_weights.flatten()        # [M * total_top_k]

    # ── Run AITER fused MoE with custom KSPLIT ──
    # Use aiter.fused_moe with explicit tile size hints for gfx950
    output = aiter.fused_moe(
        hidden_states,
        w1_padded,
        w2_padded,
        flat_expert_ids,
        flat_weights,
        M=M,
        K=d_hidden_pad,
        N=d_expert_pad,
        E=E_total,
        top_k=n_experts_per_token + n_shared_experts,
        use_fp4=True,
        block_m=64,          # Conservative tile for gfx950
        KSPLIT=KSPLIT,
        BLOCK_GEMM=1,        # Smaller GEMM blocks to reduce register pressure
    )

    # ── Return output ──
    # Trim to original d_hidden (not padded)
    return output_t(output=output[:M, :d_hidden])