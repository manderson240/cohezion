---
title: "Use Escalation + Staged Deployment for Large Repository Cleanup"
date: "2026-02-11"
status: proposed
tags: [decision]

decision_reasoning:
  chosen_option: "Use escalation + staged deployment for large repository cleanup"
  rationale: "Staged approach reduces risk of destructive git operations; escalation pattern ensures review before irreversible actions"
  confidence_score: 0.88
  alternatives_rejected:
    - "Aggressive gc + repack (high risk, unrecoverable if fails)"
    - "Manual git filter-repo (complex, requires deep git knowledge)"
  reasoning_chain:
    - "Discovered 12GB redundant pack files from git history"
    - "Simple gc --aggressive didn't consolidate them"
    - "Realized need for staged approach with validation"

metrics:
  estimated_cost: 0.0
  estimated_time_hours: 1.5
  actual_cost: 0.0
  actual_time_hours: 2.0
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated:
    []
aspect: thinker
neural:
  activation: 0.536
  stage: growing
  cluster: decisions
---

## Context

During the Session 55 repository cleanup effort, the initial approach of running `git gc --aggressive` on a 12GB repository failed to reduce size. The pack files contained historical objects from accidentally committed training data (see [[2026-02-11-session-55-critical-antipattern-training-data-committed-to-git-history-blocks-gi|Session 55 critical antipattern]]). A naive "try the most aggressive option first" approach risked data loss -- `git gc --aggressive --prune=now` combined with history rewriting tools could permanently destroy commit history if applied incorrectly.

The [[compound-engineering-investigation-retrospection-before-destructive-operations|investigation-before-destruction]] principle demanded a more careful approach. Repository cleanup involving history rewriting is inherently destructive: once a force-push replaces remote history, the old state is unrecoverable unless backups exist. The staged approach was designed to minimize blast radius at each step.

## Decision

Adopt an escalation + staged deployment pattern for repository cleanup operations:

**Stage 1 -- Diagnose (non-destructive)**
- `git count-objects -vH` to measure repository size
- `git verify-pack -v .git/objects/pack/*.idx | sort -k 3 -n | tail -20` to identify largest objects
- `git rev-list --objects --all | git cat-file --batch-check` to map objects to paths
- Document findings before proceeding

**Stage 2 -- Safe optimization (reversible)**
- `git gc --auto` (standard housekeeping)
- `git repack -Ad` (consolidate packs, prune redundant)
- Verify size reduction; if sufficient, stop here

**Stage 3 -- Aggressive optimization (reversible with backup)**
- Create a full backup: `git clone --mirror . ../repo-backup-$(date +%Y%m%d)`
- `git gc --aggressive --prune=now`
- Compare size and integrity against backup

**Stage 4 -- History rewriting (irreversible, requires force-push)**
- BFG Repo-Cleaner or git-filter-repo to strip large blobs
- `git reflog expire --expire=now --all && git gc --prune=now`
- Verify repository integrity: `git fsck --full`
- Force-push only after verification passes

Each stage requires explicit validation before escalating to the next. The key principle: **never escalate to a destructive stage without evidence that non-destructive stages are insufficient**.

## Consequences

- **Positive**: The staged approach caught that `git gc --aggressive` alone was insufficient (Stage 2 failed to reduce size), directing the team to Stage 4 (BFG cleanup) with confidence that it was necessary.
- **Positive**: The backup created at Stage 3 proved valuable when the first BFG attempt produced unexpected results (it preserved pack files referenced by reflogs that hadn't been expired).
- **Positive**: The pattern is reusable for any future repository maintenance, not just this specific incident.
- **Negative**: The staged approach took approximately 2 hours compared to an estimated 30 minutes for a direct BFG run. The additional time was justified by the safety guarantees but was a real cost.
- **Lesson**: [[lesson-14-cleanup-is-multi-pass]] -- cleanup operations almost always require multiple passes, and each pass reveals information needed for the next.

## Alternatives Considered

- **Direct BFG run without staging** -- Skip diagnosis and jump straight to history rewriting. Rejected because without understanding what objects were in the pack files, the BFG parameters (size threshold, path filters) would be guesses rather than targeted.
- **Manual git filter-branch** -- The traditional approach before BFG and filter-repo. Rejected because filter-branch is [deprecated](https://git-scm.com/docs/git-filter-branch), extremely slow on large repositories, and error-prone.
- **Abandon repository, start fresh** -- Create a new repository with only the current state. Rejected because commit history is a knowledge asset in Cohezion -- architectural decisions and their evolution are tracked through commits.
- **Git LFS migration** -- Retroactively convert large files to LFS pointers. Rejected because the files were unwanted (not just large), and LFS migration still rewrites history.

## See Also

- [[compound-engineering-investigation-retrospection-before-destructive-operations]] -- the principle that motivated staged escalation
- [[repository-health-monitoring-size-tracking-large-object-detection]] -- ongoing monitoring to detect future size regressions
- [[2026-02-11-session-55-adversarial-review-blockers-identified]] -- blockers found during the adversarial review of this cleanup
- [[lesson-14-cleanup-is-multi-pass]] -- the lesson extracted from this experience
- [[safe-persistent-storage-lifecycle]] -- broader pattern for managing persistent data safely
- [[2026-02-11-session-55-discovered-redundant-pack-files-as-root-cause-of-12gb-size-final-cons]] -- the root cause investigation
- [[adversarial-review]] -- the review process that validated the staged approach

## Primary Sources

- [Git gc documentation](https://git-scm.com/docs/git-gc) -- official docs for garbage collection
- [Git repack documentation](https://git-scm.com/docs/git-repack) -- pack consolidation reference
- [Scaling Git's garbage collection (GitHub Blog)](https://github.blog/engineering/architecture-optimization/scaling-gits-garbage-collection/) -- GitHub's approach to gc at scale
- [Keeping Your Git Repository Clean and Efficient (2025)](https://geekcafe.com/blog/2025/08/keeping-your-git-repository-clean-and-efficient) -- recommended cleanup workflow
