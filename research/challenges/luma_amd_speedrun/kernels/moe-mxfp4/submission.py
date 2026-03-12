"""
MXFP4 MoE — Clean submission (fused_moe with reference parameters).

Phase 2 findings:
- fused_moe_2stages requires pre-sorted tokens (6 extra positional args)
- moe_sorting_fwd lives at aiter.moe_sorting_fwd (not aiter.fused_moe)
- Direct 2-stage call failed: isG1U1 positional arg conflict + GPU memory fault
- cktile_moe_stage1/stage2 exist but need same sorting setup
- No tuned CSV for QuantType.per_1x32 — uses default 2-stage configs

The standard fused_moe with reference parameters is the safest path.
MoE gap is only 1.28x — the kernel is already well-optimized.
"""
from task import input_t, output_t
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe


def custom_kernel(data: input_t) -> output_t:
    (
        hidden_states, gate_up_weight, down_weight,
        gate_up_weight_scale, down_weight_scale,
        gate_up_weight_shuffled, down_weight_shuffled,
        gate_up_weight_scale_shuffled, down_weight_scale_shuffled,
        topk_weights, topk_ids, config,
    ) = data

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]

    output = fused_moe(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        topk_weights,
        topk_ids,
        expert_mask=None,
        activation=ActivationType.Silu,
        quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None,
        a2_scale=None,
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
    )

    return output
