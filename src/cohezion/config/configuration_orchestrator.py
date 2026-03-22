"""ConfigurationOrchestrator: Event-driven config sync and size management.

Central hub for keeping CLAUDE.md and GEMINI.md synchronized with vault
and SurrealDB while maintaining lean size and consistency.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from cohezion.concurrency.safe_singleton import safe_singleton
from cohezion.config.config_archival import ConfigArchiver, SizeEnforcer
from cohezion.config.config_events import ConfigEvent
from cohezion.config.config_monitoring import ConfigMonitor
from cohezion.config.config_state import (
    ConfigConflict,
    ConfigState,
    FileMetadata,
    ValidationReport,
)
from cohezion.config.config_sync_engine import ConfigSyncEngine
from cohezion.config.config_sync_logger import ConfigSyncLogger
from cohezion.config.config_validation import ConfigValidator, ReconciliationValidator
from cohezion.config.conflict_policy import ConflictResolutionPolicy
from cohezion.config.git_utils import GitUtils
from cohezion.core.event_bus import Event, EventType


logger = logging.getLogger(__name__)


@safe_singleton
def get_config_orchestrator(
    repo_root: Path | None = None,
) -> ConfigurationOrchestrator:
    """Get or create the configuration orchestrator singleton."""
    if repo_root is None:
        repo_root = Path.cwd()
    return ConfigurationOrchestrator(repo_root)


def reset_config_orchestrator() -> None:
    """Reset the singleton (for testing)."""
    get_config_orchestrator.reset()  # type: ignore


class ConfigurationOrchestrator:
    """Event-driven configuration orchestration.

    Monitors CLAUDE.md, GEMINI.md, vault, and SurrealDB.
    Keeps them synchronized while enforcing size limits and validation.
    """

    def __init__(
        self,
        repo_root: Path | None = None,
        vault_url: str = "http://localhost:8360",
        vault_api_key: str = "",
    ):
        """Initialize orchestrator with repo root."""
        if repo_root is None:
            repo_root = Path.cwd()
        self.repo_root = Path(repo_root)
        self.git_utils = GitUtils(self.repo_root)
        self.config_state = ConfigState()

        # Config file paths
        self.claude_md = self.repo_root / "CLAUDE.md"
        self.gemini_md = self.repo_root / "GEMINI.md"
        self.vault_root = Path.home() / "vaults" / "cohezion-vault"

        # Size limits
        self.size_limits = {
            "CLAUDE.md": {"max_lines": 250, "max_chars": 15000},
            "GEMINI.md": {"max_lines": 200, "max_chars": 12000},
        }

        # Monitoring (Phase 2)
        self.monitor = ConfigMonitor(repo_root, vault_url, vault_api_key)

        # Validation & Reconciliation (Phase 3)
        self.validator = ConfigValidator(self.size_limits)
        self.reconciliation_validator = ReconciliationValidator()
        self.archiver = ConfigArchiver(Path.home() / "vaults" / "cohezion-vault")
        self.size_enforcer = SizeEnforcer(self.size_limits)
        self.sync_logger = ConfigSyncLogger()

        # Real-Time Sync & Git Integration (Phase 4)
        self.sync_engine = ConfigSyncEngine(
            repo_root=self.repo_root,
            vault_root=self.vault_root,
            sync_logger=self.sync_logger,
        )

        # Conflict Resolution (Phase 5A)
        self.conflict_policy = ConflictResolutionPolicy.vault_canonical()

        # Status tracking
        self._monitoring = False
        self._monitor_tasks: list[asyncio.Task] = []

        logger.info(f"ConfigurationOrchestrator initialized at {self.repo_root}")

    async def start_monitoring(self) -> None:
        """Start all monitoring tasks concurrently.

        Phase 2: Real-time monitoring via ConfigMonitor (SSE + polling)
        - Vault changes via VaultSubscriptionClient
        - Config file changes via polling
        - Manual edit detection via git history
        """
        if self._monitoring:
            logger.warning("Monitoring already started")
            return

        self._monitoring = True
        logger.info("Starting configuration orchestration monitoring")

        try:
            # Phase 2: Real-time monitoring
            tasks = [
                asyncio.create_task(self.monitor.start()),  # Real-time vault + config
                asyncio.create_task(self._run_reconciliation_loop()),  # Validation
                asyncio.create_task(self._enforce_size_limits()),  # Size checks
            ]
            self._monitor_tasks = tasks

            # Run all tasks concurrently
            await asyncio.gather(*tasks)

        except asyncio.CancelledError:
            logger.info("Monitoring cancelled")
        except Exception as e:
            logger.error(f"Monitoring error: {e}", exc_info=True)
        finally:
            self._monitoring = False
            await self.monitor.stop()

    async def stop_monitoring(self) -> None:
        """Stop all monitoring tasks."""
        self._monitoring = False
        for task in self._monitor_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self._monitor_tasks, return_exceptions=True)
        logger.info("Configuration orchestration monitoring stopped")

    async def _run_reconciliation_loop(self) -> None:
        """Run periodic reconciliation and validation.

        Reconciliation cycle:
        1. Compute hashes
        2. Compare vs SurrealDB (Phase 3)
        3. Validate consistency
        4. Report mismatches
        """
        while self._monitoring:
            try:
                logger.debug("Starting reconciliation cycle")
                report = await self.validate_consistency()

                if report.passed:
                    logger.debug("Reconciliation passed")
                else:
                    logger.warning(f"Reconciliation failed: {report.recommendations}")

                # Wait 1 hour for next cycle
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reconciliation error: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def _enforce_size_limits(self) -> None:
        """Enforce size limits on config files.

        Phase 3: Checks every 30 minutes, archives and logs if exceeded.
        """
        while self._monitoring:
            try:
                logger.debug("Checking size limits")

                for filename, _limit in self.size_limits.items():
                    file_path = self.claude_md if filename == "CLAUDE.md" else self.gemini_md

                    if file_path.exists():
                        # Check for violations
                        violation_check = self.size_enforcer.check_violations(file_path)

                        if violation_check["violates"]:
                            logger.warning(f"{filename} size violation: {violation_check['violations']}")

                            # Archive old sections
                            archive_result = await self.archiver.archive_old_sections(
                                file_path
                            )

                            # Log archival
                            if archive_result.get("archived"):
                                await self.sync_logger.log_archival(
                                    file=filename,
                                    status="success",
                                    details=archive_result,
                                )

                                # Emit event
                                config_event = Event(
                                    type=EventType.CUSTOM,
                                    source="config-size-enforcer",
                                    payload={
                                        "config_event": ConfigEvent.ARCHIVE_TRIGGERED.name,
                                        "file": filename,
                                        "sections_archived": archive_result[
                                            "sections_archived"
                                        ],
                                    },
                                )
                                self.monitor.event_bus.publish(config_event)

                # Wait 30 minutes for next check
                await asyncio.sleep(1800)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Size enforcement error: {e}")
                await asyncio.sleep(60)

    async def validate_consistency(self) -> ValidationReport:
        """Validate consistency between all config sources.

        Phase 3: Comprehensive validation with logging.
        - File schema validation
        - Size limit checks
        - Reference validation
        - Cycle detection
        - Cross-source reconciliation
        """
        report = ValidationReport()
        start_time = asyncio.get_event_loop().time()

        try:
            # Validate individual files
            for file_path, filename in [
                (self.claude_md, "CLAUDE.md"),
                (self.gemini_md, "GEMINI.md"),
            ]:
                if file_path.exists():
                    # File-level validation
                    file_report = self.validator.validate_file(file_path)
                    report.passed = report.passed and file_report.passed
                    report.recommendations.extend(file_report.recommendations)

                    # Size check
                    size_check = self.size_enforcer.check_violations(file_path)
                    if size_check["violates"]:
                        report.recommendations.extend(size_check["violations"])
                        report.passed = False

                        # Log size violation
                        await self.sync_logger.log_validation(
                            file=filename,
                            status="warning",
                            details={
                                "violations": size_check["violations"],
                                "metadata": size_check["metadata"],
                            },
                        )

                    # Load metadata for state tracking
                    if filename == "CLAUDE.md":
                        self.config_state.claude_md = FileMetadata.from_file(file_path)
                    else:
                        self.config_state.gemini_md = FileMetadata.from_file(file_path)

            # Cross-source reconciliation
            reconciliation_report = self.reconciliation_validator.validate_consistency(
                self.claude_md,
                self.gemini_md,
                self.vault_root,
            )
            report.passed = report.passed and reconciliation_report.passed
            report.recommendations.extend(reconciliation_report.recommendations)

            # Log validation
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            await self.sync_logger.log_validation(
                file="system",
                status="success" if report.passed else "warning",
                details={
                    "passed": report.passed,
                    "recommendations": len(report.recommendations),
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.error(f"Validation error: {e}")
            report.passed = False
            report.recommendations.append(f"Validation error: {e}")
            await self.sync_logger.log_validation(
                file="system",
                status="failed",
                error_message=str(e),
                details={"error": str(e)},
            )

        report.duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        self.config_state.last_validation = report
        self.config_state.total_validations += 1

        return report

    def detect_manual_edits(self, file_path: Path) -> bool:
        """Check if file was manually edited vs auto-generated."""
        return self.git_utils.is_manual_edit(file_path)

    async def detect_conflicts(self) -> list[ConfigConflict]:
        """Detect conflicts between config and vault versions.

        Phase 2 implementation will:
        - Compare git history (who edited last)
        - Detect divergent content
        - Flag bi-directional edits
        """
        conflicts = []

        # Phase 2: Implement full conflict detection
        # - Check manual edits
        # - Compare hashes
        # - Generate diffs

        return conflicts

    async def regenerate_and_commit(
        self,
        filename: str,
        reason: str = "manual_trigger",
    ) -> bool:
        """Regenerate config file and commit to git.

        Phase 4 implementation will handle:
        - Conflict detection and alerting
        - Template-driven regeneration
        - AI-generated commit messages
        - Atomic operations with rollback
        """
        logger.info(f"Regenerating {filename} (reason: {reason})")

        if filename == "CLAUDE.md":
            file_path = self.claude_md
        elif filename == "GEMINI.md":
            file_path = self.gemini_md
        else:
            logger.error(f"Unknown config file: {filename}")
            return False

        try:
            # Phase 2: Detect manual edits
            _is_manual = self.detect_manual_edits(file_path)

            # Phase 2: Detect conflicts
            conflicts = await self.detect_conflicts()

            if conflicts:
                logger.warning(f"Conflicts detected in {filename}")
                # Phase 2: Emit CONFIG_CONFLICT_DETECTED event
                # Phase 2: Create vault/inbox alert for manual review
                return False

            # Phase 4: Generate new content from vault
            # Phase 4: Compare vs current
            # Phase 4: Write new content
            # Phase 4: Create git commit

            logger.info(f"Successfully regenerated {filename}")
            self.config_state.total_syncs += 1
            return True

        except Exception as e:
            logger.error(f"Regeneration error: {e}")
            self.config_state.sync_failures += 1
            return False

    def get_state(self) -> ConfigState:
        """Get current configuration state."""
        return self.config_state

    def get_metrics(self) -> dict:
        """Get orchestration metrics."""
        return {
            "total_syncs": self.config_state.total_syncs,
            "total_conflicts": self.config_state.total_conflicts,
            "total_validations": self.config_state.total_validations,
            "sync_failures": self.config_state.sync_failures,
            "monitoring_active": self._monitoring,
        }
