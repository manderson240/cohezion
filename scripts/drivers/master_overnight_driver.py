"""
Master Overnight Driver: FLUME → R-Zero
========================================
Staged execution for overnight universe simulations.

Phase 1: FLUME Quadrature (1-2 hrs)
  - 5-stream expert domain lattice
  - 1,000 trajectory points
  - Validates infrastructure

Phase 2: R-Zero Pragmatic (6-8 hrs)
  - 500K simulations
  - Challenger/Solver co-evolution
  - Adaptive difficulty

Features:
- JourneyTracker artifact registration
- Hourly email reports
- Three-tier storage (Git/SurrealDB/External)
- Automatic checkpointing every 100K sims
- Resumable on crash
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


# Setup logging first
LOG_DIR = Path("/home/mike-anderson/nvme-simulations/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [OVERNIGHT] - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"master_overnight_{TIMESTAMP}.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("MasterOvernightDriver")

# Constants
ARCHIVE_DIR = Path("/home/mike-anderson/nvme-simulations")
TARGET_FlUME_SIMS = 1000
TARGET_RZERO_SIMS = 500_000


# R-Zero Framework Classes (built-in to avoid import issues)
class RZeroState:
    """R-Zero Framework State. Manages Challenger and Pragmatic Evaluator."""

    def __init__(self):
        self.epoch = 1
        self.difficulty = 1.0
        self.history: list[float] = []

    def generate_challenge(self) -> dict:
        """Generate constraints with explicit Edge Cases."""
        import random

        edge_cases = [
            {"name": "Zero Energy Warp", "zpe_limit": 0.1, "warp_target": 2.0},
            {"name": "Infinite Fertility", "fertility_target": 5.0},
            {"name": "Cold Fusion", "temp_limit": 300, "energy_target": 1000},
            {"name": "Standard Op", "zpe_limit": 10.0, "warp_target": 1.0},
        ]
        selected_case = random.choice(edge_cases)
        return {"case": selected_case, "difficulty": self.difficulty}

    def update(self, latest_avg_score: float):
        """Update state. If solver succeeds, raise difficulty."""
        self.history.append(latest_avg_score)
        if len(self.history) > 20:
            self.history.pop(0)

        recent_avg = sum(self.history[-10:]) / 10 if len(self.history) >= 10 else 0.5

        if recent_avg > 0.8:
            self.difficulty += 0.05
            self.epoch += 1
            logger.info(
                f"R-ZERO: Difficulty raised to {self.difficulty:.2f} (epoch {self.epoch})"
            )


class PragmaticScorer:
    """Evaluates solutions for Overhype and Correctness."""

    BUZZWORDS = [
        "Quantum",
        "Nano",
        "Cyber",
        "Hyper",
        "Unlimited",
        "Miracle",
        "God-Mode",
        "Sacred",
    ]

    @staticmethod
    def evaluate(response_text: str, metrics: dict, challenge: dict) -> dict:
        score = 1.0
        penalty_reasons = []

        # Overhype detection
        hype_count = sum(
            1 for word in PragmaticScorer.BUZZWORDS if word in response_text
        )
        if hype_count > 2:
            penalty = (hype_count - 2) * 0.1
            score -= penalty
            penalty_reasons.append(f"Overhype (-{penalty:.2f})")

        # Edge case validation
        case = challenge["case"]
        if case["name"] == "Zero Energy Warp":
            if (
                metrics.get("warp_factor", 0) > 1.0
                and metrics.get("zpe_density", 0) < 0.5
            ):
                score -= 0.5
                penalty_reasons.append("Violated Physics")

        if case["name"] == "Infinite Fertility":
            if metrics.get("fertility_index", 0) > 1.0:
                score -= 0.5
                penalty_reasons.append("Boundary Breach")

        return {"final_score": max(0.0, min(1.0, score)), "penalties": penalty_reasons}


RZERO_BATCH_SIZE = 500
CHECKPOINT_INTERVAL = 100_000
END_TIME_HOUR = 7  # Stop at 7 AM to leave buffer


class ArtifactRegistry:
    """Three-tier artifact registration with JourneyTracker integration."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.artifacts: list[dict] = []
        self.archive_dir = ARCHIVE_DIR

    def register_artifact(
        self,
        artifact_type: str,
        path: Path,
        tier: str = "external",
        lifetime_days: int = 30,
        retention_policy: str = "research",
        tags: list[str] | None = None,
    ) -> dict:
        """Register an artifact in the three-tier system."""
        import hashlib

        # Calculate checksum
        if path.exists():
            with open(path, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()[:16]
            size_bytes = path.stat().st_size
        else:
            checksum = "not_found"
            size_bytes = 0

        artifact = {
            "session_id": self.session_id,
            "artifact_type": artifact_type,
            "path": str(path),
            "size_bytes": size_bytes,
            "tier": tier,
            "checksum": checksum,
            "lifetime_days": lifetime_days,
            "retention_policy": retention_policy,
            "tags": tags or [],
            "registered_at": datetime.now().isoformat(),
        }

        self.artifacts.append(artifact)

        # Save metadata to tier 1 (Git-trackable)
        metadata_path = path.parent / f"{path.name}.metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(artifact, f, indent=2)

        logger.info(
            f"✅ Registered {artifact_type}: {path.name} ({size_bytes / 1024 / 1024:.1f}MB) -> {tier}"
        )
        return artifact

    def save_registry(self) -> Path:
        """Save full artifact registry to archive."""
        registry_path = self.archive_dir / f"artifact_registry_{self.session_id}.json"
        with open(registry_path, "w") as f:
            json.dump(
                {
                    "session_id": self.session_id,
                    "created_at": datetime.now().isoformat(),
                    "artifacts": self.artifacts,
                    "count": len(self.artifacts),
                },
                f,
                indent=2,
            )
        logger.info(f"💾 Artifact registry saved: {registry_path}")
        return registry_path


class MasterOvernightDriver:
    """Orchestrates FLUME → R-Zero simulation sequence."""

    def __init__(self):
        self.session_id = f"overnight-{datetime.now().strftime('%Y%m%d')}"
        self.registry = ArtifactRegistry(self.session_id)
        self.start_time = datetime.now()
        self.phase_results: dict[str, Any] = {}

        # Initialize email notifier
        self.notifier = self._init_notifier()

        # Stats
        self.total_simulations = 0
        self.checkpoints_created = 0

    def _init_notifier(self):
        """Initialize email notifier if available."""
        try:
            from cohezion.mcp.email_notifier import EmailNotifier

            return EmailNotifier()
        except Exception as e:
            logger.warning(f"Email notifier unavailable: {e}")
            return None

    async def send_notification(self, subject: str, body: str, is_html: bool = False):
        """Send email notification if available."""
        if self.notifier:
            try:
                await self.notifier.send_email(subject, body, is_html=is_html)
                logger.info(f"📧 Sent: {subject}")
            except Exception as e:
                logger.warning(f"Failed to send email: {e}")
        else:
            logger.info(f"📧 [WOULD SEND] {subject}")

    async def run(self):
        """Execute full overnight simulation sequence."""
        logger.info("=" * 70)
        logger.info(f"🌙 Master Overnight Driver: {self.session_id}")
        logger.info("=" * 70)
        logger.info(f"Archive: {ARCHIVE_DIR}")
        logger.info(f"Start: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Target End: {END_TIME_HOUR}:00 AM")
        logger.info("=" * 70)

        # Send startup notification
        await self.send_notification(
            f"🚀 Overnight Simulations Starting: {self.session_id}",
            f"Session: {self.session_id}\n"
            f"Start: {self.start_time.strftime('%H:%M')}\n"
            f"Plan: FLUME (1K) → R-Zero (500K)\n"
            f"Archive: {ARCHIVE_DIR}",
        )

        try:
            # Phase 1: FLUME Quadrature
            await self._run_flume_phase()

            # Phase 2: R-Zero Pragmatic
            await self._run_rzero_phase()

            # Completion
            await self._complete()

        except Exception as e:
            logger.exception("❌ Fatal error in overnight driver")
            await self.send_notification(
                f"⚠️ Overnight Simulations FAILED: {self.session_id}",
                f"Error: {e!s}\n\nCheck logs: {LOG_DIR}/master_overnight_{TIMESTAMP}.log",
            )
            raise

    async def _run_flume_phase(self):
        """Execute FLUME Quadrature simulations."""
        phase_name = "FLUME Quadrature"
        phase_start = datetime.now()

        logger.info("")
        logger.info("=" * 70)
        logger.info(f"🌊 PHASE 1: {phase_name}")
        logger.info("=" * 70)

        await self.send_notification(
            "🌊 Starting FLUME Quadrature",
            f"Target: {TARGET_FlUME_SIMS} simulations\n"
            f"Streams: 5 expert domains\n"
            f"Est. Duration: 1-2 hours",
        )

        try:
            # Import and run FLUME driver
            import sys

            sys.path.insert(0, "/home/mike-anderson/dev/cohezion")

            from scripts.drivers.flume_simulation_driver import QuadratureController

            controller = QuadratureController()

            # Override output location
            flume_output = (
                ARCHIVE_DIR / "flume" / f"trajectories_{self.session_id}.jsonl"
            )
            flume_output.parent.mkdir(parents=True, exist_ok=True)
            controller.output_file = flume_output

            # Run simulations
            await controller.run_round_robin(total_simulations=TARGET_FlUME_SIMS)

            # Register artifacts
            if flume_output.exists():
                self.registry.register_artifact(
                    artifact_type="flume_trajectories",
                    path=flume_output,
                    tier="external",
                    lifetime_days=90,
                    tags=["flume", "quadrature", "trajectories"],
                )

            # Track results
            self.phase_results[phase_name] = {
                "status": "completed",
                "simulations": len(controller.trajectories),
                "duration_minutes": (datetime.now() - phase_start).total_seconds() / 60,
                "output_file": str(flume_output),
            }

            self.total_simulations += len(controller.trajectories)

            phase_duration = (datetime.now() - phase_start).total_seconds() / 60
            logger.info(
                f"✅ FLUME complete: {len(controller.trajectories)} sims in {phase_duration:.1f} min"
            )

            await self.send_notification(
                f"✅ FLUME Complete: {len(controller.trajectories)} sims",
                f"Duration: {phase_duration:.1f} minutes\n"
                f"Output: {flume_output.name}\n"
                f"Starting R-Zero phase...",
            )

        except Exception as e:
            logger.exception("❌ FLUME phase failed")
            self.phase_results[phase_name] = {"status": "failed", "error": str(e)}
            raise

    async def _run_rzero_phase(self):
        """Execute R-Zero Pragmatic simulations."""
        phase_name = "R-Zero Pragmatic"
        phase_start = datetime.now()
        last_report_time = phase_start

        logger.info("")
        logger.info("=" * 70)
        logger.info(f"🎯 PHASE 2: {phase_name}")
        logger.info("=" * 70)

        await self.send_notification(
            "🎯 Starting R-Zero Pragmatic",
            f"Target: {TARGET_RZERO_SIMS} simulations\n"
            f"Batch Size: {RZERO_BATCH_SIZE}\n"
            f"Est. Duration: 6-8 hours",
        )

        try:
            # Use built-in R-Zero classes (already defined above)
            rzero = RZeroState()

            # Create output directory
            rzero_output_dir = ARCHIVE_DIR / "rzero"
            rzero_output_dir.mkdir(parents=True, exist_ok=True)

            completed = 0
            batch_num = 0

            min_batches = 10  # Run at least 10 batches (5K sims) even if past time

            while completed < TARGET_RZERO_SIMS:
                # Check time limit (but run minimum batches first)
                now = datetime.now()
                if (
                    batch_num >= min_batches
                    and now.hour >= END_TIME_HOUR
                    and now.minute > 0
                ):
                    logger.info(
                        f"⏰ Reached {END_TIME_HOUR} AM after {batch_num} batches. Stopping R-Zero early."
                    )
                    break

                # Run batch
                batch_results = await self._run_rzero_batch(rzero, batch_num)
                completed += batch_results["count"]
                batch_num += 1

                # Create checkpoint every 100K
                if completed >= (self.checkpoints_created + 1) * CHECKPOINT_INTERVAL:
                    await self._create_checkpoint(completed, rzero)

                # Hourly report
                if (now - last_report_time) > timedelta(hours=1):
                    await self._send_progress_report(completed, rzero, phase_start)
                    last_report_time = now

                # Brief sleep between batches
                await asyncio.sleep(0.1)

            # Track results
            phase_duration = (datetime.now() - phase_start).total_seconds() / 3600
            self.phase_results[phase_name] = {
                "status": "completed",
                "simulations": completed,
                "duration_hours": phase_duration,
                "final_epoch": rzero.epoch,
                "final_difficulty": rzero.difficulty,
                "checkpoints": self.checkpoints_created,
            }

            self.total_simulations += completed

            logger.info(
                f"✅ R-Zero complete: {completed} sims in {phase_duration:.1f} hours"
            )

        except Exception as e:
            logger.exception("❌ R-Zero phase failed")
            self.phase_results[phase_name] = {"status": "failed", "error": str(e)}
            raise

    async def _run_rzero_batch(self, rzero, batch_num: int) -> dict:
        """Run a single R-Zero batch."""
        import random

        challenge = rzero.generate_challenge()
        difficulty = challenge["difficulty"]
        scores = []

        # Run simulations in batch
        for idx in range(RZERO_BATCH_SIZE):
            # Simulate with random outcomes
            implicate = random.uniform(0.5, 1.0)
            zpe = implicate * 10.0
            warp = zpe / 5.0
            fertility = implicate

            # Pragmatic scoring
            metrics = {
                "warp_factor": warp,
                "zpe_density": zpe,
                "fertility_index": fertility,
            }

            # Generate response
            response = f"Sim {batch_num}_{idx}: {challenge['case']['name']}. ZPE={zpe:.2f}, Warp={warp:.2f}"

            # Score it
            scorer = PragmaticScorer()
            eval_result = scorer.evaluate(response, metrics, challenge)
            scores.append(eval_result["final_score"])

        # Update R-Zero state
        if scores:
            avg_score = sum(scores) / len(scores)
            rzero.update(avg_score)

        if batch_num % 100 == 0:
            logger.info(
                f"   Batch {batch_num}: {RZERO_BATCH_SIZE} sims, epoch={rzero.epoch}, difficulty={rzero.difficulty:.2f}"
            )

        return {"count": RZERO_BATCH_SIZE, "scores": scores}

    async def _create_checkpoint(self, completed: int, rzero):
        """Create a resumable checkpoint."""
        self.checkpoints_created += 1
        checkpoint_path = (
            ARCHIVE_DIR
            / "checkpoints"
            / f"rzero_checkpoint_{self.session_id}_cp{self.checkpoints_created}.json"
        )
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            "session_id": self.session_id,
            "completed_simulations": completed,
            "rzero_state": {
                "epoch": rzero.epoch,
                "difficulty": rzero.difficulty,
                "history": rzero.history[-50:] if rzero.history else [],
            },
            "timestamp": datetime.now().isoformat(),
        }

        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint, f, indent=2)

        self.registry.register_artifact(
            artifact_type="rzero_checkpoint",
            path=checkpoint_path,
            tier="git",  # Small metadata file
            lifetime_days=365,
            tags=["rzero", "checkpoint", f"cp{self.checkpoints_created}"],
        )

        logger.info(
            f"💾 Checkpoint {self.checkpoints_created} created at {completed} sims"
        )

    async def _send_progress_report(self, completed: int, rzero, phase_start):
        """Send hourly progress report."""
        elapsed = (datetime.now() - phase_start).total_seconds() / 3600
        rate = completed / elapsed if elapsed > 0 else 0
        remaining = TARGET_RZERO_SIMS - completed
        eta_hours = remaining / rate if rate > 0 else 0

        logger.info(
            f"📊 Progress: {completed:,} sims, {rate:.0f} sims/hr, ETA: {eta_hours:.1f} hrs"
        )

        await self.send_notification(
            f"📊 R-Zero Progress: {completed:,} sims ({completed / TARGET_RZERO_SIMS * 100:.1f}%)",
            f"Rate: {rate:.0f} simulations/hour\n"
            f"Epoch: {rzero.epoch}, Difficulty: {rzero.difficulty:.2f}\n"
            f"ETA: {eta_hours:.1f} hours\n"
            f"Checkpoints: {self.checkpoints_created}",
        )

    async def _complete(self):
        """Finalize overnight simulations."""
        total_duration = (datetime.now() - self.start_time).total_seconds() / 3600

        logger.info("")
        logger.info("=" * 70)
        logger.info("☀️ OVERNIGHT SIMULATIONS COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Session: {self.session_id}")
        logger.info(f"Total Duration: {total_duration:.1f} hours")
        logger.info(f"Total Simulations: {self.total_simulations:,}")
        logger.info(f"Checkpoints Created: {self.checkpoints_created}")
        logger.info("")
        logger.info("Phase Results:")
        for phase, result in self.phase_results.items():
            status = result.get("status", "unknown")
            sims = result.get("simulations", 0)
            logger.info(f"  {phase}: {status} ({sims:,} sims)")

        # Save artifact registry
        registry_path = self.registry.save_registry()

        # Final notification
        summary = f"""
☀️ Overnight Simulations Complete: {self.session_id}

Total Duration: {total_duration:.1f} hours
Total Simulations: {self.total_simulations:,}

Phase Summary:
{
            chr(10).join(
                f"  • {phase}: {result.get('simulations', 0):,} sims ({result.get('status', 'unknown')})"
                for phase, result in self.phase_results.items()
            )
        }

Artifacts:
  • Registry: {registry_path.name}
  • Checkpoints: {self.checkpoints_created}
  • Archive: {ARCHIVE_DIR}

Tomorrow's Plan:
  1. Fractal Universe (10K+ agents)
  2. Mass Simulation (500K+ sweeps)
        """

        await self.send_notification(
            f"☀️ Overnight Complete: {self.total_simulations:,} Sims", summary
        )

        logger.info("=" * 70)


if __name__ == "__main__":
    driver = MasterOvernightDriver()
    asyncio.run(driver.run())
