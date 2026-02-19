# Autonomous Repository Management Implementation Plan

Created: 2026-02-17
Status: VERIFIED
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)

## Summary

**Goal:** Implement end-to-end autonomous repository management so that /spec workflows and manual development flow autonomously from feature branch through PR creation, CI validation, and merge to main — with proper versioning, changelog, and release automation.

**Architecture:** GitHub Flow (unchanged) with enforced quality gates via GitHub Rulesets, consolidated CI pipeline, squash-merge-only strategy, auto-merge on green CI, and release-please for automated versioning/changelog. The `/spec-verify` skill gains a new Step 3.12b that auto-creates PRs with auto-merge enabled after VERIFIED status.

**Tech Stack:** GitHub Actions, GitHub Rulesets API, `gh` CLI, release-please-action v4, conventional commits (enforced via ruff + CI check)

## Scope

### In Scope

- GitHub repo settings: squash-only merge, auto-merge, delete-branch-on-merge (via `gh repo edit`)
- GitHub Ruleset on `main`: required status checks, no direct push, no force push
- CI consolidation: delete `test.yml` and `lint.yml` (duplicates of ci.yml jobs), keep `repo-health.yml` separate (scheduled weekly maintenance), add `release.yml` — result: 3 workflow files total, but only 2 active PR pipelines (ci.yml + release.yml)
- UV dependency caching in CI
- release-please workflow for automated versioning + CHANGELOG.md
- Conventional commit validation in CI (Python-based, no Node dependency)
- Updated PR template with checklist
- `/spec-verify` Step 3.12b: auto-create PR after VERIFIED, enable auto-merge
- Setup script (`scripts/admin/setup_repo.sh`) for one-time repo configuration via `gh` CLI

### Out of Scope

- Dependabot/Renovate (separate concern, add later)
- CodeQL/Trivy security scanning (separate concern)
- Commit signing verification (requires GPG setup per-developer)
- Merge queue (requires branch protection or rulesets to be active first — can enable after this lands)
- GitHub Actions for auto-labeling or stale PR management

## Prerequisites

- `gh` CLI authenticated with admin access (verified: `viewerPermission: ADMIN`)
- GitHub Actions enabled on the repository (verified: workflows exist)
- Existing CI scripts in `scripts/ci/` (verified: 4 scripts exist)

## Context for Implementer

- **Patterns to follow:** Existing CI workflows in `.github/workflows/ci.yml` for job structure. Pre-commit config in `.pre-commit-config.yaml` for hook patterns.
- **Conventions:** Conventional commits (`feat:`, `fix:`, etc.) already documented in `.claude/rules/git-workflow.md` but not enforced in CI.
- **Key files:**
  - `.github/workflows/ci.yml` — main CI pipeline (keep, rewrite)
  - `.github/workflows/test.yml` — duplicate of ci.yml test job (delete)
  - `.github/workflows/lint.yml` — duplicate of ci.yml lint job (delete)
  - `.github/workflows/repo-health.yml` — weekly health check (keep separate, it has a schedule trigger)
  - `.github/PULL_REQUEST_TEMPLATE.md` — minimal, needs expansion
  - `pyproject.toml` — version is `1.0.0`, release-please will manage it
  - `.claude/commands/spec-verify.md` — Step 3.12 is where PR creation integrates
- **Gotchas:**
  - `tests/unit/` exists but ci.yml references it separately from `tests/` — the consolidated pipeline should run the full suite
  - `continue-on-error: true` on lint/typecheck/compound jobs means they currently never block merges
  - `cloud-vault-mcp/` is a separate sub-project with its own tests — keep it in CI
  - release-please `python` type expects `setup.py` or `setup.cfg` — for pyproject.toml-only projects, use `simple` type with `extra-files` to bump version in pyproject.toml
  - No PAT secret exists yet for release-please — `GITHUB_TOKEN` works but won't trigger downstream workflows

## Runtime Environment

- **Start command:** `uv run uvicorn cohezion.api:app --reload`
- **Port:** 8080
- **Health check:** `curl http://localhost:8080/health`
- **CI is serverless:** GitHub Actions — no deploy step needed for CI changes

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete.**

- [ ] Task 1: Configure GitHub repo settings via gh CLI
- [ ] Task 2: Consolidate CI workflows
- [ ] Task 3: Add UV caching to CI
- [ ] Task 4: Add conventional commit check to CI
- [ ] Task 5: Add release-please workflow
- [ ] Task 6: Create GitHub Ruleset on main
- [ ] Task 7: Update PR template
- [ ] Task 8: Add PR auto-creation to /spec-verify
- [ ] Task 9: Create setup script for repo configuration

**Total Tasks:** 9 | **Completed:** 0 | **Remaining:** 9

## Implementation Tasks

### Task 1: Configure GitHub Repo Settings

**Objective:** Set squash-merge-only, enable auto-merge, enable delete-branch-on-merge via `gh repo edit`.

**Dependencies:** None

**Files:**
- Create: `scripts/admin/setup_repo.sh` (idempotent setup script)

**Key Decisions / Notes:**
- Use `gh repo edit` with flags: `--enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false --enable-auto-merge --delete-branch-on-merge`
- Script is idempotent — safe to re-run
- This is a one-time setup but capturing in a script ensures reproducibility

**Definition of Done:**
- [ ] `gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,deleteBranchOnMerge` shows `{squashMergeAllowed:true, mergeCommitAllowed:false, rebaseMergeAllowed:false, deleteBranchOnMerge:true}`
- [ ] `gh api repos/manderson240/cohezion --jq '.allow_auto_merge'` returns `true`

**Verify:**
- `bash scripts/admin/setup_repo.sh` runs without error
- `gh repo view manderson240/cohezion --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,deleteBranchOnMerge`

---

### Task 2: Consolidate CI Workflows

**Objective:** Merge `ci.yml`, `test.yml`, and `lint.yml` into a single `ci.yml`. Remove `continue-on-error: true` from lint and validate jobs so they actually block merges. Keep `repo-health.yml` separate (has schedule trigger).

**Dependencies:** None

**Files:**
- Modify: `.github/workflows/ci.yml` (rewrite)
- Delete: `.github/workflows/test.yml`
- Delete: `.github/workflows/lint.yml`
- Modify: `.github/workflows/repo-health.yml` (remove `push` and `pull_request` triggers, keep only `schedule` + `workflow_dispatch`; uv caching in Task 3)

**Key Decisions / Notes:**
- Jobs: `lint` (ruff format + ruff check — MUST pass), `validate` (agent/skill/registry validation — MUST pass), `test` (pytest on Python 3.13 only — `requires-python >= 3.13` makes 3.11 invalid; MUST pass), `typecheck` (mypy — advisory, keep `continue-on-error`), `compound` (audit — advisory, keep `continue-on-error`)
- `ci-status` summary job: only gates on lint + validate + test (the three required checks)
- Cloud-vault-mcp tests stay in the pipeline (install + test as separate step in test job)
- Trigger: `push` to `main` + `pull_request` to `main` + `merge_group` (for future merge queue)
- Use `actions/setup-python@v5` (latest) and `astral-sh/setup-uv@v4` for proper uv caching

**Definition of Done:**
- [ ] Only `ci.yml` and `repo-health.yml` exist in `.github/workflows/` (release.yml is added later in Task 5)
- [ ] `lint` job fails if ruff finds errors (no `continue-on-error`)
- [ ] `validate` job fails if agent/skill validation fails (no `continue-on-error`)
- [ ] `test` job runs on Python 3.13 (single version — `requires-python >= 3.13` makes 3.11 testing invalid)
- [ ] `ci-status` summary job gates on lint + validate + test
- [ ] `merge_group` trigger is present for future merge queue support
- [ ] Test job includes a cloud-vault-mcp install and test step (separate from the main cohezion pytest suite)
- [ ] `repo-health.yml` only triggers on `schedule` and `workflow_dispatch` (no `push` or `pull_request`)

**Verify:**
- `ls .github/workflows/` shows only `ci.yml` and `repo-health.yml`
- `grep -c 'continue-on-error' .github/workflows/ci.yml` — only in typecheck and compound jobs
- `grep 'cloud-vault-mcp' .github/workflows/ci.yml` returns at least one match

---

### Task 3: Add UV Caching to CI

**Objective:** Use `astral-sh/setup-uv@v4` action with built-in caching to speed up CI installs from ~30s to ~3s.

**Dependencies:** Task 2

**Files:**
- Modify: `.github/workflows/ci.yml` (replace `pip install uv` + `uv sync` with `astral-sh/setup-uv@v4`)
- Modify: `.github/workflows/repo-health.yml` (no Python needed — pure bash, skip)

**Key Decisions / Notes:**
- `astral-sh/setup-uv@v4` includes built-in caching with `enable-cache: true`
- Replaces manual `pip install uv` and `uv sync --frozen` steps
- Cache key based on `uv.lock` file hash (automatic)

**Definition of Done:**
- [ ] CI uses `astral-sh/setup-uv@v4` with `enable-cache: true`
- [ ] No `pip install uv` commands remain in ci.yml
- [ ] `uv sync --frozen` used for reproducible installs

**Verify:**
- `grep 'astral-sh/setup-uv' .github/workflows/ci.yml` returns matches
- `grep 'pip install uv' .github/workflows/ci.yml` returns no matches

---

### Task 4: Add Conventional Commit Check to CI

**Objective:** Validate that PR titles follow conventional commit format (`feat:`, `fix:`, `refactor:`, etc.) since GitHub squash-merge uses the PR title as the commit message.

**Dependencies:** Task 2

**Files:**
- Create: `scripts/ci/check_pr_title.py` (pure Python, no Node dependencies)
- Modify: `.github/workflows/ci.yml` (add `commit-lint` job)

**Key Decisions / Notes:**
- Since we're using squash merge, the PR TITLE becomes the commit message — validate that, not individual commits
- Pure Python script using regex — no commitlint/Node dependency needed
- Pattern: `^(feat|fix|refactor|test|docs|chore|perf|ci|build|style|revert)(\(.+\))?!?: .+`
- Job only runs on `pull_request` events (not `push` or `merge_group`)
- Uses `${{ github.event.pull_request.title }}` as input

**Definition of Done:**
- [ ] `scripts/ci/check_pr_title.py` validates conventional commit format
- [ ] CI job `commit-lint` runs on PRs and fails if title doesn't match
- [ ] Script accepts valid titles: `feat: add auth`, `fix(api): handle null`, `refactor!: break API`
- [ ] Script rejects invalid titles: `Add auth`, `fixed bug`, `WIP`

**Verify:**
- `echo "feat: add feature" | uv run python scripts/ci/check_pr_title.py` exits 0
- `echo "bad title" | uv run python scripts/ci/check_pr_title.py` exits 1

---

### Task 5: Add release-please Workflow

**Objective:** Add release-please GitHub Action that auto-creates release PRs with version bumps and CHANGELOG.md based on conventional commits merged to main.

**Dependencies:** Task 4 (conventional commits must be enforced first)

**Files:**
- Create: `.github/workflows/release.yml`
- Create: `release-please-config.json`
- Create: `.release-please-manifest.json`
- Create: `CHANGELOG.md` (empty initial file)

**Key Decisions / Notes:**
- Use manifest config (advanced) for explicit control over Python versioning
- `release-please-config.json` exact content: `{"packages": {".": {"release-type": "simple", "extra-files": [{"type": "toml", "path": "pyproject.toml", "jsonpath": "$.project.version"}]}}}`
- `.release-please-manifest.json`: `{".": "1.0.0"}` (current version)
- **Prerequisite:** Create a PAT (Personal Access Token) with `repo` + `workflow` scopes, stored as repo secret `RELEASE_PLEASE_TOKEN`. Without this, release PRs won't trigger CI, required status checks never appear, and auto-merge waits forever. Use `token: ${{ secrets.RELEASE_PLEASE_TOKEN }}` in release.yml. (GITHUB_TOKEN cannot trigger downstream workflow runs on auto-created PRs — this is a GitHub platform limitation, not a nice-to-have.)
- If PAT is not yet available at implementation time: use `secrets.GITHUB_TOKEN` temporarily with a prominent `TODO` comment, and add "Create PAT for release-please" as a follow-up item
- Workflow triggers on `push` to `main` only
- Outputs `release_created` and `tag_name` for potential post-release steps

**Definition of Done:**
- [ ] `.github/workflows/release.yml` exists with release-please-action v4
- [ ] `release-please-config.json` configured for Python with pyproject.toml version bump
- [ ] `.release-please-manifest.json` has current version `1.0.0`
- [ ] `CHANGELOG.md` exists (empty or with initial entry)

**Verify:**
- `cat release-please-config.json | python -m json.tool` — valid JSON
- `cat .release-please-manifest.json | python -m json.tool` — valid JSON with version
- `ls .github/workflows/release.yml` — file exists

---

### Task 6: Create GitHub Ruleset on Main

**Objective:** Create a GitHub Ruleset that protects `main` with required status checks, no direct push, no force push, and no branch deletion.

**Dependencies:** Task 2 (CI job names must be finalized), Task 4 (commit-lint job name must be finalized)

**Files:**
- Modify: `scripts/admin/setup_repo.sh` (add ruleset creation via `gh api`)

**Key Decisions / Notes:**
- Use GitHub Rulesets API (modern replacement for branch protection rules, recommended as of 2025)
- Ruleset name: `main-protection`
- Rules: `pull_request` (require PR before merge), `required_status_checks` (lint, validate, test, ci-status, commit-lint), `non_fast_forward` (no force push), `deletion` (no branch deletion)
- Bypass actors: repository admin (owner) — allows emergency direct pushes
- Created via `gh api repos/{owner}/{repo}/rulesets --method POST` with JSON body
- Script checks if ruleset already exists before creating (idempotent)

**Definition of Done:**
- [ ] `gh api repos/manderson240/cohezion/rulesets` returns a ruleset named `main-protection`
- [ ] Ruleset requires `lint`, `validate`, `test`, `ci-status`, `commit-lint` status checks
- [ ] Ruleset blocks direct push to main (requires PR)
- [ ] Ruleset blocks force push to main
- [ ] Admin bypass is configured for emergency use

**Verify:**
- `gh api repos/manderson240/cohezion/rulesets --jq '.[].name'` returns `main-protection`
- `bash scripts/admin/setup_repo.sh` is idempotent (running twice doesn't error)

---

### Task 7: Update PR Template

**Objective:** Replace the minimal PR template with a comprehensive checklist that matches the project's workflow.

**Dependencies:** None

**Files:**
- Modify: `.github/PULL_REQUEST_TEMPLATE.md`

**Key Decisions / Notes:**
- Sections: Summary (auto-filled by /spec), Change Type (dropdown), Testing (checklist), Checklist (pre-merge verification)
- Include conventional commit reminder for PR title
- Reference plan file if applicable
- Keep it concise — don't over-template

**Definition of Done:**
- [ ] PR template has Summary, Change Type, Testing, and Checklist sections
- [ ] Template includes conventional commit format reminder
- [ ] Template is under 40 lines

**Verify:**
- `wc -l .github/PULL_REQUEST_TEMPLATE.md` — under 40 lines
- `cat .github/PULL_REQUEST_TEMPLATE.md` — readable and complete

---

### Task 8: Add PR Auto-Creation to /spec-verify

**Objective:** After `/spec-verify` sets plan status to VERIFIED, automatically push the worktree branch and create a PR with auto-merge enabled — BEFORE worktree sync. The PR auto-merge replaces the manual worktree sync as the merge mechanism.

**Dependencies:** Task 1 (auto-merge must be enabled), Task 6 (rulesets must exist for auto-merge to work)

**Files:**
- Modify: `~/.claude/commands/spec-verify.md` (add Step 3.11a BEFORE Step 3.11b worktree sync)

**Key Decisions / Notes:**
- **CRITICAL:** PR must be created BEFORE `pilot worktree sync`, because sync squash-merges to main and deletes the feature branch. After sync, there's no branch to create a PR from.
- New Step 3.11a runs AFTER VERIFIED status is set but BEFORE worktree sync prompt (Step 3.11b)
- Flow: VERIFIED → push `spec/<slug>` branch → `gh pr create` → `gh pr merge --auto --squash` → skip manual worktree sync (PR auto-merge handles it) → `pilot worktree cleanup` (branch auto-deleted by GitHub after merge)
- When auto-PR is enabled, Step 3.11b (worktree sync prompt) is SKIPPED — the PR auto-merge IS the sync mechanism
- PR title derives commit type from plan content: check for keywords in plan slug or add a `Commit-Type:` field to plan headers. Default: `feat:` for new features, `fix:` for bug fixes, `refactor:` for refactors, `chore:` for maintenance
- PR title format: `<type>: <plan-slug-with-hyphens-to-spaces>` (e.g., `feat: autonomous repo management`)
- PR body: plan Summary section + completed tasks list
- Skip if PR already exists for the branch (idempotent)
- Only runs when `Worktree: Yes` and a feature branch exists

**Definition of Done:**
- [ ] spec-verify.md has Step 3.11a that creates PR before worktree sync
- [ ] PR is created with conventional commit title (type derived from plan context)
- [ ] Auto-merge is enabled via `gh pr merge --auto --squash`
- [ ] Step 3.11b (worktree sync) is skipped when auto-PR is created
- [ ] Step is skipped if no feature branch or PR already exists

**Verify:**
- `grep '3.11a' ~/.claude/commands/spec-verify.md` — step exists
- `grep 'gh pr create' ~/.claude/commands/spec-verify.md` — PR creation command present
- `grep 'gh pr merge --auto' ~/.claude/commands/spec-verify.md` — auto-merge command present

---

### Task 9: Create Repo Setup Script

**Objective:** Consolidate all one-time repo configuration into a single idempotent setup script that can be run to bootstrap or verify repo settings.

**Dependencies:** Task 1, Task 6

**Files:**
- Modify: `scripts/admin/setup_repo.sh` (finalize with all configuration)

**Key Decisions / Notes:**
- Script combines: repo settings (Task 1) + ruleset creation (Task 6)
- Idempotent: checks current state before making changes
- Includes verification output at the end (shows current settings)
- Can be run by any admin to verify/restore repo configuration
- Add to `Makefile` as `repo-setup` target

**Definition of Done:**
- [ ] `scripts/admin/setup_repo.sh` configures all repo settings and rulesets
- [ ] Script is idempotent (safe to re-run)
- [ ] Script outputs verification summary
- [ ] `make repo-setup` target exists in Makefile

**Verify:**
- `bash scripts/admin/setup_repo.sh` — completes without error
- `make repo-setup` — runs the setup script

## Testing Strategy

- **Unit tests:** `scripts/ci/check_pr_title.py` — test with valid/invalid PR title inputs
- **Integration tests:** Push the CI changes to a branch, create a test PR, verify CI runs and checks pass
- **Manual verification:**
  1. Run `scripts/admin/setup_repo.sh` and verify repo settings via `gh repo view`
  2. Create a PR with a non-conventional title, verify CI fails
  3. Create a PR with a conventional title, verify CI passes
  4. After merge to main, verify release-please creates a release PR

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Existing PRs break with squash-only | Low | Medium | No open PRs currently; apply after merging current `spec/routes-consolidation` branch |
| CI job names change and break ruleset | Medium | Medium | Ruleset references explicit job names from consolidated ci.yml; document the mapping in setup script comments |
| release-please GITHUB_TOKEN can't trigger CI on release PRs | High | High | **Mitigated:** Use PAT (`RELEASE_PLEASE_TOKEN`) with `repo` + `workflow` scopes. Without PAT, required checks never fire on release PRs and auto-merge waits forever. If PAT unavailable at implementation time, use GITHUB_TOKEN with TODO and document as blocker for release automation. |
| Removing continue-on-error reveals existing lint/type errors | High | Low | Known: mypy and compound audit have existing issues. Keep `continue-on-error` on those two advisory jobs only |

## Open Questions

- None — task description was comprehensive and exploration confirmed feasibility.

### Deferred Ideas

- **Merge queue:** Enable after rulesets are in place and CI is stable. Requires `merge_group` trigger (added in Task 2) but ruleset config is separate.
- **Dependabot/Renovate:** Automated dependency updates — separate concern, add after core pipeline is stable.
- **CodeQL scanning:** Security analysis — add as an advisory CI job in a future iteration.
- **PAT for release-please:** Now a prerequisite (see Task 5). If not available at implementation time, use GITHUB_TOKEN with TODO comment.
