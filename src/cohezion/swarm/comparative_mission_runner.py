"""
Comparative Mission Runner - Cohezion Platform Ablation Study.

Runs 8 parallel simulations (1M rounds each) to compare:
- Baseline
- Swarm Only
- Flume Only
- Hiho Only
- All combinations
"""

import asyncio
import json
import logging
import multiprocessing
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict

import numpy as np
from cohezion.swarm.hiho_vector_engine import HihoVectorEngine

logger = logging.getLogger(__name__)

def run_single_config(config: Dict[str, Any]):
    """Target function for multiprocessing."""
    engine = HihoVectorEngine(num_rounds=config["num_rounds"])
    results = engine.run_simulation(
        swarm_enabled=config["swarm"],
        flume_enabled=config["flume"],
        hiho_enabled=config["hiho"]
    )
    # Add config name for reference
    results["config_name"] = config["name"]
    results["params"] = {
        "swarm": config["swarm"],
        "flume": config["flume"],
        "hiho": config["hiho"]
    }
    # Convert numpy arrays/scalars to JSON-serializable types
    if "bright_spot_states" in results:
        states = results["bright_spot_states"]
        results["bright_spot_samples"] = states[:50].tolist() if len(states) > 0 else []
        del results["bright_spot_states"]

    results["mean_stability"] = float(results["mean_stability"])
    results["max_reality"] = float(results["max_reality"])
    return results

class ComparativeMissionRunner:
    def __init__(self):
        self.output_dir = Path("src/cohezion/knowledge_graph/universe_nodes/debates/comparative")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.configs = self._generate_configs()

    def _generate_configs(self):
        """Generates the 8 combinations."""
        names = [
            "Baseline", "Swarm_Only", "Flume_Only", "Hiho_Only",
            "Swarm+Flume", "Swarm+Hiho", "Flume+Hiho", "FULL_STACK"
        ]
        configs = []
        i = 0
        for s in [False, True]:
            for f in [False, True]:
                for h in [False, True]:
                    configs.append({
                        "name": names[i],
                        "swarm": s,
                        "flume": f,
                        "hiho": h,
                        "num_rounds": 1_000_000
                    })
                    i += 1
        return configs

    def run_study(self):
        """Runs the 8-way comparative study in parallel."""
        logger.info(f"🚀 Starting 8-Way Comparative Study (Total N=8,000,000)...")
        start_time = time.perf_counter()

        with multiprocessing.Pool(processes=min(8, multiprocessing.cpu_count())) as pool:
            all_results = pool.map(run_single_config, self.configs)

        duration = time.perf_counter() - start_time
        logger.info(f"✅ Study Complete in {duration:.2f} seconds.")

        # Save results
        timestamp = int(time.time())
        study_id = f"comparative_study_{timestamp}"
        output_file = self.output_dir / f"{study_id}.json"

        summary = {
            "study_id": study_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "total_duration_sec": duration,
            "configs": all_results
        }

        output_file.write_text(json.dumps(summary, indent=2))
        logger.info(f"💾 Results saved to {output_file}")

        return summary

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    runner = ComparativeMissionRunner()
    runner.run_study()
