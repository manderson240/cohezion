import os


os.environ["AITER_JIT_DIR"] = "/tmp/aiter_jit_cache"
from aiter import ActivationType as at
from aiter import QuantType as qt
from aiter.fused_moe import fused_moe as fm
from task import input_t, output_t


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
