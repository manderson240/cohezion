---
title: Git History Audit — feat/adaptive-calibration-harness
date: 2026-06-06
auditor: agent (report-only, no git writes)
branch: feat/adaptive-calibration-harness
head: f4ec56944
merge_base: 785b92f30
ahead: 252
behind: 57
standards_source:
  - CLAUDE.md (Conventional Commits, Surgical Commits / Learning 363, Measurement Integrity)
  - .claude/rules/git-operations.md
  - .claude/rules/harness.md (.claude) — conventional commits required
scope: REPORT-ONLY — no rebase/cherry-pick/commit/push/reset; no file edits except this doc
---

# Git History Audit — `feat/adaptive-calibration-harness`

## 1. Coverage Statement

- **Subjects audited:** 252 / 252 (100%) — every commit's subject line regex-checked for conventional format.
- **Stat-inspected:** 252 / 252 (100%) — each commit run through `git show --stat`/`--name-only` (no full patches read) for file-count, `src/` vs `tests/` touch, and added-file cruft/large-binary scan.
- **Patch-identity:** `git cherry -v main HEAD` classified all 252 as new (`+`) vs already-in-main (`-`).
- **Conflict surface:** computed from the **new-commits-only** file set ∩ main's post-merge-base file set (the raw `785b92f30..HEAD` overlap was discarded — it is dominated by the 9,246-file `.archives/` untrack and the duplicate history).

Method was stat-only per instruction; no diff bodies were read.

## 2. Conformance Counts

| Dimension | Result |
|---|---|
| **Conventional subject (type prefix present)** | **252 / 252 conform** (0 non-conventional) |
| — of which non-core types (`audit`/`research`/`exp`) | 5 (repo-idiomatic but outside the strict feat/fix/docs/refactor/test/chore set) |
| **Patch-new (`+`) vs already-landed (`-`)** | 232 new, **20 patch-equivalent to main** (auto-drop on rebase) |
| **Mega-commits (>40 files)** | 9 (4 atomic-by-nature, 1 true Learning-363 violation, 4 squash-merge imports) |
| **feat/fix touching `src/` with NO test** | 33 raw → **~10 genuine** after excluding lint/style/noqa/import-reexport/format commits (legitimately test-exempt) |
| **Committed cruft (`__pycache__`/`.pyc`/secrets/`.env`/large non-LFS binary)** | **0** — clean |

**Net:** subject hygiene is excellent (100%). The real issues are (a) a block of 12 conflict-resolution squash-merge commits at the base of the branch, (b) ~10 feature/bugfix commits with no paired test, and (c) one Learning-363 "stage untracked files" bundling violation.

### Failure-type breakdown
- **Non-conventional subject:** 0
- **Mega-commit (genuine bundling concern):** 1 (`f7b915e08`); plus 12 squash-merge imports that are large-by-nature but each represent one merged branch.
- **Missing-test (genuine):** ~10
- **Cruft/secrets:** 0

## 3. Worst ~15 Offenders

| # | SHA | Subject (truncated) | What's wrong |
|---|---|---|---|
| 1 | `f7b915e08` | fix(repo): resolve PyTorch 2.5.1/torchao compat **and stage untracked files** | **Learning-363 violation.** 54 files spanning .gitignore + compound/flume/inference/skills/tests — two unrelated concerns ("and stage untracked files") bundled. Classic mega-commit. |
| 2 | `15de1ecb1` | refactor: untrack .archives/ and archives/ … | 9,246 files. Atomic *intent* (one untrack op) but enormous; pollutes every downstream file-overlap metric. Should be isolated/landed separately. |
| 3 | `480dcf372` | feat(physics): complete Stealthskater Bridge integration & register compound loop invariants | 496 files, **two concerns** ("integration **&** register invariants") — feature + invariant registration bundled. |
| 4 | `e2a0e887f` | feat: implement visual Stealthskater telemetry dashboard **and fix compilation types**… | Bare `feat:` (no scope) + two concerns (dashboard + type fixes), src-only, no test. |
| 5 | `98684bb4d`..`b299b46fa` | chore(merge): squash <branch> → main (NN conflicts resolved) (#15x) | **12 squash-merge commits** at branch base, each "(36–44 conflicts resolved)". Imported diverged history; each bundles a whole branch. These are the "messy older history". |
| 6 | `1c6ce2fc0` | feat(model): HIHO-LM training infrastructure + Round 7 autoresearch findings | 7 files, 6 in src/, **no test** for new training infra; also collides with main (§4). |
| 7 | `24efb0248` | feat(governance): add cerebellum neuron IMPL (item 24 fix — 78a4de… shipped only the test) | Feature IMPL with no test in the commit; the *test* shipped in a separate prior commit — split-feature (impl and test in different commits). |
| 8 | `e84511e01` | feat(inference): log-based routing accuracy measurement + calibrate task classifier | 2 src files, no test for new measurement logic. |
| 9 | `b000ffd06` | fix(physics): track 6 Phase-18 Stealthskater bridge modules | 6 src modules added, no test (tests landed elsewhere) — bare "track files" commit. |
| 10 | `846e92ce8` | feat(registry): register new ROUTING_ACCURACY_CALIBRATION_PRIME skill | New skill src, no test/validate leg in commit. |
| 11 | `2bd5dbaeb`/`3d9df0aad`/`4cab14eb8`/`5ee6c09a1`/`13289efdb`/`57c71ba6a`/`46e7de34e` | feat/fix(inference): V3–V8 routing patterns (#175–#190) | A run of 1-file `task_classifier.py` edits, each claiming a benchmark % but **no committed test/benchmark fixture** — verification-claim commits without the harness in-tree. |
| 12 | `635eb5611` | feat(inference): LYNX escalation probe — semantic quality gate (arXiv:…) | New gate logic, 1 src file, no test. |
| 13 | `881bb9c4a` | feat(inference): CLaSp speculative iGPU tier — E2B draft + E4B verify | New tier, 2 src files, no test. |
| 14 | `9dddea98e` | feat(inference): EXP-EVO-BUDGET per-task cost ceiling | New budget logic, no test. |
| 15 | `eff4ac845` | feat(compound): restore Consortium Instigator (adversarial probe, 8 vectors) | 1 src file, no test; also patch-equivalent to main (`-`) so it will auto-drop. |

(The `audit(...)`/`research(...)` type-prefix commits are *not* listed as offenders — they are intentionally docs/no-src and repo-idiomatic.)

## 4. The 57-Behind Summary + Conflict-Risk

**Subsystems main advanced since merge-base (top ~30 genuinely-new main commits):**
- `agent/` — ReflectiveDriver, SkillAdaptor, run_with_reflection, orchestration error-loop (self-improvement keystone).
- `physics/` — AnomalyGate / ConservationFilter / AnomalyQuarantine.
- `world_model/` — Observer, SurpriseRouter, Quadrature Nexus gating.
- `experiments/` — R-Zero ascension, reward-integrity eval.
- `memory/` — trust-scored ground-truth hierarchy.
- `fleet/` — Mellum FIM lane, GAIA tier, recursive trace.
- `api/` — Anthropic prompt caching + Message Batches.
- `skills/` — large skills-matrix reconcile (frontmatter backfill, merge/split, register).

**Important structural finding:** main commits **#31–57** (`45f4cd585`..`544c6c602`) have **identical subjects** to our branch commits #190–252. History diverged at the merge-base: both branches carry the same logical work with different SHAs. `git cherry` confirms **20** of our commits are already patch-equivalent in main (auto-drop on rebase); the rest were re-resolved differently (the V-routing edits, squash-merges, and conflict resolutions diverged), so they show as `+` despite matching subjects.

**Conflict surface (new-work-only ∩ main-since-merge-base):** 238 files, 184 in `src/`. Narrowing to main's *genuinely-new* work (top 30 commits) ∩ our new work, **30 `src/` files truly collide**, including high-risk shared surfaces:

```
src/cohezion/compound/executor.py            (both branches edit the 11-step executor)
src/cohezion/compound/journey_tracker.py
src/cohezion/compound/hiho_lm_gate.py
src/cohezion/compound/post_execution.py
src/cohezion/compound/token_efficient_executor.py
src/cohezion/core/compound/retrospection.py
src/cohezion/inference/registry.py
src/cohezion/inference/gaia_adapter.py
src/cohezion/cost_optimization/cost_tracker.py
src/cohezion/agent/unified_harness.py
src/cohezion/model/cohezion_lm.py            ┐ BOTH built HIHO-LM training infra
src/cohezion/model/hiho_attention.py         │ independently (our 1c6ce2fc0 vs
src/cohezion/model/train.py                  │ main 911b4920f / de0d5d0ac) —
src/cohezion/model/training_data.py          │ guaranteed collision
src/cohezion/model/__init__.py               ┘
src/cohezion/registry/skill_registry.json    ┐ TWO registry JSONs, both edited
src/cohezion/skills/skill_registry.json      ┘ on both sides — classic merge conflict
src/cohezion/skills/*_PRIME.md  (AUTODQA, COSMIC_FIRE, GREEK_PARAMETERS, HIHO_LM,
   R0_SIGMA, TRIUNE_SELF, SYNC_ASYNC_BRIDGE, TENSOR_METRIC, LANGCHAIN_RAG_TIER,
   STEALTHSKATER_CORPUS, LOCAL_INFERENCE_ROUTING)  — skills touched on both sides
src/cohezion/universe/agentic_evo_swift.py
```

**Conflict-risk: MEDIUM–HIGH.** Drivers: (a) both branches edited the core compound executor + journey_tracker; (b) both independently created HIHO-LM training infra in `src/cohezion/model/` — the same files with different content; (c) both edited the two `skill_registry.json` files and ~11 PRIME skills (main did a large skills-matrix reconcile). The skill-registry JSONs and the duplicated `model/` work are near-certain manual-merge points.

## 5. Recommended Landing Strategy

**The branch is NOT cleanly cherry-pickable onto `origin/main` as-is.** Two problems: (1) ~12 base squash-merge commits carry diverged conflict-resolution state that already partly exists on main; (2) a 30-file `src/` collision with main's new work, including duplicated `model/` HIHO-LM infra and the shared `skill_registry.json` files.

**Recommended approach — rebase, not raw cherry-pick:**

1. **`git rebase origin/main`** (interactively). Rebase will **auto-drop the 20 patch-equivalent (`-`) commits**, eliminating most of the apparent duplication for free.
2. **Drop or squash the 12 base `chore(merge): squash … (NN conflicts resolved)` commits** (`98684bb4d`..`b299b46fa`). These re-import branches whose subjects already exist on main; keeping them re-litigates resolved conflicts. This is the **messy older history** — quarantine it.
3. **Expect manual conflict resolution** on the 30-file hot set, concentrated in: `model/` (reconcile the two HIHO-LM infras — likely keep main's `911b4920f`/`de0d5d0ac` and re-apply only our genuinely-additive deltas), both `skill_registry.json` files, the PRIME skills, and `compound/executor.py` + `journey_tracker.py`.

**Clean-and-landable range vs messy range:**
- **CLEAN (land these):** the top "item N" wiring/feature session — roughly **`f7b915e08`..`HEAD`** minus `f7b915e08` itself — i.e. the additive `feat(compound)/feat(inference)/fix(wiring)` work above the squash block. These are mostly single-concern, well-scoped, default-OFF flagged, and self-documenting (each "item N DONE <hash>" backlog pairing). Cherry-pick this range onto a fresh branch off `origin/main` and it lands with only the 30-file hot set to reconcile.
- **MESSY (rework/quarantine):** the bottom block `98684bb4d`..`b299b46fa` (12 squash-merges) plus `f7b915e08` (Learning-363 bundling) and `15de1ecb1` (9,246-file untrack). Re-do the `.archives/` untrack as a standalone op on the target branch; do not drag it through the rebase.

**Before landing:** split the ~10 missing-test feature commits' verification in (or accept them as flagged) and confirm `make validate` + `uv run pytest tests/ -q` green on the rebased result — the branch's own Measurement-Integrity standard requires tests-pass, not projected-pass.
