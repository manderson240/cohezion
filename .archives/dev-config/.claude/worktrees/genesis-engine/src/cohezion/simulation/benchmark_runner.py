"""Simulation Benchmark Runner (v1.0.2 Phase 8).

Standardized benchmarking framework for Cohezion's simulation engine.
Runs reproducible benchmarks at various scales and captures metrics
for cross-run comparison.

Benchmark Configs:
    - smoke: 100 cycles, 16 agents    (~1s)
    - standard: 10_000 cycles, 64 agents  (~30s)
    - stress: 100_000 cycles, 128 agents  (~5min)
    - overnight: 1_000_000 cycles, 256 agents (~1h+)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run."""

    name: str = "smoke"
    num_cycles: int = 100
    num_agents: int = 16
    grid_size: int = 64
    seed: int = 42
    enable_red_team: bool = True
    enable_blue_team: bool = True
    log_interval: int = 10


@dataclass
class BenchmarkMetrics:
    """Metrics captured during a benchmark run."""

    run_id: str = ""
    config_name: str = ""
    total_cycles: int = 0
    wall_time_seconds: float = 0.0
    cycles_per_second: float = 0.0

    # Convergence
    cycles_to_convergence: int = -1
    final_mean_coherence: float = 0.0
    convergence_achieved: bool = False

    # Entropy
    entropy_rate: float = 0.0
    initial_entropy: float = 0.0
    final_entropy: float = 0.0

    # Agents
    agent_survival_rate: float = 0.0
    mean_agent_reward: float = 0.0

    # Emergence (from EmergentDetector)
    emergent_event_count: int = 0
    complexity_score: float = 0.0

    # Resources
    peak_memory_mb: float = 0.0

    # Validation (from SimulationValidator)
    validation_pass: bool = False
    validation_confidence: float = 0.0

    metadata: dict[str, Any] = field(default_factory=dict)


# Predefined benchmark configurations
BENCHMARK_CONFIGS: dict[str, BenchmarkConfig] = {
    "smoke": BenchmarkConfig(
        name="smoke",
        num_cycles=100,
        num_agents=16,
        seed=42,
        log_interval=10,
    ),
    "standard": BenchmarkConfig(
        name="standard",
        num_cycles=10_000,
        num_agents=64,
        seed=42,
        log_interval=100,
    ),
    "stress": BenchmarkConfig(
        name="stress",
        num_cycles=100_000,
        num_agents=128,
        seed=42,
        log_interval=1000,
    ),
    "overnight": BenchmarkConfig(
        name="overnight",
        num_cycles=1_000_000,
        num_agents=256,
        seed=42,
        log_interval=10_000,
    ),
}


class BenchmarkRunner:
    """Run standardized simulation benchmarks.

    Parameters
    ----------
    output_dir : str
        Directory to write benchmark results.
    """

    def __init__(self, output_dir: str = "data/benchmarks") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        config: BenchmarkConfig | None = None,
        config_name: str = "smoke",
    ) -> BenchmarkMetrics:
        """Run a single benchmark.

        Parameters
        ----------
        config : BenchmarkConfig, optional
            Custom config. If None, uses predefined by name.
        config_name : str
            Name of predefined config to use (if config is None).

        Returns
        -------
        BenchmarkMetrics
        """
        if config is None:
            config = BENCHMARK_CONFIGS.get(
                config_name,
                BENCHMARK_CONFIGS["smoke"],
            )

        run_id = f"bench-{config.name}-{int(time.time())}"
        logger.info(
            "Starting benchmark %s: %d cycles, %d agents",
            run_id,
            config.num_cycles,
            config.num_agents,
        )

        # Set seed for reproducibility
        np.random.seed(config.seed)
        import random

        random.seed(config.seed)

        # Initialize simulation
        from cohezion.simulation.fractal_universe import (
            FractalSimulator,
        )

        sim = FractalSimulator(num_agents=config.num_agents)

        coherence_history: list[float] = []
        entropy_history: list[float] = []
        convergence_cycle = -1

        start_time = time.time()

        for cycle in range(config.num_cycles):
            # Run one tick
            sim.grid.update_sectors()
            for agent in sim.agents:
                if agent.energy > 0:
                    agent.move(sim.grid)

            # Capture metrics
            alive = [a for a in sim.agents if a.energy > 0]
            mean_coh = float(np.mean([a.coherence for a in alive])) if alive else 0.0

            coherence_history.append(mean_coh)
            entropy_history.append(sim.grid.global_entropy)

            # Check convergence (within 5% of 0.5)
            if convergence_cycle < 0 and abs(mean_coh - 0.5) < 0.05:
                convergence_cycle = cycle

            # Progress logging
            if cycle % config.log_interval == 0:
                logger.debug(
                    "Cycle %d/%d: coherence=%.4f, entropy=%.4f",
                    cycle,
                    config.num_cycles,
                    mean_coh,
                    sim.grid.global_entropy,
                )

        wall_time = time.time() - start_time

        # Compute final metrics
        coherence_arr = np.array(coherence_history)
        entropy_arr = np.array(entropy_history)
        alive_agents = [a for a in sim.agents if a.energy > 0]

        metrics = BenchmarkMetrics(
            run_id=run_id,
            config_name=config.name,
            total_cycles=config.num_cycles,
            wall_time_seconds=wall_time,
            cycles_per_second=(config.num_cycles / wall_time if wall_time > 0 else 0),
            cycles_to_convergence=convergence_cycle,
            final_mean_coherence=float(coherence_arr[-1]) if len(coherence_arr) > 0 else 0.0,
            convergence_achieved=convergence_cycle >= 0,
            entropy_rate=float(np.mean(np.abs(np.diff(entropy_arr))))
            if len(entropy_arr) > 1
            else 0.0,
            initial_entropy=float(entropy_arr[0]) if len(entropy_arr) > 0 else 0.0,
            final_entropy=float(entropy_arr[-1]) if len(entropy_arr) > 0 else 0.0,
            agent_survival_rate=len(alive_agents) / len(sim.agents) if sim.agents else 0.0,
            mean_agent_reward=float(np.mean([a.cumulative_reward for a in sim.agents]))
            if sim.agents
            else 0.0,
        )

        # Run validation
        try:
            from cohezion.simulation.simulation_validator import (
                SimulationValidator,
            )

            validator = SimulationValidator()
            report = validator.validate(coherence_arr, entropy_arr, run_id=run_id)
            metrics.validation_pass = report.overall_pass
            metrics.validation_confidence = report.confidence_score
        except Exception as e:
            logger.warning("Validation skipped: %s", e)

        # Run emergence detection
        try:
            from cohezion.simulation.emergent_detector import (
                EmergentDetector,
            )

            # Reshape for detector: (T, N) for coherence
            coh_matrix = np.array([[a.coherence for a in sim.agents] for _ in range(1)])
            z_matrix = np.array([[a.z_vector for a in sim.agents] for _ in range(1)])
            detector = EmergentDetector()
            emergence = detector.analyze(coh_matrix, z_matrix, run_id=run_id)
            metrics.emergent_event_count = emergence.event_count
            metrics.complexity_score = emergence.complexity_score
        except Exception as e:
            logger.warning("Emergence detection skipped: %s", e)

        # Save results
        self._save_results(metrics, config)

        logger.info(
            "Benchmark %s complete: %.2fs, %.0f cycles/s, coherence=%.4f, validation=%s",
            run_id,
            wall_time,
            metrics.cycles_per_second,
            metrics.final_mean_coherence,
            "PASS" if metrics.validation_pass else "FAIL",
        )

        return metrics

    def _save_results(
        self,
        metrics: BenchmarkMetrics,
        config: BenchmarkConfig,
    ) -> None:
        """Save benchmark results to JSON."""
        result = {
            "metrics": asdict(metrics),
            "config": asdict(config),
        }

        output_file = self.output_dir / f"{metrics.run_id}.json"
        output_file.write_text(
            json.dumps(result, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("Results saved to %s", output_file)

    def compare(
        self,
        run_ids: list[str] | None = None,
    ) -> str:
        """Compare results across runs.

        Parameters
        ----------
        run_ids : list[str], optional
            Specific runs to compare. If None, compare all.

        Returns
        -------
        str
            Markdown comparison table.
        """
        json_files = sorted(self.output_dir.glob("bench-*.json"))
        results: list[dict[str, Any]] = []

        for f in json_files:
            data = json.loads(f.read_text())
            if run_ids and data["metrics"]["run_id"] not in run_ids:
                continue
            results.append(data)

        if not results:
            return "No benchmark results found."

        lines = [
            "# Benchmark Comparison",
            "",
            "| Run | Config | Cycles | Time(s) | Cyc/s | Coherence | Converged | Validation |",
            "|-----|--------|--------|---------|-------|-----------|-----------|------------|",
        ]

        for r in results:
            m = r["metrics"]
            lines.append(
                f"| {m['run_id'][:20]} | {m['config_name']} | "
                f"{m['total_cycles']} | {m['wall_time_seconds']:.1f} | "
                f"{m['cycles_per_second']:.0f} | "
                f"{m['final_mean_coherence']:.4f} | "
                f"{'✅' if m['convergence_achieved'] else '❌'} | "
                f"{'✅' if m['validation_pass'] else '❌'} |"
            )

        return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run simulation benchmarks")
    parser.add_argument(
        "--config",
        default="smoke",
        choices=list(BENCHMARK_CONFIGS.keys()),
        help="Benchmark configuration to run",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare existing results instead of running",
    )
    args = parser.parse_args()

    runner = BenchmarkRunner()
    if args.compare:
        print(runner.compare())
    else:
        runner.run(config_name=args.config)
