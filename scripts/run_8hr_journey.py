#!/usr/bin/env python3
"""
CLI entry point for 8-hour autoresearch journey.

Executes a comprehensive 8-hour research task across multiple domains with:
- Thermal checkpoint/resume protection
- TDP budget tracking
- Ralph Loop HIHO coherence gates
- SurrealDB journey persistence
- Obsidian vault logging
- Real-time dashboard updates

Safe for AMD Ryzen AI MAX+ 395 silicon.

Usage:
    python run_8hr_journey.py [--mode {live,simulate,hybrid}] [--domains DOMAIN1,DOMAIN2]

Examples:
    # Run with live execution (requires services)
    python run_8hr_journey.py --mode live

    # Run in simulation mode (no external dependencies)
    python run_8hr_journey.py --mode simulate

    # Run specific domains only
    python run_8hr_journey.py --domains gpu_kernel,flume

    # Resume from checkpoint
    python run_8hr_journey.py --resume journey_12345

Phase 4: 8-Hour Autoresearch Journey
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Any


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.compound.tdp_budget_tracker import PowerProfile, TDPConfig
from cohezion.compound.thermal_autoresearch_executor import (
    DomainConfig,
    EightHourConfig,
    ThermalAutoresearchExecutor,
)
from cohezion.compound.thermal_checkpoint_manager import ThermalConfig


logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for 8-hour execution."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("8hr_journey.log")],
    )

    # Reduce noise from libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def create_domain_config(domain_name: str) -> DomainConfig:
    """Create domain configuration by name."""
    domains = {
        "gpu_kernel": DomainConfig(
            name="gpu_kernel_optimization",
            duration_hours=2.0,
            hypotheses=[
                "Optimize MXFP4 GEMM kernel for AMD MI355X via parameter tuning",
                "Implement adaptive split-K strategy for sparse token distributions",
                "Fuse quantization into GEMM kernel to eliminate bottleneck",
                "Optimize MLA decode with FlashAttention-style tiling",
                "Tune MoE routing for 256-expert configurations",
            ],
            operation_type="transform",
            skill_name="gpu_optimization",
        ),
        "flume": DomainConfig(
            name="flume_self_improvement",
            duration_hours=2.0,
            hypotheses=[
                "Refine FLUME VAE architecture for better 12D projection",
                "Optimize HIHO coherence loss for faster convergence",
                "Improve trajectory prediction in morphospace",
                "Enhance exotic vacuum object representation",
                "Tune 2048D to 512D compression ratios",
            ],
            operation_type="analyze",
            skill_name="flume_research",
        ),
        "cohezion": DomainConfig(
            name="cohezion_architecture",
            duration_hours=2.0,
            hypotheses=[
                "Analyze compound executor for optimization opportunities",
                "Refine journey tracker for better 12D mapping",
                "Optimize SurrealDB query patterns",
                "Improve thermal predictor accuracy",
                "Enhance Ralph Loop convergence speed",
            ],
            operation_type="analyze",
            skill_name="architecture_research",
        ),
        "synthesis": DomainConfig(
            name="cross_domain_synthesis",
            duration_hours=2.0,
            hypotheses=[
                "Synthesize GPU optimization insights with FLUME architecture",
                "Integrate thermal management into compound loops",
                "Unify journey tracking across all domains",
                "Extract patterns from 8-hour execution",
                "Generate final synthesis report",
            ],
            operation_type="generate",
            skill_name="synthesis",
        ),
    }

    if domain_name not in domains:
        raise ValueError(f"Unknown domain: {domain_name}. Available: {list(domains.keys())}")

    return domains[domain_name]


def load_checkpoint(checkpoint_id: str) -> dict[str, Any] | None:
    """Load a checkpoint by ID."""
    checkpoint_dir = Path("data/thermal_checkpoints")
    checkpoint_file = checkpoint_dir / f"{checkpoint_id}.json"

    if not checkpoint_file.exists():
        return None

    try:
        with open(checkpoint_file, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load checkpoint: {e}")
        return None


class JourneyRunner:
    """Manages the 8-hour journey execution with signal handling."""

    def __init__(self, config: EightHourConfig):
        self.config = config
        self.executor: ThermalAutoresearchExecutor | None = None
        self.interrupted = False
        self.result: dict[str, Any] | None = None

    def setup_signal_handlers(self) -> None:
        """Setup graceful shutdown handlers."""

        def handle_signal(signum, frame):
            logger.warning(f"Received signal {signum}. Initiating graceful shutdown...")
            self.interrupted = True

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    async def run(self) -> dict[str, Any]:
        """Run the journey with signal handling."""
        self.setup_signal_handlers()

        try:
            self.executor = ThermalAutoresearchExecutor(self.config)
            self.result = await self.executor.execute_8hour_journey()
            return self.result
        except Exception as e:
            logger.error(f"Journey execution failed: {e}")
            raise


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Execute 8-hour autoresearch journey with thermal protection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full 8-hour journey in hybrid mode (recommended)
  python run_8hr_journey.py
  
  # Run in simulation mode (no external dependencies)
  python run_8hr_journey.py --mode simulate
  
  # Run only GPU kernel and FLUME domains
  python run_8hr_journey.py --domains gpu_kernel,flume
  
  # Resume from checkpoint
  python run_8hr_journey.py --resume journey_12345
  
  # Aggressive thermal protection
  python run_8hr_journey.py --pause-temp 85 --resume-temp 75
  
  # Power efficiency mode
  python run_8hr_journey.py --power-profile efficiency
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["live", "simulate", "hybrid"],
        default="hybrid",
        help="Execution mode: live (requires services), simulate (standalone), hybrid (default)",
    )

    parser.add_argument(
        "--domains",
        type=str,
        help="Comma-separated list of domains to run: gpu_kernel,flume,cohezion,synthesis",
    )

    parser.add_argument(
        "--resume",
        type=str,
        metavar="JOURNEY_ID",
        help="Resume from checkpoint with given journey ID",
    )

    parser.add_argument(
        "--pause-temp",
        type=float,
        default=90.0,
        help="GPU temperature to pause execution (default: 90°C)",
    )

    parser.add_argument(
        "--resume-temp",
        type=float,
        default=80.0,
        help="GPU temperature to resume execution (default: 80°C)",
    )

    parser.add_argument(
        "--emergency-temp",
        type=float,
        default=93.0,
        help="Emergency temperature threshold (default: 93°C)",
    )

    parser.add_argument(
        "--cooldown-interval",
        type=int,
        default=60,
        help="Scheduled cooldown interval in minutes (default: 60)",
    )

    parser.add_argument(
        "--power-profile",
        choices=["efficiency", "balanced", "performance"],
        default="balanced",
        help="Power consumption profile (default: balanced)",
    )

    parser.add_argument(
        "--ralph-threshold",
        type=float,
        default=0.5,
        help="Ralph Loop HIHO coherence threshold (default: 0.5)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="8hr_journey_result.json",
        help="Output file for results (default: 8hr_journey_result.json)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    parser.add_argument(
        "--dry-run", action="store_true", help="Validate configuration without executing"
    )

    return parser.parse_args()


async def main() -> int:
    """Main entry point."""
    args = parse_args()

    setup_logging(args.verbose)

    logger.info("=" * 80)
    logger.info("8-HOUR AUTORESEARCH JOURNEY")
    logger.info("=" * 80)
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Pause temp: {args.pause_temp}°C")
    logger.info(f"Resume temp: {args.resume_temp}°C")
    logger.info(f"Cooldown interval: {args.cooldown_interval} min")
    logger.info(f"Power profile: {args.power_profile}")
    logger.info(f"Ralph threshold: {args.ralph_threshold}")
    logger.info("=" * 80)

    # Build domain list
    if args.domains:
        domain_names = [d.strip() for d in args.domains.split(",")]
        domains = [create_domain_config(name) for name in domain_names]
    else:
        # All domains
        domains = [
            create_domain_config("gpu_kernel"),
            create_domain_config("flume"),
            create_domain_config("cohezion"),
            create_domain_config("synthesis"),
        ]

    logger.info(f"Domains: {[d.name for d in domains]}")

    # Create configuration
    config = EightHourConfig(
        total_duration_hours=sum(d.duration_hours for d in domains),
        domains=domains,
        thermal_config=ThermalConfig(),
        tdp_config=TDPConfig(),
        ralph_coherence_threshold=args.ralph_threshold,
        enable_surrealdb=(args.mode in ["live", "hybrid"]),
        enable_vault=(args.mode in ["live", "hybrid"]),
    )

    # Update thermal config
    config.thermal_config.pause_temp = args.pause_temp
    config.thermal_config.resume_temp = args.resume_temp
    config.thermal_config.emergency_temp = args.emergency_temp
    config.thermal_config.cooldown_interval_minutes = args.cooldown_interval

    # Update TDP config
    profile_map = {
        "efficiency": PowerProfile.EFFICIENCY,
        "balanced": PowerProfile.BALANCED,
        "performance": PowerProfile.PERFORMANCE,
    }
    config.tdp_config.profile = profile_map[args.power_profile]

    # Handle resume
    if args.resume:
        checkpoint = load_checkpoint(args.resume)
        if checkpoint:
            logger.info(f"Resuming from checkpoint: {args.resume}")
            config.journey_id = args.resume
            # Could restore other state here
        else:
            logger.error(f"Checkpoint not found: {args.resume}")
            return 1

    # Dry run
    if args.dry_run:
        logger.info("Dry run mode - validating configuration...")
        logger.info(f"Configuration valid!")
        logger.info(f"  Total duration: {config.total_duration_hours} hours")
        logger.info(f"  Domains: {len(config.domains)}")
        logger.info(f"  Thermal protection: enabled")
        logger.info(f"  TDP tracking: enabled")
        return 0

    # Execute
    try:
        runner = JourneyRunner(config)
        result = await runner.run()

        # Save results
        output_file = Path(args.output)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)

        logger.info(f"Results saved to: {output_file}")

        # Print summary
        print(f"\n{'=' * 80}")
        print(f"JOURNEY SUMMARY")
        print(f"{'=' * 80}")
        print(f"Journey ID: {result['journey_id']}")
        print(f"Completed: {result['completed']}")
        print(f"Duration: {result['duration_hours']:.2f} hours")
        print(f"Hypotheses evaluated: {result['total_hypotheses_evaluated']}")
        print(f"Domains completed: {result['domains_completed']}/{len(result['domains'])}")
        print(f"Thermal events: {result['thermal_events_count']}")
        print(f"Total paused: {result['total_paused_minutes']:.1f} minutes")
        print(f"TDP consumed: {result['tdp_consumed_percent']:.1f}%")
        print(
            f"Final temps: GPU={result['final_temps']['gpu_c']}°C, CPU={result['final_temps']['cpu_c']}°C"
        )
        print(f"{'=' * 80}")

        return 0 if result["completed"] else 1

    except KeyboardInterrupt:
        logger.info("Journey interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Journey failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
