"""MoE with KSPLIT=0 (auto-tune) — probe showed auto-tune is best (119µs vs 128.7µs@KSPLIT=2)."""

import os

from aiter import ActivationType as at
from aiter import QuantType as qt
from aiter.fused_moe import fused_moe as fm
from task import input_t, output_t


# KSPLIT=0 means auto-tune — don't bypass tune config, don't set KSPLIT
os.environ["AITER_USE_NT"] = "1"
# Explicitly remove BYPASS and KSPLIT to let aiter auto-tune
os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
os.environ.pop("AITER_KSPLIT", None)


def custom_kernel(data: input_t) -> output_t:
    hs, w1, w2, w1s, w2s, w1sh, w2sh, w1ssh, w2ssh, tw, ti, cfg = data
    return fm(
        hs,
        w1sh,
        w2sh,
        tw,
        ti,
        expert_mask=None,
        activation=at.Silu,
        quant_type=qt.per_1x32,
        doweight_stage1=False,
        w1_scale=w1ssh,
        w2_scale=w2ssh,
        hidden_pad=cfg["d_hidden_pad"] - cfg["d_hidden"],
        intermediate_pad=cfg["d_expert_pad"] - cfg["d_expert"],
    )
