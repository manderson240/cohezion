---
date: 2026-06-16
sprint: bmad-evo-loop
status: complete
---

# Retro: BMAD v6.8.0 + EVO Vacuum Loop

## What Worked

- BMAD v6.8.0 install via `npx bmad-method@latest install` was clean once CSV LFS pre-commit bug was fixed
- Agent harness wiring (6 agents × BMAD skills) was additive — no existing functionality broken
- NPU recovery pattern (API-first unload+reload) eliminates subprocess dependency, works from PID-namespaced sandboxes
- EVO vacuum telemetry in `run_agentic_loop.py` captures `evo_energy = win_rate × wins` as a dimensionless quality signature per loop run
- `resp = None` sentinel pattern cleanly resolves Pyright possibly-unbound errors in nested try/except handlers
- Category breakdown table in loop summary gives immediate signal on which task types are struggling

## What to Reuse

- `git cat-file blob :<path>` for index-based LFS detection (see `lfs-precommit-index-check` skill)
- API-first NPU recovery: `POST :13305/api/v1/unload` then `POST :13305/api/v1/load {ctx_size: 16384}` — no subprocess, works from any namespace
- BMAD adversarial 3-reviewer pattern: Blind Hunter / Edge Case Hunter / Acceptance Auditor
- EVO `evo_energy` metric: `win_rate × tasks_won` is a dimensionless quality signature that compounds (not just a rate)
- `resp = None` sentinel before nested try/except blocks — Pyright can track None vs typed across the full handler

## What to Avoid

- `path.open("rb")` for LFS pointer detection in pre-commit hooks — always sees smudged content
- `ruff format <file>` in Claude Code sandbox — silently fails with "Read-only file system". Use `ruff format --diff` to see needed changes, then apply via Edit tool
- `except (SubclassError, Exception)` tuples — the supertype `Exception` swallows all; list only sibling types
- Retro forks in session-end contexts — fork-within-a-fork is blocked by the runtime; do retro directly in the main session or as a non-fork agent
- Stale legacy skill dirs (`.opencode/skills/bmad-*`, `.pi/skills/bmad-*`) auto-restored by npm installers — clean manually in real terminal, not via Claude Code sandbox

## Discrepancies

- `.opencode/` and `.pi/` BMAD skill dirs not yet cleaned (sandbox write restriction on those paths)
- `evo_vacuum` SurrealDB schema deferred to surreal-dba agent (schema may not exist until that completes)
- Branch merge `feat/datamesh-agentic-omnirouter` → main still pending

## Skills Extracted This Session

- `lfs-precommit-index-check` v1.0.0 — git index vs working-tree for LFS pointer detection
- `flm-npu-context-recovery` v1.1.0 — API-first NPU unload+reload pattern (previously undocumented)

## Next

- Tasks #28–#35 import/type bughunts (parallel agents running)
- `evo_vacuum` SurrealDB schema (surreal-dba handling in parallel)
- Branch merge: `feat/datamesh-agentic-omnirouter` → main
- Investigate task #35 statically-false condition root cause
