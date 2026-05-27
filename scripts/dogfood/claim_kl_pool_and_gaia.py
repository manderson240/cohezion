#!/usr/bin/env python3
"""Dogfood Claims K + L — HarnessPool slot discovery + gaia_adapter AMD ranking.

K — HarnessPool discovers installed harnesses (pi, opencode, hermes)
L — rank_models_by_amd_optimization() orders NPU < iGPU < CPU < Cloud
M — amd_optimized_hierarchy() builds a 4-tier orchestrator whose first tier
    is the NPU Gemma-4-E2B model (most AMD-native).

These are deterministic claims from the inference package that the first-round
dogfood (Claims A-D) did not exercise. All run without the fleet up.

Run:
    cd /home/mike-anderson/dev/cohezion
    PYTHONPATH=/tmp/cohezion-deliver/src uv run python \\
        /tmp/cohezion-deliver/scripts/dogfood/claim_kl_pool_and_gaia.py

Exit 0 if all claims pass.
"""

from __future__ import annotations

import shutil
import sys


def _header(name: str) -> None:
    print(f"\n=== {name} ===")


def _pass(claim: str, detail: str = "") -> None:
    print(f"PASS  {claim}{' — ' + detail if detail else ''}")


def _fail(claim: str, detail: str) -> None:
    print(f"FAIL  {claim} — {detail}")


def verify_claim_k() -> bool:
    _header("Claim K — HarnessPool discovers installed harnesses")
    from cohezion.inference.harnesses import Harness, HarnessPool

    pool = HarnessPool()
    expected_installed = [h for h in Harness if shutil.which(h.value) is not None]

    if pool.size != len(expected_installed):
        _fail(
            "K",
            f"pool.size={pool.size}, filesystem shows {len(expected_installed)} installed",
        )
        return False

    installed_names = {s.harness.value for s in pool._slots}
    expected_names = {h.value for h in expected_installed}
    if installed_names != expected_names:
        _fail("K", f"installed={installed_names}, expected={expected_names}")
        return False

    if pool.available != pool.size:
        _fail("K", f"fresh pool should have all slots free; available={pool.available}")
        return False

    _pass(
        "K",
        f"pool.size={pool.size} matching binaries on PATH: {sorted(installed_names)}",
    )
    return True


def verify_claim_l() -> bool:
    _header("Claim L — rank_models_by_amd_optimization orders AMD-native first")
    from cohezion.inference.gaia_adapter import rank_models_by_amd_optimization

    # Mix of lanes in non-preferred order — ranker should reshuffle NPU first,
    # cloud last.
    mixed = [
        "claude-haiku-4-5",  # CLOUD_CLAUDE (rank 5)
        "Gemma-4-E2B-it-GGUF",  # NPU (rank 0)
        "gemini-3-flash",  # CLOUD_GEMINI (rank 4)
        "Gemma-4-31B-it-GGUF",  # CPU (rank 2)
        "Gemma-4-E4B-it-GGUF",  # IGPU_ROCWMMA (rank 1)
        "Gemma-4-26B-A4B-it-GGUF",  # IGPU_UNIFIED (rank 1)
    ]
    ranked = rank_models_by_amd_optimization(mixed)

    # NPU must be first, CLOUD_CLAUDE must be last.
    if ranked[0] != "Gemma-4-E2B-it-GGUF":
        _fail("L-first", f"expected NPU first; got {ranked[0]}")
        return False
    if ranked[-1] != "claude-haiku-4-5":
        _fail("L-last", f"expected Claude last; got {ranked[-1]}")
        return False

    # iGPU pair must come before CPU.
    igpu_indices = [
        ranked.index(m)
        for m in ranked
        if m.startswith("Gemma-4-E4B") or m.startswith("Gemma-4-26B")
    ]
    cpu_idx = ranked.index("Gemma-4-31B-it-GGUF")
    if not all(i < cpu_idx for i in igpu_indices):
        _fail("L-igpu-before-cpu", f"iGPU indices {igpu_indices} vs CPU {cpu_idx} in {ranked}")
        return False

    _pass("L", f"ranked={ranked}")
    return True


def verify_claim_m() -> bool:
    _header("Claim M — amd_optimized_hierarchy builds 4-tier local-first orchestrator")
    from cohezion.inference.gaia_adapter import amd_optimized_hierarchy

    orch = amd_optimized_hierarchy(include_cloud=False, max_cost_usd=0.05)

    # No cloud → exactly 4 tiers (NPU, iGPU ROCWMMA, iGPU Unified, CPU)
    if len(orch.tiers) != 4:
        _fail("M-tier-count", f"expected 4 local tiers; got {len(orch.tiers)}")
        return False

    first_model = orch.tiers[0][0]
    if first_model != "Gemma-4-E2B-it-GGUF":
        _fail("M-first-tier", f"expected NPU E2B first; got {first_model}")
        return False

    # With include_cloud=True, we add 2 cloud tiers
    orch_cloud = amd_optimized_hierarchy(include_cloud=True, max_cost_usd=0.05)
    if len(orch_cloud.tiers) != 6:
        _fail("M-cloud-tier-count", f"expected 6 tiers with cloud; got {len(orch_cloud.tiers)}")
        return False

    _pass(
        "M",
        "4 local tiers with E2B first; 6 total with cloud tiers",
    )
    return True


def main() -> int:
    results = [verify_claim_k(), verify_claim_l(), verify_claim_m()]
    print("\n=== Summary ===")
    for label, ok in zip(["K", "L", "M"], results):
        print(f"  {label}: {'PASS' if ok else 'FAIL'}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
