# sessions — Local Context

This file loads in addition to the root `CLAUDE.md`. Root applies here too.

**Purpose:** Cohezion Session Control Plane (SCP1–SCP4) — registry + message bus for live sessions.

## Entry points (2 modules)

| Module | Key class(es) | LOC |
|---|---|---|
| `session_bus.py` | `MessageKind`, `SessionRegistry`, `SessionBus` | 187 |

## Invariants / notes referencing this package (from harness.md / root CLAUDE.md)

- See skill: `cohezion-worktree-workflow` — covers session scripts (start/end/list_sessions.sh), manual git worktree commands, commit format with Co-Authored-By, 

_Seeded 2026-07-22, HAND-MAINTAINED since — there is no generator. The original note credited a `gen_nested_claude.py` that exists in no commit and nowhere on disk; corrected 2026-07-31 so nobody hunts for it or assumes a regeneration will clear drift. Update this file in the same commit as the code. Guarded by `scripts/ci/doc_code_consistency.py`: E1/E2 that every path and module reference resolves, E5 that the declared module count matches the package._
