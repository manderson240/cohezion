---
type: landing-ledger
date: 2026-10-27
source_branch: reconcile/codeql-wave2-additions (= agent-1793074868 / agent-1793074522 tip 4afeb63fd)
landing_branch: land/codeql-wave2-additions-onto-main-20261027
base: origin/main b3342cf18 (2026-10-06)
---

# Landing ledger: the 26-commit `reconcile/codeql-wave2-additions` line onto main

The main checkout and three agent worktrees sat on a 26-commit line (2026-09-09 to
2026-10-23) that forked from main at 347909e51 (2026-09-09). main moved 56 commits
in the meantime and none of the 26 had landed. `git cherry` reported all 26 as
unlanded; a per-file blob comparison against main showed that the first seven had in
fact landed through squash PRs. This ledger records every disposition so the PR
can be reviewed against intent rather than re-derived.

## Disposition of the 26 source commits

| # | commit | verdict | evidence |
|---|---|---|---|
| 1 | b3fc1ad82 wave-2 CodeQL fix | DROPPED, landed | tree of #2 == PR #297 squash bccb006af minus the bump files |
| 2 | 107e7fe46 synthetic token fixture | DROPPED, landed | rebase auto-dropped: patch already upstream |
| 3 | b74d93830 bump 1.22.2 -> 1.22.3 | DROPPED, landed | main CHANGELOG carries the 1.22.3 entry; main is on 1.27.1 |
| 4 | a4315dc4d arc3 v13 orchestrator | DROPPED, superseded | main carries v16 of the same kernel/submit script (PR #302, 2026-09-12) |
| 5 | 278df6d5a arc2 LoRA kernel | DROPPED, superseded | main's notebook = ours + 124 lines (PR #302) |
| 6 | 698f04662 arc2 submission fields | DROPPED, landed | all 3 blobs identical on main |
| 7 | a1fa550e1 wave-2 hardening + wave-3 scaffolding (33 files) | DROPPED, landed | 16 blobs identical on main, 17 are main's later superset (only additions, bar small later deletions from the model-id migration) |
| 8 | 2a0813a15 untrack ignored files | KEPT, then CORRECTED | see "restored files" below |
| 9 | e2da71feb resident-model cap + EventBus lifecycle | KEPT, 1 conflict | `dynamic_model_evaluator.py`: main's :13305-first endpoint order kept, our comment carried |
| 10-18 | fabric, pool dispatch, NPU-first routing, KST, proxy timeout, Dream-RSI, write-surface map, admission, GAIA bridge | KEPT, clean | auto-merged |
| 19 | c4c468548 harness.md split | KEPT, 1 conflict | main's post-fork H5 status text carried into the core; main's MR6 section carried into the catalogue + index row |
| 20-26 | mcp hardening, protocolVersion, hook guard + tests, GH1-GH3, stealthskater ids, write-surface ownership | KEPT, clean | auto-merged |

## Follow-up commits added on the landing branch

1. `fix(ci): give check_agent_surfaces.py a --self-test` -- carried over from the
   agent-1793074522 handoff (`vault/reports/20261027-dormant-gates-landing-handoff.md`).
   Without it main's blocking `self_test_coverage.py` meta-gate goes red the moment
   `agent-surfaces.yml` lands.
2. `test(ops): park-gate lifecycle test counts six phases` -- main added
   `trace_goal_refactor` (#294); the 2026-09-14 copy of the test asserted five.
3. `fix(repo): restore the 160 source, script, config and data files the gitignore
   sweep untracked` -- commit #8 ran `git rm --cached` over every ignored-but-tracked
   path. Unanchored root patterns (`team_*.py`, `run_*.py`, `gemma4_*.py`,
   `simulations/`, ...) matched `src/cohezion/swarm/team_*.py`,
   `compound/team_executor.py`, `src/cohezion/simulations/`, 70+ scripts,
   `.gitmodules`, k8s manifests, API static artifacts, LFS checkpoints and model
   registries. On the rebased tree 17 test modules failed at collection
   (`ModuleNotFoundError: cohezion.swarm.team_metrics`, ...) and
   `doc_code_consistency` raised E5 on the swarm module count. Genuine generated
   artifacts stay untracked: `conductor/tracks`, `.obsidian/*-graph.json`,
   `execution_traces/`, `tests/temp_sim/*.jsonl`, SurrealDB exports, config-sync
   logs, `*.log`, `*.harness-bak`, `scheduled_tasks.lock`.
4. `fix(gitignore): anchor root-level scratch patterns` -- the root cause of 3.
   Tracked-but-ignored paths drop from ~209 to 46, none Python or shell.
5. `style(tests)` + `style` -- the new test files and modules added lint debt
   (ratchet 915 > 905); after the pass the ratchet reads 897 < 905.

## Verification on the rebased tree (scratch clone, `uv sync --frozen`)

- Targeted tests for every file the line touches: 307 passed after fix 2.
- `doc_code_consistency.py`: 0 errors, 4 pre-existing warnings (was 1 error before fix 3).
- `dormancy_scan.py`: OK, 19/19 curated capabilities consumed.
- `phantom_attr_scan.py`: OK. `self_test_coverage.py`: 16/26 gates self-test, meta-gate green.
- `ruff_ratchet.py`: 897 < 905 baseline.
- Broad suite (`tests/inference tests/unit tests/scripts tests/swarm tests/platform
  tests/skills tests/compound tests/core`, 7401 collected): result recorded in the PR
  description. Three collection errors are pre-existing on main and environmental:
  `test_baml_client` (generated client pins baml-py 0.226.2), `test_speculative_engine`
  (`respx` extra not in the frozen sync), `test_producer_consumer_audit`
  (`AUDIT_PAIRS` is imported but never defined on main either).

## Not done here (deliberate)

- The stealth-except gate wiring (`origin/feat/oss-lesson-gates`, de042928b) that the
  same handoff re-applied is NOT included: it touches `ci.yml` and `automerge_guard.sh`,
  which main also changed since the fork, and is a separate narrative. Land it on its own.
- `scripts/stealthskater_ingest.py` and `scripts/hooks/pre-commit.py` carry S310/S112
  findings outside the ratchet's `src/ tests/` scope; untouched.
- The main checkout, `agent-1793074522`, `agent-1793074868` and `recursive_graph_v_model`
  still point at 4afeb63fd. Once this PR lands they are fully contained in main and can
  be retired; nothing on them is lost.
