---
title: Root cleanup ledger
date: 2026-11-04
status: landed (open items listed below need an owner decision)
guard: src/cohezion/governance/scripts/root_health_guard.py
rule: .claude/rules/repo-hygiene.md
prior_sweeps: [2026-04-19, 2026-05-02, 2026-08-20]
---

# Root cleanup, 2026-11-04

Every item that was moved or pruned is listed with the commit that brought it in, how it got
in, and what we learned from it. The lessons are enforced by
`src/cohezion/governance/scripts/root_health_guard.py` and written up as a standing rule in
`.claude/rules/repo-hygiene.md`.

## Why there was a fourth sweep

Root cleanups were done on 2026-04-19, 2026-05-02 and 2026-08-20, and each one regressed
within weeks. Three causes run through every item below:

1. **Mega-commits staged with `git add -A`.** Two commits account for most of the clutter:
   `9dce6ddd` (2026-07-04, a feature commit titled "implement RQGM epoch rotation") and
   `66f5186d` (2026-08-11, "Project Ouroboros-Omega Mission Engine", which came in through
   reconcile merges). Neither commit's message mentions the files it added at the root.
2. **The guard was dormant.** `root_health_guard.py` (2026-04-19) said it "fails CI", but no
   workflow, pre-commit hook or landing guard ran it. It was also count-based (fail above 75
   visible items) and skipped dot-names, so it could not have caught any of these even if
   wired: the root stayed near 57 visible items and most new clutter was hidden.
3. **`.gitignore` doesn't untrack.** Several items were already ignored when this cleanup
   started. Ignoring a path after it's committed only stops new files; the tracked ones stay
   forever.

## Pruned

| Item | Came in | How it got in | Lesson |
|---|---|---|---|
| `EOF` (0 bytes) | `6f7539bc` 2026-03-25 | A heredoc with a mistyped terminator wrote a file named after the delimiter. | An empty root file is almost always an accident. Guard: no zero-byte root files except listed flags. |
| `package.json.harness-bak` (0 bytes) | `66f5186d` 2026-08-11 | An editor or harness backup, staged by `git add -A`. There is no `package.json` at the root. | Same as above. Backups belong outside the tree. |
| `satus/config.json` | `66f5186d` 2026-08-11 | Typo for `status/`. Nothing referenced it. | A typo directory survives because nothing asks "is this name expected?" Guard: root allowlist. |
| `autoresearch.hooks/.gitkeep` | `83b7e240` 2026-05-01 | Placeholder for a hooks dir that was never filled. | A `.gitkeep` with no consumer is a declaration, not a capability. |
| `.playwright-cli/` (7 page snapshots) | `e8568285` 2026-04-06 | Browser-automation CLI output written to the cwd. | Tool output written to cwd lands at the root. The old guard skipped dot-names, so this sat for seven months. Now gitignored and caught by the allowlist. |
| `.hermes-sessions/` (2 `tmp_*.py`) | `9dce6ddd` 2026-07-04 | Agent scratch scripts. | Agent scratch belongs in a session scratchpad, never the repo. Gitignored. |
| `.claire/worktrees/virtual-painting-wren/scripts/experiments/exp_id12_feedback_loop.py`, `exp_id16_routing_accuracy.py` | `9dce6ddd` 2026-07-04 | `.claire` is a typo of `.claude`. A worktree's files were committed into the parent repo. Both files were 12 bytes, containing only the word `placeholder`. | A file named like real work can be a stub. The first pass of this cleanup moved them to `scripts/experiments/`; `ruff check` (F821 on `placeholder`) is what showed they were empty. Read a file before deciding it is worth keeping. |
| `execution_traces/unified/` (11 JSON) | `9dce6ddd` 2026-07-04 | Runtime output. It was already gitignored, so new traces were blocked but these 11 stayed tracked. | `git ls-files -ci --exclude-standard` lists tracked-but-ignored files. Run it in any sweep. |

## Moved

| Item | Now at | Came in | Lesson |
|---|---|---|---|
| `particles-casberry.jpeg` | `docs/media/particles-geodesic-sphere.jpeg` | `66f5186d` 2026-08-11 | Media goes under `docs/media/` with a name that says what it shows. |
| `tests_mycelium/coherence_walk_v2.py` | `scripts/experiments/` | `83b7e240` 2026-05-01 | It is an experiment script, not a test (pytest never collected it). A name that claims to be tests should be tests. |
| `skill_density_experiment.py` | `scripts/experiments/` | `97330030` 2026-05-11 | Root-level one-off scripts belong with their siblings. |
| `AGENT_COORDINATION.md` | `docs/archive/AGENT_COORDINATION_2026-07.md` | `9dce6ddd` 2026-07-04 | A one-time coordination note, kept for history. Dated archive names make it obvious that a doc is not current. |
| `status_update/` (video, audio, HTML) | `docs/archive/status_update_2026-07/` | `9dce6ddd` 2026-07-04 | Same as above. |
| `docs/ARCHITECTURE.md` | `docs/archive/KYUTAI_MCP_ARCHITECTURE.md` | `fa4d4bb9` 2026-02-14 | It coexisted with `docs/architecture.md` (from `ff58f28d`, 2026-03-04) for nine months. On macOS and Windows only one of the two survives a checkout, and which one you get depends on order. Its content was a Kyutai MCP design, not the system architecture. Guard: case-insensitive collision check at every path depth. |
| `docs/INDEX.md` | `docs/archive/INDEX_2026-08-17.md` | `fa4d4bb9` 2026-02-14 | Collided with `docs/index.md` the same way. |
| `docs/architecture.md` (old content) | `docs/archive/architecture_2026-03.md` | `ff58f28d` 2026-03-04 | Described 15 epics and agent personas from March, not the code. Replaced by a short map written from the code, which names its own duplication (two routing stacks) instead of hiding it. |

Links that pointed at the uppercase names (`docs/README.md`, `docs/architecture-backend.md`)
now point at `docs/architecture.md`.

## Fixed in `.gitignore`

The `overnight*.sh` through `analyze_overnight*.py` patterns had no leading `/`, so they
matched at every depth and **hid 88 real tracked files**: 78 under `scripts/`, 9 in `src/`
(for example `src/cohezion/swarm/team_orchestrator.py` and `gemma4_router.py`) and
`cloud-vault-mcp/run_mcp.py`. New files with those names would have been silently left out
of commits. They are now anchored to the root
(`/overnight*.sh`). New entries: `.playwright-cli/`, `.hermes-sessions/`, `/EOF`.

**Lesson:** a pattern meant for the root needs a leading `/`. Check any new pattern with
`git ls-files -ci --exclude-standard` to see what it would hide.

Three more unanchored directory rules have the same problem and were **left alone** because
their intent is unclear. Each one also matches a real source package:

| Rule | Also hides | Since |
|---|---|---|
| `infrastructure/` | `src/cohezion/infrastructure/__init__.py` (and the tracked root `infrastructure/`) | `f7985171` 2026-02-20 |
| `simulations/` | `src/cohezion/simulations/*.py` (5 tracked files) | `42b5c674` 2026-07-09 |
| `conductor/` | the tracked root `conductor/` (36 files) | `42b5c674` 2026-07-09 |

Tracked files are unaffected, but any new file in those packages will not be picked up by
`git add`. If the intent was the root only, the fix is a leading `/`. After this change,
`git ls-files -ci --exclude-standard` lists 88 tracked-but-ignored files, down from 172.

## Duplicate module names

`scripts/producer_consumer_audit.py` (an LLM classifier) and
`scripts/ci/producer_consumer_audit.py` (the seam audit) share a module name. Its test put
`scripts/ci` on `sys.path` and imported by name, so in the full CI run it got the other file
and failed to collect (`ImportError: AUDIT_PAIRS`). That made the `Test Results` check red on
every PR, including the base branch. The test now loads the file by path.

That one error hid far more than one test. Pytest stops at a collection error, so the whole
`Run integration tests` step had been running nothing: about 2.7k tests per CI run instead of
14k. Once the import was fixed, the step ran 14,074 tests and 217 of them failed. Those
failures already existed, mostly in endpoint tests that need a live server, and are left for
their own PR. The step is `continue-on-error`, which is why nobody noticed. A non-gating
step that errors out early looks the same as one that passes. Neither script was
renamed, because both have callers.

**Lesson:** a test for a script should load it by file path (`importlib.util.spec_from_file_location`),
as `tests/scripts/test_phantom_attr_scan.py` does, never by putting a directory on `sys.path`.

## What the unmasked integration suite showed (follow-up, 1.27.3)

The 217 failures were not 217 problems. Grouped by cause, most were a few lost changes, each
of which left a test behind that kept describing code that was no longer there:

| Cause | Tests | What happened | Lesson |
|---|---|---|---|
| Router mounts dropped | 106 | `8f712a8b` removed 20 `include_router` calls (130 endpoints) from `api/__init__.py`. Every endpoint test got 404. | A route module nobody mounts is dormant. `tests/unit/test_api_router_mounts.py` now probes every route module and requires an explicit reason for each one left unmounted. |
| Squash lost the code, kept the tests | 15 | #242 (`853084c05`) landed `tests/wiring/*` but not the `__init__` re-exports they test. | When a squash or reconcile drops half a change, the test is the only record of the other half. A test that has failed since the day it landed is a pointer to lost code, not a test to delete. |
| Reconcile kept the helpers, dropped the caller | 6 | `768f6d811` merged the health oracle's `_quality_stats`/`_is_degrading` but took main's FD-only `_synthesize`. Healthy lanes alarmed as critical. | Same as above, one level down: a method-merge can keep every symbol and still drop the consumer. Grep for a caller, not for a definition. |
| Consumer lost, parameters kept | 3 | `CompoundExecutor` still accepted `memory_service`/`enable_memory` from #198 but never used them, and `ExecutorFactory.create` no longer took them, so `scripts/codebase_refinement.py` raised TypeError. | An accepted-and-ignored kwarg is the quietest dormancy there is. |
| Tests wrote tracked files | 8 | API tests trained and saved into `data/rl/` and `data/flume/` checkpoints, overwriting LFS files in the working tree. | Tests that write must run in `tmp_path`. Check `git status` after a run. |
| Never built | 13 | MD2 executor wiring, `RealSkillStateDataset`, six physics endpoints: specified with tests (mostly in the `9dce6ddd` mega-commit), never implemented. | `xfail(strict=True)` with the evidence, so the marker fails the day the feature lands. |
| Machine-specific | 4 | Two hardcoded home-directory paths, and checks of a file in a private checkout. | A path under one person's home is a test that passes on one machine. |

About 20 failures are left for an owner decision (listed in the 1.27.3 PR): the Telegram bot
tests describe a design (no git worktree or tmux) the code does not have; the OOM guard's tests
want a RAM-floor check its author deliberately left out; two TLS tests expect verification to be
disableable; and a few tests depend on the host's free RAM.

## Not moved: open items that need an owner decision

These are listed in the guard's "Open items" group so CI stays green. Nothing new should be
added to that group.

| Item | Why it was left | Decision needed |
|---|---|---|
| `.telemetry/` | Read by `src/cohezion/scripts/telemetry_dashboard.py`, `analyze_telemetry.py` and `auto_refine_skills.py` (`make telemetry-dashboard`). | Untrack the data and keep the dir gitignored, or move it under `data/`. |
| `.omg/` | `scripts/ops/run_autonomous_20_cycles.py` writes `.omg/state`. | Same: runtime state should be gitignored. |
| `.tmp_kaggle/` | Has a submodule entry in `.gitmodules` (`.tmp_kaggle/nemo-win`). | Keep the submodule (and rename the dir) or drop it. |
| `onnx_models/` (211 ARC files) | No references found, but these are large model files and may be wanted locally. | Archive to a release asset or LFS store, or delete. |
| `spdd/` | No references found. | Keep, move under `research/`, or delete. |

## A note on untracking

Removing a tracked file deletes it from every other clone at the next `git pull`. The 11
`execution_traces` files and the `.playwright-cli` snapshots will disappear from local
checkouts when this lands. They are runtime output, so that's fine here, but anything
someone might want to keep should be backed up before the pull.
