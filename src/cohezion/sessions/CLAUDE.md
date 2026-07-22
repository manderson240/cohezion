# sessions — Local Context

This file loads in addition to the root `CLAUDE.md`. Root applies here too.

**Purpose:** Cohezion Session Control Plane (SCP1–SCP4) — registry + message bus for live sessions.

## Entry points (2 modules)

| Module | Key class(es) | LOC |
|---|---|---|
| `session_bus.py` | `MessageKind`, `SessionRegistry`, `SessionBus` | 187 |

## Invariants / notes referencing this package (from harness.md / root CLAUDE.md)

- See skill: `cohezion-worktree-workflow` — covers session scripts (start/end/list_sessions.sh), manual git worktree commands, commit format with Co-Authored-By, 

_Auto-generated 2026-07-22 (gen_nested_claude.py): facts deterministic (ast/grep), Purpose from __init__/module docstrings. Validated by scripts/ci/doc_code_consistency.py. Hand-enrich as needed._
