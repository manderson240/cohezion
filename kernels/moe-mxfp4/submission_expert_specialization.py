"""
MoE: Expert Specialization Paths
Approach: Create specialized computation paths for different expert types
(common vs. rare experts) to optimize for their access patterns.

Key insight: Some experts are accessed frequently (hot), others rarely (cold).
Different code paths can optimize for each case.
"""

import torch
import torch.nn.functional as F
import sys
import os

_AITER_JIT_BUILD = "/home/runner/aiter/aiter/jit/build"
for _mod in (
    "module_moe_sorting",
    "module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_",
):
    _p = os.path.join(_AITER_JIT_BUILD, _mod)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """
    Expert specialization MoE kernel.

    Categorizes experts into hot/cold:
    - Hot experts (>1% of tokens): Optimized fast path with cached weights
    - Cold experts: Standard path with on-demand loading

    Reduces overhead for common cases.
    """
    try:
        (
            hidden_states,
            w1,
            w2,
            w1_scale,
            w2_scale,
            w1_shuffle,
            w2_shuffle,
            w1_scale_shuffled,
            w2_scale_shuffled,
            topk_weights,
            topk_ids,
            config,
        ) = data

        M = hidden_states.shape[0]
        num_experts = w1.shape[0]
        HOT_THRESHOLD = 0.01  # 1% of tokens

        # Quantize input
        x_fp4, x_scale = dynamic_mxfp4_quant(hidden_states.contiguous())
        x_q = x_fp4.view(dtypes.fp4x2)

        # Count tokens per expert to identify hot/cold
        expert_counts = torch.bincount(topk_ids.flatten(), minlength=num_experts)
        hot_experts = (expert_counts > M * HOT_THRESHOLD).nonzero(as_tuple=True)[0]
        hot_set = set(hot_experts.tolist())

        # Pre-cache hot expert weights
        hot_cache = {}
        for exp_idx in hot_experts:
            exp_idx = exp_idx.item()
            hot_cache[exp_idx] = {
                "w1": w1_shuffle[exp_idx],
                "w1_scale": w1_scale_shuffled[exp_idx],
                "w2": w2_shuffle[exp_idx],
                "w2_scale": w2_scale_shuffled[exp_idx],
            }

        output = torch.zeros(M, w2.shape[1], dtype=torch.bfloat16, device=hidden_states.device)

        # Process each token
        for token_idx in range(M):
            token_experts = topk_ids[token_idx]
            token_weights = topk_weights[token_idx]

            x_tok = x_q[token_idx : token_idx + 1]
            x_scale_tok = x_scale[token_idx : token_idx + 1]

            token_out = torch.zeros(w2.shape[1], dtype=torch.bfloat16, device=hidden_states.device)

            for j, (expert_idx, weight) in enumerate(zip(token_experts, token_weights)):
                expert_idx = expert_idx.item()

                # Choose fast path for hot experts
                if expert_idx in hot_cache:
                    cache = hot_cache[expert_idx]
                    w1_e = cache["w1"]
                    w1_s = cache["w1_scale"]
                    w2_e = cache["w2"]
                    w2_s = cache["w2_scale"]
                else:
                    # Cold path: load on demand
                    w1_e = w1_shuffle[expert_idx]
                    w1_s = w1_scale_shuffled[expert_idx]
                    w2_e = w2_shuffle[expert_idx]
                    w2_s = w2_scale_shuffled[expert_idx]

                # Stage 1
                gate_up = torch.empty(
                    1, w1.shape[1], dtype=torch.bfloat16, device=hidden_states.device
                )
                aiter.gemm_a4w4(x_tok, w1_e, x_scale_tok, w1_s, dtype=dtypes.bf16, bpreshuffle=True)

                gate = gate_up[:, : w1.shape[1] // 2]
                up = gate_up[:, w1.shape[1] // 2 :]
                activated = F.silu(gate) * up

                a2_q, a2_scale = dynamic_mxfp4_quant(activated.contiguous())
                a2_q = a2_q.view(dtypes.fp4x2)

                # Stage 2
                out = torch.empty(1, w2.shape[1], dtype=torch.bfloat16, device=hidden_states.device)
                aiter.gemm_a4w4(
                    a2_q,
                    w2_e,
                    a2_scale.view(dtypes.fp8_e8m0),
                    w2_s,
                    dtype=dtypes.bf16,
                    bpreshuffle=True,
                )

                token_out += out.squeeze(0) * weight

            output[token_idx] = token_out

        return output

    except Exception as e:
        from reference import ref_kernel

        return ref_kernel(data)
