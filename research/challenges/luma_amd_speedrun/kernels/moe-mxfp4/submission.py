"""
MXFP4 MoE — Phase 2: Read dsv3_fp4 model configs + try cktile variants.

Introspection revealed:
1. No tuned CSV for QuantType.per_1x32 — uses 2-stage defaults
2. dsv3_fp4_tuned_fmoe.csv exists in model_configs/ — may have our shapes
3. cktile_moe_stage1/stage2 available as alternatives to ck_moe_stage1/stage2
4. get_2stage_cfgs can be called with our exact shape params

This submission reads the dsv3 configs and tries fused_moe_2stages directly
with custom parameters, falling back to fused_moe on failure.
"""
import sys
import os
from task import input_t, output_t
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe


_dsv3_dumped = False


def _dump_dsv3_configs():
    """One-time dump of DeepSeek V3 FP4 model configs."""
    global _dsv3_dumped
    if _dsv3_dumped:
        return
    _dsv3_dumped = True
    try:
        import aiter
        aiter_path = os.path.dirname(aiter.__file__)
        model_cfg_path = os.path.join(aiter_path, "configs", "model_configs")
        if os.path.isdir(model_cfg_path):
            for f in sorted(os.listdir(model_cfg_path)):
                if 'fp4' in f.lower() or 'dsv3' in f.lower() or 'deepseek' in f.lower():
                    fpath = os.path.join(model_cfg_path, f)
                    print(f"\n=== model_configs/{f} ===", file=sys.stderr)
                    with open(fpath) as fh:
                        content = fh.read()
                        # Print all lines (these files should be small)
                        print(content, file=sys.stderr)
        else:
            print(f"NO_MODEL_CONFIGS_DIR: {model_cfg_path}", file=sys.stderr)

        # Also try get_2stage_cfgs with our exact shape
        from aiter.fused_moe import get_2stage_cfgs
        import torch
        for M, d_hidden, d_expert, E, topk in [
            (8, 4096, 1024, 257, 9),
            (32, 7168, 2048, 33, 9),
            (128, 4096, 1536, 65, 7),
        ]:
            try:
                d_hidden_pad = ((d_hidden + 255) // 256) * 256
                d_expert_pad = ((d_expert + 255) // 256) * 256
                hidden_pad = d_hidden_pad - d_hidden
                intermediate_pad = d_expert_pad - d_expert
                cfgs = get_2stage_cfgs(
                    token=M, model_dim=d_hidden_pad,
                    inter_dim=2 * d_expert_pad,
                    expert=E, topk=topk,
                    dtype=torch.bfloat16,
                    q_dtype_a=torch.float4_e2m1fn_x2,
                    q_dtype_w=torch.float4_e2m1fn_x2,
                    q_type=QuantType.per_1x32,
                    use_g1u1=True,
                    activation=ActivationType.Silu,
                    doweight_stage1=False,
                    hidden_pad=hidden_pad,
                    intermediate_pad=intermediate_pad,
                    is_shuffled=True,
                )
                print(f"2STAGE_CFG M={M} E={E}: {cfgs}", file=sys.stderr)
            except Exception as e:
                print(f"2STAGE_CFG_ERR M={M} E={E}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"DSV3_DUMP_ERR: {e}", file=sys.stderr)


def custom_kernel(data: input_t) -> output_t:
    _dump_dsv3_configs()

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
