#!/usr/bin/env python3
"""Mass Simulation Driver - Standalone entry point.

Designed for unattended overnight operation with OOM protection.
Can be scheduled via cron or run directly after 2:30 AM.

Usage:
    uv run python mass_sim_driver.py                    # demo (10s)
    uv run python mass_sim_driver.py --scale medium     # medium (2min)
    uv run python mass_sim_driver.py --scale overnight  # overnight (hours)
    uv run python mass_sim_driver.py --agents 500 --epochs 5000 --universes 50

Environment:
    MASS_SIM_SCALE=demo|medium|overnight
    MASS_SIM_NO_DB=1        # Skip SurrealDB
    MASS_SIM_NO_NAV=1       # Use jitter instead of navigator
    MASS_SIM_MAX_MEM=100    # Max RSS in GB
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time

# Setup logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/mass_sim/simulation.log", mode="a"),
    ],
)
logger = logging.getLogger("mass_sim")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mass FLUME Simulation Driver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scale",
        "-s",
        choices=["demo", "medium", "overnight"],
        default=os.environ.get("MASS_SIM_SCALE", "demo"),
    )
    parser.add_argument("--agents", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--universes", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--no-navigator",
        action="store_true",
        default=bool(os.environ.get("MASS_SIM_NO_NAV")),
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        default=bool(os.environ.get("MASS_SIM_NO_DB")),
    )
    parser.add_argument(
        "--max-mem",
        type=float,
        default=float(os.environ.get("MASS_SIM_MAX_MEM", "100")),
    )
    parser.add_argument("--output-dir", type=str, default="data/mass_sim/artifacts")
    parser.add_argument(
        "--export-npy",
        action="store_true",
        help="Export final agent states as .npy files for training pipeline",
    )
    return parser.parse_args()


# Graceful shutdown on SIGTERM/SIGINT
_shutdown_requested = False


def _handle_signal(sig, frame):
    global _shutdown_requested
    logger.warning(f"Signal {sig} received, requesting graceful shutdown...")
    _shutdown_requested = True


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


async def main() -> int:
    args = parse_args()

    # Ensure output directories exist
    from pathlib import Path

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    Path("data/mass_sim/checkpoints/jsonl").mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("COHEZION MASS SIMULATION DRIVER")
    logger.info(f"  Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  PID: {os.getpid()}")
    logger.info("=" * 60)

    # Import after logging setup
    from cohezion.mass_sim.config import SCALE_TIERS, SimulationConfig
    from cohezion.mass_sim.orchestrator import MassSimOrchestrator

    # Build config
    config = SimulationConfig(
        scale=SCALE_TIERS[args.scale],
        use_navigator=not args.no_navigator,
        persist_to_db=not args.no_db,
        artifact_dir=Path(args.output_dir),
        agent_seed_base=args.seed,
        max_memory_gb=args.max_mem,
        export_npy=args.export_npy,
    )

    # Apply CLI overrides
    config = config.with_overrides(
        agents=args.agents,
        epochs=args.epochs,
        universes=args.universes,
    )

    logger.info(f"Config: {config.scale.name} | navigator={config.use_navigator}")
    logger.info(
        f"  {config.scale.n_agents} agents x "
        f"{config.scale.n_epochs} epochs x "
        f"{config.scale.n_universes} universes"
    )
    logger.info(
        f"  Total agent-epochs: "
        f"{config.scale.n_agents * config.scale.n_epochs * config.scale.n_universes:,}"
    )

    # Run
    orchestrator = MassSimOrchestrator(config)
    report = await orchestrator.run()

    # Output summary
    summary = report.summary_dict()
    logger.info("\nFinal Summary:")
    logger.info(json.dumps(summary, indent=2, default=str))

    # Write summary to file
    summary_path = Path(args.output_dir) / f"{report.run_id}_final.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info(f"Summary saved: {summary_path}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
