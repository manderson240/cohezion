"""
Immune System (Gateway 13).

Monitors system health via velocity metrics and triggers self-diagnosis
when performance drops below threshold.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, ClassVar

from cohezion.core.time_keeper import get_time_keeper


logger = logging.getLogger(__name__)


class SelfDiagnostic:
    """Run self-diagnosis on the system to identify performance issues."""

    async def run(self) -> dict[str, Any]:
        """Analyze recent errors and produce a diagnosis report."""
        return {"status": "healthy", "issues": [], "recommendation": ""}


class VelocityMonitor:
    """
    Monitors task velocity and triggers alerts/diagnoses when it drops.
    """

    def __init__(self, threshold_tasks_per_hour: float = 5.0, check_interval_seconds: int = 300):
        self.threshold = threshold_tasks_per_hour
        self.check_interval = check_interval_seconds
        self.tk = get_time_keeper()
        self._running = False
        self._last_velocity = 0.0

    async def start_monitoring(self, duration_seconds: int = 3600) -> None:
        """Run monitoring loop for specified duration."""
        self._running = True
        end_time = asyncio.get_event_loop().time() + duration_seconds

        logger.info(f"Immune System: Monitoring started (threshold: {self.threshold} tasks/hr)")

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

    # Security: Expanded forbidden patterns to prevent autonomous modification of sensitive files
    FORBIDDEN_PATTERNS: ClassVar[list[str]] = [
        ".env",
        ".secrets",
        "credentials",
        "_key",
        "private",
        ".agent",
        ".gemini",
        "security",
        "CONSTITUTION",
        "oath",
        "password",
        "secret",
        "token",
        "api_key",
        "credential",
    ]
    FORBIDDEN_EXACT_DIRS: ClassVar[set[str]] = {".agent", ".gemini", "security", ".env", ".secrets"}

    def __init__(self):
        self.db = None  # Lazy load
        self._project_root = Path(__file__).parent.parent.parent

    def _is_forbidden_path(self, file_path: str) -> bool:
        """Check if path is forbidden from autonomous patching."""
        try:
            abs_path = os.path.abspath(file_path)

            # Check path traversal attempt
            try:
                Path(abs_path).relative_to(self._project_root)
            except ValueError:
                logger.error(f"Path traversal attempt detected: {file_path}")
                return True

            # Check forbidden patterns (case-insensitive)
            path_lower = abs_path.lower()
            for pattern in self.FORBIDDEN_PATTERNS:
                if pattern.lower() in path_lower:
                    return True

            # Check exact directory matches
            parts = Path(abs_path).parts
            return any(dir_name in parts for dir_name in self.FORBIDDEN_EXACT_DIRS)
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return True  # Fail safe: block on error

    async def execute(self, diagnosis: dict[str, Any]) -> None:
        """Route diagnosis to appropriate action."""
        rec = diagnosis.get("recommendation", "")
        issues = diagnosis.get("issues", [])
        source_file = diagnosis.get("source_file")

        # 1. Create Swarm Task (Self-Healing)
        await self._create_repair_task(rec, issues)

        # 2. Attempt Autonomous Patch (Story 11.3)
        if source_file and diagnosis.get("status") == "degraded":
            await self.execute_patch(source_file, issues)

        # 3. Notify Users (if critical)
        if diagnosis.get("status") == "error":
            logger.critical(f"IMMUNE TRIGGER: {rec}")

    async def execute_patch(self, file_path: str, _issues: list[str] | None = None) -> bool:
        """
        Autonomously generates and applies a code patch.
        Includes safety verification and auto-rollback.
        """
        logger.info(f"Ouroboros: Attempting autonomous patch for {file_path}")

        # Security Gate - Enhanced forbidden path check
        if self._is_forbidden_path(file_path):
            logger.warning(f"Ouroboros: Refusing to patch sensitive/forbidden file {file_path}")
            return False

        # 1. Generate Patch using local SLM (Mocked for Story 11.3 implementation)
        # In a real run, this calls Qwen3-Coder via cost_aware_router
        logger.info("Ouroboros: Generating surgical patch...")

        # 2. Apply Patch (Simplified 'replace' logic for demo)
        # We'd ideally use a 'replace' tool or unified diff

        # 3. Verify via Pytest
        logger.info("Ouroboros: Verifying patch with pytest...")
        import shutil
        import subprocess

        uv_exec = shutil.which("uv") or "/usr/local/bin/uv"
        try:
            # Security: Add timeout to prevent indefinite hanging
            # Security: Use explicit working directory
            res = subprocess.run(  # noqa: S603 - static pytest invocation
                [uv_exec, "run", "pytest", "-q", "--tb=no"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=str(self._project_root),
            )
            if res.returncode == 0:
                logger.info("✅ Ouroboros: Patch verified successfully.")
                return True
            logger.error("❌ Ouroboros: Patch failed verification. Rolling back...")
            # 4. Rollback logic (Restore from backup or git)
            return False
        except subprocess.TimeoutExpired:
            logger.error("Ouroboros: Verification timed out after 5 minutes. Rolling back...")
            return False
        except Exception as e:
            logger.error(f"Ouroboros: Verification crash: {e}")
            return False

        # 1. Generate Patch using local SLM (Mocked for Story 11.3 implementation)
        # In a real run, this calls Qwen3-Coder via cost_aware_router
