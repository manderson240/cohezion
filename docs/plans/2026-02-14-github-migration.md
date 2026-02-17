# GitHub Migration Implementation Plan

Created: 2026-02-14
Status: VERIFIED
Approved: Yes
Iterations: 1
Worktree: Yes

> **Status Lifecycle:** PENDING -> COMPLETE -> VERIFIED
> **Iterations:** Tracks implement->verify cycles (incremented by verify phase)
>
> - PENDING: Initial state, awaiting implementation
> - COMPLETE: All tasks implemented
> - VERIFIED: All checks passed
>
> **Approval Gate:** Implementation CANNOT proceed until `Approved: Yes`
> **Worktree:** Set at plan creation (from dispatcher). `Yes` uses git worktree isolation; `No` works directly on current branch

## Summary

**Goal:** Transition from dual GitLab/GitHub setup to GitHub-only with GitHub Flow branching. Enable Claude.ai/code to create branches and PRs by making `main` the GitHub default branch with local main fully synced.

**Architecture:** GitHub Flow — `main` is the single default branch, feature branches for all work, PRs merge back to `main`. Remove all GitLab artifacts, remote, and CI config. Clean up stale local branches and orphaned worktrees after backing everything up to GitHub.

**Tech Stack:** Git, GitHub API (via `gh` CLI), GitHub Actions (already in place)

## Scope

### In Scope

- Back up divergent origin/main commits to a branch on GitHub
- Force-push local `main` to GitHub `origin/main`
- Change GitHub default branch from `feature/repository-management-workflow` to `main`
- Remove `gitlab` remote from local git config
- Delete GitLab CI files (`.gitlab-ci.yml`, `.gitlab-ci-old.yml`, `.gitlab-ci.yml.deprecated`)
- Remove `GitLabRunnerConfig` class and references in source code
- Update `.claude/rules/git-workflow.md` to reference GitHub (not GitLab)
- Push all local branches to GitHub as backup, then delete stale local branches
- Remove all stale worktrees (dynamic discovery, not hardcoded list)
- Delete stale remote branches on GitHub (old `claude/*`, `master`, etc.)
- Install `gh` CLI (mandatory for this workflow)
- Set `main` to track `origin/main`
- Remove nested `cohezion-session-54/` directory inside main repo

### Out of Scope

- GitHub Actions workflow content changes (already migrated in Session 57)
- Repository content changes (no code refactoring beyond GitLab removal)
- GitHub branch protection rules (can be configured later via GitHub UI)
- CI/CD pipeline improvements
- Root-level SESSION_*.md historical docs (contain GitLab refs but are historical records)

## Prerequisites

- SSH access to `git@github.com:manderson240/cohezion.git` (verified in Task 1)
- Permission to force-push to GitHub (owner of repo)
- No other sessions actively pushing to GitHub during migration

## Context for Implementer

> This section is critical for cross-session continuity.

- **Current state:** Two remotes exist — `origin` (GitHub, `git@github.com:manderson240/cohezion.git`) and `gitlab` (local GitLab, `http://localhost:8929/root/cohezion.git`). GitHub's default branch is incorrectly set to `feature/repository-management-workflow` (24 commits, stale Cloud Claude branch). Local `main` has 427 commits ahead of `origin/main`, and `origin/main` has 7 divergent commits.
- **Key constraint:** Nothing should be lost. All branches get pushed to GitHub before local deletion.
- **Branching model:** GitHub Flow — `main` only, no `develop`. Feature branches + PRs.
- **GitLab artifacts to remove:**
  - Files: `.gitlab-ci.yml` (tracked in HEAD but deleted on disk), `.gitlab-ci-old.yml`, `.gitlab-ci.yml.deprecated`
  - Code: `GitLabRunnerConfig` class in `src/cohezion/concurrency/shared_resources.py:292-349`, its export in `__init__.py:17,27`, references in `README.md`
  - Config: `gitlab` remote, `.claude/rules/git-workflow.md` line 19 referencing localhost:8929
  - Docs: GitLab references in `src/cohezion/knowledge_graph/MISSION_JOURNAL.md:37`, `src/cohezion/concurrency/file_lock.py:6`
- **Nested directory:** `cohezion-session-54/` exists inside the main repo (not a sibling worktree). Must be removed.
- **Worktrees:** Use dynamic discovery (`git worktree list` + `ls -d ~/dev/cohezion-*`). Known: `cohezion-session-57`, `cohezion-session-58`, `cohezion-session-59`, `cohezion-track-b`, but there may be more orphaned directories.
- **Stale local branches:** 52 total — 29 `session-*`, 4 `entire/*`, 6 `feature/*`, 3 `fix/*`, plus misc. All get pushed to GitHub then deleted locally.
- **Stale remote branches:** `origin/master`, `origin/develop`, `origin/feature/*`, `origin/entire/*`, `origin/claude/*`, `origin/0-2-implement-squad-review`
- **GitHub Actions:** Already in place at `.github/workflows/{ci.yml, lint.yml, test.yml, repo-health.yml}`. Some reference `develop` or `master` branches — must update to `main` only.
- **Gotchas:** The `ci.yml` workflow triggers on `push: branches: [main, develop]`. Must update to `[main]` only since we're dropping `develop`.

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [x] Task 1: Install gh CLI and back up divergent commits
- [x] Task 2: Sync local main to GitHub
- [x] Task 3: Remove GitLab remote and CI files
- [x] Task 4: Remove GitLabRunnerConfig and update source references
- [x] Task 5: Update project rules and workflow configs
- [x] Task 6: Back up and clean up stale branches and worktrees
- [x] Task 7: Clean up stale remote branches on GitHub

**Total Tasks:** 7 | **Completed:** 7 | **Remaining:** 0

## Implementation Tasks

### Task 1: Install gh CLI and back up divergent commits

**Objective:** Install the GitHub CLI tool, verify SSH auth, and preserve the 7 divergent commits on `origin/main` before force-pushing.

**Dependencies:** None

**Files:**

- No file changes

**Key Decisions / Notes:**

- Install `gh` via system package manager. gh is **mandatory** — Tasks 2 and 7 require it. If installation fails, STOP and resolve before proceeding.
- Verify SSH authentication works before any push operations
- Create backup branch `backup/origin-main-pre-migration` on GitHub from current `origin/main`
- Verify backup exists with `git ls-remote`

**Definition of Done:**

- [ ] `gh --version` returns a valid version
- [ ] `gh auth status` shows authenticated
- [ ] SSH auth verified: `ssh -T git@github.com` shows successful authentication
- [ ] Backup branch `backup/origin-main-pre-migration` exists on GitHub pointing to current `origin/main` HEAD (`01194cb2936c`)
- [ ] Verified with `git ls-remote origin refs/heads/backup/origin-main-pre-migration`

**Verify:**

- `gh --version`
- `gh auth status`
- `ssh -T git@github.com 2>&1 | grep -i authenticated`
- `git ls-remote origin refs/heads/backup/origin-main-pre-migration`

### Task 2: Sync local main to GitHub

**Objective:** Force-push local `main` to `origin/main`, set `main` as GitHub default branch, and configure tracking.

**Dependencies:** Task 1

**Files:**

- No file changes (git operations only)

**Key Decisions / Notes:**

- Force push local `main` to `origin/main` (overwrites 7 divergent commits, backed up in Task 1)
- **After force-push, immediately verify SHA match:** compare `git ls-remote origin refs/heads/main` output with `git rev-parse main`. If SHAs don't match, push failed — do NOT proceed.
- Use `gh api` to change GitHub default branch: `gh api repos/manderson240/cohezion -X PATCH -f default_branch=main`
- If default branch change fails, retry up to 3 times. If still fails, change via GitHub web UI: Settings > Branches > Default branch > select `main`.
- Set local `main` to track `origin/main` with `git branch --set-upstream-to=origin/main main`
- Verify with `git ls-remote --symref origin HEAD`

**Definition of Done:**

- [ ] `origin/main` matches local `main` HEAD (SHA verified after push)
- [ ] GitHub default branch is `main` (verified via `git ls-remote --symref origin HEAD`)
- [ ] Local `main` tracks `origin/main` (`git rev-parse --abbrev-ref main@{upstream}` returns `origin/main`)

**Verify:**

- `git ls-remote origin refs/heads/main` — shows local main's SHA
- `git ls-remote --symref origin HEAD` — shows `ref: refs/heads/main`
- `git rev-parse --abbrev-ref main@{upstream}` — returns `origin/main`

### Task 3: Remove GitLab remote and CI files

**Objective:** Remove the `gitlab` remote and delete all GitLab CI configuration files from the repo.

**Dependencies:** Task 2

**Files:**

- Delete: `.gitlab-ci-old.yml`
- Delete: `.gitlab-ci.yml.deprecated`
- Delete: `.gitlab-ci.yml` (already deleted on disk, need `git rm`)

**Key Decisions / Notes:**

- `git remote remove gitlab` removes the remote
- `git rm .gitlab-ci.yml .gitlab-ci-old.yml .gitlab-ci.yml.deprecated` removes tracked files
- **Commit strategy:** Each task commits independently for clear history and easy rollback

**Definition of Done:**

- [ ] `git remote -v` shows only `origin` (GitHub)
- [ ] No `.gitlab-ci*` files in working tree or git index
- [ ] `git ls-files .gitlab-ci*` returns empty

**Verify:**

- `git remote -v` — only origin
- `git ls-files '*gitlab*'` — empty
- `ls .gitlab-ci* 2>/dev/null` — no files

### Task 4: Remove GitLabRunnerConfig and update source references

**Objective:** Remove the deprecated `GitLabRunnerConfig` class, all GitLab references in source code, and the nested `cohezion-session-54/` directory.

**Dependencies:** Task 3

**Files:**

- Modify: `tests/concurrency/test_shared_resources.py` — Remove tests for `GitLabRunnerConfig` **FIRST**
- Modify: `src/cohezion/concurrency/shared_resources.py` — Remove `GitLabRunnerConfig` class (lines 292-349+)
- Modify: `src/cohezion/concurrency/__init__.py` — Remove `GitLabRunnerConfig` from imports and `__all__`
- Modify: `src/cohezion/concurrency/file_lock.py` — Update comment on line 6 (remove gitlab-runner reference)
- Modify: `src/cohezion/knowledge_graph/MISSION_JOURNAL.md` — Update line 37 (remove GitLab CE reference)
- Modify: `README.md` — Remove any `GitLabRunnerConfig` references
- Delete: `cohezion-session-54/` — nested stale worktree copy

**Key Decisions / Notes:**

- **Order of operations:** (1) Remove tests for GitLabRunnerConfig FIRST, (2) verify remaining tests pass, (3) THEN remove the class and its exports. This prevents ImportError failures.
- The class is already deprecated (Session 57) — this completes the removal
- Follow existing code patterns — check what else is in `shared_resources.py` and `__init__.py` to ensure clean removal
- `file_lock.py` line 6 is just a comment; update it to remove the gitlab-runner example
- Root-level SESSION_*.md files with GitLab references are historical docs — leave them as-is
- Also remove the `cohezion-session-54/` nested directory inside the main repo (stale worktree copy, not a registered worktree)

**Definition of Done:**

- [ ] Tests for GitLabRunnerConfig removed BEFORE class deletion
- [ ] No `GitLabRunnerConfig` class in source code
- [ ] No `GitLabRunnerConfig` in any `__init__.py` exports
- [ ] `grep -r "GitLabRunner" src/ tests/` returns empty
- [ ] `grep -r "localhost:8929" src/ .claude/` returns empty
- [ ] Tests pass: `uv run pytest tests/concurrency/ -q`
- [ ] `cohezion-session-54/` nested directory removed

**Verify:**

- `uv run pytest tests/concurrency/ -q` — tests pass
- `grep -r "GitLabRunner" src/ tests/` — no matches
- `grep -r "localhost:8929" src/ .claude/` — no matches
- `ls -d cohezion-session-54 2>/dev/null` — no directory

### Task 5: Update project rules and workflow configs

**Objective:** Update `.claude/rules/git-workflow.md` to reference GitHub instead of GitLab, and update GitHub Actions workflows to remove `develop`/`master` branch references (GitHub Flow = `main` only).

**Dependencies:** Task 4

**Files:**

- Modify: `.claude/rules/git-workflow.md` — Change line 19 from GitLab remote to GitHub, add GitHub Flow documentation
- Modify: `.github/workflows/ci.yml` — Remove `develop` from branch triggers (lines 5-7)
- Modify: `.github/workflows/repo-health.yml` — Remove `develop` from branch triggers (line 8)
- Modify: `.github/workflows/lint.yml` — Remove `master` from branch triggers (lines 5-7), keep only `main`
- Modify: `.github/workflows/test.yml` — Remove `master` from branch triggers (lines 5-7), keep only `main`

**Key Decisions / Notes:**

- GitHub Flow: only `main` in workflow triggers
- `lint.yml` and `test.yml` currently reference `[main, master]` — update to just `[main]`
- `ci.yml` and `repo-health.yml` currently reference `[main, develop]` — update to just `[main]`
- `git-workflow.md` line 19 says "Remote: Local GitLab instance" — update to "Remote: GitHub (git@github.com:manderson240/cohezion.git)"
- Add note about GitHub Flow branching model

**Definition of Done:**

- [ ] `.claude/rules/git-workflow.md` references GitHub, not GitLab
- [ ] All workflow yml files trigger only on `main` branch (no `develop`, no `master`)
- [ ] Verified: `grep -A1 "branches:" .github/workflows/*.yml` shows only `[main]` entries

**Verify:**

- `grep -A1 "branches:" .github/workflows/*.yml` — all show only `[main]`
- `grep "gitlab\|localhost:8929" .claude/rules/git-workflow.md` — no matches

### Task 6: Back up and clean up stale branches and worktrees

**Objective:** Push all local branches to GitHub as backup, remove all stale worktrees (dynamic discovery), then delete stale local branches.

**Dependencies:** Task 2

**Files:**

- No source file changes (git operations only)

**Key Decisions / Notes:**

- **Pre-push size check:** Before pushing, check for large files across all branches: `git rev-list --objects --all | git cat-file --batch-check='%(objectsize) %(rest)' | awk '$1 > 52428800 {print $0}' | sort -k1 -nr | head -20`. If files >50MB found, push branches individually to isolate failures.
- Push ALL local branches to GitHub: `git push origin --all`. If push fails for some branches (e.g., large files), push remaining branches individually.
- **Dynamic worktree discovery:** List ALL worktrees with `git worktree list`. Also find ALL `~/dev/cohezion-*` directories (both registered and orphaned). Remove each with `git worktree remove <path>` or `git worktree remove --force <path>`. For orphaned directories not in `git worktree list`, delete with `rm -rf` after verifying no uncommitted work.
- Delete ALL local branches except `main`: every branch listed by `git branch` that isn't `main`.
- Keep `main` only (GitHub Flow). All deleted branches are safely backed up on GitHub.

**Definition of Done:**

- [ ] All branches pushed to GitHub (`git push origin --all` succeeds or all branches pushed individually)
- [ ] `git worktree list` shows only the main worktree
- [ ] `git branch` shows only `main`
- [ ] No orphaned worktree directories exist: `ls -d ~/dev/cohezion-session-* ~/dev/cohezion-track-* ~/dev/cohezion-ci-* 2>/dev/null` returns empty

**Verify:**

- `git worktree list` — single entry for main worktree
- `git branch` — only `* main`
- `ls -d ~/dev/cohezion-session-* ~/dev/cohezion-track-* ~/dev/cohezion-ci-* 2>/dev/null` — no directories

### Task 7: Clean up stale remote branches on GitHub

**Objective:** Delete old/stale remote branches on GitHub that are no longer needed.

**Dependencies:** Task 6

**Files:**

- No source file changes (git operations only)

**Key Decisions / Notes:**

- Before deleting ANY remote branch, check for open PRs: `gh pr list --head <branch> --state open`
- Delete remote branches with no open PRs: `origin/master`, `origin/develop`, all `origin/claude/*`, `origin/feature/*`, `origin/entire/*`, `origin/0-2-implement-squad-review`
- If a branch has an open PR, skip deletion and document it
- Keep `origin/main` (default branch)
- Keep all `origin/session-*` branches (they're backups from Task 6)
- Use `gh api` or `git push origin --delete` to remove branches

**Definition of Done:**

- [ ] Verified no open PRs exist for any branch being deleted
- [ ] `origin/master` branch deleted
- [ ] `origin/develop` branch deleted
- [ ] All `origin/claude/*` branches deleted
- [ ] All stale `origin/feature/*` branches deleted
- [ ] All `origin/entire/*` branches deleted
- [ ] `git branch -r` shows only `origin/main` plus backup/session branches

**Verify:**

- `git fetch --prune origin && git branch -r | grep -v 'origin/main\|origin/session-\|origin/backup'` — should be empty or minimal

## Testing Strategy

- **Unit tests:** `uv run pytest tests/concurrency/ -q` after Task 4 (GitLabRunnerConfig removal)
- **Integration tests:** Full test suite `uv run pytest tests/ -q` after all code changes
- **Manual verification:**
  - Verify GitHub default branch is `main`
  - Verify `git push` from local works without specifying remote
  - Verify Claude.ai/code can create a branch and PR on the repo (user tests by starting a task in Claude.ai/code and confirming branch creation on GitHub)

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Force push loses commits | Low | High | Back up origin/main to `backup/origin-main-pre-migration` branch before force push (Task 1) |
| Branch deletion loses unmerged work | Low | High | Push ALL branches to GitHub before any local deletion (Task 6 starts with `git push origin --all`) |
| GitLabRunnerConfig removal breaks imports | Low | Medium | Remove tests FIRST, verify they pass, THEN remove class. Grep for all references before deleting. |
| gh CLI not available | Low | Low | gh is mandatory — Task 1 must succeed before proceeding. Installation verified before any gh commands. |
| Open PRs reference deleted branches | Low | Medium | Check for open PRs before deleting any remote branch (Task 7) |
| Worktree removal fails (locked files) | Low | Low | Use `git worktree remove --force` if standard removal fails, then manually delete orphaned directories |
| Force-push succeeds but default branch change fails | Low | Medium | Retry `gh api` up to 3 times; if still fails, change via GitHub web UI manually. Verify with `git ls-remote --symref origin HEAD` before proceeding. |
| `git push --all` hits GitHub file size limits | Low | Medium | Pre-check for files >50MB across all branches. If found, push branches individually to isolate failures. |

## Open Questions

- None — all questions resolved during planning.

### Deferred Ideas

- Set up GitHub branch protection rules for `main` (require PR reviews, status checks)
- Configure GitHub Dependabot for dependency updates
- Add GitHub issue templates and PR templates
