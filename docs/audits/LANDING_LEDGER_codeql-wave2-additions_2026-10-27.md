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
| 7 | a1fa550e1 wave-2 hardening + wave-3 scaffolding (33 files) | DROPPED, landed | 16 blobs identical on main, 17 are main's later superset |
| 8 | 2a0813a15 untrack ignored files | DROPPED, deferred | see "Why the untrack sweep is not in this PR" |
| 9 | e2da71feb resident-model cap + EventBus lifecycle | KEPT, 1 conflict | `dynamic_model_evaluator.py`: main's :13305-first endpoint order kept, our comment carried |
| 10-18 | fabric, pool dispatch, NPU-first routing, KST, proxy timeout, Dream-RSI, write-surface map, admission, GAIA bridge | KEPT, clean | auto-merged |
| 19 | c4c468548 harness.md split | KEPT, 1 conflict | main's post-fork H5 status text carried into the core; main's MR6 section carried into the catalogue + index row |
| 20-26 | mcp hardening, protocolVersion, hook guard + tests, GH1-GH3, stealthskater ids, write-surface ownership | KEPT, clean | auto-merged |

## Why the untrack sweep is not in this PR

Commit #8 ran `git rm --cached` over every ignored-but-tracked path. The root-level
scratch patterns in `.gitignore` (`team_*.py`, `run_*.py`, `run_*.sh`, `gemma4_*.py`,
`overnight*.py`, `simulations/`, ...) were unanchored, so they also matched
`src/cohezion/swarm/team_*.py`, `compound/team_executor.py`,
`src/cohezion/simulations/`, 70+ scripts, `.gitmodules`, k8s manifests, API static
artifacts, LFS checkpoints and model registries: 160 real files. On the rebased tree
17 test modules failed at collection (`ModuleNotFoundError: cohezion.swarm.team_metrics`,
...) and `doc_code_consistency` raised E5 on the swarm module count. The remaining
artifact deletions (`conductor/tracks`, `.obsidian/*-graph.json`, `execution_traces/`,
`tests/temp_sim`, SurrealDB exports, config-sync logs) are every one unowned in
`AGENT-SURFACES.md`, and `conductor/tracks/*` are authored plans still linked from
`conductor/tracks.md`. The sweep therefore belongs in its own PR with ownership rows and
a reviewed keep/drop list. What this PR does keep is the root cause fix: the patterns are
anchored (`/team_*.py`, ...), tracked-but-ignored paths drop from ~209 to 46, none of them
Python or shell.

## Follow-up commits added on the landing branch

1. `fix(ci): give check_agent_surfaces.py a --self-test` -- carried over from the
   agent-1793074522 handoff (`vault/reports/20261027-dormant-gates-landing-handoff.md`).
   Without it main's blocking `self_test_coverage.py` meta-gate goes red the moment
   `agent-surfaces.yml` lands.
2. `test(ops): park-gate lifecycle test counts six phases` -- main added
   `trace_goal_refactor` (#294); the 2026-09-14 copy of the test asserted five.
3. `fix(gitignore): anchor root-level scratch patterns` -- see above.
4. `style(tests)` + `style` -- the new test files and modules added lint debt
   (ratchet 915 > 905); after the pass the ratchet reads 897 < 905.
5. `fix(agi): route Dream-RSI SurrealDB reads through checked_statements` -- main's
   `surreal_http_scan` ratchet (f4ac80fcf) flags any /sql caller that does not validate
   the parsed body; an ERR statement is now a failed read, not an empty table.
6. `fix(inference): give the hybrid router fallback its own optional model variable` --
   main's `mypy_ratchet` flagged `None` assigned to a `str` local in the NPU-first commit.
7. `fix(agi): drop two unused type-ignore comments and make DiscoveryTrace iterable` --
   `__iter__` returned the records tuple itself, which `iter()` rejects at runtime.
8. `fix(agi): type the Dream-RSI SurrealDB reader honestly` -- bytes return, Mapping guard.
9. `fix: apply the adversarial review findings` -- ownership rows for the PR's own paths
   (`.gitignore`, `.githooks/**`, `.claude/**`, `src/cohezion/ops/**`, `tests/scripts/**`,
   `tests/skills/**`; the gate over `git diff main...HEAD` now reports 0 unowned);
   hermetic bus-lifecycle test (phases 5 and 6 otherwise persist to live SurrealDB);
   discriminating ERR-body test for the Dream-RSI reader; longest-glob probe in the
   agent-surfaces self-test; three docstring corrections; dead gitignore negation removed.
10. `fix(inference): pin the CPU-parallel overflow lane to the v4.1 flash model` -- the
    NPU-first commit pinned `TaskClass.CPU_PARALLEL` to a cloud model Ollama retired on
    2026-09-25; main's repo-wide guard (34daad1f3) rejects it.

## Verification on the final tree (scratch clone, `uv sync --frozen`)

- ruff format clean; `ruff_ratchet` 897 < 905; `mypy_ratchet` within baseline.
- `surreal_http_scan` at baseline (31); `dormancy_scan` 19/19; `doc_code_consistency`
  0 errors (4 pre-existing warnings); `phantom_attr_scan`, `lineage_scan`,
  `false_contract_scan`, `declared_field_scan`, `unrestricted_exec_scan` OK;
  `self_test_coverage` 16/26 (10 grandfathered), green.
- `check_agent_surfaces.py` over `git diff --name-only main...HEAD`: 0 unowned.
- Broad suite (`tests/inference tests/unit tests/scripts tests/swarm tests/platform
  tests/skills tests/compound tests/core`, 7,401 collected): 7,005 passed, 19 failed,
  3 collection errors, before fix 10. Attribution, with a pristine-main control worktree
  run under the same venv:
  - 2 were ours (`test_unified_hybrid_router` retired-model guard) -- fixed in commit 10.
  - 10 fail identically on pristine main: `test_health_oracle_quality_stats` (6),
    `test_context_engineering_mcp` (2), `test_universes_environment_and_harness` (1),
    `test_resource_manager::test_can_load_model_true_when_enough_memory` (1).
  - 4 flip between runs on BOTH trees (`test_fleet_per_model_headroom`,
    `test_fleet_recipe_gate` x3): `fleet.route` queries the live :13305 catalog
    unmocked, so the verdict depends on what is resident at that moment.
  - 3 are live-lane tests (`test_recipe_constraint_support`) that read :13305 residency.
  - The 3 collection errors exist on main too: `test_baml_client` (generated client pins
    baml-py 0.226.2), `test_speculative_engine` (`respx` extra not in the frozen sync),
    `test_producer_consumer_audit` (`AUDIT_PAIRS` imported but never defined).
- Known trunk debt, not introduced here: `check_local_llm_chokepoint.sh` flags main's own
  `scripts/ci/local_adversarial_review.py` (unbaselined on main as well);
  `mutation_ratchet` needs `mutmut`, absent from the frozen sync.
- Adversarial review (independent read-only agent, "assume broken") produced the findings
  applied in commit 9; its blocking finding was the ownership gate on the PR's own paths.

## Not done here (deliberate)

- The stealth-except gate wiring (`origin/feat/oss-lesson-gates`, de042928b) that the
  same handoff re-applied is NOT included: it touches `ci.yml` and `automerge_guard.sh`,
  which main also changed since the fork, and is a separate narrative. Land it on its own.
- `scripts/stealthskater_ingest.py` and `scripts/hooks/pre-commit.py` carry S310/S112
  findings outside the ratchet's `src/ tests/` scope; untouched.
- The main checkout, `agent-1793074522`, `agent-1793074868` and `recursive_graph_v_model`
  still point at 4afeb63fd. Once this PR lands they are contained in main except for the
  deferred untrack sweep; retire them after that decision.
