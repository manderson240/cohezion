---
date: 2026-06-07
kind: audit
thread: remediation
prompted_by: user  # "loops should also find fixes for pre-existing conditions"
status: report-only
---

# Pre-existing conditions audit (2026-06-07)

User directive: **"loops should also find fixes for pre-existing conditions."** This is the
standing remediation arm (see Remediation policy below). This document records conditions
found while addressing the bot-fix + wiring ticks, classified by safe-to-fix vs needs-human.

## Fixed this tick (verified)

| Condition | Fix | Verification |
|---|---|---|
| `src/cohezioion/` — misspelled-path junk dir (untracked, syntax error at `recursive_trace.py:92`, **0 code references** — the one `cohezioion` match was a path typo in a docstring) | Removed (untracked filesystem cleanup, not a git write; advisor-approved accident-cleanup) | `ruff check --select=E9 src/ tests/` → **"All checks passed!"** (was the sole real syntax error). |

## Needs human decision (NOT auto-fixed — non-destructive policy)

### 1. `src/cohezion/recursive_trace.py` — stalled file→package refactor
- **Untracked**, and **shadowed** by `src/cohezion/recursive_trace/` (Python imports the
  package; `import cohezion.recursive_trace` resolves to `recursive_trace/__init__.py`).
- The file **compiles fine**, but its symbols are NOT a subset of the package:
  - file: `OuroborosBridge, RecursiveTraceConfig, RecursiveTraceResult, TraceRecord, generate_hypothesis, load_failure_analysis` (+ `to_dict/from_dict`)
  - package: `TraceMemory, RecursiveTraceLoop, LatentStateTracker`
- So it is **NOT a clean husk** — it has unique content. Per non-destructive-wiring, it must
  **not** be deleted; its unique symbols should be **integrated into the package first** if
  wanted. **Broken-importer check: NONE** — no `src/`,`tests/`,`scripts/` code imports the
  file's unique symbols (they are shadowed + unreferenced = functionally dead scratch).
- **Decision needed:** (a) finish the refactor — move the wanted unique symbols
  (`generate_hypothesis`? `RecursiveTraceConfig`?) INTO `recursive_trace/`, then the file is a
  real husk and the leftover removal is bookkeeping; OR (b) confirm the file is abandoned
  scratch (nothing imports it) → remove the untracked file. Either way: a human call, because
  it carries unique (if dead) content.

### 2. Harness `--fast` ruff checks are red on pre-existing STYLE drift (not syntax)
- `ruff format --check src/ tests/`: **60 files** would be reformatted (14 `tests/wiring`, 12
  `src/cohezion`, rest scattered tests — accumulated from many ticks/sessions).
- `ruff check --select=F,E9,E501`: **831 errors** — **821 E501** (line-length), 60 F-class
  (mostly F401 unused-import / F841 unused-var), **0 E9 (syntax)**.
- **The harness check is MIS-SCOPED**: it is labelled *"Ruff quick lint (syntax errors only)"*
  but selects `F,E9,E501` — so it fails on line-length + pyflakes, NOT syntax. E501 is
  tolerated pervasively elsewhere in this repo (CLAUDE.md notes many files far over). So the
  harness has been red on intentional style drift, masquerading as a syntax gate.
- **Decision needed (user judgement — scope/churn):**
  - (a) **Re-scope the check** to `--select=E9` (true "syntax errors only") so it measures
    what its label claims — a 1-line harness edit; greens immediately and honestly; OR
  - (b) **One-shot `ruff format` pass** (style-only, idempotent, zero behaviour change) to
    clear the 60 reformats — but a 60-file churn commit (against surgical-commit discipline);
    leaves the 821 E501; OR
  - (c) **Incremental** via the remediation arm — each tick reformats/relints ONE area it
    already touches (bounded churn), chipping the 831 down over time.
- **Not done now** (advisor guard: do NOT widen the mandate into a repo-wide reformat; the 37
  LOC>500 files are report-only by the simplicity-audit policy and are out of scope).

## Remediation policy (standing — the durable arm)

> Each loop tick (build / wiring / research) MAY additionally fix **ONE verified pre-existing
> condition** it encounters, under the SAME discipline as feature work: husk-test before any
> removal (non-destructive — integrate unique content first), TDD/falsifiable where code
> changes, surgical commit (explicit paths, churn-guard, `--no-verify`), and STOP→surface for
> anything needing a human decision (true duplicate, behaviour change, or unique-content
> removal). Conditions too large for one tick (e.g. the 831-error style drift) are logged here
> and chipped incrementally, never bulk-fixed in a single sprawling commit.
