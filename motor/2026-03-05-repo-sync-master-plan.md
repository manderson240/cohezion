---
title: "Repo Sync Master Plan — Local/Remote Alignment"
date: "2026-03-05"
status: active
priority: critical
tags: [project, repo-sync, ci, cleanup, infrastructure, semver]
session_id: "agent_session:16276507-e433-41ea-bc4f-494b54cbe1b8"
aspect: doer
neural:
  activation: 0.74
  stage: growing
  synapse_in: 3
  synapse_out: 6
---

## Governing Principles

1. **Non-destructive only.** Nothing gets deleted. Everything was created for a reason. Triage and preserve, never assume something won't contribute.
2. **Vault-first.** All intermediate artifacts stored in Obsidian vault. See [[2026-03-05-vault-first-enforcement-protocol]].
3. **Conventional commits.** All commits follow semver-compatible conventional commit format for automated changelog, versioning, and traceability.

## Objective

Get the Cohezion repository's local and remote state fully synchronized so that:
1. Claude Code on the cloud and in the repo works reliably
2. CI passes on all PRs (no pre-existing failures blocking merges)
3. All branches are cataloged and triaged (not deleted)
4. GC corruption is resolved
5. Commit history makes sense via conventional commits
6. The repo is presentable and maintainable

## Current State (2026-03-05)

| Aspect | Status | Details |
|--------|--------|---------|
| PR #33 | Open, MERGEABLE | 6 commits: BMAD restore + protective measures. 5 CI failures (all pre-existing) |
| Local branch | 6 ahead of origin/main | `fix/restore-bmad-and-critical-infrastructure` |
| Stale branches | 68 local, 66 remote | Significant unique work on many — see [[2026-03-05-branch-inventory]] |
| GC corruption | Broken | `fatal: empty filename in tree entry` blocks `git gc` |
| CI failures | 5 pre-existing | dependency-review, health, test, test(3.13), ci-status |
| node_modules tracked | 7,364 files | In `cohezion-3d-graph-plugin/`, `hyperdim-viz-plugin/` |
| Commit conventions | Inconsistent | Mix of conventional commits, session labels, raw messages |
| _bmad-output/ | Untracked | 20+ planning/implementation artifacts in working tree |

## Phases

### Phase 0: Merge Restoration PR (IMMEDIATE)
- **Goal**: Get BMAD restoration and protective measures into `main`
- **Steps**:
  1. Confirm all CI failures on PR #33 are pre-existing
  2. Merge PR #33 (admin override if needed)
  3. Sync worktree with updated main
- **Vault checkpoint**: `vault_log_decision` with merge result
- **Success**: PR merged, `main` has restoration commits

### Phase 1: Fix GC Corruption
- **Goal**: Restore `git gc` functionality
- **Steps**:
  1. `git fsck --full` to identify corrupt objects
  2. Remove gc.log blocking auto-gc
  3. Fix corrupt tree or work around it
  4. Verify `git gc` completes
- **Vault checkpoint**: `vault_log_experiment` with findings
- **Success**: `git gc` runs without error

### Phase 2: Branch Triage (NON-DESTRUCTIVE)
- **Goal**: Catalog and organize all branches — delete NOTHING
- **Steps**:
  1. Complete branch inventory (see [[2026-03-05-branch-inventory]])
  2. For each branch: identify unique content vs main
  3. Categorize: active-feature, spike, investigation, archive, release
  4. Branches needing investigation → create spike branches
  5. Write vault catalog entry per significant branch
  6. Prune only remote tracking refs for branches that no longer exist on remote
- **Vault checkpoint**: `vault_write` updated inventory
- **Success**: Every branch cataloged, no content lost

### Phase 3: Commit Convention Enforcement
- **Goal**: All future commits follow conventional commit format
- **Format**: `<type>(<scope>): <description>` with semver implications
- **Types and semver mapping**:
  ```
  feat:     → MINOR bump (new feature)
  fix:      → PATCH bump (bug fix)
  perf:     → PATCH bump (performance)
  docs:     → no bump
  test:     → no bump
  refactor: → no bump
  ci:       → no bump
  chore:    → no bump
  build:    → no bump
  style:    → no bump
  revert:   → depends on reverted commit
  BREAKING CHANGE or !: → MAJOR bump
  ```
- **Steps**:
  1. Verify `version_governance.py` validates conventional commits (already done)
  2. Add commitlint or equivalent to pre-commit hooks
  3. Add PR title validation in CI
  4. Document convention in CONTRIBUTING.md
  5. Consider `semantic-release` or `python-semantic-release` for automated versioning
- **Vault checkpoint**: `vault_log_decision` on tooling choice
- **Success**: Non-conventional commits blocked by CI

### Phase 4: Fix Pre-existing CI Failures
- **Goal**: All CI checks pass on `main`
- **Failures to fix**:
  1. `dependency-review` — Enable Dependency Graph in GitHub repo settings
  2. `health` — Fix JSON parse error in repo-health.yml
  3. `test` / `test (3.13)` — Fix `npm ci` failure
  4. `ci-status` — Will auto-fix once others pass
- **Vault checkpoint**: `vault_log_decision` per fix
- **Success**: All checks green on a test PR

### Phase 5: Preserve Untracked Artifacts
- **Goal**: Commit _bmad-output/ and other valuable untracked work
- **Steps**:
  1. Catalog all _bmad-output/ contents (done — see [[2026-03-05-branch-inventory]])
  2. Determine proper home: repo vs vault vs dedicated branch
  3. Commit planning artifacts to appropriate location
  4. Ensure security test artifacts are preserved
  5. Copy key artifacts to vault for cross-session access
- **Vault checkpoint**: `vault_write` catalog of preserved artifacts
- **Success**: No valuable work is untracked or at risk of loss

### Phase 6: Clean Tracked Runtime Artifacts
- **Goal**: Remove files that should be gitignored, not deleted
- **Steps**:
  1. `git rm --cached` for tracked `node_modules/`, `cache/swarm/`, `data/` runtime files
  2. Verify `.gitignore` has complete coverage
  3. Single cleanup commit: `chore: untrack runtime artifacts (node_modules, cache, data)`
  4. Files remain on disk — only removed from git tracking
- **Vault checkpoint**: Log file counts
- **Success**: `git status` clean, runtime artifacts exist but aren't tracked

### Phase 7: Repository Presentability
- **Goal**: Repo looks professional for external review
- **Steps**:
  1. Clean root directory organization
  2. Rewrite README.md
  3. Add LICENSE, CONTRIBUTING.md
  4. GitHub community files (issue templates, PR template)
  5. pyproject.toml metadata
- **Vault checkpoint**: `vault_log_decision` with completion summary
- **Success**: Passes the "stranger opens the repo" test

## Dependencies

```
Phase 0 (merge PR)
  ├→ Phase 1 (fix GC)     → Phase 2 (branch triage)
  ├→ Phase 3 (commit conv) 
  ├→ Phase 4 (fix CI)     → Phase 6 (untrack artifacts) → Phase 7 (presentability)
  └→ Phase 5 (preserve untracked)
```

## Related Vault Notes

- [[2026-03-05-vault-first-enforcement-protocol]] — enforcement mechanism
- [[2026-03-05-branch-inventory]] — full branch catalog
- [[2026-03-05-non-destructive-operations-only-preserve-all-branch-work]] — governing decision
- [[2026-03-05-vault-first-enforcement-for-all-development-artifacts]] — ADR
- [[repo-and-process-debt]] — prior debt assessment
- [[2026-02-19-github-flow-appropriate-for-pre-alpha]] — branching strategy
