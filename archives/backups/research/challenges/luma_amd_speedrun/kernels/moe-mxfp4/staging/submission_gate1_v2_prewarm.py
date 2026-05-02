import os


os.environ["AITER_JIT_DIR"] = "/tmp/aiter_jit_cache"
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
import sys

import torch
from aiter import ActivationType as at
from aiter import QuantType as qt
from aiter import dtypes
from aiter.fused_moe import fused_moe as fm
from aiter.ops.shuffle import shuffle_weight
from aiter.utility import fp4_utils
from task import input_t, output_t


# Pre-warm JIT at import time so sys.path is updated before
# multiprocessing pool workers are forked (Linux fork inherits parent sys.path).
# Uses minimal shapes to trigger moe_sorting + ck2stages builds quickly.
try:
    _M = 4
    _E = 4
    _K = 256  # d_hidden (must be 256-aligned)
    _N = 256  # d_expert (must be 256-aligned)
    _topk = 2
    from aiter import QuantType

    _torch_quant = __import__("aiter").get_torch_quant(QuantType.per_1x32)

    _w1_bf = torch.zeros(_E, 2 * _N, _K, device="cuda", dtype=torch.bfloat16)
    _w2_bf = torch.zeros(_E, _K, _N, device="cuda", dtype=torch.bfloat16)
    _w1_q, _w1_s = _torch_quant(_w1_bf, quant_dtype=dtypes.fp4x2)
    _w2_q, _w2_s = _torch_quant(_w2_bf, quant_dtype=dtypes.fp4x2)
    _w1_q = _w1_q.view(_E, 2 * _N, _K // 2)
    _w2_q = _w2_q.view(_E, _K, _N // 2)
    _w1_sh = shuffle_weight(_w1_q, layout=(16, 16))
    _w2_sh = shuffle_weight(_w2_q, layout=(16, 16))
    _w1_ssh = fp4_utils.e8m0_shuffle(_w1_s)
    _w2_ssh = fp4_utils.e8m0_shuffle(_w2_s)

    _hs = torch.zeros(_M, _K, device="cuda", dtype=torch.bfloat16)
    _tw = torch.ones(_M, _topk, device="cuda", dtype=torch.float32) / _topk
    _ti = torch.zeros(_M, _topk, device="cuda", dtype=torch.int32)

    fm(
        _hs,
        _w1_sh,
        _w2_sh,
        _tw,
        _ti,
        expert_mask=None,
        activation=at.Silu,
        quant_type=qt.per_1x32,
        doweight_stage1=False,
        w1_scale=_w1_ssh,
        w2_scale=_w2_ssh,
        hidden_pad=0,
        intermediate_pad=0,
    )
    torch.cuda.synchronize()
    print("[gate1_v2] JIT prewarm OK — sys.path updated for forked workers", file=sys.stderr)
except Exception as e:
    print(f"[gate1_v2] JIT prewarm FAILED: {e}", file=sys.stderr)


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
