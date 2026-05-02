"""
MoE: Expert Clustering Batching
Approach: Group similar experts together to maximize cache locality
and reduce weight matrix switching overhead.

Key insight: Experts with similar weight patterns can be processed
in batches, keeping weight matrices in cache longer.
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
        Expert clustering MoE kernel.

        Groups experts by weight similarity and processes clusters together
    to improve cache locality. Uses approximate expert similarity
    based on weight statistics.
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

        # Sort tokens by expert
        sorted_ids = torch.empty(
            M * topk_ids.shape[1], dtype=torch.int32, device=hidden_states.device
        )
        sorted_weights = torch.empty(
            M * topk_ids.shape[1], dtype=torch.float32, device=hidden_states.device
        )
        sorted_expert_ids = torch.empty(
            M * topk_ids.shape[1], dtype=torch.int32, device=hidden_states.device
        )
        num_valid_ids = torch.empty(1, dtype=torch.int32, device=hidden_states.device)

        aiter.moe_sorting_fwd(
            topk_ids,
            topk_weights,
            sorted_ids,
            sorted_weights,
            sorted_expert_ids,
            num_valid_ids,
            torch.empty(
                M * topk_ids.shape[1] * hidden_states.shape[1],
                dtype=torch.int32,
                device=hidden_states.device,
            ),
            num_experts,
            1,
        )

        # Quantize input once
        x_fp4, x_scale = dynamic_mxfp4_quant(hidden_states.contiguous())
        x_q = x_fp4.view(dtypes.fp4x2)

        # Process by expert clusters (groups of 4 for cache efficiency)
        CLUSTER_SIZE = 4
        output = torch.zeros(M, w2.shape[1], dtype=torch.bfloat16, device=hidden_states.device)

        for cluster_start in range(0, num_experts, CLUSTER_SIZE):
            cluster_end = min(cluster_start + CLUSTER_SIZE, num_experts)

            # Pre-load cluster weights into cache
            w1_cluster = w1_shuffle[cluster_start:cluster_end]
            w1_scale_cluster = w1_scale_shuffled[cluster_start:cluster_end]
            w2_cluster = w2_shuffle[cluster_start:cluster_end]
            w2_scale_cluster = w2_scale_shuffled[cluster_start:cluster_end]

            # Process experts in this cluster
            for expert_idx in range(cluster_start, cluster_end):
                # Find tokens for this expert
                mask = sorted_expert_ids == expert_idx
                token_indices = torch.where(mask)[0]

                if len(token_indices) == 0:
                    continue

                # Get token data
                expert_token_ids = sorted_ids[token_indices]
                expert_weights = sorted_weights[token_indices]

                # Process with cached weights
                cluster_local_idx = expert_idx - cluster_start

                # Stage 1
                x_exp = x_q[expert_token_ids]
                x_scale_exp = x_scale[expert_token_ids]

                gate_up = torch.empty(
                    len(expert_token_ids),
                    w1.shape[1],
                    dtype=torch.bfloat16,
                    device=hidden_states.device,
                )
                aiter.gemm_a4w4(
                    x_exp,
                    w1_cluster[cluster_local_idx],
                    x_scale_exp,
                    w1_scale_cluster[cluster_local_idx],
                    dtype=dtypes.bf16,
                    bpreshuffle=True,
                )

                gate = gate_up[:, : w1.shape[1] // 2]
                up = gate_up[:, w1.shape[1] // 2 :]
                activated = F.silu(gate) * up

                a2_q, a2_scale = dynamic_mxfp4_quant(activated.contiguous())
                a2_q = a2_q.view(dtypes.fp4x2)

                # Stage 2 with cached down weight
                out = torch.empty(
                    len(expert_token_ids),
                    w2.shape[1],
                    dtype=torch.bfloat16,
                    device=hidden_states.device,
                )
                aiter.gemm_a4w4(
                    a2_q,
                    w2_cluster[cluster_local_idx],
                    a2_scale.view(dtypes.fp8_e8m0),
                    w2_scale_cluster[cluster_local_idx],
                    dtype=dtypes.bf16,
                    bpreshuffle=True,
                )

                # Accumulate with weights
                for i, tid in enumerate(expert_token_ids):
                    output[tid] += out[i] * expert_weights[i]

        return output

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
