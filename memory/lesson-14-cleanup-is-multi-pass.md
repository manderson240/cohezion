---
title: Cleanup Is Multi-Pass: Single-Pass Cleanups Always Miss Residual Artifacts
date: 2026-02-23
severity: HIGH
category: operational
cost_of_forgetting: "Repository remains bloated after 'cleanup'; CI clone times stay slow because residual pack files were not removed"
tags: [cleanup, git, operations, multi-pass, verification]
status: validated
aspect: knower
neural:
  activation: 0.7
  stage: growing
  synapse_in: 4
  synapse_out: 4
---

# Lesson: Cleanup Is Multi-Pass: Single-Pass Cleanups Always Miss Residual Artifacts

## Context

During the recovery from the 8.6M file incident (Session 55, February 2026 -- see [[lesson-13-8-6m-file-incident]]), the team ran `git filter-repo` to remove the large training data file from history. After the filter operation, `du -sh .git/` showed the repository had shrunk, but not to the expected size. Investigation revealed that git's internal storage (pack files, loose objects, stale refs) retained artifacts from the removed history that required additional cleanup passes.

## Problem

Git's internal storage model means a single cleanup operation is never sufficient:

1. **Pack file residue**: `git filter-repo` rewrites history but leaves old pack files alongside new ones. The old packs contain the removed objects.
2. **Loose objects**: Rewriting history creates dangling objects (commits, trees, blobs) that reference the removed content. These are "loose" and not in any pack.
3. **Ref residue**: Stale refs (backup refs created by filter-repo, reflogs) keep old objects reachable, preventing garbage collection from removing them.

After the initial `git filter-repo` pass, the repository was still 8GB (down from 12GB). The target was under 500MB. Two more passes (aggressive repack + gc) were needed to reach the target.

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

## Solution

The canonical cleanup sequence is three passes with verification between each:

1. **Filter**: `git filter-repo` removes the target content from history
2. **Repack**: `git repack -adf` consolidates all remaining objects into a single optimized pack, eliminating redundant pack files
3. **GC**: `git gc --prune=now --aggressive` removes loose objects, expires reflogs, and performs final compaction

Each pass should include a size check (`du -sh .git/` and `git count-objects -vH`) to verify progress. If the size does not decrease as expected, investigate what is keeping objects reachable.

## Prevention

- **Measure before and after each pass**: Do not trust that a single command did the job
- **Run all three passes**: Filter alone is insufficient; repack alone is insufficient; gc alone is insufficient
- **Expire reflogs explicitly**: `git reflog expire --expire=now --all` before gc ensures reflogs do not keep old objects alive
- **Verify target size**: Know what the repository should be after cleanup, and keep running passes until you reach it

## Cost of Forgetting

- **Repository stays bloated**: Single-pass cleanup leaves 60-80% of the bloat in place
- **CI remains slow**: Clone times stay elevated because pack files still contain the removed objects
- **False completion**: "Cleanup done" declared prematurely; the problem resurfaces when someone notices CI is still slow

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
- [[lesson-13-8-6m-file-incident]] - The incident that required this multi-pass cleanup
- [[data-governance-prevention-through-pre-commit-enforcement]] - Prevention is better than multi-pass cleanup
- [[compound-engineering]] - Thorough cleanup enables clean compound git workflows

## Validation

**Discovered**: Feb 2026 (Session 55) -- redundant pack files found after initial cleanup
**Impact**: Repository recovered from 12GB to under 500MB after full three-pass cleanup
**Status**: Validated
