import os

from aiter import ActivationType as at
from aiter import QuantType as qt
from aiter.fused_moe import fused_moe as fm
from task import input_t, output_t


os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
_s = {"k": None}


def _sk(m, e):
    t = "2"
    if m >= 50:
        t = "0"
    elif e >= 200 and m < 10:
        t = "4"
    if _s["k"] != t:
        if t == "0":
            os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
            os.environ.pop("AITER_KSPLIT", None)
        else:
            os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
            os.environ["AITER_KSPLIT"] = t
        _s["k"] = t


def custom_kernel(data: input_t) -> output_t:
    hs, w1, w2, w1s, w2s, w1sh, w2sh, w1ssh, w2ssh, tw, ti, cfg = data
    ne = w1sh.shape[0]
    em = ti.numel() // ne
    _sk(em, ne)
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
