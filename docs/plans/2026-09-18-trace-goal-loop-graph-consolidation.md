---
title: Trace → Goal → Loop — one graph, one spine (V-model spec)
date: 2026-09-18
status: PENDING
worktree: no   # built in <repo>/.cache/clones/<agent>, landed as land/tgl-graph-20260918
owner: orchestrator session (adjudication); build + verify delegated
related: docs/tutorials/tripartite_goal_loop_and_trace_refactor_tutorial.md, docs/vmodel-recommendations.html,
  ~/vaults/cohezion-vault/references/loop-spec-canonical-template.md,
  ~/vaults/cohezion-vault/references/20260904-loops-and-goals-consolidated-index.md,
  ~/vaults/cohezion-vault/reports/20260814-elegant-simplicity-audit.md (rival-implementations pattern),
  memory memory-graph-lives-in-main-not-vault (the proven graph shape)
---

# Trace → Goal → Loop: one graph, one spine

## 0. As-is (measured 2026-09-18 on origin/main 455ffbb2a + SurrealDB ns=cohezion db=main)

**Data — 31 goal/loop/trace-shaped tables, seven rival schemas, canonical `loop` empty:**

| table | rows | shape |
|---|---|---|
| `goal` | 4,650 | id, title, status, target_metric, target_threshold, max_iterations, origin_trace_ids, created_at |
| `loop` | **0** | — |
| `{doctor,kaggle,metrics,quadrature_nexus,smith,twin,verification}_loop` | 6/60/4/5/3/7/8 | name, goal, spec, verify, stop_when, cadence, rung, session, impl, lane, note, created_at (≈ the canonical loop-spec template, one table per session) |
| `{doctor,kaggle,kg,metrics,quadrature_nexus,smith,twin,verification}_goal` | 6/22/3/4/5/6/6/6 | name/title, status, target, measured, session, note/doc |
| `autonomous_loop` | 8 | converged, exit_predicate, iteration_count, is_livelock, is_progressive, cycle_pattern |
| `compound_loop` / `event_log` / `execution_trace` / `loop_trace` | 5,029 / 5,902 / 36 / 32 | the traces (not to be copied) |
| `goal_node`, `traces` | 0 / 0 | phantom |

The 2026-09-04 index found loop docs whose `mirror:` frontmatter cited graph tables that did not
exist (0 nodes). The per-session tables are the mechanism: each session minted its own pair, so no
reader could see all goals or all loops, and "mirror" became a claim rather than a row.

**Code — five implementations of the same concepts** (inventory by `tgl-inventory`, §3 pending):
`flume/loop_goal_refactor_engine.py`, `compound/goals_and_loops_orchestrator.py`,
`recursive_trace/goal_loop.py`, `recursive_trace/tripartite_goal_loop.py`,
`flume/monadic_markov_trace_engine.py`. The tutorial composes engine → TripartiteGoalLoop →
GoalDrivenTraceLoop; the other two are rivals until evidence says otherwise.

**Provenance notes (2026-09-18):** the checkout `security/codeql-wave2` shows the engine
*without* `PlanSegment`/`MemoryAsPlans` — not a removal: `git log --full-history 455ffbb2a..HEAD`
touches the file in no commit; the branch forked before main gained them (7 behind). Main is
canonical; MemoryAsPlans lives in the engine. The working tree carries a prior session's
uncommitted docstring: *"no production JOURNEY_STEP subscriber feeds this engine — verified
2026-09-14; a documented future trigger, not live wiring"* — i.e. the engine's trace intake is
DORMANT on main today. R4's reader and the pipeline's `vault`+`main` scan are the first live
consumers; the build must not claim the JOURNEY_STEP path is wired unless it adds the subscriber.

**The proven shape in the same database:** the memory graph — `memory` nodes + one `relates_to`
edge table (1,054 edges) with a `domain` field. Three node kinds, one typed edge, domain as data.

## 1. Requirements (left leg)

R1 **One graph.** Node tables `goal`, `loop` (existing names; `goal` extended, `loop` populated) and
   one edge table `goal_graph` with `DEFINE FIELD kind` ∈ {`pursues` loop→goal, `derived_from`
   goal→trace-row, `supersedes` goal→goal, `mirrors` node→doc-path}. `DEFINE FIELD domain` and
   `session` on every node (replaces the table-name prefix). Traces are NOT copied: `derived_from`
   points at existing `event_log` / `compound_loop` / `kanban_item` record ids.
   **R1a — traces span two databases (measured 2026-09-18):** `event_log` in db=`main` holds only
   `JOURNEY_STEP`/`AGENT_COMPLETE`/`SYSTEM_HEALTH` (3,505/1,424/984) — zero finding-type rows — so
   `refactor_traces_to_goals.py --dry-run` on its default db synthesizes 0 goals (controlled at
   `--limit 1000`), while `--database vault` synthesizes 1 (`Stabilize: autopoiesis_engine`). The
   event bridge publishes session findings to `vault`; goals live in `main`. SurrealDB record ids do
   not span databases, so `derived_from` edges carry `source_db` + `source_id` (string), and the
   reader (R4) resolves through both. The pipeline's default source becomes `vault` for findings
   with `main` for journey/health signals — one scan, two sources, tagged.
   Falsifier: `--dry-run` with no `--database` flag yields ≥ 1 goal whose `derived_from.source_db`
   is `vault`.
R2 **Migrate, integrate-first.** Every `<domain>_goal` / `<domain>_loop` / `autonomous_loop` row is
   written into the canonical tables with `domain=<prefix>`, `source_table`, `source_id` retained.
   Old tables are NOT dropped by this change (a later, user-confirmed step, after R4's reader is
   the only reader). Idempotent: re-running the migration adds zero rows.
R3 **One code spine** (filled from `tgl-inventory`): the canonical `GoalSpecification` +
   `LoopSpec` dataclasses (fields = the loop-spec template: goal, each_iteration, verify, stop_when,
   bound, on_stop, rung, cadence, domain, session) live in ONE module; the other modules become
   thin adapters or are integrated into it. No new module unless the inventory shows none of the
   five can be the spine. Rival modules keep their tests until integration proves equivalence.
R4 **A production consumer reads the graph.** `scripts/ops/refactor_traces_to_goals.py --status`
   (or the operator banner) prints per-domain counts, goals-without-loops, loops-without-goals,
   and the newest `mirrors` targets — read from `goal_graph`, not from the per-domain tables.
R5 **Mirror claims become checkable.** A CI check (`scripts/ci/loop_doc_mirror_check.py`, wired
   next to `doc_code_consistency.py` in `automerge_guard.sh`) parses every loop doc's `mirror:`
   line, resolves the cited table + scope to a live row count, and FAILS on zero — with its own
   `--self-test` that plants a phantom mirror and requires RED, then GREEN.
R6 **Loop maturation is data.** `loop.rung` (0 = never run … 4 = unattended) is a field the
   consumer shows; `loop_depth.py`'s measured loopception depth is written to `loop.depth` for the
   compound daemon's loop (closes the "never measured" finding at the data layer).

## 2. Falsifying commands — written BEFORE code (V-model rule 1)

Each requirement has the command that would prove it false. A build is done when none of these
fires; a review that cannot make one fire has learned nothing.

| Req | Falsifier (must FAIL before the change, PASS after) |
|---|---|
| R1 | `curl … "INFO FOR TABLE goal_graph;"` → fields include `kind`, `domain`; `SELECT count() FROM goal_graph WHERE kind='pursues' GROUP ALL` > 0 |
| R2 | `SELECT count() FROM loop GROUP ALL` ≥ 90 (was 0); per domain: `SELECT domain, count() FROM loop GROUP BY domain` equals the old tables' counts (6/60/4/5/3/7/8/8); running the migration twice → identical counts |
| R3 | `python scripts/ci/dormancy_scan.py` + `false_contract_scan.py` exit 0; `git grep -c "class GoalSpecification" src` == 1; every rival module's public symbol either re-exports the spine's or has an importer that is not a test |
| R4 | neutralise the reader (make `--status` read `[]`) → `tests/unit/test_trace_goal_pipeline.py::test_status_reads_goal_graph_not_domain_tables` FAILS; with a live DB, `--status` lists ≥ 7 domains |
| R5 | plant `mirror: SurrealDB … nonexistent_loop` in a temp doc → check exits 1; real doc (`twin_loop`, session-scoped) → exit 0; delete the twin rows in a scratch db → RED |
| R6 | `SELECT depth FROM loop WHERE domain='compound' AND session=<latest>` is not NULL after one daemon cycle |
| all | un-mocked boundary smoke: `refactor_traces_to_goals.py --dry-run` against live `event_log` yields ≥ 1 goal; `--persist` adds exactly that many `goal` rows + `derived_from` edges; re-read by id |

## 3. Design — the spine (from `tgl-inventory`, measured at 455ffbb2a; consumption, not imports)

**Spine: `src/cohezion/flume/loop_goal_refactor_engine.py`** (477 LOC, 20 tests). It is the only
module of the five reached from a registered CLI command (`ops refactor-traces`, `cli/main.py:1020`)
AND from the perpetual loop (`ops loop` → `unified_perpetual_orchestrator.py:324`
`AutonomousGoalExecutor(goal, memory=self.memory_as_plans)`), the only owner of the `goal` /
`loop_trace` tables (`DurableSurrealGoalPersistence`), and `recursive_trace/tripartite_goal_loop.py`
imports its `GoalSpecification` + persistence rather than defining rivals → **tripartite is a layer
on the spine** (its only rivalry is the marimo notebook re-declaring its 5 dataclasses as WASM stubs).

**Husks / rivals (retire by wiring, never by deletion — non-destructive-wiring.md):**
- `compound/goals_and_loops_orchestrator.py` — 0 tests, 0 persistence; its one `src/` importer
  (`inter_daemon_loop_nexus.py:72`) assigns it to a field never read; one runnable caller, the
  one-shot `scripts/ops/master_codebase_graph_and_loops_expansion.py`. Its BMAD vocabulary
  (`LoopStage`, `AcceptanceCriterion`, `GoalStatus`) is the only content worth keeping → optional
  fields on the spine's `GoalSpecification`/`LoopSpec`; the module becomes a re-export shim.
- `recursive_trace/goal_loop.py` — 0 tests, a third Goal shape, own storage (`resolution_log.jsonl`
  + `RELATE` against `127.0.0.1:8001` vs the engine's `localhost:8001`); reached only by
  `scripts/ops/prove_all_seven_mandates.py`. → shim over the spine's executor.
- `flume/monadic_markov_trace_engine.py` — NOT in this family (no Goal type; monad laws + Markov
  routing). **Excluded** from the consolidation.
- Triplicated `goal` write path: `DurableSurrealGoalPersistence` + `scripts/ops/refactor_traces_to_goals.py`
  (own `_sql`) + `scripts/ops/demo_trace_to_goal_loop_refactor.py:92` (raw `CREATE goal`). → one
  write path; the scripts call the persistence class.

**Three independent implementations of one file.** `feat/trace-goal-loop-pipeline` (015e15695) and
`feat/trace-goal-loop-closure` (cd4189357, 0ab8076b8) are NOT deltas on main: the engine did not
exist at their merge-base `cbb33ec69`; main created it in `fe6735b10` (#294). No revision is a
superset:

| capability | main | pipeline branch | closure branch |
|---|---|---|---|
| `MemoryAsPlans` / `PlanSegment` | ✅ | ✗ | ✗ |
| convergence polarity (`direction`, `is_satisfied_by`) — main hardcodes `>=`, so `error_rate <= 0.05` goals are mis-scored | ✗ | ✗ | ✅ |
| goal closure `mark_goal_converged` — main has **no `UPDATE goal` anywhere** | ✗ | ✗ | ✅ |
| `persist_goal` re-open bug: `UPSERT goal:<content-id> MERGE {status:'active',…}` overwrites the very field its comment claims to preserve → every re-run re-opens every goal; `fetch_open_goals` grows monotonically | ✗ (bug) | ✗ | fixed by closure semantics |
| kanban as trace source (`synthesize_goal_from_kanban_item`, failure clustering) | ✗ | ✅ | ✗ |
| ABSENT-vs-UNKNOWN (saturated `fixed_in` page → `None`, `ORDER BY timestamp DESC`) | ✗ | ✗ | ✅ |
| dormancy-scan registration | ✗ | ✗ | ✅ |
| shared `payload_looks_like_failure` (main duplicates it in the ops CLI) | ✗ | ✗ | ✅ |

**Port order (each step T2-tested, mutation-verified, gates green before the next):**
1. Closure + polarity + the MERGE re-open fix + ABSENT-vs-UNKNOWN onto main's engine (from cd4189357/0ab8076b8, re-cut by hand — the branches are not cherry-pickable).
2. Kanban trace source + failure clustering (from 015e15695), reading `kanban_item` (24,130 rows) and the `vault` db per R1a.
3. The graph layer (R1/R2): `goal_graph` edges written by the ONE persistence class; `loop` rows written for every executed loop (`LoopSpec` = canonical template fields + `rung`, `depth`); migration script for the 8 domain pairs + `autonomous_loop`.
4. Reader (R4) + mirror check (R5).
5. Rival modules → shims re-exporting the spine (their scripts keep working); the triplicated write path collapses to one.
Note: the `/tmp/cohezion_4h_runner.py` heredoc in `scripts/ops/start_background_4h_daemon.sh` is the
only place kanban meets goals today — invisible to every static gate. The kanban source must land
in `src/` so the gates can see it.

## 4. Verification ladder (right leg)

1. Unit — dataclass round-trips, migration mapping per source table (fixtures = one real row per
   old table, captured from the census).
2. Integration (un-mocked) — SurrealDB at :8001, scratch db `tgl_test`: migrate the fixtures,
   assert counts/edges, run the reader, run the mirror check both directions.
3. System — live db=main: dry-run, persist one synthesized goal from `event_log`, `--status`
   shows it; compound daemon writes `loop.depth`.
4. Mutation — R4 reader neutralised; migration `domain` dropped (counts collapse); mirror check
   with the zero-guard removed (phantom passes) — each must turn a named test red.
5. Adversarial second pass — fresh agent, "assume broken", traces producer → consumer in the
   assembled system (verification-depth.md §4).
6. Gates — the cohezion-land battery; then feature-branch push + user PR (main-protection).

## 5. Out of scope (explicit)

Dropping the old tables; rewriting `event_log`/`compound_loop`; the JEPA/FLUME V-model items
(P0/P1 in vmodel-recommendations.html — different subsystem); landing the codegraph generator
(`origin/tooling/codegraph`, separate small land).
