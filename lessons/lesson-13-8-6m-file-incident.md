---
title: 8.6M File Incident: Large Generated Files Committed to Git Corrupt Repository Health
date: 2026-02-23
severity: CRITICAL
category: git
tags: [git, repository-health, large-files, pre-commit, data-governance]
status: validated
---

# Lesson: 8.6M File Incident: Large Generated Files Committed to Git Corrupt Repository Health

## Context

An 8.6M training data file was committed to the main repository, inflating it to 12GB+, causing CI clone timeouts. Recovery required git-filter-repo and took multiple sessions with history rewriting.

## Core Learning

**Generated files, training data, and binary assets MUST be gitignored before first commit. Adding after the fact requires history rewrite.**

### Why This Matters
- Git stores every version of every file permanently -- no delete without history rewrite
- A single 8.6M file can inflate clone times from seconds to minutes
- CI runners clone fresh every run -- large repos cause cascading timeouts
- History rewrite breaks all open branches and forks

### Pattern
```bash
# .gitignore -- prevent before it happens
*.jsonl              # Training data
*.parquet            # ML datasets
data/generated/      # Any generated output directory

# Pre-commit hook size check
git diff --cached --name-only | xargs -I{} find {} -size +1M
```

## Recommendations

### Do
- Add large file patterns to .gitignore BEFORE generating them
- Configure pre-commit hooks to block files over 1MB
- Run weekly: git ls-files --cached | xargs ls -lh | sort -k5 -hr | head -20

### Don't
- Commit generated data files without checking size first
- Run git add . without reviewing what's being staged

## Related Concepts

- [[data-governance-prevention-through-pre-commit-enforcement]] - Prevention mechanism
- [[repository-health-monitoring-size-tracking-large-object-detection]] - Detection
- [[sentinel-1-ice-sheets]] - both involve discipline around large scientific/operational datasets: Sentinel-1 produces gigabytes of radar imagery requiring careful pipeline governance; this incident shows what happens to git repositories without equivalent data governance controls

## Validation

**Discovered**: Feb 2026 (Session 55)
**Impact**: Repository ballooned to 12GB+, required multi-session recovery
**Status**: CRITICAL -- pre-commit hooks now mandatory
