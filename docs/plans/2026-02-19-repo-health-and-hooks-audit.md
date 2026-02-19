# Repository Health & Hooks Audit Implementation Plan

Created: 2026-02-19
Status: PENDING
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)

## Summary

**Goal:** Fix auto-merge availability by aligning GitHub required status checks with actual CI job names, register the guard-services Claude hook, consolidate duplicate CI workflows, and clean up orphaned GitHub Actions workflows.

**Architecture:** The fix is primarily configuration changes: updating the GitHub ruleset's required status checks to match actual CI job names, registering the existing guard-services.sh hook in Claude settings, and consolidating the duplicate `lint.yml`/`test.yml` workflows (whose jobs already exist in `ci.yml`).

**Tech Stack:** GitHub Actions, GitHub rulesets API (`gh api`), Claude Code hooks (`.claude/settings.json`)

## Scope

### In Scope

- Fix ruleset required status checks to match actual CI job names
- Remove nonexistent `commit-lint` required check (or add a commit-lint job)
- Fix `test` required check → `test (3.11)` / `test (3.13)` matrix naming
- Register `guard-services.sh` as a PreToolUse[Bash] hook in `.claude/settings.json`
- Remove duplicate `lint.yml` and `test.yml` workflows (jobs already exist in `ci.yml`)
- Disable orphaned GitHub Actions workflows (`claude-code-review`, `claude`, `deploy-portfolio`, `phase-4a-tests`)
- Fix CI `continue-on-error: true` on lint steps that should fail the build

### Out of Scope

- Adding new CI jobs or features
- Changing the CI pipeline architecture
- Modifying pre-commit hooks
- Branch protection migration from rulesets to legacy API
- Fixing test failures in the test suite itself

## Prerequisites

- GitHub CLI (`gh`) authenticated with repo admin permissions
- Write access to `.claude/settings.json`

## Context for Implementer

- **Patterns to follow:** The existing `.claude/settings.json` hook registration pattern at `.claude/settings.json:47-57` (PreToolUse matcher)
- **Conventions:** GitHub rulesets are used (not legacy branch protection). Update via `gh api` PATCH calls.
- **Key files:**
  - `.claude/settings.json` - Claude Code hook registration
  - `.claude/hooks/guard-services.sh` - Bash guard hook (exists but unregistered)
  - `.github/workflows/ci.yml` - Primary CI pipeline (lint, validate, test, compound, typecheck, ci-status)
  - `.github/workflows/lint.yml` - Duplicate lint workflow (to remove)
  - `.github/workflows/test.yml` - Duplicate test workflow (to remove)
  - `.github/workflows/repo-health.yml` - Repo health check (keep as-is)
- **Existing hooks examined (no issues found):** SessionStart, SessionEnd, UserPromptSubmit, Stop, PreToolUse[Task], PostToolUse[Task], PostToolUse[TodoWrite] — all use `entire hooks claude-code <event>` commands which are provided by the Entire CLI and are working correctly.
- **Gotchas:**
  - Auto-merge DOES work with rulesets (not just legacy branch protection). The issue is the required status check names don't match actual CI job names.
  - The `test` job uses a matrix strategy producing `test (3.11)` and `test (3.13)` - the ruleset requires plain `test` which never matches.
  - `commit-lint` is required in the ruleset but no workflow produces that status check.
  - `lint.yml` and `test.yml` are older duplicates of jobs already in `ci.yml`. They cause duplicate runs on every PR.
  - 4 workflows are orphaned on GitHub (files deleted from repo but workflows still active).
  - `ci.yml` lint steps use `continue-on-error: true` which means lint failures never block PRs.

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [ ] Task 1: Fix GitHub ruleset required status checks
- [ ] Task 2: Register guard-services.sh hook in Claude settings
- [ ] Task 3: Remove duplicate CI workflows
- [ ] Task 4: Fix CI lint steps continue-on-error
- [ ] Task 5: Disable orphaned GitHub Actions workflows
- [ ] Task 6: Add conventional commit lint job to CI

**Total Tasks:** 6 | **Completed:** 0 | **Remaining:** 6

## Implementation Tasks

### Task 1: Fix GitHub Ruleset Required Status Checks

**Objective:** Update the `main-protection` ruleset (ID 12910460) so required status check names match actual CI job names. This is the root cause of auto-merge being unavailable.

**Dependencies:** None

**Files:**
- No file changes (API calls only)

**Key Decisions / Notes:**
- **First, verify ruleset ID:** Run `gh api repos/manderson240/cohezion/rulesets --jq '.[].id'` to confirm ID 12910460 before patching
- Current required checks: `lint`, `validate`, `test`, `ci-status`, `commit-lint`
- Actual CI job names: `lint`, `validate`, `test (3.11)`, `test (3.13)`, `ci-status`, `compound`, `typecheck`, `check-repo-health`
- `test` must be replaced with `test (3.11)` and `test (3.13)` (or just keep `ci-status` which already gates on test results)
- Keep `commit-lint` in required checks — Task 6 will add the matching CI job
- The `ci-status` summary job already checks lint, validate, and test results, so it's the most reliable gate
- Use `gh api` PATCH to update the ruleset

**Definition of Done:**
- [ ] Ruleset required status checks match actual CI job names
- [ ] `gh api repos/manderson240/cohezion/rulesets/12910460` shows updated check names
- [ ] A test PR can have auto-merge enabled (verified by checking `gh pr merge --auto --squash` works)

**Verify:**
- `gh api repos/manderson240/cohezion/rulesets/12910460 --jq '.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context'` — shows correct check names

### Task 2: Register guard-services.sh Hook in Claude Settings

**Objective:** The `guard-services.sh` file exists at `.claude/hooks/guard-services.sh` but is not registered in `.claude/settings.json`. Register it as a PreToolUse[Bash] hook so it actually runs.

**Dependencies:** None

**Files:**
- Modify: `.claude/settings.json`

**Key Decisions / Notes:**
- Add a PreToolUse entry with `"matcher": "Bash"` that runs `bash .claude/hooks/guard-services.sh`
- The hook reads JSON from stdin (tool input), extracts the `command` field, and checks for dangerous patterns
- Must use absolute or relative path that works from the project root
- Existing PreToolUse hooks use the `entire hooks` command pattern; this is a direct bash script

**Definition of Done:**
- [ ] `.claude/settings.json` has a PreToolUse entry for Bash commands that invokes `guard-services.sh`
- [ ] Hook is correctly formatted to receive JSON on stdin and return exit codes (0=allow, 2=block)

**Verify:**
- `python3 -c "import json; d=json.load(open('.claude/settings.json')); hooks=[h for h in d['hooks'].get('PreToolUse',[]) if h.get('matcher')=='Bash']; print('Found' if hooks else 'Missing')"` — prints "Found"

### Task 3: Remove Duplicate CI Workflows

**Objective:** Remove `lint.yml` and `test.yml` which duplicate jobs already in `ci.yml`. These cause double CI runs on every PR.

**Dependencies:** Task 1 (ruleset must not require check names from these workflows)

**Files:**
- Delete: `.github/workflows/lint.yml`
- Delete: `.github/workflows/test.yml`

**Key Decisions / Notes:**
- `ci.yml` already has `lint`, `validate`, `test`, `compound`, `typecheck`, and `ci-status` jobs
- `lint.yml` duplicates the lint job with slightly different config (Python 3.11 vs 3.13, uses pip instead of uv)
- `test.yml` duplicates the test job and adds `test-markers` which is unused
- After deletion, the `lint.yml` workflow will remain "active" on GitHub until its next trigger finds no file — this is normal

**Definition of Done:**
- [ ] `.github/workflows/lint.yml` deleted from repo
- [ ] `.github/workflows/test.yml` deleted from repo
- [ ] `ci.yml` still contains all necessary lint and test jobs

**Verify:**
- `test ! -f .github/workflows/lint.yml && test ! -f .github/workflows/test.yml && echo "Deleted"` — confirms both files are absent
- `grep -c "lint:" .github/workflows/ci.yml` — confirms lint job exists in ci.yml

### Task 4: Fix CI Lint Steps continue-on-error

**Objective:** Remove `continue-on-error: true` from lint steps in `ci.yml` so lint failures actually block PRs.

**Dependencies:** None

**Files:**
- Modify: `.github/workflows/ci.yml`

**Key Decisions / Notes:**
- Lines 31 and 35 in `ci.yml` have `continue-on-error: true` on ruff format and ruff lint steps
- This means lint failures are silently ignored — PRs merge with lint errors
- The `ci-status` job checks `needs.lint.result` but lint never fails due to continue-on-error
- Remove continue-on-error from lint steps to enforce code quality
- Keep `continue-on-error: true` on integration tests (line 108) since those may have external dependencies
- Keep `continue-on-error: true` on compound audit (line 147) and typecheck (line 175) since those are advisory

**Definition of Done:**
- [ ] `ci.yml` lint job ruff format step has no `continue-on-error`
- [ ] `ci.yml` lint job ruff check step has no `continue-on-error`
- [ ] Integration tests and advisory jobs still have `continue-on-error: true`

**Verify:**
- `grep -A1 "Ruff format check" .github/workflows/ci.yml` — no continue-on-error
- `grep -A1 "Ruff lint check" .github/workflows/ci.yml` — no continue-on-error
- `grep "continue-on-error" .github/workflows/ci.yml` — only on integration tests, compound, typecheck

### Task 5: Disable Orphaned GitHub Actions Workflows

**Objective:** Disable 4 GitHub Actions workflows whose files were deleted from the repo but remain active on GitHub.

**Dependencies:** None

**Files:**
- No file changes (API calls only)

**Key Decisions / Notes:**
- Orphaned workflows: `claude-code-review.yml`, `claude.yml`, `deploy-portfolio.yml`, `phase-4a-tests.yml`
- These can be disabled via `gh api -X PUT repos/manderson240/cohezion/actions/workflows/{id}/disable`
- Workflow IDs: 235553117, 235554666, 234748740, 234594952

**Definition of Done:**
- [ ] All 4 orphaned workflows show state `disabled_manually` via GitHub API
- [ ] No ghost workflow runs appear on future PRs

**Verify:**
- `gh api repos/manderson240/cohezion/actions/workflows --jq '.workflows[] | select(.state != "active") | .name'` — lists the 4 disabled workflows

### Task 6: Add Conventional Commit Lint Job to CI

**Objective:** Add a `commit-lint` job to `ci.yml` that validates PR titles follow conventional commit format, matching the required status check in the ruleset.

**Dependencies:** Task 1 (Task 1 keeps `commit-lint` in the ruleset; this task adds the matching CI job)

**Files:**
- Modify: `.github/workflows/ci.yml`

**Key Decisions / Notes:**
- **Decision: Option B — add the commit-lint job.** The git-workflow rules already require conventional commits (`feat:`, `fix:`, etc.), so enforcing this in CI aligns with existing standards.
- Use `amannn/action-semantic-pull-request` GitHub Action to validate PR title format
- The job checks PR titles only (not individual commits) since squash merge is the only allowed merge method
- Job name must be exactly `commit-lint` to match the ruleset
- Only runs on `pull_request` events (not pushes to main)

**Definition of Done:**
- [ ] `ci.yml` has a `commit-lint` job that checks PR title format
- [ ] Job name is exactly `commit-lint` in CI output
- [ ] PR titles like `feat: add feature` pass; titles like `added feature` fail

**Verify:**
- `grep "commit-lint:" .github/workflows/ci.yml` — job exists
- `gh api repos/manderson240/cohezion/rulesets/12910460 --jq '.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context'` — includes `commit-lint`

## Testing Strategy

- **Unit tests:** No code tests needed — this is infrastructure/configuration
- **Integration tests:** Verify via GitHub API that ruleset checks match CI job names
- **Manual verification:** Create a test PR, confirm auto-merge can be enabled, confirm CI status checks all report correctly

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Removing lint.yml/test.yml breaks existing PR checks | Low | Medium | Verify ci.yml already has equivalent jobs before deletion |
| Updating ruleset locks out PRs if check names wrong | Medium | High | Test with `gh api` GET before PATCH; verify check names match exactly against latest CI run |
| commit-lint job blocks existing PRs with non-conventional titles | Medium | Low | Make commit-lint check PR title only (squash merge), not individual commits |
| Guard-services hook blocks legitimate commands | Low | Low | Hook only blocks specific dangerous patterns (Restart=always without StartLimitBurst, systemctl mask without service name); all other commands pass through |

## Open Questions

- None at this time — all decisions can be made during implementation.
