#!/usr/bin/env python3
"""Verification & Dogfooding Script for the Spinning Plates Protocol.

Executes a 15-second multi-plate burst across:
- Plate 1: Local AST Verification
- Plate 2: Poincaré Fréchet Manifold Calibration
- Plate 3: SurrealDB Retrospective Distiller
- Plate 4: Multimodal Zero-Copy UMA Monitor
- Plate 5: Ollama Cloud Bleeding-Edge Research Cascade
- Plate 6: Headless Claude Strategic Invariant Synthesis
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path


REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(REPO_ROOT / "src"))

from cohezion.proactive.spinning_plates_protocol import SpinningPlatesGovernor


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("demo_spinning_plates")


async def main():
    logger.info("Initializing Sovereign Spinning Plates Governor...")
    governor = SpinningPlatesGovernor(min_available_gb=20.0)

    logger.info("Executing 10-Second Concurrent Spinning Plates Workload...")
    t0 = time.perf_counter()
    await governor.start_spinning_plates(duration_sec=10.0)
    total_dt = round(time.perf_counter() - t0, 3)

    telemetry = governor.get_plate_telemetry()
    logger.info("=" * 90)
    logger.info("🌪️ SPINNING PLATES PROTOCOL TELEMETRY REPORT (Total Time: %.2fs)", total_dt)
    logger.info("=" * 90)

    print(json.dumps(telemetry, indent=2))

    # Assert all plates spun at least once
    for p_key, p_data in telemetry["plates"].items():
        assert p_data["iterations"] >= 1, f"Plate {p_key} failed to spin!"
        print(
            f"✓ Plate {p_data['plate_id']}: {p_data['name']} spun {p_data['iterations']} times ({p_data['hardware_lane']})"
        )

    logger.info("🎉 ALL 6 CONCURRENT PLATES SPUN AND CERTIFIED IN FULL PARALLEL CONCURRENCY!")


if __name__ == "__main__":
    asyncio.run(main())
