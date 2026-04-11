"""
Unified Probe: FlyDSL + Universal KSPLIT Test
AMD MoE Breakthrough Probes - Session 78

Probe 1: FlyDSL Discovery - Check if MLIR compilation available via Python
Probe 2: Universal KSPLIT=2 - Verify KSPLIT bypasses all CSV tune configs
"""

from __future__ import annotations

import os
import sys
import time
import inspect

import torch
import aiter
from aiter import ActivationType as at
from aiter import QuantType as qt
from aiter.fused_moe import fused_moe as fm
from task import input_t, output_t

_probed = False


def custom_kernel(data: input_t) -> output_t:
    """Unified probe for FlyDSL and KSPLIT validation."""
    global _probed
    hs, w1, w2, w1s, w2s, w1sh, w2sh, w1ssh, w2ssh, tw, ti, cfg = data
    ne = w1sh.shape[0]

    if not _probed:
        _probed = True
        print("\n" + "=" * 60, file=sys.stderr)
        print("UNIFIED PROBE: FlyDSL + Universal KSPLIT", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        # ===== PROBE 1: FlyDSL Availability =====
        print("\n[PROBE 1] FlyDSL Discovery", file=sys.stderr)
        print("-" * 40, file=sys.stderr)
        try:
            import flydsl

            print("✓ FlyDSL AVAILABLE!", file=sys.stderr)
            fly_attrs = [a for a in dir(flydsl) if not a.startswith("_")]
            print(f"  Attributes: {fly_attrs[:15]}", file=sys.stderr)
            if hasattr(flydsl, "__version__"):
                print(f"  Version: {flydsl.__version__}", file=sys.stderr)
            # Check for MLIR-related functions
            mlir_funcs = [a for a in fly_attrs if "mlir" in a.lower()]
            compile_funcs = [a for a in fly_attrs if "compile" in a.lower()]
            print(f"  MLIR functions: {mlir_funcs}", file=sys.stderr)
            print(f"  Compile functions: {compile_funcs}", file=sys.stderr)
        except ImportError as e:
            print(f"✗ FlyDSL NOT available: {e}", file=sys.stderr)
        except Exception as e:
            print(f"✗ FlyDSL error: {e}", file=sys.stderr)

        # Check for rocMLIR
        print("\n[PROBE 1b] rocMLIR/MLIR Python Bindings", file=sys.stderr)
        try:
            import mlir

            print("✓ MLIR Python bindings available", file=sys.stderr)
        except ImportError:
            print("✗ MLIR Python bindings NOT available", file=sys.stderr)

        try:
            import rocmlir

            print("✓ rocMLIR available", file=sys.stderr)
        except ImportError:
            print("✗ rocMLIR NOT available", file=sys.stderr)

        # ===== PROBE 2: Universal KSPLIT=2 =====
        print("\n[PROBE 2] Universal KSPLIT Validation", file=sys.stderr)
        print("-" * 40, file=sys.stderr)

        # Warmup with KSPLIT=2
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

        # Test KSPLIT=4
        os.environ["AITER_KSPLIT"] = "4"
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(5):
            r4 = fm(
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
        t4 = (time.perf_counter() - t0) / 5

        # Test KSPLIT=0 (CSV lookup - no bypass)
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

        # Results
        diff_2_6 = abs(t2 - t6) / max(t2, t6) * 100
        diff_2_4 = abs(t2 - t4) / max(t2, t4) * 100
        diff_csv = abs(t0_time - t2) / max(t0_time, t2) * 100

        print(
            f"  Config: E={ne} bs={cfg.get('bs', '?')} d={cfg.get('d_expert', '?')}",
            file=sys.stderr,
        )
        print(f"  KSPLIT=2:  {t2 * 1e6:.1f} us", file=sys.stderr)
        print(f"  KSPLIT=4:  {t4 * 1e6:.1f} us", file=sys.stderr)
        print(f"  KSPLIT=6:  {t6 * 1e6:.1f} us", file=sys.stderr)
        print(f"  KSPLIT=0 (CSV): {t0_time * 1e6:.1f} us", file=sys.stderr)
        print(f"\n  Difference KSPLIT=2 vs 6: {diff_2_6:.1f}%", file=sys.stderr)
        print(f"  Difference KSPLIT=2 vs 4: {diff_2_4:.1f}%", file=sys.stderr)
        print(f"  Difference CSV vs KSPLIT=2: {diff_csv:.1f}%", file=sys.stderr)

        if diff_2_6 < 2.0:
            print("\n  VERDICT: KSPLIT has NO EFFECT (< 2% difference)", file=sys.stderr)
            print("  CSV configs may be the only tuning mechanism.", file=sys.stderr)
        else:
            print(f"\n  VERDICT: KSPLIT HAS EFFECT ({diff_2_6:.1f}% difference)", file=sys.stderr)
            print("  Universal KSPLIT=2 is a valid bypass strategy.", file=sys.stderr)

        # Check env vars
        print("\n[PROBE 3] AITER Environment", file=sys.stderr)
        print("-" * 40, file=sys.stderr)
        for var in [
            "AITER_KSPLIT",
            "AITER_BYPASS_TUNE_CONFIG",
            "AITER_USE_NT",
            "AITER_MLA_USE_PERSISTENT",
            "AITER_JIT_DIR",
        ]:
            val = os.environ.get(var, "NOT SET")
            print(f"  {var}={val}", file=sys.stderr)

        print("\n" + "=" * 60, file=sys.stderr)
        print("PROBE COMPLETE", file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)

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
