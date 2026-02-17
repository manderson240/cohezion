"""
Unified Master Driver v3.0 - The Ultimate Simulation System
============================================================

Features:
- YAML configuration
- Parallel execution (ThreadPool)
- SurrealDB persistence
- Real-time resource monitoring
- Automatic checkpointing
- Live progress dashboard
- Better physics simulation
- Comprehensive metrics

Usage:
    uv run python scripts/drivers/unified_master_driver.py --config config/simulation.yaml
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# Add scripts/drivers to path
sys.path.insert(0, str(Path(__file__).parent))

from simulation_config import (
    SimulationConfig,
    FlumeConfig,
    RZeroConfig,
    FractalConfig,
    MassSimConfig,
    load_default_config,
)
from resource_monitor import ResourceMonitor, get_resource_monitor
from enhanced_simulation_engine import (
    EnhancedSimulationEngine,
    SimulationResult,
    BatchResult,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [UNIFIED] - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"/home/mike-anderson/nvme-simulations/logs/unified_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)
logger = logging.getLogger("UnifiedMasterDriver")


class LiveDashboard:
    """Real-time dashboard for simulation progress."""

    def __init__(self, update_interval: float = 5.0):
        self.update_interval = update_interval
        self.stats = {}
        self._running = False

    def update(self, phase: str, completed: int, total: int, metrics: dict):
        """Update dashboard with latest stats."""
        self.stats[phase] = {
            "completed": completed,
            "total": total,
            "percent": (completed / total * 100) if total > 0 else 0,
            "metrics": metrics,
            "timestamp": time.time(),
        }

    def render(self) -> str:
        """Render dashboard as string."""
        lines = []
        lines.append("╔════════════════════════════════════════════════════════════╗")
        lines.append("║           🚀 UNIFIED SIMULATION DASHBOARD v3.0             ║")
        lines.append("╚════════════════════════════════════════════════════════════╝")
        lines.append("")

        for phase, stats in self.stats.items():
            percent = stats["percent"]
            bar_length = 30
            filled = int(bar_length * percent / 100)
            bar = "█" * filled + "░" * (bar_length - filled)

            lines.append(f"📊 {phase}")
            lines.append(f"   [{bar}] {percent:.1f}%")
            lines.append(f"   {stats['completed']:,} / {stats['total']:,}")

            if stats.get("metrics"):
                for key, value in list(stats["metrics"].items())[:3]:
                    if isinstance(value, float):
                        lines.append(f"   {key}: {value:.3f}")
                    else:
                        lines.append(f"   {key}: {value}")
            lines.append("")

        return "\n".join(lines)

    def save(self, path: Path):
        """Save dashboard state to JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.stats, f, indent=2)


class UnifiedMasterDriver:
    """Ultimate simulation driver with all enhancements."""

    def __init__(
        self,
        config: SimulationConfig,
        flume_config: FlumeConfig,
        rzero_config: RZeroConfig,
        fractal_config: FractalConfig,
        mass_config: MassSimConfig,
    ):
        self.config = config
        self.flume_config = flume_config
        self.rzero_config = rzero_config
        self.fractal_config = fractal_config
        self.mass_config = mass_config

        self.session_id = (
            config.session_id or f"unified-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.archive_dir = Path(config.archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Components
        self.engine = EnhancedSimulationEngine(config)
        self.resource_monitor = get_resource_monitor()
        self.dashboard = LiveDashboard()

        # Results
        self.results = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "phases": {},
        }

    async def run(self):
        """Execute all simulation phases."""
        logger.info("=" * 70)
        logger.info(f"🚀 UNIFIED MASTER DRIVER v3.0")
        logger.info(f"Session: {self.session_id}")
        logger.info("=" * 70)

        try:
            # Phase 1: FLUME Quadrature
            if self.flume_config.enabled:
                await self._run_flume_phase()

            # Phase 2: R-Zero Pragmatic
            if self.rzero_config.enabled:
                await self._run_rzero_phase()

            # Phase 3: Fractal Universe
            if self.fractal_config.enabled:
                await self._run_fractal_phase()

            # Phase 4: Mass Simulation
            if self.mass_config.enabled:
                await self._run_mass_phase()

            # Complete
            await self._complete()

        except Exception as e:
            logger.exception("❌ Fatal error")
            raise
        finally:
            await self.engine.close()

    async def _run_flume_phase(self):
        """Run FLUME simulations."""
        logger.info("")
        logger.info("🌊 PHASE 1: FLUME Quadrature")
        logger.info(f"   Target: {self.flume_config.target_simulations:,} trajectories")
        logger.info(f"   Streams: {', '.join(self.flume_config.streams)}")

        start_time = time.time()

        # Run parallel simulations
        batches = await self.engine.run_flume_simulations(
            target_count=self.flume_config.target_simulations
        )

        # Collect results
        total = sum(len(b.results) for b in batches)
        duration = time.time() - start_time

        self.results["phases"]["FLUME"] = {
            "status": "completed",
            "simulations": total,
            "duration_seconds": duration,
            "rate": total / duration if duration > 0 else 0,
            "batches": len(batches),
        }

        logger.info(f"✅ FLUME complete: {total:,} trajectories in {duration:.1f}s")

    async def _run_rzero_phase(self):
        """Run R-Zero simulations."""
        logger.info("")
        logger.info("🎯 PHASE 2: R-Zero Pragmatic")
        logger.info(f"   Target: {self.rzero_config.target_simulations:,} simulations")
        logger.info(f"   Initial difficulty: {self.rzero_config.initial_difficulty}")

        start_time = time.time()

        batches = await self.engine.run_rzero_simulations(
            target_count=self.rzero_config.target_simulations
        )

        total = sum(len(b.results) for b in batches)
        duration = time.time() - start_time

        self.results["phases"]["RZero"] = {
            "status": "completed",
            "simulations": total,
            "duration_seconds": duration,
            "rate": total / duration if duration > 0 else 0,
            "batches": len(batches),
        }

        logger.info(f"✅ R-Zero complete: {total:,} simulations in {duration:.1f}s")

    async def _run_fractal_phase(self):
        """Run Fractal Universe simulation."""
        logger.info("")
        logger.info("🌌 PHASE 3: Fractal Universe")
        logger.info(f"   Agents: {self.fractal_config.num_agents:,}")
        logger.info(
            f"   Grid: {self.fractal_config.grid_size}×{self.fractal_config.grid_size}"
        )
        logger.info(f"   Steps: {self.fractal_config.simulation_steps:,}")

        start_time = time.time()

        # Initialize agents
        agents = []
        for i in range(self.fractal_config.num_agents):
            agents.append(
                {
                    "id": i,
                    "x": __import__("random").randint(
                        0, self.fractal_config.grid_size - 1
                    ),
                    "y": __import__("random").randint(
                        0, self.fractal_config.grid_size - 1
                    ),
                    "coherence": 0.5,
                    "energy": 100.0,
                }
            )

        # Run simulation
        for step in range(self.fractal_config.simulation_steps):
            # Update each agent
            for agent in agents:
                # Random walk with coherence drift toward 0.5
                agent["x"] = (
                    agent["x"] + __import__("random").randint(-1, 1)
                ) % self.fractal_config.grid_size
                agent["y"] = (
                    agent["y"] + __import__("random").randint(-1, 1)
                ) % self.fractal_config.grid_size

                # HIHO: Drift toward 0.5 coherence
                target = self.fractal_config.target_coherence
                agent["coherence"] += (
                    target - agent["coherence"]
                ) * self.fractal_config.coherence_learning_rate
                agent["energy"] -= self.fractal_config.agent_energy_decay

            # Progress
            if step % 100 == 0:
                avg_coherence = sum(a["coherence"] for a in agents) / len(agents)
                logger.info(
                    f"   Step {step}/{self.fractal_config.simulation_steps}, coherence={avg_coherence:.3f}"
                )

            await asyncio.sleep(0)

        duration = time.time() - start_time
        final_coherence = sum(a["coherence"] for a in agents) / len(agents)

        self.results["phases"]["Fractal"] = {
            "status": "completed",
            "agents": len(agents),
            "steps": self.fractal_config.simulation_steps,
            "final_coherence": final_coherence,
            "duration_seconds": duration,
        }

        logger.info(
            f"✅ Fractal complete: {len(agents):,} agents × {self.fractal_config.simulation_steps:,} steps"
        )

    async def _run_mass_phase(self):
        """Run Mass Monte Carlo simulation."""
        logger.info("")
        logger.info("⚡ PHASE 4: Mass Simulation")
        logger.info(f"   Target: {self.mass_config.target_sweeps:,} parameter sweeps")

        start_time = time.time()

        # Run parallel sweeps
        def simulate_sweep(idx: int, state: dict) -> SimulationResult:
            """Simulate a single parameter sweep."""
            t_start = time.time()

            # Random parameters
            alpha = __import__("random").uniform(
                self.mass_config.parameter_ranges["alpha"]["min"],
                self.mass_config.parameter_ranges["alpha"]["max"],
            )
            beta = __import__("random").uniform(
                self.mass_config.parameter_ranges["beta"]["min"],
                self.mass_config.parameter_ranges["beta"]["max"],
            )
            gamma = __import__("random").uniform(
                self.mass_config.parameter_ranges["gamma"]["min"],
                self.mass_config.parameter_ranges["gamma"]["max"],
            )

            # Calculate score
            score = alpha * 0.4 + beta * 0.3 + abs(gamma) * 0.3

            return SimulationResult(
                sim_id=f"mass_{idx}",
                score=score,
                metrics={"alpha": alpha, "beta": beta, "gamma": gamma},
                timestamp=time.time(),
                duration_ms=(time.time() - t_start) * 1000,
            )

        batches = await self.engine.run_parallel_simulations(
            simulate_sweep, self.mass_config.target_sweeps, "MassSimulation"
        )

        total = sum(len(b.results) for b in batches)
        duration = time.time() - start_time

        self.results["phases"]["Mass"] = {
            "status": "completed",
            "sweeps": total,
            "duration_seconds": duration,
            "rate": total / duration if duration > 0 else 0,
        }

        logger.info(f"✅ Mass complete: {total:,} sweeps in {duration:.1f}s")

    async def _complete(self):
        """Finalize simulation run."""
        self.results["end_time"] = datetime.now().isoformat()
        self.results["resource_summary"] = self.resource_monitor.get_summary()

        # Calculate totals
        total_sims = sum(
            p.get("simulations", p.get("sweeps", p.get("agents", 0)))
            for p in self.results["phases"].values()
        )

        logger.info("")
        logger.info("=" * 70)
        logger.info("🌟 ALL PHASES COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Session: {self.session_id}")
        logger.info(f"Total simulations/sweeps/agents: {total_sims:,}")

        for phase_name, phase_data in self.results["phases"].items():
            logger.info(f"  {phase_name}: {phase_data['status']}")

        # Save results
        results_path = self.archive_dir / f"unified_results_{self.session_id}.json"
        with open(results_path, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"💾 Results saved: {results_path}")

        # Save resource history
        self.resource_monitor.save_history(
            self.archive_dir / f"resource_history_{self.session_id}.json"
        )

        logger.info("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Unified Master Driver v3.0")
    parser.add_argument("--config", type=Path, help="Path to YAML config file")
    parser.add_argument("--flume", type=int, default=1000, help="FLUME simulations")
    parser.add_argument("--rzero", type=int, default=5000, help="R-Zero simulations")
    parser.add_argument("--fractal", type=int, default=10000, help="Fractal agents")
    parser.add_argument("--mass", type=int, default=50000, help="Mass sweeps")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers")
    args = parser.parse_args()

    # Load or create config
    if args.config and args.config.exists():
        main_config = SimulationConfig.from_yaml(args.config)
        flume_config = FlumeConfig()
        rzero_config = RZeroConfig()
        fractal_config = FractalConfig()
        mass_config = MassSimConfig()
    else:
        main_config, flume_config, rzero_config, fractal_config, mass_config = (
            load_default_config()
        )

    # Override with CLI args
    flume_config.target_simulations = args.flume
    rzero_config.target_simulations = args.rzero
    fractal_config.num_agents = args.fractal
    mass_config.target_sweeps = args.mass
    main_config.max_workers = args.workers

    # Run
    driver = UnifiedMasterDriver(
        main_config, flume_config, rzero_config, fractal_config, mass_config
    )
    asyncio.run(driver.run())


if __name__ == "__main__":
    main()
