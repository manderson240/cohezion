import os
import sys

import torch
from aiter import ActivationType as at
from aiter import QuantType as qt
from aiter.fused_moe import fused_moe as fm
from task import input_t, output_t


# Contingency: No KSPLIT manipulation. Focus on:
# 1. OPUS token sorting for better memory coalescing
# 2. Activation pre-quantization via a1_scale/a2_scale
# 3. Auto-tune (no BYPASS) for large-batch shapes
# 4. AITER_USE_NT=1 for non-transposed layout
os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_USE_OPUS_MOE_SORTING"] = "1"

_probed = False
_prequant_helps = False


def custom_kernel(data: input_t) -> output_t:
    global _probed, _prequant_helps
    hs, w1, w2, w1s, w2s, w1sh, w2sh, w1ssh, w2ssh, tw, ti, cfg = data
    ne = w1sh.shape[0]
    M = hs.shape[0]
    hp = cfg["d_hidden_pad"] - cfg["d_hidden"]
    ip = cfg["d_expert_pad"] - cfg["d_expert"]

    # On first call, probe whether pre-quantized activations help
    if not _probed:
        _probed = True
        # Try pre-quantizing activations
        try:
            from aiter.ops.triton.quant import dynamic_mxfp4_quant

            a_q, a_s = dynamic_mxfp4_quant(hs)
            # Warmup both paths
            for _ in range(2):
                fm(
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
                    hidden_pad=hp,
                    intermediate_pad=ip,
                )
            torch.cuda.synchronize()
            import time

            # Time without pre-quant
            t0 = time.perf_counter()
            for _ in range(5):
                fm(
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
                    hidden_pad=hp,
                    intermediate_pad=ip,
                )
                torch.cuda.synchronize()
            t_no = (time.perf_counter() - t0) / 5
            # Time with pre-quant (pass a1_scale)
            t0 = time.perf_counter()
            for _ in range(5):
                fm(
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
                    a1_scale=a_s,
                    hidden_pad=hp,
                    intermediate_pad=ip,
                )
                torch.cuda.synchronize()
            t_pre = (time.perf_counter() - t0) / 5
            pct = abs(t_no - t_pre) / max(t_no, t_pre) * 100
            _prequant_helps = t_pre < t_no * 0.98
            print(f"[CONTINGENCY] E={ne} M={M} d={cfg.get('d_expert', '?')}", file=sys.stderr)
            print(f"[CONTINGENCY] No pre-quant: {t_no * 1e6:.1f}us", file=sys.stderr)
            print(f"[CONTINGENCY] With a1_scale: {t_pre * 1e6:.1f}us", file=sys.stderr)
            print(
                f"[CONTINGENCY] Diff: {pct:.1f}% prequant_helps={_prequant_helps}", file=sys.stderr
            )
            print("[CONTINGENCY] OPUS_SORTING=1, USE_NT=1", file=sys.stderr)
        except Exception as e:
            print(f"[CONTINGENCY] Pre-quant probe failed: {e}", file=sys.stderr)

    # Use auto-tune for large batches (no BYPASS), bypass for small batches
    em = ti.numel() // ne  # estimated tokens per expert
    if M >= 256:
        # Large batch: let auto-tuner pick
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
    else:
        # Small batch: bypass tune config (faster startup)
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ.pop("AITER_KSPLIT", None)

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
        hidden_pad=hp,
        intermediate_pad=ip,
    )
