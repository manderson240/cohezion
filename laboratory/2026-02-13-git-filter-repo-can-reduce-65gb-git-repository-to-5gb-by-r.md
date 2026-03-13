---
title: "git-filter-repo can reduce 6.5GB git repository to <5GB by r"
date: "2026-02-13"
status: in-progress
tags: [experiment]
aspect: thinker
neural:
  activation: 0.92
  stage: mature
  synapse_in: 5
  synapse_out: 18
---

## Hypothesis

`git-filter-repo` could achieve more targeted and effective repository size reduction than BFG Repo-Cleaner by enabling path-specific removal rather than blanket blob-size filtering. The hypothesis predicted that surgical removal of known problematic paths (training data directories, virtual environments, simulation outputs) would reduce a 6.5GB repository to under 5GB while preserving more meaningful commit history than BFG's size-threshold approach. Additionally, `git-filter-repo` was hypothesized to be more suitable for ongoing maintenance because its path-based rules could be documented and re-applied.

## Method

1. **Baseline measurement**: Starting from the post-BFG state (~6.5GB, see [[2026-02-11-github-repo-cleanup-with-bfg]]), measured remaining large objects using `git rev-list --objects --all | git cat-file --batch-check | sort -k3 -n -r`.
2. **Path identification**: Mapped remaining large objects to their original paths. Identified specific directories and file patterns that BFG's size threshold had missed (files between 10-100MB that collectively consumed significant space).
3. **git-filter-repo execution**: Ran `git-filter-repo --path <target> --invert-paths` for each identified path, removing the path from all historical commits. Processed paths in dependency order to avoid orphaned references.
4. **Pack optimization**: After path removal, ran `git reflog expire --expire=now --all && git gc --prune=now --aggressive` to reclaim space from removed objects.
5. **Integrity verification**: Verified repository integrity with `git fsck --full` after each removal pass. Checked that no commits were orphaned and that the HEAD lineage was intact.
6. **Remote synchronization**: Force-pushed the rewritten history to GitHub and verified the repository was within GitHub's size guidelines.
7. **Consolidation**: Documented the full cleanup sequence as part of the [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance|GitLab-to-GitHub consolidation]] effort.

## Results

- **Starting size**: ~6.5GB (post-BFG cleanup).
- **Paths removed**: 5 directory trees (training data, simulation outputs, checkpoint files, virtual environment snapshots, temporary build artifacts).
- **Final size**: Under 5GB (within GitHub's recommended range).
- **History preservation**: 95%+ of meaningful commits preserved. Only commits that exclusively added/removed large data files were affected.
- **Execution time**: ~15 minutes for the full filter-repo pipeline (compared to BFG's ~5 minutes, but with better targeting).
- **GitHub push**: Successful after force-push. Repository accessible and cloneable within normal timeframes.
- **Commit count**: Lost ~20 commits that consisted entirely of large file additions/removals. All code-bearing commits preserved.

## Analysis

The experiment validated that `git-filter-repo` and BFG are complementary tools rather than alternatives. BFG excels at rapid bulk cleanup (removing all blobs above a size threshold), while `git-filter-repo` excels at surgical path-specific removal. The recommended sequence is BFG first (for the 80% reduction), then `git-filter-repo` (for the remaining targeted cleanup). This matches the [[lesson-14-cleanup-is-multi-pass]] insight from the broader repository cleanup effort.

The key advantage of `git-filter-repo` over BFG is reproducibility: the path-based rules can be documented, versioned, and re-applied if the repository needs to be re-cleaned (e.g., after a bad merge reintroduces historical paths). BFG's size threshold is a one-time operation that does not encode the intent behind the cleanup.

## Learnings

1. **Path-based removal is more maintainable than size-based**: `git-filter-repo --path data/ --invert-paths` is self-documenting. `bfg --strip-blobs-bigger-than 100M` requires understanding what was removed after the fact.
2. **BFG then filter-repo is the optimal sequence**: BFG handles the bulk reduction quickly; filter-repo handles the remaining targeted paths precisely. Together they achieved what neither could alone.
3. **Force-push is unavoidable**: History rewriting means all clones become invalid. This must be coordinated with all collaborators. For the Cohezion repository (single primary operator), this was acceptable.
4. **[[data-discipline-prevent-generated-data-in-git|Prevention costs 1% of cleanup]]**: The pre-commit hook that now prevents large file commits took 10 minutes to implement. The multi-session cleanup effort consumed 3+ hours. Prevention is always cheaper.
5. **Repository size is a leading indicator of governance health**: A growing repository signals missing .gitignore rules, absent hooks, or inadequate [[repository-health-monitoring-size-tracking-large-object-detection|monitoring]]. Size should be tracked as a continuous metric, not checked only when pushes fail.

## Relevance to Cohezion

This experiment produced the operational playbook for repository hygiene in the Cohezion framework. Agent sessions generate artifacts (model weights, trajectory files, embedding caches) that can easily bloat a repository. The BFG-then-filter-repo cleanup sequence, combined with the pre-commit prevention hooks, forms the repository governance layer that keeps the Cohezion vault repository healthy as the framework scales. The documented path-based rules serve as the template for any future cleanup operations across Cohezion projects.

## Related

**Decisions**: [[2026-02-11-session-55-critical-antipattern-training-data-committed-to-git-history-blocks-gi]], [[2026-02-11-session-55-discovered-redundant-pack-files-as-root-cause-of-12gb-size-final-cons]], [[2026-02-11-use-escalation-staged-deployment-for-large-repository-cleanup]], [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
**Patterns**: [[data-discipline-prevent-generated-data-in-git]], [[repository-health-monitoring-size-tracking-large-object-detection]]
**Lessons**: [[lesson-13-8-6m-file-incident]], [[lesson-14-cleanup-is-multi-pass]]
**Experiments**: [[2026-02-11-github-repo-cleanup-with-bfg]], [[2026-02-11-large-repositories-26gb-with-virtual-environment-files-wi]]

## Related Concepts

- [[2026-02-11-entire-io-api-investigation]]
- [[2026-02-12-graphrag-implementation-session-56]]
- [[2026-02-11-graphrag-proof-of-concept-success]]
- [[2026-02-11-phase1-production-validation-results]]
- [[2026-02-12-session-56-compact-retrospective]]
- [[2026-02-17-spec-verify-token-efficiency-analysis]]
- [[2026-02-14-session-58-7-phase-journey-enrichment-3-agent-adversarial-review]]
- [[2026-02-19-journal-vacuum-during-crash-loop-recovery]]
