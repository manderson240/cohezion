#!/usr/bin/env python3
"""
HIHO Simulation Worker - Runs continuously
Utilizes 1-2 CPU cores, ~10GB RAM per worker
"""

import sys


sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

import json
import time
from datetime import datetime
from pathlib import Path

from cohezion.swarm.hiho_vector_engine import HihoVectorEngine


worker_id = sys.argv[1] if len(sys.argv) > 1 else "1"
output_dir = Path(f"/home/mike-anderson/dev/cohezion/data/overnight/worker_{worker_id}")
output_dir.mkdir(parents=True, exist_ok=True)

print(f"🔬 HIHO Worker {worker_id} starting at {datetime.now()}", flush=True)

iteration = 0
results_log = []

while True:
    iteration += 1
    start = datetime.now()

    # Run 1M HIHO simulation
    engine = HihoVectorEngine(num_rounds=1_000_000)
    results = engine.run_simulation()

    end = datetime.now()
    duration = (end - start).total_seconds()

    result_summary = {
        "worker_id": worker_id,
        "iteration": iteration,
        "timestamp": start.isoformat(),
        "duration_seconds": duration,
        "bright_spots": results["bright_spot_count"],
        "mean_stability": results["mean_stability"],
        "max_reality": results.get("max_reality", 0),
    }

    results_log.append(result_summary)

    print(
        f"[Worker {worker_id}] Iter {iteration}: {results['bright_spot_count']:,} spots, "
        f"stability={results['mean_stability']:.4f}, {duration:.1f}s",
        flush=True,
    )

    # Save every 10 iterations
    if iteration % 10 == 0:
        (output_dir / "results.json").write_text(json.dumps(results_log, indent=2))

    # Brief pause to let other workers run
    time.sleep(5)
