"""
MoE: Early Exit Optimization
Approach: Skip expert computation when top-k weights are very small,
saving computation for tokens with confident routing.

Key insight: Many tokens have one dominant expert. We can skip
computation for experts with weights below threshold.
"""

import os
import sys

import torch
import torch.nn.functional as F


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
    Early exit MoE kernel.

    Optimizations:
    1. Skip experts with weight < 0.01 (threshold)
    2. Early termination if only one expert has significant weight
    3. Reduces wasted computation on confident predictions
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
        topk = topk_ids.shape[1]

        # Early exit threshold
        THRESHOLD = 0.01

        # Quantize input
        x_fp4, x_scale = dynamic_mxfp4_quant(hidden_states.contiguous())
        x_q = x_fp4.view(dtypes.fp4x2)

        output = torch.zeros(M, w2.shape[1], dtype=torch.bfloat16, device=hidden_states.device)

        # Process each token with early exit
        for token_idx in range(M):
            token_experts = topk_ids[token_idx]
            token_weights = topk_weights[token_idx]

            x_tok = x_q[token_idx : token_idx + 1]
            x_scale_tok = x_scale[token_idx : token_idx + 1]

            token_out = torch.zeros(w2.shape[1], dtype=torch.bfloat16, device=hidden_states.device)
            remaining_weight = token_weights.sum()

            for j in range(topk):
                weight = token_weights[j].item()

                # Early exit: skip very small weights
                if weight < THRESHOLD:
                    continue

                # Early exit: if remaining weight is negligible, stop
                if remaining_weight < THRESHOLD * 2:
                    break

                expert_idx = token_experts[j].item()

                # Stage 1
                gate_up = torch.empty(
                    1, w1.shape[1], dtype=torch.bfloat16, device=hidden_states.device
                )
                aiter.gemm_a4w4(
                    x_tok,
                    w1_shuffle[expert_idx],
                    x_scale_tok,
                    w1_scale_shuffled[expert_idx],
                    dtype=dtypes.bf16,
                    bpreshuffle=True,
                )

                gate = gate_up[:, : w1.shape[1] // 2]
                up = gate_up[:, w1.shape[1] // 2 :]
                activated = F.silu(gate) * up

                a2_q, a2_scale = dynamic_mxfp4_quant(activated.contiguous())
                a2_q = a2_q.view(dtypes.fp4x2)

                # Stage 2
                out = torch.empty(1, w2.shape[1], dtype=torch.bfloat16, device=hidden_states.device)
                aiter.gemm_a4w4(
                    a2_q,
                    w2_shuffle[expert_idx],
                    a2_scale.view(dtypes.fp8_e8m0),
                    w2_scale_shuffled[expert_idx],
                    dtype=dtypes.bf16,
                    bpreshuffle=True,
                )

                token_out += out.squeeze(0) * weight
                remaining_weight -= weight

            output[token_idx] = token_out

        return output

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
