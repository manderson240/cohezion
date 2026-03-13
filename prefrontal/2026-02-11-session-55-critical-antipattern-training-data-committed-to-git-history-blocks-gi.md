---
title: 'Session 55 - CRITICAL ANTIPATTERN: Training data committed to git history
  blocks GitHub push'
date: '2026-02-11'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  reasoning_chain:
  - sequence: 1
    content: 'Context: Session 55 - CRITICAL ANTIPATTERN: Training data committed
      to git history blocks...'
    type: research
    confidence: 0.65
    assumption: Problem was clearly identified
  - sequence: 2
    content: Explored multiple implementation approaches and trade-offs
    type: pattern
    confidence: 0.6
    assumption: Multiple options were considered
  - sequence: 3
    content: Evaluated options against project constraints and criteria
    type: research
    confidence: 0.58
    assumption: Options were systematically evaluated
  reasoning_type: research
  confidence_score: 0.6
aspect: thinker
neural:
  activation: 0.77
  stage: growing
  synapse_in: 4
  synapse_out: 9
---

## Context

During Session 55, a critical antipattern was discovered: training data files (ML model weights, simulation trajectories, and generated datasets ranging from 50MB to 6GB per file) had been committed directly to the git repository history. This bloated the repository from its expected ~500MB to over 12GB, making `git push` to GitHub fail with HTTP 413 (request too large) and SSH timeout errors. The files had been removed from the working tree in subsequent commits, but remained embedded in git's pack files as historical objects.

This is a well-documented antipattern in ML engineering. The [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) and [git-filter-repo](https://github.com/newren/git-filter-repo) tools exist specifically to address it. GitHub's own documentation warns that repositories should stay under 5GB, with individual files under 100MB. The root cause was the absence of `.gitignore` rules for generated data directories and the lack of pre-commit hooks to enforce file size limits.

## Decision

1. **Immediate remediation**: Use BFG Repo-Cleaner to strip all blobs larger than 100MB from git history, followed by `git reflog expire --expire=now --all && git gc --prune=now --aggressive` to reclaim space.
2. **Prevention**: Add comprehensive `.gitignore` rules for all generated data directories (`data/`, `models/`, `outputs/`, `*.pt`, `*.h5`, `*.parquet`, `*.arrow`). Install a pre-commit hook that rejects files exceeding 10MB.
3. **Future large files**: Adopt Git LFS for any legitimate large files that must be version-controlled (e.g., reference datasets used in tests).
4. **Documentation**: Record this as a critical [[adversarial-review|antipattern]] in the vault's decision records to prevent recurrence across all Cohezion projects.

## Consequences

- **Positive**: Repository size reduced from 12GB to ~800MB after BFG cleanup, enabling normal git push operations to resume.
- **Positive**: Pre-commit hooks provide an automated guardrail that catches large file commits before they enter history.
- **Negative**: History rewrite required force-push, invalidating all existing clones. All collaborators needed to re-clone.
- **Negative**: BFG cleanup took approximately 2 hours including verification, during which the repository was effectively locked.
- **Risk**: Any fork or cached clone that still contains the old history could re-introduce bloated objects if merged carelessly.

## Alternatives Considered

- **git filter-repo** -- The [officially recommended replacement](https://git-scm.com/docs/git-filter-branch) for git-filter-branch. More powerful than BFG for complex rewrites but slower and more complex to use. Rejected for this case because BFG's simpler interface was sufficient for blob-size-based stripping.
- **git gc --aggressive alone** -- Attempted first but failed to consolidate redundant pack files. As documented in [[2026-02-11-session-55-git-aggressive-gc-doesnt-consolidate-packs-manual-repack-forced]], aggressive gc does not remove objects still referenced by history; it only optimizes delta compression.
- **Migrate to Git LFS retroactively** -- `git lfs migrate import` can rewrite history to replace large files with LFS pointers. Rejected because the training data files were not needed in any form; they were accidental commits, not intentional version-controlled assets.
- **Start a fresh repository** -- Discard all history and start clean. Rejected because the commit history contained valuable context about architectural decisions and the evolution of the project.

## See Also

- [[data-discipline-prevent-generated-data-in-git]] -- the prevention pattern this decision instantiates
- [[data-governance-prevention-through-pre-commit-enforcement]] -- the pre-commit hook approach adopted
- [[lesson-13-8-6m-file-incident]] -- the specific incident that first surfaced this problem
- [[repository-health-monitoring-size-tracking-large-object-detection]] -- monitoring to catch future size regressions
- [[2026-02-11-session-55-discovered-redundant-pack-files-as-root-cause-of-12gb-size-final-cons]] -- the root cause investigation that identified pack file bloat
- [[ai-safety]] -- data governance as an aspect of responsible AI engineering
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]] -- later migration decision motivated partly by this cleanup

## Primary Sources

- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) -- 10-720x faster alternative to git-filter-branch
- [git-filter-repo on GitHub](https://github.com/newren/git-filter-repo) -- officially recommended history rewriting tool
- [Effective Methods to Permanently Remove Large Files from Git History](https://sqlpey.com/git/effective-methods-to-remove-large-files-from-git-history/)
