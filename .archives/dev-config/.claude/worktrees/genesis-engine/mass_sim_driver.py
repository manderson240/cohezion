"""Mass simulation CLI driver.

Entry point for run_mass_sim.sh. Runs the physics-based simulation
pipeline (not the LLM swarm) with OOM protection and .npy export
for FLUME VAE training.

Usage:
    python mass_sim_driver.py --scale overnight --max-mem 100 --output-dir data/mass_sim/artifacts
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from cohezion.mass_sim.config import SCALE_TIERS, SimulationConfig
from cohezion.mass_sim.orchestrator import MassSimOrchestrator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("mass_sim_driver")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mass simulation driver")
    parser.add_argument(
        "--scale",
        choices=list(SCALE_TIERS.keys()),
        default="medium",
        help="Scale tier (default: medium)",
    )
    parser.add_argument(
        "--max-mem",
        type=float,
        default=100.0,
        help="Max RSS in GB before abort (default: 100)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/mass_sim/artifacts",
        help="Directory for .npy output files",
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=None,
        help="Override agent count from scale tier",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Override epoch count from scale tier",
    )
    parser.add_argument(
        "--universes",
        type=int,
        default=None,
        help="Override universe count from scale tier",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Disable SurrealDB persistence (JSONL fallback only)",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Disable .npy export of final states",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    scale = SCALE_TIERS[args.scale]
    logger.info(f"Scale tier: {scale.name}")
    logger.info(f"  {scale.n_agents} agents x {scale.n_epochs} epochs x {scale.n_universes} universes")

    config = SimulationConfig(
        scale=scale,
        max_memory_gb=args.max_mem,
        persist_to_db=not args.no_db,
        export_npy=not args.no_export,
    )

    if args.output_dir:
        from pathlib import Path

        config = SimulationConfig(
            scale=scale,
            max_memory_gb=args.max_mem,
            persist_to_db=not args.no_db,
            export_npy=not args.no_export,
            artifact_dir=Path(args.output_dir),
        )

    # Apply CLI overrides
    config = config.with_overrides(
        agents=args.agents,
        epochs=args.epochs,
        universes=args.universes,
    )

    effective = config.scale
    total_agent_epochs = effective.n_agents * effective.n_epochs * effective.n_universes
    mem_per_universe_mb = (effective.n_agents * 256 * 4 * 3) / 1e6
    logger.info(f"  Total agent-epochs: {total_agent_epochs:,}")
    logger.info(f"  Memory per universe: ~{mem_per_universe_mb:.1f} MB")
    logger.info(f"  Max memory limit: {config.max_memory_gb} GB")
    logger.info(f"  Export .npy: {config.export_npy}")
    logger.info(f"  Output dir: {config.artifact_dir}")

    orchestrator = MassSimOrchestrator(config)

    try:
        report = asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(1)

    summary = report.summary_dict()
    logger.info("=" * 60)
    logger.info("SIMULATION COMPLETE")
    logger.info(f"  Universes: {summary['universes']}")
    logger.info(f"  Agent-epochs: {summary['total_agent_epochs']:,}")
    logger.info(f"  Elapsed: {summary['elapsed_seconds']:.1f}s")
    logger.info(f"  Artifacts: {summary['artifacts_generated']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
