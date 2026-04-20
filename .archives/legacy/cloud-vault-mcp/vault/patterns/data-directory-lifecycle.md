# Data Directory Lifecycle Pattern

**Date:** 2026-03-04  
**Pattern Type:** Repository Health  
**Applied To:** Cohezion  
**Priority:** P3 (Party Mode Consensus)

---

## Problem Statement

The `data/` directory accumulated 15GB+ of generated files mixed with tracked files, causing:
1. Repository bloat (slow clones, large pushes)
2. Merge conflicts on generated files
3. Unclear onboarding (what to regenerate?)
4. CI/CD instability (large working directories)

---

## Solution: Data Lifecycle Policy

### Core Principle

**`data/` is ephemeral cache, not source control.**

All contents must be regenerable from source code and configuration.

---

## Implementation

### 1. .gitignore Rules

```gitignore
# Data directory - all contents are generated
data/
!data/.gitkeep
!data/README.md

# Specific cache patterns (anywhere in repo)
*.parquet
*.jsonl
*.pt
*.pkl
```

### 2. Makefile Targets

```makefile
clean-data:   ## Remove all generated data
reset-data:    ## Clean + regenerate
data-status:   ## Show data directory status
```

### 3. Directory Structure

```
data/
├── .gitkeep         # Tracks empty directory
├── README.md        # Policy documentation
├── journeys_25m/    # IGNORED (regenerable)
├── surrealdb/       # IGNORED (regenerable)
├── flume/           # IGNORED (regenerable)
└── ...              # All IGNORED
```

---

## Recovery Process

1. `make clean-data` - Remove all generated data
2. `make onboard` - Regenerate seed data
3. All data regenerated from source

---

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Tracked data files | 211 | 2 (.gitkeep + README) |
| Untracked data files | 732+ | 0 (all ignored) |
| Repository size | ~15GB in data/ | ~0 in git |
| Clone time | Slow | Fast |

---

## Apply This Pattern

1. Add `.gitignore` rules for `data/`
2. Create `data/README.md` with lifecycle policy
3. Create `data/.gitkeep` placeholder
4. Add `make clean-data` target
5. Add `make reset-data` target (clean + onboard)
6. Track only `.gitkeep` and `README.md`

---

## Related Patterns

- [CI Health Check](./design-thinking-pattern.md) - P1 Consensus
- [Untracked Files Triage](./untracked-files-triage.md) - P2 Consensus

---

_Should be applied to any project with generated artifacts._