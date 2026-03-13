---
title: "GitHub Repo Cleanup with BFG"
date: "2026-02-11"
status: in-progress
tags: [experiment]
aspect: thinker
neural:
  activation: 0.95
  stage: mature
  synapse_in: 3
  synapse_out: 19
---

## Hypothesis

BFG Repo-Cleaner could rapidly reduce a bloated git repository from 12GB+ to under 5GB by stripping all historical blobs exceeding 100MB, and that this size-threshold approach would be sufficient as a first-pass cleanup without requiring path-specific knowledge of which files caused the bloat. The hypothesis was that the vast majority of repository bloat would come from a small number of large blobs (ML model weights, training datasets, virtual environment packages) that exceeded the 100MB threshold, making BFG's blunt-instrument approach effective.

## Method

1. **Pre-cleanup baseline**: Measured repository size with `du -sh .git/` and identified largest objects via `git rev-list --objects --all | git cat-file --batch-check | sort -k3 -n -r | head -20`.
2. **BFG execution**: Ran `java -jar bfg.jar --strip-blobs-bigger-than 100M` on a mirror clone of the repository. BFG operates on bare repositories for safety, requiring `git clone --mirror` first.
3. **Garbage collection**: After BFG's history rewrite, ran `git reflog expire --expire=now --all && git gc --prune=now --aggressive` to physically remove the dereferenced objects and optimize pack files.
4. **Integrity check**: Verified repository integrity with `git fsck --full` and confirmed that HEAD and all branch tips resolved correctly.
5. **Size verification**: Measured post-cleanup size and compared against the pre-cleanup baseline and GitHub's 5GB recommendation.
6. **Push test**: Attempted `git push` to GitHub to verify the repository was within pushable limits.

## Results

- **Pre-cleanup size**: ~12GB (repository could not be pushed to GitHub; HTTP 413 and SSH timeouts).
- **Objects identified by BFG**: 47 blobs exceeding 100MB, totaling ~8.5GB of historical data. Largest single blob: 1.2GB (a PyTorch model checkpoint committed during Session 53).
- **Post-BFG size**: ~6.5GB (reduced by ~5.5GB, a 46% reduction).
- **Post-gc size**: ~5.9GB (additional 600MB from pack optimization).
- **Execution time**: BFG processing took ~5 minutes. The subsequent `git gc --aggressive` took ~10 minutes.
- **Integrity**: `git fsck --full` passed with no errors. All branches and tags intact.
- **Push result**: Still slightly above GitHub's comfort zone at 5.9GB. Subsequent [[2026-02-13-git-filter-repo-can-reduce-65gb-git-repository-to-5gb-by-r|git-filter-repo]] pass needed to reach <5GB.
- **History impact**: ~30 commits rewritten (those that touched large blobs). Commit messages and authorship preserved. File changes in those commits preserved except for the removed blobs.

## Analysis

BFG proved effective as a rapid first-pass tool. Its 100MB threshold approach correctly identified the primary bloat contributors without requiring any knowledge of which paths or files were problematic. However, the 5.9GB result showed that BFG alone was insufficient to reach the target: files between 10-100MB (numerous smaller training data files, cached embeddings, intermediate outputs) collectively added up to ~1GB that BFG's threshold missed.

The experiment validated the [[lesson-14-cleanup-is-multi-pass]] insight: BFG handles the "big rocks" efficiently, but a secondary tool (git-filter-repo) is needed for the "gravel" of medium-sized files. The multi-pass approach (BFG for bulk, filter-repo for targeted) is safer than trying to do everything in one pass, because each step can be verified independently.

The 5-minute execution time makes BFG suitable for emergency situations (repository suddenly unpushable), while the more surgical git-filter-repo is better suited for planned maintenance.

## Learnings

1. **BFG is fast but imprecise**: 5 minutes to remove 5.5GB of bloat is excellent for emergency cleanup. But the 100MB threshold is a blunt instrument that misses medium-sized files.
2. **Mirror clones are essential for safety**: BFG operates on bare repositories. Working on a mirror clone means the original repository is untouched until the force-push, providing a rollback path.
3. **`git gc --aggressive` matters**: The additional 600MB recovered by aggressive garbage collection is significant. Skipping this step leaves dereferenced objects consuming disk space.
4. **Single-pass cleanup is usually insufficient**: BFG took the repository from 12GB to 5.9GB, but the target was <5GB. A second tool ([[2026-02-13-git-filter-repo-can-reduce-65gb-git-repository-to-5gb-by-r|git-filter-repo]]) was required to finish the job.
5. **The [[lesson-13-8-6m-file-incident|8.6M file incident]] was preventable**: A single large model checkpoint commit started the bloat cascade. Pre-commit hooks checking file size would have caught it at the source.

## Relevance to Cohezion

BFG Repo-Cleaner became the recommended first-response tool in Cohezion's repository governance playbook. When agent sessions accidentally commit large artifacts (model checkpoints, trajectory files, embedding caches), the immediate response is: (1) add the path to `.gitignore`, (2) run BFG on a mirror clone to strip the blob from history, (3) follow up with git-filter-repo for any remaining targeted cleanup. This three-step playbook, combined with the [[data-governance-prevention-through-pre-commit-enforcement|pre-commit enforcement hooks]], forms Cohezion's complete strategy for preventing and recovering from repository bloat caused by [[agentic-ai|agent-generated]] artifacts.

## Related

**Decisions**: [[2026-02-11-session-55-critical-antipattern-training-data-committed-to-git-history-blocks-gi]], [[2026-02-11-use-escalation-staged-deployment-for-large-repository-cleanup]], [[2026-02-11-session-55-discovered-redundant-pack-files-as-root-cause-of-12gb-size-final-cons]]
**Patterns**: [[data-discipline-prevent-generated-data-in-git]], [[data-governance-prevention-through-pre-commit-enforcement]], [[repository-health-monitoring-size-tracking-large-object-detection]]
**Lessons**: [[lesson-13-8-6m-file-incident]], [[lesson-14-cleanup-is-multi-pass]]
**Concepts**: [[agentic-ai]]
**Experiments**: [[2026-02-13-git-filter-repo-can-reduce-65gb-git-repository-to-5gb-by-r]], [[2026-02-11-large-repositories-26gb-with-virtual-environment-files-wi]]

## Related Concepts

- [[2026-02-11-entire-io-api-investigation]]
- [[2026-02-12-graphrag-implementation-session-56]]
- [[2026-02-11-graphrag-proof-of-concept-success]]
- [[2026-02-11-phase1-production-validation-results]]
- [[2026-02-12-session-56-compact-retrospective]]
- [[2026-02-17-spec-verify-token-efficiency-analysis]]
- [[2026-02-14-session-58-7-phase-journey-enrichment-3-agent-adversarial-review]]
- [[2026-02-19-journal-vacuum-during-crash-loop-recovery]]
