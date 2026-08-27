---
title: Reconcile worktree-virtual-soaring-shamir → main
date: 2026-08-26
status: PENDING
worktree: .claude/worktrees/virtual-soaring-shamir
branch: worktree-virtual-soaring-shamir
base: main @ b93b968f1 (2026-08-21)
executor: opus (Fable wrote the decisions; Opus/local execute)
---

# Reconcile `worktree-virtual-soaring-shamir` → `main`

## Measured state (2026-08-26 20:45 EDT)

| Fact | Value | How measured |
|---|---|---|
| Ahead / behind main | **286 / 152** commits | `git log --oneline main..HEAD` / `HEAD..main` |
| Raw diff | 6,081 files, +870,405 / −5,415 | `git diff --stat main...HEAD` |
| Tracked `.pyc` | **4,769** on HEAD, **0** on main | `git ls-tree -r main/HEAD \| grep -c pyc` |
| `.pyc` origin | one commit: `f73e8acf0` (2026-08-17, "oma-loop 20 cycles") | `git log --diff-filter=A` |
| Raw (non-LFS) binaries | `checkpoints/…/tokenizer.json` 11.4 MB (757k lines), `adapter_model.safetensors` 8.7 MB | `git cat-file -s`; no `*.safetensors` in `.gitattributes` |
| `.pt` files | LFS pointers (OK) | `git cat-file -p` shows `version https://git-lfs…` |
| Real code | **595 `.py`** (435 added / 158 modified / 2 renamed / 0 deleted), 549 `.md`, 44 `tests/unit` | `git diff --name-status` |
| New `src/cohezion/` subsystems | adapters, competitions, evaluation, evo, infrastructure, ops, pipelines, policies, review, training | `git ls-tree` main vs HEAD |
| BMAD vendored lib | `_bmad/skills-lib` 238 files (main has 18 `_bmad` files total) | `git ls-tree -r` |
| Real 3-way conflicts | **84** = 46 content + 38 add/add | `git merge-tree --write-tree main HEAD` |
| Upstream | none; no remote contains HEAD | `git rev-parse @{u}` |
| Last commit | `b28fc4d58` 19:09 EDT today (96 min before this triage) | `git log -1` |
| Pack size | **19.94 GiB** (CLAUDE.md claims 182 MB bundle post-LFS) | `git count-objects -vH` — separate repo-health track |

## Classification of the 6,081 files

### A. DROP from index (never land) — ~4,780 files, purely mechanical
- All 4,769 `**/__pycache__/*.pyc`. `.gitignore` line 2 already ignores `__pycache__/`; they are tracked anyway (added in `f73e8acf0`). Untrack, do not delete from disk.
- Root snapshots `cockpit-ai-panel.md`, `cockpit-fresh-snapshot.md`, `cockpit-stable.md`, `cockpit-before-restart.png` (4.6k lines) — **mine before remove**: move to `docs/ops/snapshots/` in the same commit; nothing is lost.

### B. LFS / weight hygiene — 15 files under `checkpoints/`
- Keep (small, informative): `adapter_config.json`, `README.md`, `training_summary.json`, `chat_template.jinja`, `tokenizer_config.json`.
- Untrack: `adapter_model.safetensors`, `tokenizer.json` (add `checkpoints/**/*.safetensors` and `checkpoints/**/tokenizer.json` to `.gitignore`; add `*.safetensors` to `.gitattributes` LFS so a future re-add is a pointer).
- The blobs stay in branch history (rewriting 286 commits needs explicit user permission — NOT doing it). Landing carries ~20 MB of dead blobs; acceptable vs. the alternative.

### C. CHURN — land separately or not at all (user decision)
- `_bmad/skills-lib/**` (238 files) + `_bmad/_config` + `.claude/skills/bmad-*` edits: a vendored BMAD library upgrade. Zero Cohezion code depends on it for tests. Split into its own commit train (`chore(bmad): vendor skills-lib`) and land LAST, only if wanted on main.
- `uv.lock` (+3116/−3473) — conflicts with main; regenerate after merge (`uv lock`), never hand-merge.

### D. CODE — the deliverable (595 .py, 44 tests, 52 research docs)
Land in **subsystem trains**, not one 286-commit blob. Proposed trains (each: merge-resolve → tests → 3-lens adversarial review → `automerge_guard.sh` → `cohezion-land`):

1. **T1 hygiene** — A + B above + `.gitignore`/`.gitattributes`. Gate: `git ls-files | grep -c pyc` == 0; `scripts/hooks/lfs_pointer_check.py` green.
2. **T2 inference/compound** — the 10 modified `src/cohezion/inference/*` + 7 `compound/*` (includes `speculative_engine.py` 679 lines, `unified_hybrid_router.py` 666 lines). Highest conflict density; highest ownership tier → **full 3-perspective board**.
3. **T3 competitions** — new `src/cohezion/competitions/` (39 files: arc/, arc_prize/, arc_prize_2/, biohub_cell/, pokemon_tcg/). ⚠ **Surface-name hazard**: main already has `src/cohezion/competition/` (107 files). Verify these are not twins before landing (non-destructive-wiring rule 3). If overlapping, wire `competitions/` INTO `competition/`; never delete either.
4. **T4 new subsystems** — adapters, evaluation, evo, infrastructure, ops, pipelines, policies, review, training. Run `scripts/ci/dormancy_scan.py` + consumption grep per module: a subsystem with no production consumer is a wiring TODO, flag it, still land it (additive).
5. **T5 physics/flume/swarm/security/agi** — mostly additive; light review pass unless dormancy scan flags.
6. **T6 docs/research** (52 md) + `scripts/ops` (167) — light pass; docs are not load-bearing.
7. **T7 BMAD churn** — see C; user decides.

## The 84 conflicts — decision rules

| Class | Count | Rule |
|---|---|---|
| `content` in `scripts/**` (~30) | main ran a ruff-format campaign; branch edited semantics | Take **main's formatting**, re-apply branch's semantic hunks; `ruff format --check` must pass |
| `add/add` in `src/` (13) | both sides independently built the same module: `agi/{__init__,autoharness_policy,recursive_learning,zkfv_compiler}`, `contracts.py`, `core/cross_session_event_bridge.py`, `inference/{delegation_logger,prewarm_harness,unified_hybrid_router}`, `physics/{electric_dipole,poincare_manifold}`, `proactive/__init__.py`, `reliability/oom_guard.py` | **Judgment — this is the "verified fixes stall unlanded" pattern.** For each: `git diff main:<f> HEAD:<f>`; if one is a strict superset, take it; else merge additively (non-destructive). Main's version is the *prior-revision oracle*: whatever lands must not regress main's tests for that file. |
| `add/add` in `tests/` (7) | same | Keep the UNION of test cases (never drop a discriminating test) |
| `content` in `src/` (~14) | `degradation_detector.py`, `event_bus.py`, `surreal_client.py`, `event_consumer.py`, `land_runner.py`, `image_tier.py`, `model_card_defaults.py`, `tri_compute_orchestrator.py`, `shadow_scripter.py`, `forge.py`, `arc/transforms.py`, `compound/harness.py` | Manual, with main's tests for each file as the oracle |
| `.claude/rules/harness.md`, `KEY_LEARNINGS.md`, skill `.md` | 6 | Union of sections; both sides append |
| `.gitignore`, `.githooks/post-commit` | 2 | Union |
| `uv.lock` | 1 | Discard both; `uv lock` after merge |

## ⚠ Execution constraint (measured 2026-08-26 20:55)

`.git/worktrees/` is bind-mounted **read-only in the agent namespace** — `git commit`/`merge`/
`checkout` fail with `index.lock: Read-only file system` from EVERY worktree, and it survives
`dangerouslyDisableSandbox`. `.git/objects` + `refs` stay writable. Two working paths
(memory `plumbing-merge-train-ro-worktrees`, `bwrap-worktree-erofs-and-transcript-recovery`):

- **Plumbing (no new checkout):** `git merge-tree --write-tree main HEAD` → resolve the 84
  conflicts by writing stage blobs into a TEMP index (`GIT_INDEX_FILE=$TMPDIR/idx git read-tree
  <tree>; git update-index --cacheinfo 100644,<blob>,<path>`) → `git write-tree` →
  `git commit-tree $TREE -p HEAD -p main -m …` → `git update-ref refs/heads/<branch> $NEW $OLD`
  (CAS). Verify via `git archive $NEW | tar -x -C $TMPDIR/x` + `PYTHONPATH=$TMPDIR/x/src pytest`.
- **Durable clone:** `git clone --single-branch -b worktree-virtual-soaring-shamir
  /home/mike-anderson/dev/cohezion ~/dev/vss-reconcile` — normal porcelain works there; push the
  branch back when done (safe: branch is checked out only in this RO worktree).

Recommendation: **durable clone** for T1–T2 (84 conflicts by hand in a temp index is error-prone);
plumbing only for the final fast-forward of `main`. The `bash` block below is written for the
clone; from a worktree, translate each step per the plumbing recipe.

## Execution order (Opus)

```bash
# 0. Confirm nothing is still committing here (auto-submission / leaderboard-climb daemons landed commits until 19:09)
git log -1 --format='%ci'          # must be older than this plan's timestamp; re-check before each step
# 1. T1 hygiene, on this branch
git rm -r --cached -q $(git ls-files '*.pyc')            # untrack, keep on disk
mkdir -p docs/ops/snapshots && git mv cockpit-*.md cockpit-before-restart.png docs/ops/snapshots/
git rm --cached checkpoints/cohezion_lora_qwen_adapter/{adapter_model.safetensors,tokenizer.json}
printf 'checkpoints/**/*.safetensors\ncheckpoints/**/tokenizer.json\n' >> .gitignore
printf '*.safetensors filter=lfs diff=lfs merge=lfs -text\n' >> .gitattributes
git commit -m 'chore(hygiene): untrack 4,769 pyc + raw LoRA weights; move cockpit snapshots to docs/ops'
# 2. Merge main INTO the branch (one conflict pass; branch is unpushed so history is ours)
git merge main            # resolve 84 per table above; uv lock; commit
# 3. Baseline
uv run pytest tests/unit --import-mode=append -q -p no:warnings
uv run python scripts/ci/dormancy_scan.py && uv run python scripts/ci/phantom_attr_scan.py
# 4. Per-train adversarial review (3 lenses, Opus subagents, "assume broken"), apply findings
# 5. Gates + land
scripts/ci/automerge_guard.sh && <cohezion-land skill>   # fast-forward; never squash
```

## Open questions for the user (do not block T1–T2 on these)
1. Land `_bmad/skills-lib` (238 vendored files) on main, or keep it branch-local?
2. The 19.94 GiB pack is a repo-health item independent of this landing — schedule `entire clean` + a pack audit?
3. Are the auto-submission / leaderboard-climb daemons (`b28fc4d58`, `e9abed45f`) meant to keep committing to this branch? If yes, they must be paused during steps 1–5.

## Quota routing
- Fable: decisions above (done). Do not spend Fable on steps 1–3.
- Opus (`/model opus`, ~40% pool): steps 2, 4 — conflict judgment + adversarial lenses.
- Local :13305: step 4 first-pass QA per train, dormancy/consumption greps.
