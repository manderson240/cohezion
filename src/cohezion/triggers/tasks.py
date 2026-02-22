"""Background task definitions for Trigger.dev integration.

Each task is a self-contained entry point that Trigger.dev invokes via the
Python build extension.  Tasks write structured JSON to stdout so the TS
wrapper can capture results.

Task categories
---------------
- ``research/*``  : Model scouting, paper ingestion, experiment analysis
- ``simulation/*``: Training pipelines, FLUME VAE, RL policy, universe sims
- ``health/*``    : Test suites, repo hygiene, security audits, degradation
- ``compound/*``  : Skill refinement, retrospection loops
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskCategory(str, Enum):
    """Top-level task categories matching Trigger.dev queue names."""

    RESEARCH = "research"
    SIMULATION = "simulation"
    HEALTH = "health"
    COMPOUND = "compound"


class TaskPriority(int, Enum):
    """Priority levels (higher = runs first)."""

    CRITICAL = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25
    BACKGROUND = 10


@dataclass
class TaskDefinition:
    """Metadata for a registered background task."""

    task_id: str
    category: TaskCategory
    description: str
    cron: str | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    max_concurrent: int = 1
    timeout_seconds: int = 3600
    queue: str | None = None
    tags: list[str] = field(default_factory=list)

    @property
    def queue_name(self) -> str:
        return self.queue or f"cohezion-{self.category.value}"


# ---------------------------------------------------------------------------
# Task registry
# ---------------------------------------------------------------------------

TASK_DEFINITIONS: list[TaskDefinition] = [
    # -- Research Lab -------------------------------------------------------
    TaskDefinition(
        task_id="research/model-scout",
        category=TaskCategory.RESEARCH,
        description="Scout for new SOTA models on HuggingFace/Ollama registry",
        cron="0 6 * * *",  # daily at 6 AM UTC
        priority=TaskPriority.LOW,
        tags=["research", "models"],
    ),
    TaskDefinition(
        task_id="research/paper-ingest",
        category=TaskCategory.RESEARCH,
        description="Ingest and index new research papers from configured feeds",
        cron="0 8 * * *",  # daily at 8 AM UTC
        priority=TaskPriority.LOW,
        tags=["research", "papers"],
    ),
    TaskDefinition(
        task_id="research/experiment-analysis",
        category=TaskCategory.RESEARCH,
        description="Analyze recent experiment results and surface insights",
        cron="0 12 * * *",  # daily at noon UTC
        priority=TaskPriority.NORMAL,
        tags=["research", "analysis"],
    ),
    # -- Universe Simulations -----------------------------------------------
    TaskDefinition(
        task_id="simulation/training-pipeline",
        category=TaskCategory.SIMULATION,
        description="Full training pipeline: sim -> VAE -> RL -> bridge -> compare",
        cron="0 0 * * 0",  # weekly on Sunday midnight UTC
        priority=TaskPriority.HIGH,
        max_concurrent=1,
        timeout_seconds=28800,  # 8 hours
        tags=["simulation", "training", "pipeline"],
    ),
    TaskDefinition(
        task_id="simulation/flume-vae-train",
        category=TaskCategory.SIMULATION,
        description="Train FLUME VAE on latest simulation artifacts",
        cron=None,  # on-demand only
        priority=TaskPriority.HIGH,
        timeout_seconds=7200,  # 2 hours
        tags=["simulation", "vae", "training"],
    ),
    TaskDefinition(
        task_id="simulation/rl-policy-train",
        category=TaskCategory.SIMULATION,
        description="Train RL policy on FlumeNav-v0 environment",
        cron=None,  # on-demand only
        priority=TaskPriority.HIGH,
        timeout_seconds=7200,
        tags=["simulation", "rl", "training"],
    ),
    TaskDefinition(
        task_id="simulation/mass-sim",
        category=TaskCategory.SIMULATION,
        description="Run mass simulation to generate training data",
        cron="0 2 * * 1,4",  # Mon and Thu at 2 AM UTC
        priority=TaskPriority.NORMAL,
        timeout_seconds=3600,
        tags=["simulation", "mass-sim"],
    ),
    TaskDefinition(
        task_id="simulation/universe-bridge",
        category=TaskCategory.SIMULATION,
        description="Bridge trained weights to simulation engine and validate",
        cron=None,  # on-demand
        priority=TaskPriority.NORMAL,
        tags=["simulation", "bridge"],
    ),
    # -- Project Health -----------------------------------------------------
    TaskDefinition(
        task_id="health/test-suite",
        category=TaskCategory.HEALTH,
        description="Run full pytest suite and report results",
        cron="0 */6 * * *",  # every 6 hours
        priority=TaskPriority.HIGH,
        timeout_seconds=600,  # 10 min
        tags=["health", "tests"],
    ),
    TaskDefinition(
        task_id="health/repo-hygiene",
        category=TaskCategory.HEALTH,
        description="Run repo janitor: git health, dead code, bloat detection",
        cron="0 3 * * *",  # daily at 3 AM UTC
        priority=TaskPriority.NORMAL,
        tags=["health", "hygiene"],
    ),
    TaskDefinition(
        task_id="health/security-audit",
        category=TaskCategory.HEALTH,
        description="Run security scout and vulnerability checks",
        cron="0 4 * * *",  # daily at 4 AM UTC
        priority=TaskPriority.HIGH,
        tags=["health", "security"],
    ),
    TaskDefinition(
        task_id="health/metrics-snapshot",
        category=TaskCategory.HEALTH,
        description="Collect and persist system metrics snapshot",
        cron="*/30 * * * *",  # every 30 minutes
        priority=TaskPriority.LOW,
        timeout_seconds=120,
        tags=["health", "metrics"],
    ),
    TaskDefinition(
        task_id="health/degradation-check",
        category=TaskCategory.HEALTH,
        description="Check for HIHO coherence degradation across agents",
        cron="0 */2 * * *",  # every 2 hours
        priority=TaskPriority.CRITICAL,
        timeout_seconds=300,
        tags=["health", "degradation", "hiho"],
    ),
    TaskDefinition(
        task_id="health/db-pruning",
        category=TaskCategory.HEALTH,
        description="Prune stale SurrealDB records and optimize storage",
        cron="0 5 * * 0",  # weekly on Sunday at 5 AM
        priority=TaskPriority.LOW,
        timeout_seconds=600,
        tags=["health", "database"],
    ),
    # -- Compound Engineering -----------------------------------------------
    TaskDefinition(
        task_id="compound/skill-refinement",
        category=TaskCategory.COMPOUND,
        description="Run skill refinement loop: analyze -> update -> validate",
        cron="0 10 * * *",  # daily at 10 AM UTC
        priority=TaskPriority.NORMAL,
        timeout_seconds=1800,
        tags=["compound", "skills"],
    ),
    TaskDefinition(
        task_id="compound/retrospection",
        category=TaskCategory.COMPOUND,
        description="Run retrospection engine on recent executions",
        cron="0 22 * * *",  # daily at 10 PM UTC
        priority=TaskPriority.NORMAL,
        timeout_seconds=1200,
        tags=["compound", "retrospection"],
    ),
    TaskDefinition(
        task_id="compound/journey-audit",
        category=TaskCategory.COMPOUND,
        description="Audit 12D journey tracking for drift and anomalies",
        cron="0 14 * * *",  # daily at 2 PM UTC
        priority=TaskPriority.NORMAL,
        timeout_seconds=600,
        tags=["compound", "journey", "audit"],
    ),
    TaskDefinition(
        task_id="compound/vault-compile",
        category=TaskCategory.COMPOUND,
        description="Compile MEMORY.md from vault learnings",
        cron="0 9 * * 1",  # weekly on Monday at 9 AM
        priority=TaskPriority.LOW,
        timeout_seconds=300,
        tags=["compound", "vault", "memory"],
    ),
]


def get_task_registry() -> dict[str, TaskDefinition]:
    """Return task definitions keyed by task_id."""
    return {t.task_id: t for t in TASK_DEFINITIONS}


def get_scheduled_tasks() -> list[TaskDefinition]:
    """Return only tasks that have a cron schedule."""
    return [t for t in TASK_DEFINITIONS if t.cron is not None]


def get_tasks_by_category(category: TaskCategory) -> list[TaskDefinition]:
    """Return tasks filtered by category."""
    return [t for t in TASK_DEFINITIONS if t.category == category]


# ---------------------------------------------------------------------------
# Stdout result helper (for Trigger.dev Python extension)
# ---------------------------------------------------------------------------


def emit_result(result: dict[str, Any]) -> None:
    """Write a JSON result to stdout for the TS wrapper to capture."""
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    sys.stdout.flush()
