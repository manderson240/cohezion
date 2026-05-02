import os
import sys


# Redirect AITER JIT builds to /tmp and add to sys.path so modules are importable.
# This fixes "No module named 'module_moe_sorting'" — the .so builds to _AITER_JIT_DIR
# but importlib can't find it unless that dir is in sys.path.
_AITER_JIT_DIR = "/tmp/aiter_jit_cache"
os.makedirs(_AITER_JIT_DIR, exist_ok=True)
os.environ["AITER_JIT_DIR"] = _AITER_JIT_DIR
if _AITER_JIT_DIR not in sys.path:
    sys.path.insert(0, _AITER_JIT_DIR)

os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

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
