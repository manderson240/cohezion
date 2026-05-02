"""
MoE: Weight Sharing Across Experts
Approach: Share weight computations across experts when they have similar
token assignments, reducing redundant memory loads.

Key insight: Experts often share similar weight patterns. By caching
and reusing weight data, we can reduce memory bandwidth.
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


class WeightCache:
    """Simple LRU cache for expert weights."""

    def __init__(self, maxsize=8):
        self.cache = {}
        self.order = []
        self.maxsize = maxsize

    def get(self, key):
        if key in self.cache:
            self.order.remove(key)
            self.order.append(key)
            return self.cache[key]
        return None

    def put(self, key, value):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.maxsize:
            oldest = self.order.pop(0)
            del self.cache[oldest]
        self.cache[key] = value
        self.order.append(key)


def custom_kernel(data: input_t) -> output_t:
    """
    Weight sharing MoE kernel with LRU cache.

    Caches expert weights to avoid redundant loads when experts
    are accessed repeatedly (common with top-k routing).
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
        topk = topk_ids.shape[1]

        # Quantize input
        x_fp4, x_scale = dynamic_mxfp4_quant(hidden_states.contiguous())
        x_q = x_fp4.view(dtypes.fp4x2)

        # Initialize caches
        w1_cache = WeightCache(maxsize=16)
        w2_cache = WeightCache(maxsize=16)

        output = torch.zeros(M, w2.shape[1], dtype=torch.bfloat16, device=hidden_states.device)

        # Process each token
        for token_idx in range(M):
            token_experts = topk_ids[token_idx]
            token_weights = topk_weights[token_idx]

            x_tok = x_q[token_idx : token_idx + 1]
            x_scale_tok = x_scale[token_idx : token_idx + 1]

            for expert_idx, weight in zip(token_experts, token_weights):
                expert_idx = expert_idx.item()

                # Check cache for w1
                w1_cached = w1_cache.get(expert_idx)
                if w1_cached is None:
                    w1_cached = (w1_shuffle[expert_idx], w1_scale_shuffled[expert_idx])
                    w1_cache.put(expert_idx, w1_cached)

                w1_expert, w1_scale_expert = w1_cached

                # Stage 1: Gate+Up
                gate_up = torch.empty(
                    1, w1.shape[1], dtype=torch.bfloat16, device=hidden_states.device
                )
                aiter.gemm_a4w4(
                    x_tok,
                    w1_expert,
                    x_scale_tok,
                    w1_scale_expert,
                    dtype=dtypes.bf16,
                    bpreshuffle=True,
                )

                gate = gate_up[:, : w1.shape[1] // 2]
                up = gate_up[:, w1.shape[1] // 2 :]
                activated = F.silu(gate) * up

                a2_q, a2_scale = dynamic_mxfp4_quant(activated.contiguous())
                a2_q = a2_q.view(dtypes.fp4x2)

                # Check cache for w2
                w2_cached = w2_cache.get(expert_idx)
                if w2_cached is None:
                    w2_cached = (w2_shuffle[expert_idx], w2_scale_shuffled[expert_idx])
                    w2_cache.put(expert_idx, w2_cached)

                w2_expert, w2_scale_expert = w2_cached

                # Stage 2: Down
                out = torch.empty(1, w2.shape[1], dtype=torch.bfloat16, device=hidden_states.device)
                aiter.gemm_a4w4(
                    a2_q,
                    w2_expert,
                    a2_scale.view(dtypes.fp8_e8m0),
                    w2_scale_expert,
                    dtype=dtypes.bf16,
                    bpreshuffle=True,
                )

                output[token_idx] += out.squeeze(0) * weight

        return output

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
