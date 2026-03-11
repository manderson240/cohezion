---
title: Context Awareness Engine Improvements
date: 2026-02-24
status: PENDING
tags: [plan, cohezion-engine, context, compound-engineering]
Worktree: Yes
---

# Context Awareness Engine Improvements

**Goal:** Make the cohezion-engine context module genuinely predictive and actionable — moving from passive percentage reporting to active context budget management with vault-integrated handoff.

## Problem

The current `cz context --json` reports a percentage and status. It does not tell you:
- How fast context is growing (velocity)
- How many more turns remain before CLEAR_NEEDED
- Which turns consumed the most tokens
- Whether a planned task will fit in remaining budget
- What was happening when context pressure peaked

This limits compound engineering efficiency: agents must react to context pressure instead of planning around it.

## Compound Engineering Value

Token-efficient compound engineering requires context-aware task scheduling. Without velocity and budget data, agents run tasks that overrun context, forcing emergency handoffs that lose work. With velocity-aware planning, agents can:
1. Batch cheap tasks at end of session
2. Defer expensive tasks to fresh sessions
3. Trigger handoff after completing a task (not mid-task)
4. Include context cost metadata in vault observations

## Tasks

**Progress:** Done: 0 | Left: 6

### Task 1: Add Output Token Tracking [ ]
Track `output_tokens` from assistant messages (currently ignored). Include in percentage calculation and return separately in the result dict.

**Files:** `context.py`, `test_context.py`
**Acceptance:** `estimate_context()` returns `output_tokens` key; percentage includes outputs; tests cover output-only token scenarios.

### Task 2: Add Context Velocity [ ]
Compute tokens/turn rate using the last N turns (configurable, default 5). Report projected turns until CLEAR_NEEDED.

**Files:** `context.py`, `test_context.py`
**Acceptance:**
- `estimate_context()` returns `velocity_tokens_per_turn`, `turns_remaining` keys
- `turns_remaining` = `None` when velocity = 0
- `turns_remaining` rounds to int, minimum 0
- Tests cover: zero velocity, positive velocity, CLEAR_NEEDED already hit

### Task 3: Add Per-Turn Context Breakdown [ ]
Return top-N most expensive turns in the result. Enables identifying which operations consumed context budget.

**Files:** `context.py`, `test_context.py`
**Acceptance:**
- `estimate_context(top_turns=5)` returns `top_turns` list of `{turn: int, tokens: int}` dicts
- `top_turns` sorted descending by tokens
- `top_turns=0` (default) omits the field entirely (no breaking change)
- Tests cover: fewer turns than top_turns limit, empty session

### Task 4: Add `cz context estimate` Subcommand [ ]
Pre-flight check: given a token estimate, report whether the task fits and what status would be after.

```bash
cz context estimate --tokens 15000
# → {"fits": true, "status_after": "OK", "percentage_after": 62.5, "turns_remaining_after": 4}

cz context estimate --tokens 80000
# → {"fits": false, "status_after": "CLEAR_NEEDED", "percentage_after": 95.0, "turns_remaining": 0}
```

**Files:** `cli.py`, `context.py`, `test_cli.py`, `test_context.py`
**Acceptance:**
- `estimate` subcommand exists under `context`
- Returns JSON with `fits`, `status_after`, `percentage_after`
- `fits` = True when `percentage_after < 90.0`
- Reuses existing `estimate_context()` with new `hypothetical_tokens` param

### Task 5: Add Context Snapshot on WARNING [ ]
When context transitions to WARNING (crosses 80%), write a brief snapshot file to the session directory. Enables post-mortem analysis of what was happening when pressure peaked.

```
~/.cohezion-engine/sessions/<id>/context-snapshots/YYYYMMDD-HHMMSS.json
{
  "timestamp": "...",
  "percentage": 83.2,
  "status": "WARNING",
  "velocity_tokens_per_turn": 8400,
  "turns_remaining": 2,
  "top_turns": [...]
}
```

**Files:** `context.py`, `session.py`, `hooks/context_monitor.py`, `test_context.py`, `test_hooks.py`
**Acceptance:**
- Snapshot written when status transitions to WARNING or CLEAR_NEEDED
- Snapshot NOT written on repeat calls at same status (only on transition)
- `context_monitor.py` hook calls snapshot writer
- Previous status stored in session dir as `context-status.txt`
- Tests cover: first call at WARNING writes snapshot, second call doesn't, OK→WARNING transition writes, WARNING→WARNING does not

### Task 6: Rich CLI Output for `cz context` [ ]
When called without `--json`, display human-readable context status with velocity and turns remaining.

```
Context: 67.3% [OK]
  Velocity: ~8,400 tokens/turn
  Turns remaining: ~4
  Peak turn: turn 12 (14,200 tokens)
```

**Files:** `cli.py`, `test_cli.py`
**Acceptance:**
- Non-JSON output includes velocity, turns_remaining, peak turn
- `--json` output is unchanged (backward compat)
- `turns_remaining` shows "∞" when velocity = 0
- Tests verify output format for OK, WARNING, CLEAR_NEEDED statuses

## Architecture Notes

### `estimate_context()` Extended Signature
```python
def estimate_context(
    session_jsonl: Path | None = None,
    context_limit: int = DEFAULT_CONTEXT_LIMIT,
    warn_threshold: float = 80.0,
    clear_threshold: float = 90.0,
    velocity_window: int = 5,       # NEW: turns to average for velocity
    top_turns: int = 0,             # NEW: 0 = omit, N = return top N
    hypothetical_tokens: int = 0,   # NEW: for estimate subcommand
) -> dict:
```

### Return Dict Extended Format
```python
{
    "status": "OK",
    "percentage": 67.3,
    "input_tokens": 120_000,        # NEW: breakdown
    "output_tokens": 14_500,        # NEW: breakdown
    "velocity_tokens_per_turn": 8_400,  # NEW
    "turns_remaining": 4,           # NEW (None if velocity=0)
    "top_turns": [                  # NEW (only if top_turns > 0)
        {"turn": 12, "tokens": 14_200},
        {"turn": 8, "tokens": 11_800},
    ],
}
```

### Context Snapshot Transition Logic
```python
# In context_monitor.py hook
prev_status = read_previous_status(session_dir)
curr = estimate_context(...)
if curr["status"] != prev_status and curr["status"] in ("WARNING", "CLEAR_NEEDED"):
    write_snapshot(session_dir, curr)
write_current_status(session_dir, curr["status"])
```

## Test Strategy

All tasks follow TDD — tests written before implementation:
1. Write failing test → verify it fails → implement → verify pass
2. No mocks for internal logic — use `tmp_path` fixtures with real JSONL files
3. CLI tests use `subprocess.run([sys.executable, "-m", "cohezion_engine.cli", ...])` pattern (existing convention)

## Verification

After all tasks:
```bash
cd tools/cohezion-engine
uv run pytest -q          # All 71+ tests pass
ruff check src tests      # 0 linting errors
```

Manual verification:
```bash
cz context --json         # Shows velocity and turns_remaining
cz context estimate --tokens 50000 --json   # Shows fits/status_after
```

## Related Concepts
- [[context-management]]
- [[cohezion]]
- [[compound-engineering]]
- [[token-efficiency]]
