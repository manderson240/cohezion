import os
import sys


os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"

# Fix for aiter JIT "No module named 'module_moe_sorting'" on GitHub Actions runners.
# aiter builds .so files to /home/runner/aiter/aiter/jit/build/<module>/ but the install
# step (copy to jit/) is blocked by filesystem permissions. Pre-inject build subdirs so
# importlib.import_module() finds the .so directly in the build directory.
_AITER_JIT_BUILD = "/home/runner/aiter/aiter/jit/build"
for _mod in (
    "module_moe_sorting",
    "module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_",
):
    _p = os.path.join(_AITER_JIT_BUILD, _mod)
    if _p not in sys.path:
        sys.path.insert(0, _p)

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
