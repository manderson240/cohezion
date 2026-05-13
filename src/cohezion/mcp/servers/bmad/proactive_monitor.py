#!/usr/bin/env python3
"""BMad Proactive Monitor - Anticipates needs and suggests actions.

This module implements proactive BMad behavior:
1. Monitors repository layer for changes
2. Detects patterns that need BMad alignment
3. Suggests actions automatically
4. Executes with user confirmation

Proactive Principles:
- Detect → Suggest → Confirm → Execute
- Learn from patterns
- Minimize user cognitive load
- Maximize automation with safety
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.core.persistence.repositories.surreal_proactive_repository import (
    PatternEffectiveness,
    SuggestionAcceptance,
    SurrealProactiveRepository,
)


logger = logging.getLogger(__name__)


@dataclass
class ProactiveSuggestion:
    """A proactive suggestion from BMad."""

    id: str
    title: str
    description: str
    priority: str  # critical, high, medium, low
    category: str  # alignment, optimization, quality, maintenance
    suggested_action: str
    auto_executable: bool = False
    confidence: float = 0.0
    timestamp: str = field(default_factory=lambda: "")
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class PatternMatch:
    """Detected pattern that triggers proactive suggestions."""

    name: str
    description: str
    detection_fn: Callable[[Path], bool]
    suggestion_fn: Callable[[Path], ProactiveSuggestion]
    enabled: bool = True


class ProactiveMonitor:
    """Monitors codebase and suggests proactive actions.

    Usage:
        monitor = ProactiveMonitor(project_root=Path("."))
        suggestions = await monitor.scan_for_suggestions()

        for suggestion in suggestions:
            print(f"[{suggestion.priority}] {suggestion.title}")
            if suggestion.auto_executable:
                confirm = input("Execute? (y/n): ")
                if confirm.lower() == 'y':
                    await monitor.execute_suggestion(suggestion)
    """

    def __init__(self, project_root: Path, db: Any | None = None):
        """Initialize proactive monitor.

        Args:
            project_root: Root path of the project to monitor
            db: Optional SurrealDB connection for learning system
        """
        self.project_root = project_root
        self.suggestions: list[ProactiveSuggestion] = []
        self.patterns: list[PatternMatch] = []
        self._last_scan_hash: str | None = None
        self._repository: SurrealProactiveRepository | None = None

        # Initialize learning system if database provided
        if db is not None:
            self._repository = SurrealProactiveRepository(db)
            logger.info("proactive_monitor_learning_system_enabled")

        # Register detection patterns
        self._register_repository_patterns()
        self._register_workflow_patterns()
        self._register_quality_patterns()

    def _register_repository_patterns(self):
        """Register repository layer detection patterns."""

        # Pattern 1: New repository without BMad workflow
        def detect_new_repo(path: Path) -> bool:
            repo_files = list(path.glob("**/repositories/*.py"))
            workflow_manifest = path / "_bmad/_config/workflow-manifest.csv"
            if not workflow_manifest.exists():
                return len(repo_files) > 4  # More than base repos

            # Check if repository operations are in workflow manifest
            content = workflow_manifest.read_text()
            return "repository" not in content.lower()

        def suggest_repo_workflow(path: Path) -> ProactiveSuggestion:
            return ProactiveSuggestion(
                id="repo-workflow-missing",
                title="Repository Operations Missing BMad Workflows",
                description="Detected repository layer without formal BMad workflow definitions",
                priority="high",
                category="alignment",
                suggested_action="Create BMad workflows for repository batch operations",
                auto_executable=True,
                confidence=0.9,
                metadata={"repo_count": len(list(path.glob("**/repositories/*.py")))},
            )

        self.patterns.append(
            PatternMatch(
                name="repository-workflow-gap",
                description="New repository without BMad workflow",
                detection_fn=detect_new_repo,
                suggestion_fn=suggest_repo_workflow,
            )
        )

        # Pattern 2: Repository metrics not integrated with BMad observability
        def detect_metrics_gap(path: Path) -> bool:
            base_repo = path / "src/cohezion/core/persistence/repositories/base.py"
            bmad_observability = path / "_bmad/core/observability"

            if base_repo.exists() and not bmad_observability.exists():
                return True
            return False

        def suggest_metrics_integration(path: Path) -> ProactiveSuggestion:
            return ProactiveSuggestion(
                id="metrics-observability-gap",
                title="Repository Metrics Not Integrated with BMad Observability",
                description="RepositoryMetrics collected but not routed to BMad monitoring",
                priority="medium",
                category="integration",
                suggested_action="Create BMad observability integration for RepositoryMetrics",
                auto_executable=True,
                confidence=0.85,
            )

        self.patterns.append(
            PatternMatch(
                name="metrics-observability-gap",
                description="Metrics not integrated with observability",
                detection_fn=detect_metrics_gap,
                suggestion_fn=suggest_metrics_integration,
            )
        )

        # Pattern 3: Batch operations without BMad task definitions
        def detect_batch_tasks_missing(path: Path) -> bool:
            task_manifest = path / "_bmad/_config/task-manifest.csv"
            base_repo = path / "src/cohezion/core/persistence/repositories/base.py"

            if not task_manifest.exists() or not base_repo.exists():
                return False

            content = task_manifest.read_text()
            return "batch_create" not in content and "batch_get" not in content

        def suggest_batch_tasks(path: Path) -> ProactiveSuggestion:
            return ProactiveSuggestion(
                id="batch-tasks-missing",
                title="Batch Operations Missing from BMad Task Manifest",
                description="Repository batch operations not defined as BMad tasks",
                priority="high",
                category="alignment",
                suggested_action="Add batch_create, batch_get to task-manifest.csv",
                auto_executable=True,
                confidence=0.95,
            )

        self.patterns.append(
            PatternMatch(
                name="batch-tasks-missing",
                description="Batch operations not in task manifest",
                detection_fn=detect_batch_tasks_missing,
                suggestion_fn=suggest_batch_tasks,
            )
        )

    def _register_workflow_patterns(self):
        """Register workflow detection patterns."""

        # Pattern: Adversarial review without BMad quality gate
        def detect_adversarial_gap(path: Path) -> bool:
            adversarial_tests = list(path.glob("**/test_*adversarial*.py"))
            quality_gates = path / "_bmad/core/quality-gates"

            return len(adversarial_tests) > 0 and not quality_gates.exists()

        def suggest_quality_gate(path: Path) -> ProactiveSuggestion:
            return ProactiveSuggestion(
                id="adversarial-quality-gap",
                title="Adversarial Review Not Integrated as BMad Quality Gate",
                description="Adversarial review tests exist but not formalized as quality gate",
                priority="medium",
                category="quality",
                suggested_action="Create BMad quality gate for adversarial review",
                auto_executable=True,
                confidence=0.8,
            )

        self.patterns.append(
            PatternMatch(
                name="adversarial-quality-gap",
                description="Adversarial review without quality gate",
                detection_fn=detect_adversarial_gap,
                suggestion_fn=suggest_quality_gate,
            )
        )

    def _register_quality_patterns(self):
        """Register code quality detection patterns."""

        # Pattern: Test coverage below threshold
        def detect_low_coverage(path: Path) -> bool:
            coverage_file = path / "htmlcov/status.json"
            if not coverage_file.exists():
                return False

            try:
                data = json.loads(coverage_file.read_text())
                coverage = float(data.get("totals", {}).get("percent_covered", 100))
                return coverage < 80.0
            except Exception:
                return False

        def suggest_coverage_improvement(path: Path) -> ProactiveSuggestion:
            return ProactiveSuggestion(
                id="low-test-coverage",
                title="Test Coverage Below 80% Threshold",
                description="Current test coverage is below BMad quality threshold",
                priority="high",
                category="quality",
                suggested_action="Run test coverage analysis and identify gaps",
                auto_executable=False,
                confidence=1.0,
            )

        self.patterns.append(
            PatternMatch(
                name="low-test-coverage",
                description="Test coverage below threshold",
                detection_fn=detect_low_coverage,
                suggestion_fn=suggest_coverage_improvement,
            )
        )

    async def scan_for_suggestions(self) -> list[ProactiveSuggestion]:
        """Scan codebase for proactive suggestions.

        Returns:
            List of proactive suggestions sorted by priority
        """
        self.suggestions = []

        # Check each pattern
        for pattern in self.patterns:
            if not pattern.enabled:
                continue

            try:
                if pattern.detection_fn(self.project_root):
                    suggestion = pattern.suggestion_fn(self.project_root)
                    self.suggestions.append(suggestion)
                    logger.info(f"Proactive detection: {pattern.name} → {suggestion.title}")
            except Exception as e:
                logger.error(f"Pattern {pattern.name} detection failed: {e}")

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        self.suggestions.sort(key=lambda s: priority_order.get(s.priority, 4))

        return self.suggestions

    async def execute_suggestion(
        self,
        suggestion: ProactiveSuggestion,
        confirm: bool = True,
    ) -> bool:
        """Execute a proactive suggestion.

        Args:
            suggestion: The suggestion to execute
            confirm: Require user confirmation before execution

        Returns:
            True if executed successfully, False otherwise
        """
        if not suggestion.auto_executable:
            logger.warning(f"Suggestion {suggestion.id} is not auto-executable")
            return False

        if confirm:
            print("\n🤖 BMad Proactive Suggestion:")
            print(f"   {suggestion.title}")
            print(f"   Action: {suggestion.suggested_action}")
            response = input("\n   Execute? (y/n): ")
            if response.lower() != "y":
                return False

        logger.info(f"Executing proactive suggestion: {suggestion.id}")

        # Execute based on suggestion ID
        execution_map = {
            "repo-workflow-missing": self._create_repository_workflows,
            "metrics-observability-gap": self._integrate_metrics_observability,
            "batch-tasks-missing": self._add_batch_tasks,
            "adversarial-quality-gap": self._create_quality_gate,
        }

        executor = execution_map.get(suggestion.id)
        if not executor:
            logger.error(f"No executor for suggestion {suggestion.id}")
            return False

        try:
            await executor()
            logger.info(f"Suggestion {suggestion.id} executed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to execute {suggestion.id}: {e}")
            return False

    async def _create_repository_workflows(self) -> bool:
        """Create BMad workflows for repository operations."""
        workflow_path = self.project_root / "_bmad/core/workflows/repository-operations"
        workflow_path.mkdir(parents=True, exist_ok=True)

        # Create batch operation workflow
        workflow_content = """---
name: repository-batch-operations
description: Execute repository batch operations with metrics collection
---

# Repository Batch Operations Workflow

**Goal:** Execute batch operations on repositories with automatic metrics collection

## Steps

1. **Initialize Repository**
   - Load repository from manifest
   - Initialize connection pool
   - Validate configuration

2. **Execute Batch Operation**
   - batch_create: Create multiple entities
   - batch_get: Retrieve multiple entities
   - Track metrics automatically

3. **Collect Metrics**
   - RepositoryMetrics recorded
   - Success rate calculated
   - Cache hit rate tracked

4. **Report Results**
   - BatchOperationResult returned
   - Metrics sent to observability
   - Errors logged with context
"""

        (workflow_path / "workflow.md").write_text(workflow_content)
        logger.info(f"Created repository workflows at {workflow_path}")
        return True

    async def _integrate_metrics_observability(self) -> bool:
        """Integrate RepositoryMetrics with BMad observability."""
        observability_path = self.project_root / "_bmad/core/observability"
        observability_path.mkdir(parents=True, exist_ok=True)

        integration_content = """# BMad Observability - Repository Metrics Integration

## RepositoryMetrics Routing

```python
from cohezion.core.persistence.repositories.base import RepositoryMetrics
from _bmad.core.observability.metrics_collector import MetricsCollector

class RepositoryMetricsCollector:
    '''Collects and routes RepositoryMetrics to BMad observability.'''

    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    def record(self, metrics: RepositoryMetrics):
        '''Route repository metrics to BMad observability.'''
        self.collector.record(
            service="repository-layer",
            operation=metrics.operation,
            duration_ms=metrics.duration_ms,
            success=metrics.success,
            metadata={
                "cache_hit": metrics.cache_hit,
                "batch_size": metrics.batch_size,
                "items_processed": metrics.items_processed,
            }
        )
```

## Dashboards

- Repository Operations Throughput
- Batch Operation Success Rates
- Cache Hit/Miss Ratios
- Slow Operation Alerts (>1s)
"""

        (observability_path / "README.md").write_text(integration_content)
        logger.info(f"Created observability integration at {observability_path}")
        return True

    async def _add_batch_tasks(self) -> bool:
        """Add batch operations to BMad task manifest."""
        manifest_path = self.project_root / "_bmad/_config/task-manifest.csv"

        if not manifest_path.exists():
            # Create initial manifest
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text("id,name,description,category,priority,workflow\n")

        # Read existing content
        content = manifest_path.read_text()
        lines = content.strip().split("\n")

        # Add batch tasks if not present
        new_tasks = [
            "repo-batch-create,Repository Batch Create,"
            "Create multiple entities in batch,repository,high,repository-batch-operations",
            "repo-batch-get,Repository Batch Get,"
            "Retrieve multiple entities in batch,repository,high,repository-batch-operations",
            "repo-metrics-collect,Collect Repository Metrics,"
            "Collect and route RepositoryMetrics,observability,medium,repository-observability",
            "repo-adversarial-review,Adversarial Repository Review,"
            "8-perspective code review,quality,high,adversarial-review",
        ]

        existing_ids = [line.split(",")[0] for line in lines[1:] if line]

        for task in new_tasks:
            task_id = task.split(",")[0]
            if task_id not in existing_ids:
                lines.append(task)
                logger.info(f"Added task to manifest: {task_id}")

        manifest_path.write_text("\n".join(lines) + "\n")
        logger.info(f"Updated task manifest at {manifest_path}")
        return True

    async def _create_quality_gate(self) -> bool:
        """Create BMad quality gate for adversarial review."""
        quality_path = self.project_root / "_bmad/core/quality-gates"
        quality_path.mkdir(parents=True, exist_ok=True)

        gate_content = """---
name: adversarial-review-gate
description: 8-perspective adversarial code review quality gate
---

# Adversarial Review Quality Gate

**Purpose:** Ensure all code passes 8-perspective adversarial review before merge

## Quality Criteria

All code must pass adversarial review across 8 perspectives:

1. ✅ **Security**: No injection vulnerabilities, proper input validation
2. ✅ **Performance**: Query optimization, efficient algorithms
3. ✅ **Reliability**: Error handling, fallback strategies
4. ✅ **Usability**: Clear API design, good documentation
5. ✅ **Maintainability**: Clean code structure, testability
6. ✅ **Compliance**: Audit trails, data privacy
7. ✅ **Innovation**: Novel patterns, best practices
8. ✅ **Ethics**: Fair data handling, transparency

## Enforcement

```bash
# Run adversarial review
uv run pytest tests/compound/tdd_adversarial/ -v

# Must pass all tests
# Minimum 8 perspectives validated
# No critical/high severity findings
```

## Integration

- Runs automatically on PR creation
- Blocks merge if any perspective fails
- Findings posted as PR comments
"""

        (quality_path / "adversarial-review.md").write_text(gate_content)
        logger.info(f"Created quality gate at {quality_path}")
        return True

    async def record_feedback(
        self,
        suggestion: ProactiveSuggestion,
        accepted: bool,
        execution_time_ms: float | None = None,
        feedback: str | None = None,
        user_id: str = "default",
    ) -> SuggestionAcceptance:
        """Record user feedback for a suggestion.

        Args:
            suggestion: The suggestion that was acted on
            accepted: Whether the suggestion was accepted
            execution_time_ms: Optional execution time in milliseconds
            feedback: Optional user feedback text
            user_id: User identifier

        Returns:
            The recorded acceptance record
        """
        if self._repository is None:
            logger.warning("feedback_recording_skipped_no_repository")
            raise RuntimeError("Learning system not initialized - provide db parameter")

        acceptance = SuggestionAcceptance(
            suggestion_id=suggestion.id,
            pattern_id=suggestion.metadata.get("pattern_id", suggestion.category),
            accepted=accepted,
            execution_time_ms=execution_time_ms,
            feedback=feedback,
            user_id=user_id,
            project_root=str(self.project_root),
            confidence_at_decision=suggestion.confidence,
        )

        await self._repository.record_acceptance(acceptance)
        logger.info(
            "feedback_recorded",
            suggestion_id=suggestion.id,
            accepted=accepted,
            feedback=feedback,
        )
        return acceptance

    async def adjust_pattern_confidence(self, pattern_name: str) -> float:
        """Adjust pattern confidence based on historical acceptance rates.

        Uses exponential moving average with decay:
        - High acceptance (>0.8): Increase confidence by 5%
        - Medium acceptance (0.5-0.8): Maintain confidence
        - Low acceptance (<0.5): Decrease confidence by 10%

        Args:
            pattern_name: The pattern to adjust

        Returns:
            New confidence value (0.0-1.0)
        """
        if self._repository is None:
            logger.warning("confidence_adjustment_skipped_no_repository")
            return 0.0

        try:
            effectiveness = await self._repository.get_pattern_effectiveness(pattern_name)

            if effectiveness.total_suggestions < 5:
                # Not enough data for adjustment
                logger.debug(
                    "confidence_adjustment_insufficient_data",
                    pattern_name=pattern_name,
                    samples=effectiveness.total_suggestions,
                )
                return 0.0

            acceptance_rate = effectiveness.acceptance_rate
            current_confidence = effectiveness.avg_confidence

            # Exponential moving average adjustment
            if acceptance_rate > 0.8:
                # High acceptance - increase confidence
                adjustment_factor = 0.05
                new_confidence = min(1.0, current_confidence * (1 + adjustment_factor))
            elif acceptance_rate < 0.5:
                # Low acceptance - decrease confidence
                adjustment_factor = 0.10
                new_confidence = max(0.0, current_confidence * (1 - adjustment_factor))
            else:
                # Medium acceptance - maintain
                new_confidence = current_confidence

            logger.info(
                "pattern_confidence_adjusted",
                pattern_name=pattern_name,
                old_confidence=current_confidence,
                new_confidence=new_confidence,
                acceptance_rate=acceptance_rate,
            )
            return new_confidence

        except Exception as e:
            logger.error("confidence_adjustment_failed", pattern_name=pattern_name, error=str(e))
            return 0.0

    async def get_pattern_effectiveness_report(self) -> list[PatternEffectiveness]:
        """Get effectiveness report for all patterns.

        Returns:
            List of PatternEffectiveness sorted by effectiveness score
        """
        if self._repository is None:
            logger.warning("effectiveness_report_skipped_no_repository")
            raise RuntimeError("Learning system not initialized - provide db parameter")

        effectiveness_list = await self._repository.get_all_pattern_effectiveness()
        sorted_list = sorted(effectiveness_list, key=lambda x: x.effectiveness_score, reverse=True)

        logger.info(
            "effectiveness_report_generated",
            patterns_count=len(sorted_list),
        )
        return sorted_list

    async def cleanup_old_records(self, days_old: int = 90) -> int:
        """Clean up old acceptance records.

        Args:
            days_old: Delete records older than this many days

        Returns:
            Number of records deleted
        """
        if self._repository is None:
            logger.warning("cleanup_skipped_no_repository")
            return 0

        deleted = await self._repository.delete_old_records(days_old)
        logger.info("old_records_cleaned_up", deleted_count=deleted)
        return deleted

    def get_summary(self) -> dict[str, Any]:
        """Get summary of proactive monitoring state.

        Returns:
            Dictionary with monitoring summary
        """
        return {
            "total_patterns": len(self.patterns),
            "enabled_patterns": sum(1 for p in self.patterns if p.enabled),
            "active_suggestions": len(self.suggestions),
            "learning_system_enabled": self._repository is not None,
            "by_priority": {
                "critical": sum(1 for s in self.suggestions if s.priority == "critical"),
                "high": sum(1 for s in self.suggestions if s.priority == "high"),
                "medium": sum(1 for s in self.suggestions if s.priority == "medium"),
                "low": sum(1 for s in self.suggestions if s.priority == "low"),
            },
            "by_category": {
                "alignment": sum(1 for s in self.suggestions if s.category == "alignment"),
                "integration": sum(1 for s in self.suggestions if s.category == "integration"),
                "quality": sum(1 for s in self.suggestions if s.category == "quality"),
                "maintenance": sum(1 for s in self.suggestions if s.category == "maintenance"),
            },
        }


async def main():
    """Run proactive monitor."""
    import sys

    # Get project root from argument or use current directory
    project_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    monitor = ProactiveMonitor(project_root)

    print("🔍 BMad Proactive Monitor Scanning...")
    suggestions = await monitor.scan_for_suggestions()

    if not suggestions:
        print("✅ No proactive suggestions - system is well-aligned!")
        return

    print(f"\n📋 Found {len(suggestions)} proactive suggestions:\n")

    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. [{suggestion.priority.upper()}] {suggestion.title}")
        print(f"   {suggestion.description}")
        if suggestion.auto_executable:
            print(f"   ⚡ Auto-executable: {suggestion.suggested_action}")
        print()

    # Execute suggestions with confirmation
    for suggestion in suggestions:
        if suggestion.auto_executable:
            await monitor.execute_suggestion(suggestion, confirm=True)


if __name__ == "__main__":
    asyncio.run(main())
