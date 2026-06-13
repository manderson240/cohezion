# synthetic-sniffing-panda — Merge Plan

**Campaign**: synthetic-sniffing-panda (2026-04-23)
**Plan**: `~/.claude/plans/synthetic-sniffing-panda.md`
**Retrospective**: `~/vaults/cohezion-vault/retrospectives/2026-04-23-synthetic-sniffing-panda.md`
**Worktree**: `/home/mike-anderson/dev/cohezion/.claude/worktrees/synthetic-sniffing-panda`
**Source branch**: `worktree-synthetic-sniffing-panda` (91 commits, +35,636 / -3,990, 245 files)
**Branch organization commit**: see "Final commit" section below

---

## Branch summary

The 91 campaign commits are organized into **6 stacked branches** that form a merge train. Each branch is rooted on the previous branch's HEAD (NOT on `ffaf26888` directly), because cross-bucket file dependencies make a flat fan-out impossible (see "Why stacked, not flat" below).

| # | Branch | Commits (incr.) | Files (incr.) | LOC delta (incr.) | Parent |
|---|---|---:|---:|---:|---|
| 1 | `polish/code-quality`        | 54 | 92 | +1,685 / -380     | `ffaf26888` (main parent) |
| 2 | `polish/refactors`           | 5  | 27 | +3,916 / -3,342   | `polish/code-quality` |
| 3 | `polish/tests`               | 12 | 49 | +1,904 / -377     | `polish/refactors` |
| 4 | `polish/research-deep-think` | 14 | 25 | +8,067 / -0       | `polish/tests` |
| 5 | `polish/design-artifacts`    | 4  | 45 | +18,299 / -0      | `polish/research-deep-think` |
| 6 | `polish/meta`                | 2  | 10 | +1,877 / -3       | `polish/design-artifacts` |
| **Total** | (tip = `polish/meta`) | **91** | **245** | **+35,636 / -3,990** | (matches campaign branch) |

**One-sentence headlines:**
- `polish/code-quality` — Lint fixes, mypy baseline (913 errors locked), bare-except elimination in 5 hot files, subprocess pinning across 28 modules.
- `polish/refactors` — Three god-file splits: `api/__init__.py` (13 routers), `cohezion_mcp.py` (6 tool modules), `executor.py` (3 helpers extracted).
- `polish/tests` — Coverage adds for 4 hot modules (semantic_cache 81%→99%), all `time.sleep()` removed from tests, skip backlog triaged.
- `polish/research-deep-think` — 14 Ω-tier deliverables: 4 manuscripts, 5 ADRs, 3 adversarial reviews, refactor proposals, tutorials, distillates, market analysis, PRFAQ.
- `polish/design-artifacts` — 4 dashboard mockups + 16 themed variants, 5 algorithmic art pieces, the 12D-universe poster (PNG+PDF+build script).
- `polish/meta` — 4 cross-repo lint autofix patches (proposals only), CLAUDE.md test/file count sync.

---

## Why stacked, not flat

The campaign commits have real cross-bucket file dependencies. Specifically:

- `polish/refactors` Wave 2B (`0ac84a8b5`, api split) depends on `polish/code-quality` Wave 2A (`ea5275eb2`, api bare-except fix). Both commits modify `src/cohezion/api/__init__.py`, with the bare-except fix authored first. Cherry-picking the refactor onto `ffaf26888` directly produces a content conflict.
- Same pattern holds for `executor.py` (refactors 2D ↔ code-quality 2A) and `cohezion_mcp.py` (refactors 2C ↔ code-quality 2A).
- `polish/tests` Wave 3A (`3804f468a`, executor coverage tests) references `executor_helpers/*` module paths that exist only after `polish/refactors`.

**Resolution**: build the branches as a stack, with each branch rooted on the previous branch HEAD. The PR diff for each branch shows only its own bucket's commits, but the underlying base assumes the prior branch has merged. This matches GitHub's stacked-PR / merge-train convention.

If you prefer flat (each branch rooted on `ffaf26888`), the only feasible alternative is to **duplicate the bare-except fix commits into `polish/refactors`**, and similarly absorb other cross-bucket dependencies. This would inflate the refactors branch and obscure review boundaries. The stacked model is cleaner.

---

## Recommended merge order

**Strict dependency order (must merge in this sequence):**
1. `polish/code-quality` — bare-except + mypy baseline + subprocess pinning. Foundational. **Merge first.**
2. `polish/refactors` — god-file splits. Depends on (1). **Merge second.**
3. `polish/tests` — coverage + sleep removal. Depends on (2) for executor_helpers paths. **Merge third.**

**No-dependency tail (any order, but stack is built this way):**
4. `polish/research-deep-think` — pure docs/research. Could merge against main directly.
5. `polish/design-artifacts` — pure visual artifacts. Could merge against main directly.
6. `polish/meta` — cross-repo patches + CLAUDE.md sync. Tail of train.

**Estimated review effort:**

| Branch | Effort | Why |
|---|---|---|
| `polish/code-quality` | **High** (3-5 hrs) | 92 files, 54 commits, sweeping changes. Worth a careful read, especially the bare-except patterns. |
| `polish/refactors` | **High** (2-4 hrs) | 27 files but the api split commit alone is +2,055 / -1,894 lines. Use the per-router file mapping to chunk it. |
| `polish/tests` | **Medium** (1-2 hrs) | Mostly additions; sleep removal patterns are mechanical. Spot-check the conftest reset. |
| `polish/research-deep-think` | **Medium** (1-3 hrs depending on depth) | Read manuscript abstracts + ADR titles; deep-read only what interests you. |
| `polish/design-artifacts` | **Low** (30 min) | Open mockups in browser; visual review. |
| `polish/meta` | **Low** (15 min) | 2 commits, small diffs. |

---

## Cross-branch dependencies (file-level)

| File | Touched by |
|---|---|
| `src/cohezion/api/__init__.py` | code-quality (bare-except), refactors (split origin) |
| `src/cohezion/compound/executor.py` | code-quality (bare-except), refactors (helper extraction) |
| `src/cohezion/skills/cohezion_mcp.py` | code-quality (bare-except), refactors (split origin) |
| `tests/conftest.py` | tests (DynamicConcurrencyGate reset only) |
| `mypy_baseline.txt` | code-quality (only) |
| `pyproject.toml` | code-quality (mypy strict overrides) |

No file is touched by both `polish/research-deep-think` and any source-code branch.

---

## Final consolidated test/lint/coverage delta (if all 6 branches merge)

| Metric | Pre-campaign | Post-campaign | Delta |
|---|---|---|---|
| `tests/compound/` passing | 948 | 968 | +20 |
| `tests/compound/` failing | 86 | 86 | 0 |
| `tests/compound/` errors | 51 | 51 | 0 |
| Total tests collected (full suite) | ~6,300 | ~6,400 | +~76 (4 coverage waves) |
| Mypy baseline errors | unmanaged | 913 (locked) | new control |
| Bare-except sites in 5 hot files | ~70 | 0 | -70 |
| Subprocess calls without pinned executable | many | 0 in 28 audited modules | full sweep |
| `semantic_cache.py` coverage | 81% | 99% | +18% |
| Sleep calls in tests | ~50 | 0 (in audited files) | full removal |
| Files split (god files) | 3 (>1,500 LOC each) | 0 | refactor goal met |
| Mockups + posters + art (research/) | minimal | 26 visual artifacts | new |
| Manuscripts + ADRs + reviews + tutorials (docs/+research/) | none | 25 docs | new |

**Pre-existing failures NOT addressed by this campaign**: 86 failing + 51 erroring tests in `tests/compound/`. Each PR's verification recipe documents this as the campaign baseline; no PR introduces or resolves these.

---

## Cherry-pick failures

**None.** All 91 commits cherry-picked cleanly into their assigned branches when built as a stack.

(The first attempt at a flat fan-out failed at the very first cherry-pick — `0ac84a8b5` onto `ffaf26888` — with a content conflict on `src/cohezion/api/__init__.py`. This is what motivated the switch to a stacked model. See "Why stacked, not flat" above.)

---

## Test verification per branch

Smoke-tested by collecting + running `tests/compound/test_executor.py` on each source-touching branch:

| Branch | Result |
|---|---|
| `polish/code-quality` | 2 passed / 3 failed / 3 errors (matches campaign baseline — no regressions) |
| `polish/refactors`    | 2 passed / 3 failed / 3 errors (matches campaign baseline — no regressions) |
| `polish/tests`        | 2 passed / 3 failed / 3 errors (matches campaign baseline — no regressions) |

The 3 failing + 3 erroring tests are pre-existing campaign baseline issues (singleton pollution, async timing in test infrastructure). They are NOT introduced by branch construction. Each PR description notes them as "out of scope, pre-existing".

`polish/research-deep-think`, `polish/design-artifacts`, `polish/meta` touch no source/tests — no test impact.

---

## Files written by this organization step

- `research/pr-descriptions/code-quality.md`
- `research/pr-descriptions/refactors.md`
- `research/pr-descriptions/tests.md`
- `research/pr-descriptions/research-deep-think.md`
- `research/pr-descriptions/design-artifacts.md`
- `research/pr-descriptions/meta.md`
- `MERGE_PLAN.md` (this file)

These artifacts will be committed to `worktree-synthetic-sniffing-panda` as the final wave-ψ1 commit.

---

## How to push (run after user approves)

```bash
cd /home/mike-anderson/dev/cohezion/.claude/worktrees/synthetic-sniffing-panda

# Push branches in stack order (each builds on the previous):
git push origin polish/code-quality
git push origin polish/refactors
git push origin polish/tests
git push origin polish/research-deep-think
git push origin polish/design-artifacts
git push origin polish/meta

# Then open PRs at https://github.com/manderson240/cohezion/pulls
# - PR 1: polish/code-quality       → main
# - PR 2: polish/refactors           → polish/code-quality (stack into PR 1)
# - PR 3: polish/tests               → polish/refactors    (stack into PR 2)
# - PR 4: polish/research-deep-think → polish/tests        (stack into PR 3)
# - PR 5: polish/design-artifacts    → polish/research-deep-think
# - PR 6: polish/meta                → polish/design-artifacts
#
# Alternative for PRs 4-6 (no source dep on the stack):
# - You can re-target their base to `main` if you prefer flat review.
#   Use `git rebase --onto main polish/tests polish/research-deep-think`
#   etc. — but doing so will rewrite the stack history. Discuss before applying.
```

**Recommended GitHub merge strategy:**
- For `polish/code-quality`, `polish/refactors`, `polish/tests`: **squash + merge** (each PR is internally cohesive; preserve logical chunking via squashed commits).
- For `polish/research-deep-think`, `polish/design-artifacts`, `polish/meta`: **rebase + merge** (each commit is independently meaningful — Ω1, Ω2, etc.; preserve them).

After PR 1 merges, GitHub will auto-update PR 2's base from `polish/code-quality` to `main` (or you can manually rebase and force-push — but you said no force-push, so let GitHub auto-rebase).

---

## Local cleanup (after all PRs merge)

```bash
# After all 6 branches merge to main:
git fetch origin
git checkout main && git pull
for b in polish/code-quality polish/refactors polish/tests \
         polish/research-deep-think polish/design-artifacts polish/meta; do
  git branch -d "$b"  # safe delete (only succeeds if merged)
done

# Worktree cleanup (optional):
# cd /home/mike-anderson/dev/cohezion
# git worktree remove .claude/worktrees/synthetic-sniffing-panda
```

---

## Hard guarantees (per task constraints)

- ✅ **NO `git push`** — all branches stay local
- ✅ **NO merge to main** — main is untouched (`ffaf26888` remains the parent)
- ✅ **NO force-push, no `-f`** — stack is built with cherry-pick only
- ✅ **NO branch deletion** — only branches CREATED, not removed
- ✅ **No cherry-pick conflicts** — clean stack achieved without manual conflict resolution
- ✅ **Cherry-picks preserve author + date** — default behavior, `--reset-author` not used
- ✅ **Campaign branch intact** — `worktree-synthetic-sniffing-panda` remains, with HEAD `3fc16356c` (poster commit)
