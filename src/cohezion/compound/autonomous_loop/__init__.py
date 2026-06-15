"""Autonomous compound engineering loop package.

Subprocess-based autonomous improvement system that runs Claude Code
processes to fix real issues in the codebase.

Components:
- LoopCoordinator: budget management, checkpoint/resume, sprint tracking
- TaskGenerator: scans codebase for real issues to fix
- ImprovementExecutor: runs Claude Code subprocesses for each task
- FirstSprint: test stabilization sprint (fixes collection errors)
- run: CLI entry point

Usage:
    # Run the full autonomous loop
    uv run python -m cohezion.compound.autonomous_loop.run

    # Run with custom config
    uv run python -m cohezion.compound.autonomous_loop.run --hours 2 --resume

    # Generate tasks only (no execution)
    uv run python -m cohezion.compound.autonomous_loop.run --generate-only
"""

from __future__ import annotations

from .coordinator import LoopConfig, LoopCoordinator, LoopReport, LoopTask, SprintResult
from .executor import ImprovementExecutor
from .first_sprint import TestStabilizationSprint
from .task_generator import TaskGenerator


__all__ = [
    "ImprovementExecutor",
    "LoopConfig",
    "LoopCoordinator",
    "LoopReport",
    "LoopTask",
    "SprintResult",
    "TaskGenerator",
    "TestStabilizationSprint",
]
