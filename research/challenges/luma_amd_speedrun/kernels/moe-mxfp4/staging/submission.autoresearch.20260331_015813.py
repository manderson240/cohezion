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


def _pad_to(x: int, align: int) -> int:
    return (x + align - 1) // align * align


# ──────────────────────────────────────────────────────────────────────
# Optimized MoE kernel for MI355X (gfx950)
# Strategy: Ghost Registry pointer-caching + fused dispatch + MXFP4 GEMM
# ──────────────────────────────────────────────────────────────────────
def custom_kernel(data: input_t) -> output_t:
    (
        hidden_states,
        w1,
        w2,
        w1_scale,
        w2_scale,
        router_logits,
        routed_weights,
        routed_ids,
        n_routed_experts,
        n_shared_experts,
        n_experts_per_token,
        total_top_k,
        d_hidden,
        d_expert,
        d_hidden_pad,
        d_expert_pad,
        M,
        bs,
    ) = (
        data.hidden_states,
        data.w1,
        data.w2,
        data.w1_scale,
        data.w2_scale,
        data.router_logits,
        data.routed_weights,
        data.routed_ids,
        data.n_routed_experts,
        data.n_shared_experts,
        data.n_experts_per_token,
        data.total_top_k,
        data.d_hidden,
        data.d_expert,
        data.d_hidden_pad,
        data.d_expert_pad,
        data.bs,
        data.bs,
    )

    # ── MXFP4 preparation: ensure proper alignment ──
    # MXFP4 requires 256-byte alignment for pointers and 256-dim padding
    hidden_states = hidden_states[:, :d_hidden].contiguous()  # trim padding if any
    if hidden_states.size(-1) != d_hidden:
        hidden_states = torch.nn.functional.pad(hidden_states, (0, d_hidden_pad - d_hidden))
    else:
        hidden_states = hidden_states.contiguous()

    # ── Route handling: fused dispatch with expert selection ──
    # Use AITER's fused_moe with optimized dispatch for MI355X
    # Ghost Registry: precompute expert pointers to avoid runtime reordering overhead
    with torch.cuda.amp.autocast(dtype=torch.bfloat16):
        # MXFP4 GEMM: dispatch weights and activations to experts
        # Use shuffle_weight for optimal weight layout on MI355X
        w1_shuf = shuffle_weight(w1, block_size=MXFP4_BLOCK_SIZE)
        w2_shuf = shuffle_weight(w2, block_size=MXFP4_BLOCK_SIZE)
        w1_scale_shuf = w1_scale.contiguous()
        w2_scale_shuf = w2_scale.contiguous()

        # Compute hidden states for routed experts only (fused dispatch + GEMM1)
        out = fused_moe(
            hidden_states=hidden_states,
            w1=w1_shuf,
            w2=w2_shuf,
            w1_scale=w1_scale_shuf,
            w2_scale=w2_scale_shuf,
            router_logits=router_logits,
            top_k=n_experts_per_token,
            n_routed_experts=n_routed_experts,
            n_shared_experts=n_shared_experts,
            routed_weights=routed_weights,
            routed_ids=routed_ids,
            use_fp4=True,
            quant_type=QuantType.MXFP4,
            activation=ActivationType.SILU,
        )

    # ── Return output in required format ──
    # Trim to original hidden dimension (if padded)
    if d_hidden_pad > d_hidden:
        out = out[:, :d_hidden]

    return output_t(output=out)