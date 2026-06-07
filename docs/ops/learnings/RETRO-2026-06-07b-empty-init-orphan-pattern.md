---
date: 2026-06-07
kind: retro
thread: [wiring, research-calibration]
prompted_by: retro-watch ([retro:due], 10 tasks)
status: captured
related_commits: [1684c24cb, 9c0e90377, 696258b77, 7347778c7, ccf8ae4b1]
---

# Retro — the empty-`__init__.py` orphan-maker (reusable wiring pattern)

## The recurring file-level wiring pattern

Across `flux` (commit 1684c24cb) and `eval` (9c0e90377) — and earlier `reporting` — the SAME
root cause produced intra-package orphans: an **empty package `__init__.py`**. When `__init__`
re-exports nothing, the package's own modules are reachable only by whatever happens to import
them directly — usually `tests/<pkg>/*` alone → they are tests-only intra-package orphans
(static-import-invisible from production).

**The fix is mechanical and identical every time:**
1. Classify each `<pkg>/*.py`: production edge (reachable, leave it) vs tests-only (orphan).
2. Populate the empty `__init__.py` with `from cohezion.<pkg>.<mod> import <PrimaryClass> as <PrimaryClass>` for each orphan module (the `X as X` alias = intentional re-export, ruff-safe vs F401).
3. **Cycle-check before trusting it**: `python -c "import cohezion.<pkg>"`. Populating `__init__`
   moves module imports to package-load time; if a re-exported module imports a consumer at module
   level (e.g. `eval.capability_scorecard` is used by `compound.capability_matrix`), you can create
   a cycle. In `eval` the consumer used a *function-local* import (`capability_matrix.py:442`), so
   no cycle — but VERIFY, don't assume.
4. One identity discriminating test: `assert pkg.X is module.X` (NOT `hasattr` — a mis-pointed
   re-export passes `hasattr`, fails identity), + run the FULL `tests/<pkg>/` suite for regressions.

**Why this matters:** an `X as X` re-export is a real STATIC import edge (unlike importlib-on-a-
string), so it makes the file reachable to the audit's BFS, IDEs, and bundlers — non-destructively
(adds an edge, changes no behaviour; the package's runtime API is unchanged, just discoverable).

Remaining unswept small packages likely to share this shape: `vibe`, `vanguard`, `services`,
`dogfooding`, `worldviews`. Check `<pkg>/__init__.py` first — if empty, this pattern applies.

## Research-filter calibration held BOTH ways (rounds 28-29)

- Round 28: `Qwen3-Coder-Next-GGUF` looked like an easy embrace (3M dl, GGUF, apache-2.0) — the
  K1/rule-5 **size gate** caught it (55.8 GB). Verify the binding constraint, not the vanity metric.
- Round 29: `jina-reranker-v3-GGUF` is tiny + on a real seam (`Task.RERANK`) — but it **overlaps the
  already-seeded item-19 reranker** and is **cc-by-nc-4.0** (non-commercial). Logged feed-only with
  an explicit promotion condition, not embraced. The deeper insight: the persistently-surfacing
  rerankers (item-125 signal) are blocked by item-19's *unproven serving path*, not a missing model.

Neither over-embraced nor over-declined — each logged with the exact constraint that decided it.
This is the RETRO-2026-06-06d discipline (over-build/over-decline are the same miscalibration)
generalized to the *accept* direction.

## Persistence
- Wiring ledger: 33 packages DONE (eval added). Two-consecutive-clean-pass termination not yet hit.
- Build loop: items 71 (feed↔backlog crossref), 72 (cerebellum_drift), 73 (TIDE problem-discovery)
  shipped; frontier items 125/126/127 queued. Cadence ~20min via ScheduleWakeup.
