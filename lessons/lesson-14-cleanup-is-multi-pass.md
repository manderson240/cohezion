---
title: Cleanup Is Multi-Pass: Single-Pass Cleanups Always Miss Residual Artifacts
date: 2026-02-23
severity: HIGH
category: operational
tags: [cleanup, git, operations, multi-pass, verification]
status: validated
---

# Lesson: Cleanup Is Multi-Pass: Single-Pass Cleanups Always Miss Residual Artifacts

## Context

Repository cleanup operations consistently leave residual artifacts on the first pass. Redundant pack files, dangling blobs, and stale refs survive initial cleanup and re-inflate the repository.

## Core Learning

**Always run cleanup in at least 2-3 passes, verifying size reduction after each pass.**

### Pattern
```bash
# Pass 1: Remove target content
git filter-repo --path data/ --invert-paths

# Verify pass 1
git count-objects -vH

# Pass 2: Aggressive repack
git repack -adf --window=250 --depth=250

# Pass 3: Prune loose objects
git gc --prune=now --aggressive

# Final verification
du -sh .git/
```

## Recommendations

### Do
- Measure repository size before and after EACH cleanup pass
- Always run git repack -adf after git filter-repo
- Run at least 3 passes: filter, repack, gc

### Don't
- Declare cleanup complete after one pass
- Trust git gc alone to consolidate packs

## Related Concepts

- [[repository-health-monitoring-size-tracking-large-object-detection]] - Monitoring post-cleanup

## Validation

**Discovered**: Feb 2026 (Session 55) -- redundant pack files found after initial cleanup
**Status**: Validated
