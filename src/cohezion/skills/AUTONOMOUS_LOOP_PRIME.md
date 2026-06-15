---
name: autonomous-loop
description: Subprocess-based autonomous compound engineering loop — LoopCoordinator, TaskGenerator, ImprovementExecutor for unattended self-improvement
version: "1.0.0"
tags: [compound, loop-engineering, autonomous, subprocess, self-improvement, checkpoint]
---

# Autonomous Compound Engineering Loop

## Purpose

Provides an unattended self-improvement loop that runs Claude Code subprocesses to fix
real codebase issues. Each subprocess gets a fresh context — no context bloat within
the main coordinator. The coordinator manages budget, sprint tracking, and checkpoint/resume.

## Module

`src/cohezion/compound/autonomous_loop/`

## Architecture

```
LoopCoordinator → TaskGenerator → ImprovementExecutor → Claude Code subprocess
```

- **LoopCoordinator**: budget (wall-clock + token), sprint lifecycle, checkpoint/resume
- **TaskGenerator**: scans codebase for real issues (test failures, lint, type errors, refactors)
- **ImprovementExecutor**: runs `claude -p <prompt>` subprocesses with timeout
- **TestStabilizationSprint**: first-sprint task list targeting collection errors
- **LoopConfig**: configurable budget, paths, behavior

## Usage

```bash
# Run 3-hour autonomous loop
uv run python -m cohezion.compound.autonomous_loop.run

# Custom config
uv run python -m cohezion.compound.autonomous_loop.run --hours 2 --resume

# Generate tasks only (dry run)
uv run python -m cohezion.compound.autonomous_loop.run --generate-only
```

## Python API

```python
from cohezion.compound.autonomous_loop import (
    LoopCoordinator, LoopConfig, TaskGenerator, ImprovementExecutor
)

config = LoopConfig(max_wall_clock_hours=3.0, max_tokens=1_000_000)
coordinator = LoopCoordinator(config)
generator = TaskGenerator(config.worktree_path)
executor = ImprovementExecutor(config)

backlog = generator.generate_all_tasks()
coordinator.set_backlog(backlog)
report = coordinator.run(executor)
```

## LoopTask Categories

| Category | Source | Verification |
|----------|--------|--------------|
| `test_fix` | `pytest --collect-only` failures | `pytest <file> -q` |
| `lint_fix` | `ruff check` errors | `ruff check <file>` |
| `type_fix` | `mypy` errors | `mypy <file>` |
| `refactor` | Files >500 lines | `pytest` + import check |
| `feature` | Manual task list | Task-specific |

## Budget Management

```python
# Default limits:
max_wall_clock_hours = 3.0   # 3-hour wall clock
max_tokens = 1_000_000       # 1M token cap per loop
sprint_duration_seconds = 900  # 15-min sprints
checkpoint_interval_seconds = 900  # save state every 15 min
```

## Checkpoint/Resume

State is saved to `/tmp/cohezion-autonomous-loop/checkpoint.json` after each sprint.
`--resume` flag loads existing checkpoint and continues where it left off.

## Design Rationale

Subprocess-based execution (vs. in-process Agent spawning) means:
- Each task gets a fresh Claude Code context (no compounding context bloat)
- The coordinator's context remains small regardless of task count
- Failed subprocesses don't crash the coordinator
- Natural timeout boundary at the OS process level
