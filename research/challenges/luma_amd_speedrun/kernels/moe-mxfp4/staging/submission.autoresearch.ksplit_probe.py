import os
import sys
import time

import torch
from aiter import ActivationType as at
from aiter import QuantType as qt
from aiter.fused_moe import fused_moe as fm
from task import input_t, output_t


_probed = False


def custom_kernel(data: input_t) -> output_t:
    global _probed
    hs, w1, w2, w1s, w2s, w1sh, w2sh, w1ssh, w2ssh, tw, ti, cfg = data
    ne = w1sh.shape[0]

    # Run the probe ONCE on first call
    if not _probed:
        _probed = True
        # Warmup
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"
        for _ in range(3):
            _ = fm(
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
        torch.cuda.synchronize()

        # Test KSPLIT=2
        os.environ["AITER_KSPLIT"] = "2"
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(5):
            r2 = fm(
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
            torch.cuda.synchronize()
        t2 = (time.perf_counter() - t0) / 5

        # Test KSPLIT=6
        os.environ["AITER_KSPLIT"] = "6"
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(5):
            r6 = fm(
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
            torch.cuda.synchronize()
        t6 = (time.perf_counter() - t0) / 5

        # Test KSPLIT=0 (no bypass)
        os.environ.pop("AITER_BYPASS_TUNE_CONFIG", None)
        os.environ.pop("AITER_KSPLIT", None)
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(5):
            r0 = fm(
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
            torch.cuda.synchronize()
        t0_time = (time.perf_counter() - t0) / 5

        diff_pct = abs(t2 - t6) / max(t2, t6) * 100
        print(
            f"[KSPLIT PROBE] E={ne} bs={cfg.get('bs', '?')} d={cfg.get('d_expert', '?')}",
            file=sys.stderr,
        )
        print(f"[KSPLIT PROBE] KSPLIT=2: {t2 * 1e6:.1f}us", file=sys.stderr)
        print(f"[KSPLIT PROBE] KSPLIT=6: {t6 * 1e6:.1f}us", file=sys.stderr)
        print(f"[KSPLIT PROBE] KSPLIT=0 (auto): {t0_time * 1e6:.1f}us", file=sys.stderr)
        print(f"[KSPLIT PROBE] Difference: {diff_pct:.1f}%", file=sys.stderr)
        if diff_pct < 2.0:
            print("[KSPLIT PROBE] VERDICT: KSPLIT has NO EFFECT (< 2% difference)", file=sys.stderr)
        else:
            print(
                f"[KSPLIT PROBE] VERDICT: KSPLIT HAS EFFECT ({diff_pct:.1f}% difference)",
                file=sys.stderr,
            )

        # Restore default for actual benchmark
        os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
        os.environ["AITER_KSPLIT"] = "2"

    # Normal execution for correctness check
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
