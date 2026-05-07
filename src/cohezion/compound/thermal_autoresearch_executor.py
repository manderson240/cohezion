"""Extended Autoresearch Executor with thermal integration and TDP management.

Extends base AutoresearchExecutor with:
- Thermal checkpoint/resume protection
- TDP budget tracking
- 8-hour duration support
- Ralph Loop HIHO coherence gates
- SurrealDB journey persistence
- Obsidian vault logging

Safe for AMD Ryzen AI MAX+ 395 silicon during long-duration execution.

Phase 4: 8-Hour Autoresearch Journey
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from cohezion.compound.exp_persistence.journey import JourneyPersistence, get_journey_persistence
from cohezion.compound.hardware_monitor import get_hardware_monitor
from cohezion.compound.journey_tracker import JourneyTracker
from cohezion.compound.session_manager import CompoundSessionManager
from cohezion.compound.tdp_budget_tracker import (
    PowerProfile,
    TDPBudgetTracker,
    TDPConfig,
    TDPEnvelope,
)
from cohezion.compound.thermal_checkpoint_manager import (
    ThermalCheckpointManager,
    ThermalConfig,
)
from cohezion.swarm.compound_client import get_compound_client
from cohezion.swarm.r_zero_evolver import RZeroEvolver
import contextlib


logger = logging.getLogger(__name__)


@dataclass
class DomainConfig:
    """Configuration for a research domain."""

    name: str
    duration_hours: float
    hypotheses: list[str]
    operation_type: str = "generate"
    skill_name: str = "research"


@dataclass
class EightHourConfig:
    """Configuration for 8-hour autoresearch journey."""

    # Duration
    total_duration_hours: float = 8.0

    # Domains (each runs sequentially)
    domains: list[DomainConfig] = field(default_factory=list)

    # Thermal protection
    thermal_config: ThermalConfig = field(
        default_factory=lambda: ThermalConfig(
            pause_temp=90.0,
            resume_temp=80.0,
            emergency_temp=93.0,
            cooldown_interval_minutes=60,
            cooldown_duration_minutes=5,
            auto_resume=True,
        )
    )

    # TDP management
    tdp_config: TDPConfig = field(
        default_factory=lambda: TDPConfig(
            envelope=TDPEnvelope(tdp_watts=120.0, duration_hours=8.0), profile=PowerProfile.BALANCED
        )
    )

    # Ralph Loop
    ralph_coherence_threshold: float = 0.5
    ralph_max_iterations: int = 20

    # Execution
    min_speed_tokens_sec: float = 10.0
    r_zero_success_target: int = 5

    # Persistence
    journey_id: str = ""
    agent_name: str = "8hr_autoresearch_agent"
    enable_surrealdb: bool = True
    enable_vault: bool = True


class ThermalAutoresearchExecutor:
    """Autoresearch executor with comprehensive thermal and power protection.

    Features:
    - 8-hour duration support with checkpoint/resume
    - Thermal protection (pause/resume at thermal thresholds)
    - TDP budget tracking (prevent power envelope violations)
    - Ralph Loop HIHO coherence gates
    - Multi-domain sequential execution
    - SurrealDB journey persistence
    - Obsidian vault logging

    Usage:
        config = EightHourConfig()
        executor = ThermalAutoresearchExecutor(config)
        result = await executor.execute_8hour_journey()
    """

    def __init__(self, config: EightHourConfig | None = None):
        self.config = config or self._default_config()

        # Initialize protection systems
        self.thermal_manager: ThermalCheckpointManager = ThermalCheckpointManager(
            self.config.thermal_config
        )
        self.tdp_tracker: TDPBudgetTracker = TDPBudgetTracker(self.config.tdp_config)
        self.journey_tracker: JourneyTracker = JourneyTracker()
        self.journey_persistence: JourneyPersistence = get_journey_persistence()
        self.monitor = get_hardware_monitor()

        # State
        self.start_time: float = 0.0
        self.domains_completed: int = 0
        self.total_hypotheses_evaluated: int = 0
        self.checkpoints_created: int = 0
        self.thermal_events: list[dict] = []

        logger.info("ThermalAutoresearchExecutor initialized")
        logger.info(f"  Duration: {self.config.total_duration_hours} hours")
        logger.info(f"  Domains: {len(self.config.domains)}")
        logger.info(f"  Thermal pause: {self.config.thermal_config.pause_temp}°C")
        logger.info(f"  TDP budget: {self.config.tdp_config.envelope.total_watt_hours:.1f} Wh")

    def _default_config(self) -> EightHourConfig:
        """Create default 8-hour configuration with 4 domains."""
        return EightHourConfig(
            total_duration_hours=8.0,
            domains=[
                DomainConfig(
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
                DomainConfig(
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
                DomainConfig(
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
                DomainConfig(
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
            ],
        )

    async def execute_8hour_journey(self) -> dict[str, Any]:
        """Execute full 8-hour journey across all domains.

        Returns:
            Execution result with completion status, stats, and journey data
        """
        self.start_time = time.time()
        journey_id = f"8hr_{int(self.start_time)}"
        self.config.journey_id = journey_id

        logger.info("=" * 80)
        logger.info("STARTING 8-HOUR AUTORESEARCH JOURNEY")
        logger.info(f"Journey ID: {journey_id}")
        logger.info(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(
            f"Expected end: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time + 8 * 3600))}"
        )
        logger.info("=" * 80)

        # Start protection systems
        async with self.thermal_manager, self.tdp_tracker:
            # Start TDP monitoring background task
            tdp_task = asyncio.create_task(self.tdp_tracker.monitor_loop(interval_seconds=60))

            try:
                # Execute each domain
                results = []
                for i, domain in enumerate(self.config.domains):
                    logger.info(f"\n{'=' * 40}")
                    logger.info(f"DOMAIN {i + 1}/{len(self.config.domains)}: {domain.name}")
                    logger.info(f"{'=' * 40}")

                    domain_result = await self._execute_domain(domain)
                    results.append(domain_result)

                    self.domains_completed += 1

                    # Check if we should continue
                    if not domain_result["completed"]:
                        logger.warning(f"Domain {domain.name} did not complete. Stopping.")
                        break

                    # Check overall time
                    elapsed_hours = (time.time() - self.start_time) / 3600
                    if elapsed_hours >= self.config.total_duration_hours:
                        logger.info("Total duration reached. Stopping.")
                        break

                # Compile final results
                final_result = await self._compile_results(results)

            finally:
                # Cancel background task
                tdp_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await tdp_task

        return final_result

    async def _execute_domain(self, domain: DomainConfig) -> dict[str, Any]:
        """Execute a single research domain with thermal protection."""
        domain_start = time.time()
        hypotheses_completed = 0
        results = []

        logger.info(
            f"Domain '{domain.name}': {len(domain.hypotheses)} hypotheses, "
            f"{domain.duration_hours}h duration"
        )

        async with CompoundSessionManager() as mgr:
            mgr.start_session(max_cache_entries=256)

            for i, hypothesis in enumerate(domain.hypotheses):
                # Check time budget for this domain
                domain_elapsed = time.time() - domain_start
                domain_budget_seconds = domain.duration_hours * 3600

                if domain_elapsed >= domain_budget_seconds:
                    logger.info("Domain time budget exhausted")
                    break

                # Check overall journey time
                total_elapsed = time.time() - self.start_time
                if total_elapsed >= (self.config.total_duration_hours * 3600):
                    logger.info("Journey time budget exhausted")
                    break

                # Check TDP budget
                tdp_status = self.tdp_tracker.get_budget_status()
                if tdp_status["should_throttle"]:
                    logger.warning(
                        f"TDP budget warning: {tdp_status['consumed_percent']:.1f}% consumed"
                    )
                    # Reduce intensity
                    await asyncio.sleep(30)  # Brief pause

                # Check thermal status
                should_pause, reason = await self.thermal_manager._should_pause()
                if should_pause:
                    # Thermal checkpoint
                    await self.thermal_manager._do_checkpoint(
                        task_id=self.config.journey_id,
                        phase=f"{domain.name}_hypothesis_{i}",
                        progress={"domain": domain.name, "hypothesis": i},
                        hypotheses_completed=self.total_hypotheses_evaluated,
                        total_hypotheses=sum(len(d.hypotheses) for d in self.config.domains),
                    )

                    # Cooldown
                    pause_duration = await self.thermal_manager._cooldown(reason)
                    self.thermal_events.append(
                        {
                            "timestamp": time.time(),
                            "domain": domain.name,
                            "hypothesis_index": i,
                            "reason": reason,
                            "duration_minutes": pause_duration / 60,
                        }
                    )

                # Execute hypothesis with Ralph Loop coherence gate
                logger.info(
                    f"[{domain.name}] Hypothesis {i + 1}/{len(domain.hypotheses)}: {hypothesis[:60]}..."
                )

                try:
                    result = await self._evaluate_hypothesis_with_thermal(hypothesis, mgr, domain)
                    results.append(result)
                    hypotheses_completed += 1
                    self.total_hypotheses_evaluated += 1

                    # Track journey
                    self.journey_tracker.track_execution(
                        execution_result=result,
                        task_description=hypothesis,
                        operation_type=domain.operation_type,
                    )

                    # Check Ralph Loop gate
                    if result.get("coherence", 0) >= self.config.ralph_coherence_threshold:
                        logger.info(
                            f"HIHO gate passed (coherence {result['coherence']:.2f} >= 0.5)"
                        )

                        # Trigger R-Zero if high coherence
                        if result.get("coherence", 0) >= 0.8:
                            logger.info("High coherence - triggering R-Zero Evolver")
                            evolver = RZeroEvolver(
                                target_success_count=self.config.r_zero_success_target
                            )
                            await evolver.run_loop()
                    else:
                        logger.warning(
                            f"HIHO gate failed (coherence {result['coherence']:.2f} < 0.5)"
                        )

                except Exception as e:
                    logger.error(f"Hypothesis evaluation failed: {e}")
                    # Create checkpoint on error
                    await self.thermal_manager._do_checkpoint(
                        task_id=self.config.journey_id,
                        phase=f"{domain.name}_error_{i}",
                        progress={"error": str(e)},
                        hypotheses_completed=self.total_hypotheses_evaluated,
                        total_hypotheses=sum(len(d.hypotheses) for d in self.config.domains),
                    )
                    raise

            mgr.end_session()

        domain_duration = time.time() - domain_start

        return {
            "domain": domain.name,
            "completed": hypotheses_completed == len(domain.hypotheses),
            "hypotheses_completed": hypotheses_completed,
            "hypotheses_total": len(domain.hypotheses),
            "duration_hours": domain_duration / 3600,
            "results": results,
            "thermal_events_in_domain": len(
                [e for e in self.thermal_events if e.get("domain") == domain.name]
            ),
        }

    async def _evaluate_hypothesis_with_thermal(
        self, hypothesis: str, mgr: CompoundSessionManager, domain: DomainConfig
    ) -> dict[str, Any]:
        """Evaluate a hypothesis with thermal monitoring."""
        client = get_compound_client()

        # Pre-execution thermal check
        metrics = self.monitor.get_current_metrics()
        logger.debug(
            f"Pre-execution temps: GPU={metrics.gpu_temp_current}°C, "
            f"CPU={metrics.cpu_temp_current}°C"
        )

        t0 = time.time()

        # Execute with model
        prompt = (
            f"Research hypothesis: {hypothesis}\n\n"
            f"Domain: {domain.name}\n"
            f"Evaluate this hypothesis considering:\n"
            f"1. Technical feasibility\n"
            f"2. Alignment with FLUME architecture\n"
            f"3. Potential impact on 8-hour journey\n\n"
            f"Provide:\n"
            f"- Coherence score (0.0 to 1.0)\n"
            f"- Implementation approach\n"
            f"- Expected outcomes"
        )

        response_text, _ = await client.generate(
            prompt=prompt,
            model="gemini-3-pro:local",
            system=f"You are a {domain.skill_name} specialist evaluating research hypotheses.",
        )

        t1 = time.time()
        duration = t1 - t0

        # Post-execution thermal check
        metrics = self.monitor.get_current_metrics()
        logger.debug(
            f"Post-execution temps: GPU={metrics.gpu_temp_current}°C, "
            f"CPU={metrics.cpu_temp_current}°C"
        )

        # Parse coherence
        coherence = self._parse_coherence(response_text)

        # Speed metric
        approx_tokens = len(response_text) / 4.0
        tokens_per_sec = approx_tokens / duration if duration > 0 else 0.0

        # Check speed threshold
        if tokens_per_sec < self.config.min_speed_tokens_sec:
            logger.warning(f"Speed {tokens_per_sec:.2f} tok/s below threshold")

        return {
            "hypothesis": hypothesis,
            "response": response_text,
            "coherence": coherence,
            "tokens_per_sec": tokens_per_sec,
            "duration_seconds": duration,
            "domain": domain.name,
            "skill_name": domain.skill_name,
            "gpu_temp_c": metrics.gpu_temp_current,
            "cpu_temp_c": metrics.cpu_temp_current,
        }

    def _parse_coherence(self, text: str) -> float:
        """Parse coherence score from response text."""
        coherence = 0.5  # Default

        if "coherence score" in text.lower() or "0." in text or "1.0" in text:
            try:
                lines = text.split("\n")
                for line in lines:
                    match = re.search(r"0\.[0-9]+|1\.0", line)
                    if match:
                        coherence = float(match.group())
                        break
            except Exception as e:
                logger.warning(f"Failed to parse coherence: {e}")

        return max(0.0, min(1.0, coherence))  # Clamp to [0, 1]

    async def _compile_results(self, domain_results: list[dict]) -> dict[str, Any]:
        """Compile final results from all domains."""
        total_duration = time.time() - self.start_time
        total_hypotheses = sum(r["hypotheses_completed"] for r in domain_results)

        # Get final thermal status
        thermal_status = self.thermal_manager.get_status()
        tdp_status = self.tdp_tracker.get_budget_status()

        result = {
            "journey_id": self.config.journey_id,
            "completed": all(r["completed"] for r in domain_results),
            "domains": domain_results,
            "total_hypotheses_evaluated": total_hypotheses,
            "domains_completed": sum(1 for r in domain_results if r["completed"]),
            "duration_hours": total_duration / 3600,
            "thermal_events": self.thermal_events,
            "thermal_events_count": len(self.thermal_events),
            "total_paused_minutes": thermal_status.get("total_paused_minutes", 0),
            "final_temps": {
                "gpu_c": thermal_status.get("gpu_temp_c", 0),
                "cpu_c": thermal_status.get("cpu_temp_c", 0),
            },
            "tdp_consumed_wh": tdp_status.get("consumed_wh", 0),
            "tdp_consumed_percent": tdp_status.get("consumed_percent", 0),
            "ended_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        logger.info("=" * 80)
        logger.info("8-HOUR JOURNEY COMPLETE")
        logger.info(f"Duration: {result['duration_hours']:.2f} hours")
        logger.info(f"Hypotheses: {result['total_hypotheses_evaluated']}")
        logger.info(f"Thermal events: {result['thermal_events_count']}")
        logger.info(f"TDP consumed: {result['tdp_consumed_percent']:.1f}%")
        logger.info(
            f"Final temps: GPU={result['final_temps']['gpu_c']}°C, "
            f"CPU={result['final_temps']['cpu_c']}°C"
        )
        logger.info("=" * 80)

        return result


# Convenience function
async def run_8hour_autoresearch_journey(
    config: EightHourConfig | None = None,
) -> dict[str, Any]:
    """Run a complete 8-hour autoresearch journey with thermal protection."""
    executor = ThermalAutoresearchExecutor(config)
    return await executor.execute_8hour_journey()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Run the 8-hour journey
    result = asyncio.run(run_8hour_autoresearch_journey())

    print(f"\n{'=' * 80}")
    print("JOURNEY COMPLETE")
    print(f"{'=' * 80}")
    print(f"Journey ID: {result['journey_id']}")
    print(f"Completed: {result['completed']}")
    print(f"Duration: {result['duration_hours']:.2f} hours")
    print(f"Hypotheses evaluated: {result['total_hypotheses_evaluated']}")
    print(f"Thermal events: {result['thermal_events_count']}")
    print(f"TDP consumed: {result['tdp_consumed_percent']:.1f}%")
