---
title: 8.6M File Incident: Large Generated Files Committed to Git Corrupt Repository Health
date: 2026-02-23
severity: CRITICAL
category: git
cost_of_forgetting: "Repository bloats to 12GB+; CI clone timeouts; recovery requires history rewrite breaking all branches"
tags: [git, repository-health, large-files, pre-commit, data-governance]
status: validated
aspect: knower
neural:
  activation: 0.75
  stage: growing
  synapse_in: 8
  synapse_out: 6
---

# Lesson: 8.6M File Incident: Large Generated Files Committed to Git Corrupt Repository Health

## Context

During Session 55 (February 2026), a developer ran `git add .` to stage changes for a commit. Among the staged files was an 8.6MB training data file (`.jsonl` format) that had been generated as part of an ML pipeline experiment. The file was committed and pushed. Because git stores every version of every file in its history, this single commit permanently inflated the repository.

## Problem

The consequences cascaded across the entire development workflow:

1. **Repository size explosion**: The repository grew from ~500MB to 12GB+ because git pack files retained the large object even after the file was deleted in a subsequent commit.
2. **CI clone timeouts**: CI runners (GitLab) clone the full repository on every run. Clone times went from 15 seconds to 8+ minutes, exceeding the CI timeout threshold. All CI pipelines began failing.
3. **Developer friction**: Every `git clone` and `git fetch` for every developer on the team became painfully slow.
4. **Recovery cost**: Removing the file from history required `git-filter-repo`, which rewrites every commit in the affected branch. This broke all open branches and forks, required force-pushing, and took multiple sessions to complete (see [[lesson-14-cleanup-is-multi-pass]]).

The root cause was simple: `.gitignore` did not include patterns for generated data files, and there was no pre-commit hook to block large files.

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

## Solution

Three layers of prevention were implemented:

1. **Gitignore patterns**: Added comprehensive patterns for training data, ML datasets, generated outputs, and binary assets to `.gitignore` before any future generation runs.
2. **Pre-commit hook**: A file size check hook blocks any staged file over 1MB. The hook runs automatically on every commit attempt.
3. **Weekly audit**: A scheduled script runs `git ls-files --cached | xargs ls -lh | sort -k5 -hr | head -20` to catch any large files that slipped through.

For the immediate incident, recovery required `git-filter-repo --path data/ --invert-paths` followed by multiple cleanup passes (repack, gc) -- see [[lesson-14-cleanup-is-multi-pass]].

## Prevention

- **Gitignore BEFORE generating**: Add patterns for new file types before the pipeline that creates them runs
- **Pre-commit hook**: Block files over 1MB at commit time; this is the last line of defense
- **Never `git add .`**: Always review what is being staged. Use `git add <specific-files>` instead.
- **Weekly size audit**: Monitor repository size and largest tracked files

## Cost of Forgetting

- **12GB+ repository** that takes 8+ minutes to clone (should be 15 seconds)
- **CI pipeline failures** from clone timeouts blocking all deployments
- **Multi-session recovery** requiring history rewrite that breaks all open branches
- **Developer productivity loss** from slow git operations across the entire team

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
- [[data-discipline-prevent-generated-data-in-git]] - The principle behind this lesson: generated data does not belong in git
- [[lesson-14-cleanup-is-multi-pass]] - The recovery process: multi-pass cleanup was required to fully remove the large file
- [[lesson-22-gitignore-ordering]] - Gitignore rule ordering matters; verify with `git check-ignore -v`
- [[sentinel-1-ice-sheets]] - both involve discipline around large scientific/operational datasets

## Validation

**Discovered**: Feb 2026 (Session 55)
**Impact**: Repository ballooned to 12GB+, required multi-session recovery
**Status**: CRITICAL -- pre-commit hooks now mandatory
