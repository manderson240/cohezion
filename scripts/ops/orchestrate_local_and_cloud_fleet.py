#!/usr/bin/env python3
"""CLI for orchestrating Local Silicon (Lemonade :13305) and Ollama Cloud (:11434).

Enforces:
- COHEZION-T2-ARCH-094 Compute Partitioning
- arXiv:2608.25924 VGI Code-as-Perception
- Strict Active Kaggle Competition Filter (excludes Pokémon TCG)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# Ensure src is in sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from cohezion.inference.vgi_fleet_orchestrator import (  # noqa: E402
    ACTIVE_COMPETITIONS,
    VGIFleetOrchestrator,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Orchestrate Local Silicon and Ollama Cloud for VGI and Kaggle campaigns."
    )
    parser.add_argument(
        "--status", action="store_true", help="Display fleet and competition status"
    )
    parser.add_argument(
        "--run-vgi-cycle", action="store_true", help="Execute an autonomous VGI cycle"
    )
    parser.add_argument(
        "--competition",
        choices=ACTIVE_COMPETITIONS,
        default="arc-prize-2026-arc-agi-3",
        help="Target competition for VGI cycle",
    )
    parser.add_argument("--persist", action="store_true", help="Persist execution to SurrealDB")

    args = parser.parse_args()
    orchestrator = VGIFleetOrchestrator()

    if args.status or not (args.run_vgi_cycle):
        print("=" * 70)
        print("COHEZION VGI HYBRID FLEET & COMPETITIONS AUDIT")
        print("=" * 70)
        health = orchestrator.check_fleet_health()
        print(f"Lemonade Local NPU Healthy:  {health.local_npu_healthy}")
        print(f"Lemonade Local iGPU Healthy: {health.local_igpu_healthy}")
        print(f"Ollama Cloud Healthy:        {health.cloud_healthy}")
        print(
            f"Loaded Local Models ({len(health.loaded_models)}): {', '.join(health.loaded_models[:6])}..."
        )
        print(
            f"Cloud Models ({len(health.cloud_models)}):        {', '.join(health.cloud_models[:6])}..."
        )
        print("-" * 70)
        print("ACTIVE KAGGLE COMPETITIONS (Strict Whitelist):")
        submissions = orchestrator.audit_active_submissions()
        for sub in submissions:
            print(
                f"  [{sub['competition']}] Ref: {sub.get('latest_ref')} | "
                f"Status: {sub.get('status')} | Score: {sub.get('score')} | "
                f"Desc: {sub.get('description')[:50]}..."
            )
        print("=" * 70)

    if args.run_vgi_cycle:
        print("\nExecuting VGI Code-as-Perception Cycle (arXiv:2608.25924)...")
        # Representative ARC spatial task grid (3x3 with color markers)
        sample_grid = [
            [0, 1, 0],
            [1, 2, 1],
            [0, 1, 0],
        ]
        result = orchestrator.execute_vgi_cycle(
            competition=args.competition,
            task_id="task_arc3_affordance_vgi_001",
            task_desc="Preserve core marker color 2 and dilate border affordance color 1 outward",
            grid=sample_grid,
        )
        print(f"Competition:          {result.competition}")
        print(f"Task ID:              {result.task_id}")
        print(f"Spatial Invariants:   {json.dumps(result.spatial_invariants)}")
        print(f"Model Chain:          {' -> '.join(result.model_chain)}")
        print(f"AutoHarness Verified: {result.autoharness_verified}")
        print(f"Execution Success:    {result.execution_success}")
        print(f"Output:               {result.execution_output}")
        print(f"Cycle Latency:        {result.latency_ms:.2f} ms")

        if args.persist:
            persisted = orchestrator.persist_cycle_record(result)
            print(f"Persisted to SurrealDB: {persisted}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
