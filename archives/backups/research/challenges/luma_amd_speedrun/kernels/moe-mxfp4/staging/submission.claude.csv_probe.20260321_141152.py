"""Probe: Inspect the runner's CSV tuning config for MXFP4 MoE shapes."""

import os


os.environ["AITER_USE_NT"] = "1"

from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    (
        hidden_states,
        gate_up_weight,
        down_weight,
        gate_up_weight_scale,
        down_weight_scale,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        gate_up_weight_scale_shuffled,
        down_weight_scale_shuffled,
        topk_weights,
        topk_ids,
        config,
    ) = data

    # Probe: Dump the CSV tuning database
    import csv
    import glob

    csv_files = glob.glob("/home/runner/aiter/aiter/configs/*.csv") + glob.glob(
        "/home/runner/aiter/aiter/configs/model_configs/*.csv"
    )
    for f in sorted(csv_files):
        if "fmoe" in f.lower() or "moe" in f.lower():
            print(f"\n=== {f} ===")
            try:
                with open(f) as fh:
                    reader = csv.reader(fh)
                    for i, row in enumerate(reader):
                        if i < 3 or "fp4" in str(row).lower() or "per_1x32" in str(row).lower():
                            print(f"  [{i}] {row}")
                        if i > 50:
                            print(f"  ... ({i}+ rows)")
                            break
            except Exception as e:
                print(f"  ERROR: {e}")

    # Also check available fused_moe kwargs
    import inspect

    sig = inspect.signature(fused_moe)
    print("\n=== fused_moe signature ===")
    for name, param in sig.parameters.items():
        print(
            f"  {name}: {param.default if param.default is not inspect.Parameter.empty else '(required)'}"
        )

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
