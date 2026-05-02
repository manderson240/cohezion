# Repository Management Documentation

## Overview

This document describes the CI/CD automation for worktree lifecycle management and repository health monitoring in the Cohezion project.

## Worktree Lifecycle Scripts

### worktree-create.py

Creates a new worktree with proper branch structure and manifest.

```bash
# Create a new worktree
python scripts/worktree-create.py my-feature --base-branch main

# With JSON output
python scripts/worktree-create.py my-feature --base-branch main --json
```

**Features:**
- Creates branch `spec/<slug>`
- Creates worktree at `.worktrees/spec-<slug>-<hash>/`
- Generates `MANIFEST.md` with metadata
- Validates branch doesn't already exist

### worktree-archive.py

Archives a worktree non-destructively with git bundle and manifest.

```bash
# Archive a worktree
python scripts/worktree-archive.py .worktrees/spec-my-feature-abc123

# With JSON output
python scripts/worktree-archive.py .worktrees/spec-my-feature-abc123 --json
```

**Features:**
- Creates git bundle preserving all refs
- Copies `MANIFEST.md` with updated status
- Archives to `archive/worktrees/<name>/`
- Preserves additional files (logs, configs)

### worktree-sync.py

Squash merges a worktree branch back to its base branch.

```bash
# Sync worktree to base
python scripts/worktree-sync.py my-feature

# With custom message
python scripts/worktree-sync.py my-feature --message "feat: implement feature"

# With JSON output
python scripts/worktree-sync.py my-feature --json
```

**Features:**
- Reads base branch from manifest
- Performs squash merge
- Returns commit hash and files changed
- Returns to original branch after merge

### repo-health-check.py

Runs automated repository health checks.

```bash
# Run all checks
python scripts/repo-health-check.py

# With JSON output
python scripts/repo-health-check.py --json
```

**Checks:**
- Ruff linting
- Pytest test suite
- File size limits (500 lines hard limit)
- Import best practices
- Git status summary

## GitHub Actions Workflows

### health.yml

Runs on every PR and push to main/develop:
- Ruff linting
- Ruff format check
- Pytest with coverage
- File size validation
- Uploads coverage to Codecov

### skill-validation.yml

Runs when skills or skill registry change:
- Validates `skills.json` structure
- Checks skill frontmatter in markdown files
- Ensures no duplicate skill names
- Verifies required fields

### worktree-lifecycle.yml

Runs monthly (1st at 00:00 UTC):
- Finds worktrees inactive for 90+ days
- Archives them using `worktree-archive.py`
- Can be triggered manually with custom threshold

## Pre-commit Hooks

The `.pre-commit-hooks.yaml` defines hooks for:

1. **ruff-format**: Checks code formatting
2. **ruff-check**: Runs linter checks
3. **skill-validation**: Validates skill registry
4. **file-size-check**: Ensures files stay under limits

Install hooks:

```bash
pip install pre-commit
pre-commit install
```

## File Size Limits

| Level | Lines | Action |
|-------|-------|--------|
| Warning | 300 | CI warning, soft limit |
| Error | 500 | CI failure, hard limit |

## Integration with cz-cli

These scripts complement the `cz` CLI tool:

| cz Command | Script Equivalent |
|------------|-------------------|
| `cz worktree create` | `worktree-create.py` |
| `cz worktree archive` | `worktree-archive.py` |
| `cz worktree sync` | `worktree-sync.py` |
| `cz status` | `repo-health-check.py` |

## Archive Structure

```
archive/
└── worktrees/
    └── spec-<slug>-<hash>/
        ├── <slug>-<date>.bundle  # Git bundle
        ├── MANIFEST.md           # Archived manifest
        ├── *.log                 # Log files
        └── .env*                 # Environment files
```

## Troubleshooting

### Worktree already exists

If `worktree-create.py` reports the worktree already exists:
1. Check if the branch exists: `git branch | grep spec/`
2. Remove existing worktree: `git worktree remove <path>`
3. Delete branch if needed: `git branch -D spec/<slug>`

### Archive failed

If archiving fails:
1. Verify the path is a valid worktree: `git worktree list`
2. Check disk space for bundle creation
3. Ensure the worktree path is correct

### Sync conflicts

If `worktree-sync.py` fails:
1. Manually resolve conflicts in the worktree
2. Commit changes in the worktree
3. Re-run the sync command

## Maintenance

- Run `repo-health-check.py` before committing
- Archive old worktrees monthly via GitHub Actions
- Review file sizes quarterly to identify refactoring candidates
