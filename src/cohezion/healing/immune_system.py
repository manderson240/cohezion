"""
Immune System (Gateway 13).

Monitors system health via velocity metrics and triggers self-diagnosis
when performance drops below threshold.
"""

import asyncio
import logging
from typing import Any

from cohezion.agents.critic import CriticAgent
from cohezion.core.time_keeper import get_time_keeper
from cohezion.swarm.swarm_types import Perspective, ThoughtVector


logger = logging.getLogger(__name__)


class VelocityMonitor:
    """
    Monitors task velocity and triggers alerts/diagnoses when it drops.
    """

    def __init__(
        self, threshold_tasks_per_hour: float = 5.0, check_interval_seconds: int = 300
    ):
        self.threshold = threshold_tasks_per_hour
        self.check_interval = check_interval_seconds
        self.tk = get_time_keeper()
        self._running = False
        self._last_velocity = 0.0

    async def start_monitoring(self, duration_seconds: int = 3600) -> None:
        """Run monitoring loop for specified duration."""
        self._running = True
        end_time = asyncio.get_event_loop().time() + duration_seconds

        logger.info(
            f"Immune System: Monitoring started (threshold: {self.threshold} tasks/hr)"
        )

        while self._running and asyncio.get_event_loop().time() < end_time:
            await self._check_health()
            await asyncio.sleep(self.check_interval)

        logger.info("Immune System: Monitoring stopped.")

    async def _check_health(self) -> None:
        """Check current velocity and trigger diagnosis if needed."""
        try:
            velocity = await self.tk.calculate_velocity(window_minutes=60)
            self._last_velocity = velocity

            logger.info(f"Health Check: Velocity = {velocity:.1f} tasks/hr")

            if velocity < self.threshold:
                logger.warning(f"LOW VELOCITY ALERT: {velocity:.1f} < {self.threshold}")
                await self._trigger_diagnosis()

        except Exception as e:
            logger.error(f"Health check failed: {e}")

    async def _trigger_diagnosis(self) -> None:
        """Analyze recent errors and produce diagnosis."""
        logger.info("Triggering self-diagnosis...")

        diagnosis = await SelfDiagnostic().run()

        # Log to TimeKeeper for auditing
        await self.tk.log_event(
            "ImmuneSystem",
            "DIAGNOSIS_COMPLETE",
            {"velocity": self._last_velocity, "diagnosis": diagnosis},
        )

        if diagnosis.get("status") in ["degraded", "error"]:
            logger.info("Executing corrective protocols...")
            await ActuatorSystem().execute(diagnosis)

    def stop(self) -> None:
        """Stop monitoring loop."""
        self._running = False


class ActuatorSystem:
    """
    Executes corrective actions based on immune system diagnosis.
    Follows "Compound Engineering" - turning diagnoses into actionable tasks.
    """

    def __init__(self):
        self.db = None  # Lazy load

    async def execute(self, diagnosis: dict[str, Any]) -> None:
        """Route diagnosis to appropriate action."""
        rec = diagnosis.get("recommendation", "")
        issues = diagnosis.get("issues", [])

        # 1. Create Swarm Task (Self-Healing)
        await self._create_repair_task(rec, issues)

        # 2. Notify Users (if critical)
        if diagnosis.get("status") == "error":
            logger.critical(f"IMMUNE TRIGGER: {rec}")

    async def _create_repair_task(self, recommendation: str, issues: list[str]) -> None:
        """Create a structured task in SurrealDB for the Swarm."""
        import hashlib
        import time

        from cohezion.core.persistence.surreal_client import SurrealClient

        client = SurrealClient()
        await client.connect()

        desc = f"IMMUNE SYSTEM AUTO-TASK: {recommendation}"
        context = "\n".join(issues)
        task_id = hashlib.sha256(f"immune_{time.time()}_{desc}".encode()).hexdigest()

        task = {
            "id": task_id,
            "type": "bugfix",
            "description": desc,
            "context": context,
            "status": "pending",
            "source_file": "immune_system_generated",
            "line_number": 0,
            "priority": "high",
            "created_at": time.time(),
        }

        try:
            # Upsert logic (using create for now as per previous fix)
            await client.create("swarm_tasks", task)
            logger.info(f"✅ Created Self-Healing Task: {task_id}")
        except Exception as e:
            logger.error(f"Failed to create repair task: {e}")


class SelfDiagnostic:
    """
    Uses CriticAgent to analyze recent errors and produce recommendations.
    """

    def __init__(self):
        self.tk = get_time_keeper()
        self.critic = CriticAgent()

    async def run(self) -> dict[str, Any]:
        """Analyze recent errors and return diagnosis."""
        try:
            # 1. Fetch recent errors from velocity_events
            errors = await self._fetch_recent_errors(limit=10)

            if not errors:
                return {
                    "status": "healthy",
                    "message": "No recent errors found.",
                    "recommendation": "System appears healthy. Low velocity may be due to low task volume.",
                }

            # 2. Format errors as ThoughtVectors for Critic
            thoughts = self._errors_to_thoughts(errors)

            # 3. Run Critic analysis
            critique = await self.critic.critique(thoughts)

            return {
                "status": "degraded",
                "error_count": len(errors),
                "coherence": critique.overall_coherence,
                "recommendation": critique.recommendation,
                "issues": critique.logical_issues,
            }

        except Exception as e:
            logger.error(f"Self-diagnosis failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "recommendation": "Manual investigation required.",
            }

    async def _fetch_recent_errors(self, limit: int = 10) -> list[dict]:
        """Fetch recent error events from SurrealDB."""
        query = f"""
        SELECT * FROM velocity_events
        WHERE type IN ['LLM_ERROR', 'MINING_ERROR', 'IMAP_ERROR']
        ORDER BY timestamp DESC
        LIMIT {limit}
        """

        try:
            result = await self.tk.db.query(query)
            return result if result else []
        except Exception as e:
            logger.error(f"Failed to fetch errors: {e}")
            return []

    def _errors_to_thoughts(self, errors: list[dict]) -> list[ThoughtVector]:
        """Convert error events to ThoughtVectors for Critic analysis."""
        thoughts = []
        for err in errors:
            content = f"Error Type: {err.get('type', 'UNKNOWN')}\n"
            content += f"Agent: {err.get('agent', 'unknown')}\n"
            content += f"Details: {err.get('details', {})}\n"
            content += f"Time: {err.get('timestamp', 'unknown')}"

            thoughts.append(
                ThoughtVector(
                    perspective=Perspective.TECHNICAL,
                    content=content,
                    confidence=0.8,
                    metadata={"source": "error_log"},
                )
            )

        return thoughts


# --- Demo / Test ---
async def demo_immune_system():
    print("--- Immune System Demo ---")
    monitor = VelocityMonitor(threshold_tasks_per_hour=100)  # High threshold to trigger

    # Run single check instead of loop for demo
    await monitor._check_health()

    print(f"Last Velocity: {monitor._last_velocity}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(demo_immune_system())
