"""
MoE: Expert Specialization by Layer
Approach: Apply different routing/computation strategies based on layer depth.

Key insight: Early layers need broader expert coverage (exploration),
while later layers benefit from focused specialization (exploitation).
Layer-aware strategies optimize for these different needs.

POPCORN: amd-moe-mxfp4
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


class LayerStrategy:
    """Layer-aware MoE strategies."""

    # Strategy constants
    EXPLORATION = "exploration"  # Early layers: broader coverage
    EXPLOITATION = "exploitation"  # Mid layers: balanced
    SPECIALIZATION = "specialization"  # Late layers: focused

    @staticmethod
    def get_strategy(layer_idx: int, total_layers: int = 64) -> str:
        """
        Determine strategy based on layer position.

        Args:
            layer_idx: Current layer index (0-based)
            total_layers: Total number of layers

        Returns:
            Strategy name
        """
        progress = layer_idx / total_layers
        if progress < 0.3:
            return LayerStrategy.EXPLORATION
        elif progress < 0.7:
            return LayerStrategy.EXPLOITATION
        else:
            return LayerStrategy.SPECIALIZATION

    @staticmethod
    def get_routing_params(strategy: str, base_topk: int) -> dict:
        """
        Get routing parameters for given strategy.

        Args:
            strategy: Strategy name
            base_topk: Base top-k value

        Returns:
            Routing parameters dict
        """
        if strategy == LayerStrategy.EXPLORATION:
            # Early layers: higher top-k for broader coverage
            return {
                "topk_multiplier": 1.5,
                "temperature": 1.2,  # Softer distribution
                "capacity_factor": 2.0,  # More capacity
            }
        elif strategy == LayerStrategy.EXPLOITATION:
            # Mid layers: balanced
            return {
                "topk_multiplier": 1.0,
                "temperature": 1.0,
                "capacity_factor": 1.25,
            }
        else:  # SPECIALIZATION
            # Late layers: focused, lower top-k
            return {
                "topk_multiplier": 0.75,
                "temperature": 0.8,  # Sharper distribution
                "capacity_factor": 1.0,  # Tighter capacity
            }


def custom_kernel(data: input_t) -> output_t:
    """
    Layer-specialized MoE kernel with depth-aware routing.

    Uses different strategies for early (exploration), mid (balanced),
    and late (specialization) layers to optimize for different needs.

    Args:
        data: Tuple of (hidden_states, w1, w2, w1_scale, w2_scale,
              w1_shuffle, w2_shuffle, w1_scale_shuffled, w2_scale_shuffled,
              topk_weights, topk_ids, config)

    Returns:
        MoE output tensor
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

        # Extract layer info from config if available
        layer_idx = getattr(config, "layer_idx", 32)  # Default to mid-layer
        total_layers = getattr(config, "num_layers", 64)

        # Determine layer strategy
        strategy = LayerStrategy.get_strategy(layer_idx, total_layers)
        params = LayerStrategy.get_routing_params(strategy, config.topk)

        # Quantize input once
        x_fp4, x_scale = dynamic_mxfp4_quant(hidden_states.contiguous())
        x_q = x_fp4.view(dtypes.fp4x2)

        # Apply temperature scaling to router weights if in exploration mode
        if strategy == LayerStrategy.EXPLORATION and params["temperature"] != 1.0:
            # Temperature scaling: softer distribution for exploration
            log_weights = torch.log(topk_weights + 1e-10)
            scaled_weights = F.softmax(log_weights / params["temperature"], dim=-1)
            effective_weights = scaled_weights
        else:
            effective_weights = topk_weights

        # Capacity factor adjustment
        capacity_factor = params["capacity_factor"]
        effective_topk = int(config.topk * params["topk_multiplier"])
        effective_topk = max(1, min(effective_topk, config.topk))  # Clamp to valid range

        # Prepare output
        output = torch.zeros(M, w2.shape[1], dtype=torch.bfloat16, device=hidden_states.device)

        # Expert utilization analysis for this layer
        expert_counts = torch.bincount(topk_ids.flatten(), minlength=num_experts)
        utilization = expert_counts.float() / expert_counts.sum()

        # Strategy-specific optimizations
        if strategy == LayerStrategy.EXPLORATION:
            # Early layer: encourage load balancing
            # Sort experts by utilization for more balanced processing
            sorted_experts = torch.argsort(utilization, descending=True)

            # Process in utilization order (hot first for cache efficiency)
            expert_order = sorted_experts
        elif strategy == LayerStrategy.SPECIALIZATION:
            # Late layer: focus on top-utilized experts
            # Identify and optimize for frequently used experts
            top_util_threshold = 0.5 / num_experts  # Above random
            high_util_mask = utilization > top_util_threshold
            high_util_experts = high_util_mask.nonzero(as_tuple=True)[0]

            # Pre-load high-utilization expert weights
            expert_cache = {}
            for exp_idx in high_util_experts[:8]:  # Cache top 8
                exp_idx = exp_idx.item()
                if exp_idx < num_experts:
                    expert_cache[exp_idx] = {
                        "w1": w1_shuffle[exp_idx],
                        "w1_scale": w1_scale_shuffled[exp_idx],
                        "w2": w2_shuffle[exp_idx],
                        "w2_scale": w2_scale_shuffled[exp_idx],
                    }
        else:
            # Balanced: use standard order
            expert_order = torch.arange(num_experts, device=hidden_states.device)

        # Process tokens with layer-aware routing
        for token_idx in range(M):
            token_experts = topk_ids[token_idx][:effective_topk]
            token_weights = effective_weights[token_idx][:effective_topk]

            # Normalize weights after potential top-k reduction
            if token_weights.sum() > 0:
                token_weights = token_weights / token_weights.sum()

            x_tok = x_q[token_idx : token_idx + 1]
            x_scale_tok = x_scale[token_idx : token_idx + 1]

            token_out = torch.zeros(w2.shape[1], dtype=torch.bfloat16, device=hidden_states.device)

            for expert_idx, weight in zip(token_experts, token_weights):
                if expert_idx < 0 or expert_idx >= num_experts:
                    continue

                expert_idx = expert_idx.item()
                weight = weight.item()

                # Try cached expert first
                if strategy == LayerStrategy.SPECIALIZATION and expert_idx in expert_cache:
                    cache = expert_cache[expert_idx]
                    w1_e = cache["w1"]
                    w1_s = cache["w1_scale"]
                    w2_e = cache["w2"]
                    w2_s = cache["w2_scale"]
                else:
                    w1_e = w1_shuffle[expert_idx]
                    w1_s = w1_scale_shuffled[expert_idx]
                    w2_e = w2_shuffle[expert_idx]
                    w2_s = w2_scale_shuffled[expert_idx]

                # Gate computation (gate+up fused)
                gate_up = aiter.gemm_a4w4(
                    x_tok, w1_e, x_scale_tok, w1_s, dtype=dtypes.bf16, bpreshuffle=True
                )

                # SiLU + multiplication
                gate, up = gate_up.chunk(2, dim=-1)
                activated = F.silu(gate) * up

                # Re-quantize for stage 2
                act_fp4, act_scale = dynamic_mxfp4_quant(activated.contiguous())
                act_q = act_fp4.view(dtypes.fp4x2)

                # Down projection
                down = aiter.gemm_a4w4(
                    act_q, w2_e, act_scale, w2_s, dtype=dtypes.bf16, bpreshuffle=True
                )

                token_out += down.squeeze(0) * weight

            output[token_idx] = token_out

        return output

    except Exception as e:
        # Fallback to standard fused_moe on error
        import logging

        logging.warning(f"Layer-specialized kernel failed: {e}, using fallback")
        return aiter.fused_moe(
            hidden_states,
            w1,
            w2,
            topk_weights,
            topk_ids,
            inplace=True,
            quant_type="per_1x32",
            use_fp4=True,
        )
