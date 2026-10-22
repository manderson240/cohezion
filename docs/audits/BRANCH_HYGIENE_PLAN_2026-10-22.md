---
type: plan
title: Branch, worktree and primary-checkout hygiene plan
date: 2026-10-22
scope: /home/mike-anderson/dev/cohezion shared .git (origin/main b3342cf18)
status: sections-A-B1-B2-D-E-executed
tags: [coherence, repo-hygiene, git]
---

# Branch, worktree and primary-checkout hygiene plan — 2026-10-22

Coherence audit finding F6. Everything below was measured with read-only git commands on
2026-10-22; nothing has been deleted. Each section ends with the exact commands. Deletions,
worktree removals and remote pushes are permission-gated: run only the sections you approve.

**Measured:** 186 local branches, 308 remote; 53 local branches fully merged into `origin/main`
(25 deletable now, 28 pinned by a registered worktree); 76 remote branches whose tip is already
an ancestor of `origin/main`; 87 registered worktrees, 2 with missing directories; the primary
checkout is on `security/codeql-wave2` (21 ahead / 56 behind main) with 9 tracked dotfiles
really deleted on disk (`.gitignore`, `.gitattributes`, `.pre-commit-config.yaml`,
`.secrets.baseline`, `.git-blame-ignore-revs`, `.worktreeinclude`, `.antigravity.md`,
`.autoresearch-off`, `.env.sheets-research.example`).

**Constraint for agent sessions:** `.git/worktrees` is a read-only mount, so `git worktree
prune/remove` and `git worktree add` fail from any Claude session (verified, with and without
the sandbox). Section B must be run from a normal user shell.

---

## A. Safe to delete now — 25 local branches, fully merged, held by no worktree

`git branch --merged origin/main` lists each; none is checked out anywhere. `git branch -d`
(lower-case d) refuses anything not merged, so the command is self-checking.

| Branch | Last commit | Remote twin |
|---|---|---|

| `campaign-candidate` |  | no |
| `chore/deps-inference-20261021` |  | yes |
| `docs/restore-constitution` |  | no |
| `exp/scienceide-mini-loop-20260919` |  | yes |
| `feat/honest-graders` |  | yes |
| `feat/inference-cascade-hardening` |  | no |
| `feat/kv-arch-from-gguf` |  | yes |
| `feat/lemond-admission-gate` |  | yes |
| `fix/anthropic-scan-followups` |  | no |
| `fix/oom-relief-loop-and-byte-aware-topology` |  | yes |
| `fix/syspath-relative` |  | yes |
| `integrate/improvement-loop-20261020` |  | yes |
| `land/codegraph-rebased` |  | yes |
| `land/false-success-fixes-20260919` |  | yes |
| `land/front-b-fixes` |  | no |
| `land/h5-arc-proposer-20260919` |  | yes |
| `land/h5-exec-gate-20260918` |  | yes |
| `land/harvest-20260831` |  | no |
| `land/kaggle-mcp-tools` |  | yes |
| `land/loop-mcp-event-publish` |  | no |
| `land/train1-fixes` |  | no |
| `land/train3-ports` |  | no |
| `land/verified-fixes-slice` |  | no |
| `land/vss-20260831` |  | no |
| `reconcile/vss-merged` |  | no |

```bash
cd /home/mike-anderson/dev/cohezion
git branch -d campaign-candidate \
  chore/deps-inference-20261021 \
  docs/restore-constitution \
  exp/scienceide-mini-loop-20260919 \
  feat/honest-graders \
  feat/inference-cascade-hardening \
  feat/kv-arch-from-gguf \
  feat/lemond-admission-gate \
  fix/anthropic-scan-followups \
  fix/oom-relief-loop-and-byte-aware-topology \
  fix/syspath-relative \
  integrate/improvement-loop-20261020 \
  land/codegraph-rebased \
  land/false-success-fixes-20260919 \
  land/front-b-fixes \
  land/h5-arc-proposer-20260919 \
  land/h5-exec-gate-20260918 \
  land/harvest-20260831 \
  land/kaggle-mcp-tools \
  land/loop-mcp-event-publish \
  land/train1-fixes \
  land/train3-ports \
  land/verified-fixes-slice \
  land/vss-20260831 \
  reconcile/vss-merged
```

Expected after: `git branch --merged origin/main | grep -vE 'main|^\*' | wc -l` prints 28 (the pinned set).

---

## B. Needs a look — 28 merged branches pinned by worktrees (user shell only)

Each branch is fully merged into `origin/main` and has **0 commits** that main lacks; a registered
worktree holds it, so `git branch -d` refuses until the worktree is removed. `.git/worktrees` is a
read-only mount for agent sessions (verified again 2026-10-22, with and without the sandbox), so the
removals below must run from a normal shell.

**Inspected 2026-10-22.** Dirt was classified after excluding caches, compiled files, the 22 media
files that read as modified against LFS, and sandbox scaffold dotfiles. **Every worktree's remaining
unstaged diff, staged diff and real untracked files were harvested first** to
`~/vaults/cohezion-vault/reports/worktree-harvest-20261022/<branch>/` (996 KB), so removal loses nothing.

### B1. Clean — 14 worktrees, no real dirt, nothing ahead of main

| Branch | Worktree |
|---|---|
| `agent-1787958482` | `~/dev/cohezion/.worktrees/cohezion-agent-1787958482` |
| `claude/cosmogony-state-45bef2` | `~/dev/cohezion/.claude/worktrees/cosmogony-state-45bef2` |
| `claude/fervent-allen-5f2209` | `~/dev/cohezion/.claude/worktrees/fervent-allen-5f2209` |
| `claude/kaggle-token-efficient-bd1eca` | `~/dev/cohezion/.claude/worktrees/kaggle-token-efficient-bd1eca` |
| `claude/local-files-google-drive-c6584d` | `~/dev/cohezion/.claude/worktrees/local-files-google-drive-c6584d` |
| `deploy/services` | `~/dev/cohezion-services` |
| `feat/codebase-graph-map` | `~/dev/cohezion/.worktrees/graph-map` |
| `fix/main-code-health` | `~/dev/cohezion/.worktrees/main-health-fix` |
| `worktree-fancy-cooking-rocket` | `~/dev/cohezion/.claude/worktrees/fancy-cooking-rocket` |
| `worktree-fluffy-mapping-pebble` | `~/dev/cohezion/.claude/worktrees/fluffy-mapping-pebble` |
| `worktree-glimmering-floating-canyon` | `~/dev/cohezion/.claude/worktrees/glimmering-floating-canyon` |
| `worktree-glowing-tinkering-peach` | `~/dev/cohezion/.claude/worktrees/glowing-tinkering-peach` |
| `worktree-happy-popping-wand` | `~/dev/cohezion/.claude/worktrees/happy-popping-wand` |
| `worktree-snoopy-foraging-kettle` | `~/dev/cohezion/.claude/worktrees/snoopy-foraging-kettle` |

### B2. Trivial dirt only — 6 worktrees (harvested; safe to remove with --force)

| Branch | Worktree | Dirt |
|---|---|---|
| `agent-1788098353` | `~/dev/cohezion/.worktrees/cohezion-agent-1788098353` | data/compound/cache/token_cache.jsonl only |
| `agent-1788098455` | `~/dev/cohezion/.worktrees/cohezion-agent-1788098455` | token_cache.jsonl only |
| `agent-1788098546` | `~/dev/cohezion/.worktrees/cohezion-agent-1788098546` | token_cache.jsonl only |
| `claude/capabilities-exploration-9e9a8d` | `~/dev/cohezion/.claude/worktrees/capabilities-exploration-9e9a8d` | .claude/scheduled_tasks.lock deleted |
| `claude/consolidate-work-into-main-27b73e` | `~/dev/cohezion/.claude/worktrees/consolidate-work-into-main-27b73e` | scheduled_tasks.lock + sandbox scaffold dotfiles |
| `worktree-virtual-soaring-shamir` | `~/dev/cohezion/.claude/worktrees/virtual-soaring-shamir` | one untracked plan doc, already in the vault |

### B3. Real uncommitted work — 8 worktrees (harvested; review the patch before removing)

| Branch | Worktree | What is there |
|---|---|---|
| `agent-1787957534` | `~/dev/cohezion/.worktrees/cohezion-agent-1787957534` | token_cache + edits to docs/audits/UNAWAITED_SURREAL_WRITES_2026-08-28.md |
| `worktree-splendid-seeking-sonnet` | `~/dev/cohezion/.claude/worktrees/splendid-seeking-sonnet` | 2 untracked scripts under scripts/loop/ |
| `worktree-validated-snuggling-melody` | `~/dev/cohezion/.claude/worktrees/validated-snuggling-melody` | skill_refiner.py + its test (163 KB diff) |
| `claude/drivendata-doe-gems-66a1e7` | `~/dev/cohezion/.claude/worktrees/drivendata-doe-gems-66a1e7` | STAGED rubric_middleware work + new test |
| `worktree-scalable-humming-pumpkin` | `~/dev/cohezion/.claude/worktrees/scalable-humming-pumpkin` | degradation_detector/harness + tests (166 KB diff) |
| `fix/lemonade-router` | `~/dev/cohezion/.worktrees/fix-lemonade-router` | 8 files incl. event_bus, unified_hybrid_router (70 KB diff) |
| `worktree-bright-swinging-squirrel` | `~/dev/cohezion/.claude/worktrees/bright-swinging-squirrel` | 44 files (231 KB diff) + 19 untracked |
| `feat/inference-service-mesh` | `~/dev/cohezion/.worktrees/inference-service-mesh` | 60 files (106 KB diff, 9.5 KB staged) + 33 untracked |

```bash
# NORMAL SHELL ONLY. B1 + B2 (20 worktrees). Each branch is verified an ancestor of origin/main
# before deletion; -D is used because -d checks the branch's own upstream, not origin/main.
cd /home/mike-anderson/dev/cohezion && git fetch -q origin main
while IFS='|' read -r path branch; do
  git merge-base --is-ancestor "$branch" origin/main || { echo "SKIP not merged: $branch"; continue; }
  git worktree remove --force "$path" && git branch -D "$branch"
done <<'LIST'
/home/mike-anderson/dev/cohezion/.worktrees/cohezion-agent-1787958482|agent-1787958482
/home/mike-anderson/dev/cohezion/.claude/worktrees/cosmogony-state-45bef2|claude/cosmogony-state-45bef2
/home/mike-anderson/dev/cohezion/.claude/worktrees/fervent-allen-5f2209|claude/fervent-allen-5f2209
/home/mike-anderson/dev/cohezion/.claude/worktrees/kaggle-token-efficient-bd1eca|claude/kaggle-token-efficient-bd1eca
/home/mike-anderson/dev/cohezion/.claude/worktrees/local-files-google-drive-c6584d|claude/local-files-google-drive-c6584d
/home/mike-anderson/dev/cohezion-services|deploy/services
/home/mike-anderson/dev/cohezion/.worktrees/graph-map|feat/codebase-graph-map
/home/mike-anderson/dev/cohezion/.worktrees/main-health-fix|fix/main-code-health
/home/mike-anderson/dev/cohezion/.claude/worktrees/fancy-cooking-rocket|worktree-fancy-cooking-rocket
/home/mike-anderson/dev/cohezion/.claude/worktrees/fluffy-mapping-pebble|worktree-fluffy-mapping-pebble
/home/mike-anderson/dev/cohezion/.claude/worktrees/glimmering-floating-canyon|worktree-glimmering-floating-canyon
/home/mike-anderson/dev/cohezion/.claude/worktrees/glowing-tinkering-peach|worktree-glowing-tinkering-peach
/home/mike-anderson/dev/cohezion/.claude/worktrees/happy-popping-wand|worktree-happy-popping-wand
/home/mike-anderson/dev/cohezion/.claude/worktrees/snoopy-foraging-kettle|worktree-snoopy-foraging-kettle
/home/mike-anderson/dev/cohezion/.worktrees/cohezion-agent-1788098353|agent-1788098353
/home/mike-anderson/dev/cohezion/.worktrees/cohezion-agent-1788098455|agent-1788098455
/home/mike-anderson/dev/cohezion/.worktrees/cohezion-agent-1788098546|agent-1788098546
/home/mike-anderson/dev/cohezion/.claude/worktrees/capabilities-exploration-9e9a8d|claude/capabilities-exploration-9e9a8d
/home/mike-anderson/dev/cohezion/.claude/worktrees/consolidate-work-into-main-27b73e|claude/consolidate-work-into-main-27b73e
/home/mike-anderson/dev/cohezion/.claude/worktrees/virtual-soaring-shamir|worktree-virtual-soaring-shamir
LIST
git worktree prune   # also clears the 2 dangling registrations
git branch --merged origin/main | grep -vcE 'main|^\*'   # expect 8 (the B3 set)
```

B3 stays until someone applies or discards each harvested patch (`git apply`
`~/vaults/cohezion-vault/reports/worktree-harvest-20261022/<branch>/unstaged.patch` on a fresh
branch off main, run the tests, land or drop). The two large ones, `worktree-bright-swinging-squirrel`
and `feat/inference-service-mesh`, overlap the 2026-08-31 harvest campaign and should be checked
against `reports/worktree-harvest-20260831/` before any effort is spent.

---

## C. Needs a look — 75 unmerged local branches not held by any worktree

Unmerged into `origin/main`. Many show 51–53 "unique" commits only because they were cut from a
pre-squash base; others carry 1–12 genuine commits. **Not deletion candidates until each is
either landed or judged obsolete.** Suggested triage: anything from `verify-*` /
`automerge-integ-*` / `agent-*` families is a landing scaffold whose content is on main or
in the matching `land/*` branch; the `fix/*` and `feat/*` rows need a reviewer.

| Branch | Last commit | Commits not on main |
|---|---|---|
| `feat/durable-run-reattach` | 2026-08-19 | 4 |
| `provenance-gate-landing` | 2026-08-22 | 1 |
| `reconcile/vss-plan` | 2026-08-26 | 2 |
| `pr/skills-capability-repair` | 2026-08-27 | 8 |
| `skills-capability-repair` | 2026-08-27 | 31 |
| `feat/silicon-residency-24x7` | 2026-08-29 | 52 |
| `feat/silicon-residency-on-main` | 2026-08-29 | 1 |
| `fix/anthropic-model-pricing-refresh` | 2026-08-30 | 1 |
| `fix/proxy-phantom-haiku-model-id` | 2026-08-30 | 1 |
| `fix/revive-mypy-gate` | 2026-08-30 | 1 |
| `integration/three-fixes` | 2026-08-30 | 1 |
| `feat/ifbench-benchmark-harness` | 2026-09-02 | 53 |
| `feat/model-scout-hf-mem-fit` | 2026-09-02 | 10 |
| `fix/autodqa-skill-health-wiring` | 2026-09-02 | 53 |
| `fix/circuit-registry-split-guard` | 2026-09-02 | 53 |
| `fix/h5-subprocess-sandbox` | 2026-09-02 | 53 |
| `fix/unified-hybrid-router-local-first-routing` | 2026-09-03 | 52 |
| `squishy-brewing-creek-landed` | 2026-09-03 | 52 |
| `fix/aimo-test-collection-error` | 2026-09-04 | 52 |
| `fix/arc-transforms-and-semantic-cache-tests` | 2026-09-04 | 52 |
| `fix/cross-session-event-persistence` | 2026-09-04 | 6 |
| `fix/data-mesh-eval-flux-physics-wiring` | 2026-09-04 | 52 |
| `fix/degradation-detector-and-health-oracle-tests` | 2026-09-04 | 52 |
| `fix/inference-suite-remaining-failures` | 2026-09-04 | 52 |
| `fix/physics-endpoint-contract-complete` | 2026-09-04 | 52 |
| `fix/rate-limiter-hourly-window` | 2026-09-04 | 1 |
| `fix/resource-guard-floor-enforcement` | 2026-09-04 | 52 |
| `fix/semantic-cache-hash-false-hits` | 2026-09-04 | 1 |
| `fix/stt-residency-probe` | 2026-09-04 | 2 |
| `verify-1788472213` | 2026-09-04 | 2 |
| `verify-agent-1788472386` | 2026-09-04 | 3 |
| `verify-cross-session-event-persistence` | 2026-09-04 | 6 |
| `verify-provenance-gate` | 2026-09-04 | 1 |
| `doctor/context-cleanup` | 2026-09-05 | 12 |
| `feat/trace-goal-loop-closure` | 2026-09-05 | 2 |
| `feat/trace-goal-loop-pipeline` | 2026-09-05 | 1 |
| `fix/loopception-depth4-contract` | 2026-09-05 | 2 |
| `fix/physics-extended-deduplicate-triplication` | 2026-09-05 | 1 |
| `trace-goals-refactor-landed` | 2026-09-05 | 52 |
| `verify-aimo-test-collection-error` | 2026-09-05 | 1 |
| `verify-arc-transforms-and-semantic-cache-tests` | 2026-09-05 | 1 |
| `verify-eval-flux-wiring` | 2026-09-05 | 1 |
| `verify-physics-endpoint-contract-complete` | 2026-09-05 | 1 |
| `verify-resource-guard-floor-enforcement` | 2026-09-05 | 1 |
| `automerge-integ-295` | 2026-09-09 | 3 |
| `feat/kaggle-autoharness-and-storyboards` | 2026-09-09 | 73 |
| `security/codeql-hardening` | 2026-09-09 | 2 |
| `agent-1789063968` | 2026-09-10 | 6 |
| `agent-1789153240` | 2026-09-10 | 7 |
| `agent-1789153364` | 2026-09-10 | 7 |
| `agent-1789153991` | 2026-09-10 | 7 |
| `security/codeql-wave2-ci` | 2026-09-10 | 1 |
| `security/wave3-landing` | 2026-09-11 | 7 |
| `automerge-integ-302` | 2026-09-12 | 16 |
| `automerge-integ-303` | 2026-09-12 | 19 |
| `automerge-integ-304` | 2026-09-12 | 3 |
| `automerge-integ-305` | 2026-09-12 | 2 |
| `automerge-integ-306` | 2026-09-12 | 2 |
| `automerge-integ-307` | 2026-09-12 | 2 |
| `feat/map-wam-trace-goal-refactor` | 2026-09-12 | 2 |
| `feat/perpetual-loop-map-wam-memory` | 2026-09-12 | 1 |
| `fix/h5-exec-gate-consolidation` | 2026-09-14 | 2 |
| `fix/config-event-bus-reconciled` | 2026-09-18 | 12 |
| `land/codegraph-20260918` | 2026-09-18 | 1 |
| `land/fix-set-20260918` | 2026-09-18 | 22 |
| `land/pricing-5-1-20260918` | 2026-09-18 | 1 |
| `land/stale-base-set-20260918` | 2026-09-18 | 2 |
| `land/tgl-graph-20260918` | 2026-09-18 | 5 |
| `land/verify-set-20260918` | 2026-09-18 | 9 |
| `land/verify-set-20260918-r2` | 2026-09-18 | 9 |
| `land/verify-set-20260918-r3` | 2026-09-18 | 9 |
| `land/wave2-misc-20260918` | 2026-09-18 | 6 |
| `research/jlens-local-replication` | 2026-09-18 | 5 |
| `fix/prepush-refuse-main` | 2026-10-06 | 2 |
| `chore/portfolio-coherence` | 2026-10-22 | 4 |

Command when a row is judged obsolete (force-delete, because it is unmerged): `git branch -D <branch>`.

---

## D. Remote branches already contained in origin/main — 76

Their tips are ancestors of `origin/main`, so nothing is lost by deleting the ref; PR history
stays on GitHub. This is a push, so it is a user decision. Includes the `session-4x/5x`
series from the February–March deployment sprints and `backup/local-main-2026-06-04`.

<details><summary>List</summary>


- `origin/backup/local-main-2026-06-04`
- `origin/challenge-luma-cqq4mojz`
- `origin/chore/quarter-on-a-string-enforce`
- `origin/ci/drop-unresolvable-semantic-release`
- `origin/claude/fix-code-antipatterns-qa9Gn`
- `origin/claude/novel-agent-metrics-h4gNT`
- `origin/epic1-land`
- `origin/exp/scienceide-mini-loop-20260919`
- `origin/feat/compound-elegant-simplification`
- `origin/feat/cosmic-fire-wired`
- `origin/feat/datamesh-endorse-gapminer`
- `origin/feat/datamesh-event-consumer`
- `origin/feat/declared-field-scan`
- `origin/feat/genesis-tdd-a2ui`
- `origin/feat/honest-graders`
- `origin/feat/honest-graders-2`
- `origin/feat/knowledge-corpus-retrieval`
- `origin/feat/lemonade-inference-gaps`
- `origin/feat/lemond-admission-gate`
- `origin/feat/lineage-scan-and-action-writer`
- `origin/feat/local-adversarial-review`
- `origin/feat/mcp-compound`
- `origin/feat/model-residency-service`
- `origin/feat/moe-logit-updates-hiho-kernel`
- `origin/feat/research-source-control`
- `origin/feat/spawned-lineage-edge`
- `origin/feat/trajectory-fields-persisted`
- `origin/feat/work-queue-actioner`
- `origin/feature/2026-tip-of-the-spear`
- `origin/feature/nemotron-reasoning-20260322`
- `origin/feature/repository-management-workflow`
- `origin/fix/adversarial-gate-local-first`
- `origin/fix/checked-sql-writers-batch1`
- `origin/fix/coherence-polarity`
- `origin/fix/coherence-sweep-and-semver-governance`
- `origin/fix/compound-suite-hermeticity`
- `origin/fix/f2-phase1-guard`
- `origin/fix/genesis-journey-table`
- `origin/fix/geometric-regime-honest-latent`
- `origin/fix/mutation-ratchet-muttest-twin`
- `origin/fix/mypy-ratchet-h5-20260919`
- `origin/fix/oom-relief-loop-and-byte-aware-topology`
- `origin/fix/preexisting-card-cache`
- `origin/fix/repo-health-enforcement`
- `origin/fix/restore-harness-invariants`
- `origin/fix/work-queue-silent-data-loss`
- `origin/gemm-hip-cpp-fused`
- `origin/isolated/session-oom-modularity`
- `origin/land/codegraph-rebased`
- `origin/land/false-success-fixes-20260919`
- `origin/land/h5-arc-proposer-20260919`
- `origin/land/h5-exec-gate-20260918`
- `origin/land/harness-drift-fix`
- `origin/land/ikettle-20260709`
- `origin/land/kaggle-mcp-tools`
- `origin/land/skills-capability-repair`
- `origin/reconcile/worktree-kazoo`
- `origin/refactor/embeddable-lemonade-apps`
- `origin/session--DEPLOYMENT`
- `origin/session-43-fastmcp-fix`
- `origin/session-47-documentation-consolidation`
- `origin/session-47-phase-2-security`
- `origin/session-48-test-fixes`
- `origin/session-49-TLS-CERT-FIX`
- `origin/session-49-test-fixes`
- `origin/session-49-test-isolation-fixes`
- `origin/session-49-tls-cert-fix`
- `origin/session-51-DEPLOYMENT-FINAL`
- `origin/session-53-config-orchestration`
- `origin/session-53-final-production-security`
- `origin/session-54-test-fixes`
- `origin/session-55-test-fixes`
- `origin/session-repo-health-automation`
- `origin/spec/genesis-engine`
- `origin/worktree-genesis-engine`
- `origin/worktree-wondrous-conjuring-ember`

</details>

```bash
# one push, run only after reviewing the list
git push origin --delete backup/local-main-2026-06-04 challenge-luma-cqq4mojz chore/quarter-on-a-string-enforce ci/drop-unresolvable-semantic-release claude/fix-code-antipatterns-qa9Gn claude/novel-agent-metrics-h4gNT epic1-land exp/scienceide-mini-loop-20260919 feat/compound-elegant-simplification feat/cosmic-fire-wired feat/datamesh-endorse-gapminer feat/datamesh-event-consumer feat/declared-field-scan feat/genesis-tdd-a2ui feat/honest-graders feat/honest-graders-2 feat/knowledge-corpus-retrieval feat/lemonade-inference-gaps feat/lemond-admission-gate feat/lineage-scan-and-action-writer feat/local-adversarial-review feat/mcp-compound feat/model-residency-service feat/moe-logit-updates-hiho-kernel feat/research-source-control feat/spawned-lineage-edge feat/trajectory-fields-persisted feat/work-queue-actioner feature/2026-tip-of-the-spear feature/nemotron-reasoning-20260322 feature/repository-management-workflow fix/adversarial-gate-local-first fix/checked-sql-writers-batch1 fix/coherence-polarity fix/coherence-sweep-and-semver-governance fix/compound-suite-hermeticity fix/f2-phase1-guard fix/genesis-journey-table fix/geometric-regime-honest-latent fix/mutation-ratchet-muttest-twin fix/mypy-ratchet-h5-20260919 fix/oom-relief-loop-and-byte-aware-topology fix/preexisting-card-cache fix/repo-health-enforcement fix/restore-harness-invariants fix/work-queue-silent-data-loss gemm-hip-cpp-fused isolated/session-oom-modularity land/codegraph-rebased land/false-success-fixes-20260919 land/h5-arc-proposer-20260919 land/h5-exec-gate-20260918 land/harness-drift-fix land/ikettle-20260709 land/kaggle-mcp-tools land/skills-capability-repair reconcile/worktree-kazoo refactor/embeddable-lemonade-apps session--DEPLOYMENT session-43-fastmcp-fix session-47-documentation-consolidation session-47-phase-2-security session-48-test-fixes session-49-TLS-CERT-FIX session-49-test-fixes session-49-test-isolation-fixes session-49-tls-cert-fix session-51-DEPLOYMENT-FINAL session-53-config-orchestration session-53-final-production-security session-54-test-fixes session-55-test-fixes session-repo-health-automation spec/genesis-engine worktree-genesis-engine worktree-wondrous-conjuring-ember
```

---

## E. Primary checkout — restore the nine deleted dotfiles, then move it back to main

The deletions are real on disk, not a mount artifact: `ls .gitignore` fails from a host shell.
With `.gitignore` gone, 687 files show as untracked and every ignore-based tool misreads the
tree. Restoring tracked files from the index loses nothing:

```bash
cd /home/mike-anderson/dev/cohezion
git checkout -- .gitignore .gitattributes .pre-commit-config.yaml .secrets.baseline \
  .git-blame-ignore-revs .worktreeinclude .antigravity.md .autoresearch-off .env.sheets-research.example
```

The checkout is also on `security/codeql-wave2` with 131 modified tracked files. Whether that
work is finished is a question for whoever owns it; when it is landed or parked on its branch,
the primary checkout should return to `main` (`git switch main && git pull --ff-only`) and all
branch work should happen in worktrees or shared clones, so the audit's numbers describe the
repository rather than a stale branch.

---

## Execution record

- **2026-10-22, section A executed** (user approved A only): all 25 branches deleted; local
  branches 186 → 162; `git branch --merged origin/main` now lists only the 28 worktree-pinned
  branches. Two things learned in the doing:
  - `git branch -d` judges "merged" against the branch's **own upstream** when one is set, not
    against `origin/main`, so 4 of the 25 were refused by `-d` although `git merge-base
    --is-ancestor <b> origin/main` held. They were deleted with `-D` **after** re-running that
    ancestor check per branch. Use the same pair (verify, then `-D`) for sections B and C.
  - `.git/config` could not be locked from this session (with or without the sandbox); git
    warned but the ref deletions went through, and the stale `branch.<name>.*` section count
    was 105 before and after, so today's deletions left none behind. The pre-existing 105 are a
    separate cleanup from a normal shell:
    `git config --get-regexp '^branch\..*\.remote$' | sed -E 's/^branch\.(.*)\.remote .*/\1/' | while read b; do git show-ref -q --verify refs/heads/$b || git config --remove-section branch.$b; done`
- **2026-10-22, section E executed** (user approved): the nine dotfiles restored from the index.
  A stale zero-byte `.git/index.lock` dated 2026-09-21 (no git process holding it) blocked the
  checkout and was removed first. Result: `git status` deleted 9 → 0, untracked 687 → 89,
  modified 131 unchanged. The primary checkout is still on `security/codeql-wave2`; moving it
  back to `main` remains with that branch's owner.
- **2026-10-22, section D executed** (user approved): after a fresh `git fetch --prune`, the
  set of remote branches that are strict ancestors of `origin/main` was recomputed (still 76,
  none from the active coherence stack) and deleted in four pushes of ≤20. Remote branches
  309 → 233; zero of the 76 remain. Merged PR history is unaffected on GitHub.
- **2026-10-22, section B inspected and harvested** (user approved B): 14 clean, 6 trivial, 8 with real work; all 28 worktrees' diffs and untracked files saved to the vault harvest folder. Removal itself is blocked for agent sessions by the read-only `.git/worktrees` mount; the exact script is in B.
- **2026-10-22 (later), section B executed from the user's Terminal panel** (host shell, outside the
  agent namespace, with the user's explicit permission grant): the B1 + B2 script ran as written.
  20 worktrees removed, 20 branches deleted, `git worktree prune` cleared the 2 dangling registrations.
  Worktrees 87 → 65; local branches 162 → 142; `git branch --merged origin/main` now lists exactly
  the 8 B3 branches. Also found and removed a stale `.git/config.lock` dated 2026-09-26 (zero bytes,
  no process), which is why every config write had failed for a month; 107 stale `branch.*`
  sections then cleared (9 remain, all for live branches).
- Section C: not executed (needs per-branch review). B3 (8 worktrees with real work) untouched.

## Verification after each approved section

- A: `git branch --merged origin/main | grep -vcE 'main|^\*'` → 28
- B: `git worktree list | wc -l` falls by the number removed; `git worktree list --porcelain | grep -c prunable` → 0
- D: `git branch -r | wc -l` → 308 − deleted
- E: `git status --porcelain | grep -c '^ D'` → 0 and `git status --porcelain | grep -c '^??'` drops from 687
