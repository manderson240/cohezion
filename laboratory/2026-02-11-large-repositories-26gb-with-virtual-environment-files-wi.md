---
title: "Large repositories (26GB+) with virtual environment files wi"
date: "2026-02-11"
status: in-progress
tags: [experiment]
aspect: thinker
neural:
  activation: 0.95
  stage: mature
  synapse_in: 9
  synapse_out: 20
---

## Hypothesis

A repository that had grown to 26GB+ (with virtual environment files, training data, and simulation outputs committed to git history) could be diagnosed and reduced to a manageable size using a multi-pass cleanup approach. The hypothesis predicted that the bulk of the bloat came from a small number of large blobs (ML model weights, `.venv/` directories, trajectory data) embedded in git's pack files, and that identifying and removing these blobs would restore the repository to GitHub's recommended size range (under 5GB) without losing meaningful commit history.

## Method

1. **Diagnosis**: Ran `git count-objects -vH` and `git rev-list --objects --all | git cat-file --batch-check` to identify the largest objects in the repository's history. Sorted by size to find the top offenders.
2. **Root cause analysis**: Traced the large blobs to specific commits where virtual environment directories (`.venv/`, `node_modules/`), training data files (`*.pt`, `*.h5`, `*.parquet`), and simulation outputs (`trajectories/`, `checkpoints/`) had been committed. These files were later removed from the working tree but remained in git history.
3. **Size breakdown**: Mapped the 26GB total to component sources: ~12GB from redundant pack files, ~8GB from training data blobs, ~4GB from virtual environment snapshots, ~2GB from simulation checkpoints.
4. **BFG cleanup**: Applied BFG Repo-Cleaner to strip all blobs larger than 100MB from history (see [[2026-02-11-github-repo-cleanup-with-bfg]]).
5. **git-filter-repo validation**: Followed up with [[2026-02-13-git-filter-repo-can-reduce-65gb-git-repository-to-5gb-by-r|git-filter-repo]] as a more surgical alternative for targeted path removal.
6. **Prevention**: Implemented `.gitignore` rules and pre-commit hooks (see [[data-governance-prevention-through-pre-commit-enforcement]]) to prevent recurrence.

## Results

- **Initial size**: 26GB (12GB pack files + 14GB historical blobs).
- **After BFG cleanup**: Reduced to ~6.5GB (stripped all blobs >100MB).
- **After git gc aggressive**: Further reduced to ~5GB through pack file optimization.
- **After git-filter-repo**: Achieved final size under 5GB by targeting specific paths.
- **Root cause**: 85% of bloat traced to 3 commit ranges where training data directories were added and later removed.
- **Pack file issue**: Discovered redundant pack files as an independent size contributor (see [[2026-02-11-session-55-discovered-redundant-pack-files-as-root-cause-of-12gb-size-final-cons]]).
- **GitHub push**: Successfully restored to pushable state after cleanup.

## Analysis

The experiment confirmed a well-known but often-ignored pattern in ML/AI repositories: [[data-discipline-prevent-generated-data-in-git|generated data committed to git history is effectively permanent]] without history rewriting. Git's content-addressable storage means that even after `git rm`, the blob persists in pack files until explicitly purged. The 26GB repository was a textbook case of this antipattern, compounded by the absence of size-limiting hooks.

The multi-pass approach was necessary because no single tool addressed all size contributors. BFG handled the large blobs efficiently but did not address redundant pack files. `git gc --aggressive` addressed pack file optimization but could not remove historical blobs. `git-filter-repo` offered the most surgical control but required careful path specification. The lesson: repository cleanup is inherently multi-pass (see [[lesson-14-cleanup-is-multi-pass]]).

## Learnings

1. **Virtual environments in git are a silent repository killer**: `.venv/` directories contain thousands of small files that collectively consume gigabytes. A single accidental commit can add 2-4GB that persists forever without history rewriting.
2. **Multi-pass cleanup is the only reliable approach**: No single tool (BFG, git-filter-repo, git gc) addresses all size contributors. The cleanup must be staged: large blobs first, then path-specific removal, then pack optimization.
3. **Pre-commit hooks are the only reliable prevention**: `.gitignore` alone is insufficient because `git add -f` bypasses it. Pre-commit hooks that reject files above a size threshold provide a hard gate that cannot be accidentally circumvented.
4. **[[repository-health-monitoring-size-tracking-large-object-detection|Repository health monitoring]] must be continuous**: The bloat accumulated over weeks before being noticed. A daily size check (or pre-push hook) would have caught it when only one large commit existed, making cleanup trivial.
5. **Escalation strategy works**: The [[2026-02-11-use-escalation-staged-deployment-for-large-repository-cleanup|staged escalation]] approach (diagnose, then BFG, then filter-repo, then gc) minimized risk at each step.

## Relevance to Cohezion

This experiment directly motivated Cohezion's [[data-discipline-prevent-generated-data-in-git|data discipline]] patterns and the pre-commit enforcement framework. Agent sessions in Cohezion generate large artifacts (model checkpoints, trajectory data, embeddings) that must never enter git history. The repository cleanup experience produced the governance rules that the [[agent-journey-tracking]] system now enforces: all generated artifacts are registered with the JourneyTracker and stored outside the git tree, with only metadata pointers committed to the repository.

## Related

**Decisions**: [[2026-02-11-session-55-critical-antipattern-training-data-committed-to-git-history-blocks-gi]], [[2026-02-11-session-55-discovered-redundant-pack-files-as-root-cause-of-12gb-size-final-cons]], [[2026-02-11-use-escalation-staged-deployment-for-large-repository-cleanup]]
**Patterns**: [[data-discipline-prevent-generated-data-in-git]], [[repository-health-monitoring-size-tracking-large-object-detection]]
**Lessons**: [[lesson-13-8-6m-file-incident]], [[lesson-14-cleanup-is-multi-pass]], [[lesson-22-gitignore-ordering]]
**Experiments**: [[2026-02-11-github-repo-cleanup-with-bfg]], [[2026-02-13-git-filter-repo-can-reduce-65gb-git-repository-to-5gb-by-r]]

## Related Concepts

- [[2026-02-11-entire-io-api-investigation]]
- [[2026-02-12-graphrag-implementation-session-56]]
- [[2026-02-11-graphrag-proof-of-concept-success]]
- [[2026-02-11-phase1-production-validation-results]]
- [[2026-02-12-session-56-compact-retrospective]]
- [[2026-02-17-spec-verify-token-efficiency-analysis]]
- [[2026-02-14-session-58-7-phase-journey-enrichment-3-agent-adversarial-review]]
- [[2026-02-19-journal-vacuum-during-crash-loop-recovery]]
