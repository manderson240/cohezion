"""AGI Autoresearch Driver - Cognitive Framework Optimization."""

import asyncio
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


# Add project root to path
sys.path.append(str(Path(__file__).parents[1]))

from cohezion.research.autoresearch_driver import AutoresearchDriver


logger = logging.getLogger(__name__)


@dataclass
class AGIRalphConfig:
    coherence_threshold: float = 0.7
    hiho_threshold: float = 0.5
    max_iterations: int = 10


class AGIAutoresearchDriver:
    """Autoresearch driver for Measuring AGI benchmark."""

    def __init__(self, config: AGIRalphConfig | None = None):
        self.config = config or AGIRalphConfig()
        self.best_score: float = 0.0
        self.iterations: int = 0

    async def run_benchmark(self) -> float:
        """Run the 75-task local benchmark."""
        print("  [AGI] Running local kbench evaluation...")
        # Use unbuffered output to log file
        log_file = f"agi_ar_run_{self.iterations}.log"
        cmd = f"uv run python -u kaggle-agi-benchmark/evaluator_kbench.py > {log_file} 2>&1"
        os.system(cmd)

        # Extract score from log
        try:
            with open(log_file) as f:
                content = f.read()
                m = re.search(r"Final AGI Cognitive Framework Score: ([\d.]+)", content)
                return float(m.group(1)) if m else 0.0
        except:
            return 0.0

    async def run_cycle(self):
        print(f"\n--- AGI Autoresearch Cycle {self.iterations + 1} ---")

        # 1. Local Benchmark
        score = await self.run_benchmark()
        print(f"  Local Benchmark Score: {score:.4f}")

        # 2. Improvement Gate
        if score > self.best_score:
            print("  🔥 Improvement detected! Submitting benchmark results to Kaggle...")
            self.best_score = score

            # Update submission notebook
            # (Assuming notebook generation script handles the data injection)

            # Trigger Kaggle Submission
            kaggle_driver = AutoresearchDriver(target="agi")
            await kaggle_driver.run_kaggle_experiment(
                "improved_reasoning_swarm", f"agi_ar_{self.iterations}"
            )

        self.iterations += 1

    async def run_journey(self):
        for _ in range(self.config.max_iterations):
            await self.run_cycle()
            if self.best_score >= 1.0:
                print("🏆 Perfect score achieved locally. Journey complete.")
                break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    driver = AGIAutoresearchDriver()
    asyncio.run(driver.run_journey())
