"""Top-level mass simulation orchestrator.

Coordinates universe generation, agent population, batch simulation,
persistence, analysis, and artifact generation with OOM protection.
"""

from __future__ import annotations

import asyncio
import logging
import time

from cohezion.mass_sim.agent_factory import AgentFactory
from cohezion.mass_sim.analysis import SimulationAnalyzer
from cohezion.mass_sim.artifacts import ArtifactGenerator
from cohezion.mass_sim.batch_runner import BatchSimulationRunner
from cohezion.mass_sim.config import (
    SimulationConfig,
    SimulationReport,
    UniverseSpec,
)
from cohezion.mass_sim.persistence import SimulationPersistence
from cohezion.mass_sim.system_monitor import MemoryGuard


logger = logging.getLogger(__name__)


class MassSimOrchestrator:
    """Orchestrate mass simulation across universes.

    Flow:
        1. Generate agent population (shared across universes)
        2. For each universe: create weights -> simulate -> persist -> artifacts
        3. Cross-universe analysis
        4. Final report
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.runner = BatchSimulationRunner(config)
        self.persistence = SimulationPersistence(config)
        self.analyzer = SimulationAnalyzer()
        self.artifact_gen = ArtifactGenerator(config.artifact_dir)
        self.guard = MemoryGuard(max_memory_gb=config.max_memory_gb)

    async def run(self) -> SimulationReport:
        """Execute the full mass simulation."""
        t0 = time.time()
        run_id = f"mass_sim_{int(t0)}"
        cfg = self.config
        scale = cfg.scale

        logger.info(f"Mass Simulation {run_id}")
        logger.info(
            f"  Scale: {scale.name} | {scale.n_agents} agents x {scale.n_epochs} epochs x {scale.n_universes} universes"
        )
        logger.info(f"  Navigator: {'FULL' if cfg.use_navigator else 'JITTER'}")
        self.guard.log_status("  Initial ")

        # Store run metadata
        await self.persistence.store_run_metadata(run_id, cfg)

        # Generate universe seeds
        universe_seeds = cfg.universe_seeds or list(range(scale.n_universes))

        # Generate shared agent population
        logger.info("  Generating agent population...")
        agents = AgentFactory.create_batch(
            scale.n_agents,
            cfg.agent_seed_base,
            z_dim=256,
        )
        logger.info(f"  Population: {agents.shape} ({agents.nbytes / 1e6:.1f} MB)")

        # Simulate each universe
        all_results = []
        for i, seed in enumerate(universe_seeds):
            # OOM check before each universe
            if self.guard.should_abort():
                logger.error(f"Aborting at universe {i}/{len(universe_seeds)} (memory)")
                break

            spec = UniverseSpec(f"universe_{seed}", seed)
            logger.info(f"Universe {i + 1}/{len(universe_seeds)}: seed={seed}")

            # Run simulation in thread pool (CPU-bound Rust work)
            result = await asyncio.to_thread(self.runner.simulate_universe, spec, agents)

            all_results.append(result)

            # Persist per-universe results
            await self.persistence.store_universe_result(run_id, result)

            # Generate per-universe artifacts
            self.artifact_gen.generate_universe_artifacts(result)

            # Periodic memory status
            if (i + 1) % 10 == 0:
                self.guard.log_status(f"  After {i + 1} universes: ")

        # Cross-universe analysis
        logger.info("Computing Anthropic-style insights...")
        insights = self.analyzer.analyze_all(all_results, cfg.coherence_bounds)

        # Build report
        elapsed = time.time() - t0
        report = SimulationReport(
            run_id=run_id,
            config_name=scale.name,
            n_universes=len(all_results),
            n_agents=scale.n_agents,
            n_epochs=scale.n_epochs,
            universe_results=all_results,
            insights=insights,
            total_elapsed_seconds=elapsed,
        )

        # Generate cross-universe artifacts
        report_artifacts = self.artifact_gen.generate_report_artifacts(report)
        report.artifacts = [str(p) for p in report_artifacts if p]
        report.artifacts.extend(self.artifact_gen.generated)

        # Persist final report
        await self.persistence.store_report(run_id, report)

        # Final summary
        logger.info("=" * 60)
        logger.info(f"COMPLETE: {run_id}")
        logger.info(f"  Universes: {len(all_results)}/{len(universe_seeds)}")
        logger.info(f"  Elapsed: {elapsed:.1f}s")
        logger.info(f"  Artifacts: {len(report.artifacts)}")

        perf = insights.get("performance", {})
        logger.info(f"  Throughput: {perf.get('throughput_agent_epochs_per_sec', 0):,.0f} agent-epochs/sec")

        safety = insights.get("safety", {})
        logger.info(f"  Safety: {safety.get('mean_final_within_bounds', 0):.1%} agents within HIHO bounds")

        self.guard.log_status("  Final ")
        logger.info("=" * 60)

        return report
