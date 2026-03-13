---
title: Context Awareness — Next Tier
date: 2026-02-26
status: PENDING
tags: [plan, cohezion-engine, context, compound-engineering]
Worktree: Yes
neural:
  activation: 0.89
  stage: growing
  synapse_in: 2
  synapse_out: 5
---

# Context Awareness — Next Tier

**Goal:** Elevate context awareness from passive reporting to active budget management — attributing cost to specific tool calls, gating spec phase transitions, and surfacing session-level analytics for compound engineering decisions.

## Background

The February 24 plan shipped velocity tracking, `turns_remaining`, `top_turns`, context snapshots, and `cz context estimate`. Those features are all live in `context.py` and tested (100 passing). This plan builds the next layer on top of that foundation.

The addition of `overture-mcp` (plan visualization as interactive flowcharts) opens a new integration surface: annotating plan nodes with projected context cost before the agent begins coding.

## Problem

The current engine answers "how much context have I used?" but not:

- **Which tool calls are the most expensive?** (`top_turns` gives turn ranks but not tool attribution)
- **Will this spec phase transition fit?** (Phase gates check context manually; no first-class CLI support)
- **How efficiently am I using the cache?** (Cache hit rate affects billing but is invisible today)
- **How much did the whole spec workflow cost, across sessions?** (No cross-session aggregation)

Without these answers, agents can't make informed scheduling decisions, and post-mortem analysis of expensive runs is limited to snapshot timestamps.

## Tasks

**Progress:** Done: 0 | Left: 5

### Task 1: Tool-Call Context Attribution [ ]

Parse `tool_use` and `tool_result` entries from the session JSONL alongside the existing `usage` fields. Annotate each turn with the tool name that triggered it. Expose as `top_tools` in `estimate_context()`.

**Files:** `context.py`, `tests/test_context.py`

**Acceptance:**
- `estimate_context(top_tools=N)` returns a `top_tools` list of `{tool: str, total_tokens: int, turn_count: int}` dicts, sorted descending by `total_tokens`
- `top_tools=0` (default) omits the field — no breaking change
- Turns without a tool_use entry are attributed to `"(assistant)"`
- Tests cover: mixed tool + non-tool turns, tool appearing multiple times, empty session

**CLI:**
```bash
cz context --json --top-tools 5
# → {..., "top_tools": [{"tool": "Bash", "total_tokens": 42000, "turn_count": 3}, ...]}
```

---

### Task 2: Cache Efficiency Metrics [ ]

Track `cache_creation_input_tokens` vs `cache_read_input_tokens` separately. Compute a cache hit rate and estimated billing savings. Include in `estimate_context()` output and context snapshots.

**Files:** `context.py`, `tests/test_context.py`

**Acceptance:**
- `estimate_context()` always returns `cache_hit_rate` (0.0–1.0) and `cache_saved_tokens` (int)
- `cache_hit_rate` = `total_cache_read / (total_cache_creation + total_cache_read)` (0.0 when no cache activity)
- `cache_saved_tokens` = `total_cache_read` (tokens that would have been re-processed)
- Context snapshots include these fields when written
- Tests cover: no cache, pure cache reads, mixed, zero division guard

---

### Task 3: `cz context check-gate` — Phase Transition Guard [ ]

A new CLI subcommand for use at spec phase transitions. Reads the current context percentage and optional token estimate, then prints an actionable recommendation with a machine-readable exit code.

**Files:** `cli.py`, `tests/test_cli.py`

```bash
# Check whether to proceed with a phase transition
cz context check-gate --tokens 20000
# Exit 0 → OK to proceed
# Exit 1 → WARNING: proceed with caution (80–89%)
# Exit 2 → BLOCKED: do not start new phase, hand off first (90%+)

# JSON output
cz context check-gate --tokens 20000 --json
# → {"proceed": true, "reason": "OK", "percentage": 62.1, "percentage_after": 72.4}
```

**Acceptance:**
- Exit code 0 when `status_after == "OK"`, 1 for WARNING, 2 for CLEAR_NEEDED
- `--tokens` defaults to 0 (check current state only)
- `proceed` field is `True` only on exit 0
- `reason` is one of `"OK"`, `"WARNING"`, `"BLOCKED"`
- Rules in `workflow-enforcement.md` reference this command for the 80% phase gate
- Tests cover all three exit codes and JSON output format

---

### Task 4: Session Aggregate Report [ ]

A new CLI command that reads all context snapshots for the current session and produces a summary: total tokens consumed, peak status, most expensive turn, cache efficiency across the session.

**Files:** `context.py`, `cli.py`, `tests/test_context.py`, `tests/test_cli.py`

```bash
cz context report --json
# → {
#     "session_id": "abc123",
#     "snapshot_count": 4,
#     "peak_percentage": 89.2,
#     "peak_status": "WARNING",
#     "turns_at_warning": 2,
#     "cache_hit_rate": 0.61,
#     "total_tokens_at_peak": 178_400
#   }

cz context report   # Human-readable summary
```

**Acceptance:**
- Reads snapshots from `~/.cohezion-engine/sessions/<id>/context-snapshots/`
- Returns `{"snapshot_count": 0}` gracefully when no snapshots exist
- `peak_percentage` is the max across all snapshots
- `turns_at_warning` counts snapshots where `status == "WARNING"` or `"CLEAR_NEEDED"`
- `cache_hit_rate` averaged across snapshots
- Tests use `tmp_path` with synthetic snapshot JSON files

---

### Task 5: Overture Plan Node Cost Annotation [ ]

A new hook (`hooks/overture_annotator.py`) that fires on `PreToolUse` for tool calls that submit plans to Overture. It enriches the plan JSON with a `context_cost_estimate` field per node, derived from `estimate_context()` velocity data and a configurable per-task token budget.

**Files:** `hooks/overture_annotator.py`, `tests/test_hooks.py`

**Acceptance:**
- Hook reads `OVERTURE_ANNOTATE=1` env var; exits silently when unset (opt-in, non-disruptive)
- When active, reads the plan JSON from stdin (tool_input), attaches `_context_estimate` metadata to each task node: `{"budget_tokens": N, "fits": bool, "turns_cost": float}`
- Token budget per task defaults to `velocity_tokens_per_turn` (from current session) × 2
- Hook exits 0 always (never blocks tool calls)
- Tests cover: annotation with known velocity, missing velocity falls back to 0, env var off skips annotation

---

## Architecture Notes

### Token Attribution (Task 1)

The session JSONL interleaves `tool_use` content blocks in assistant messages. A turn's tool attribution is the `name` field of the first `tool_use` block in `message.content`:

```json
{
  "message": {
    "role": "assistant",
    "content": [{"type": "tool_use", "name": "Bash", "id": "..."}],
    "usage": {"input_tokens": 12000, ...}
  }
}
```

Turns with no `tool_use` blocks (pure text responses) are attributed to `"(assistant)"`.

### Cache Efficiency (Task 2)

Cache tokens already appear in `_parse_turns()`. The new fields are additive — no changes to existing return keys.

```python
total_cache_create = sum(t["cache_creation"] for t in turns)
total_cache_read   = sum(t["cache_read"] for t in turns)
denom = total_cache_create + total_cache_read
cache_hit_rate = total_cache_read / denom if denom > 0 else 0.0
```

### check-gate Exit Codes (Task 3)

Exit codes are designed for direct use in shell scripts and the spec workflow dispatcher:

```bash
if ! cz context check-gate --tokens 25000; then
    echo "Context pressure too high — deferring phase transition"
    exit 1
fi
```

### Overture Hook Integration (Task 5)

`overture-mcp` was added 2026-02-26. The hook is opt-in via `OVERTURE_ANNOTATE=1` so it has zero impact on sessions that don't use Overture. The annotation enriches Overture's graph nodes with cost data so the visual plan can color-code expensive vs. cheap steps.

## Test Strategy

- TDD throughout: write failing test → verify fail → implement → verify pass
- No mocks for internal logic; use `tmp_path` JSONL fixtures (existing convention)
- CLI tests via `subprocess.run([sys.executable, "-m", "cohezion_engine.cli", ...])`
- Hook tests via `run_hook()` helper in `test_hooks.py`
- Target: ≥ 120 tests passing after all tasks

## Verification

```bash
cd tools/cohezion-engine
uv run pytest -q                  # 120+ tests pass
ruff check src tests              # 0 linting errors
basedpyright src                  # 0 type errors
```

Manual smoke tests:
```bash
cz context --json                                    # includes cache_hit_rate
cz context --json --top-tools 5                      # tool attribution
cz context check-gate --tokens 30000 --json          # phase gate
cz context report --json                             # session aggregate
```

## Dependency Order

Tasks 1 and 2 are independent (both extend `estimate_context()`).
Task 3 builds on the `hypothetical_tokens` path (already in context.py).
Task 4 reads snapshots written by Task 2.
Task 5 reads velocity from `estimate_context()` — depends on nothing new.

Recommended implementation order: **1 → 2 → 3 → 4 → 5**

## Related Concepts
- [[context-management]]
- [[cohezion]]
- [[compound-engineering]]
- [[token-efficiency]]
- [[workflow-orchestration]]
