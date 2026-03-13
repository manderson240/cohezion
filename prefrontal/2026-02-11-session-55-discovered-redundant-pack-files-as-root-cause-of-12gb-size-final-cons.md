---
title: Session 55 - Discovered redundant pack files as root cause of 12GB size; final
  consolidation in progress
date: '2026-02-11'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  reasoning_chain:
  - sequence: 1
    content: 'Context: Session 55 - Discovered redundant pack files as root cause
      of 12GB size; final c...'
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
  - sequence: 4
    content: Selected option with best balance of trade-offs
    type: hybrid
    confidence: 0.62
    assumption: Best option was chosen based on analysis
  reasoning_type: research
  confidence_score: 0.6
aspect: thinker
neural:
  activation: 0.83
  stage: mature
  synapse_in: 3
  synapse_out: 11
---

## Context

During Session 55, the Cohezion vault repository had grown to 12GB -- far exceeding the expected ~500MB. Initial investigation with `git count-objects -vH` revealed that the `.git/objects/pack/` directory contained multiple large pack files totaling over 11GB. The working tree itself was only ~300MB, meaning nearly all bloat was in git's internal storage.

The root cause investigation followed the [[compound-engineering-investigation-retrospection-before-destructive-operations|investigation-before-destruction]] principle. Using `git verify-pack -v` to inspect pack file contents, the analysis revealed that the pack files contained historical objects from training data, model weights, and simulation output files that had been committed in earlier sessions and subsequently deleted. Git's architecture preserves all historical objects in pack files by design -- `git rm` removes files from the working tree but not from history.

Critically, `git gc --aggressive` did not reduce the size because it only recomputes delta compression between objects; it does not remove objects that are still reachable from any ref (branch, tag, or reflog entry). The reflog retained references to the commits that introduced the large files, preventing garbage collection from reclaiming space. This finding was documented in [[2026-02-11-session-55-git-aggressive-gc-doesnt-consolidate-packs-manual-repack-forced]].

## Decision

1. **Root cause confirmed**: Redundant pack files containing historical large objects (training data, model weights) are the sole cause of the 12GB repository size. No other factors (corrupt objects, pack index fragmentation, etc.) contribute meaningfully.
2. **Remediation path**: Follow the [[2026-02-11-use-escalation-staged-deployment-for-large-repository-cleanup|escalation staged deployment]] pattern to clean up the repository in controlled stages.
3. **Immediate action**: Expire all reflogs (`git reflog expire --expire=now --all`) to make the historical objects unreachable, then run `git gc --prune=now` to remove them. If this is insufficient, escalate to BFG Repo-Cleaner for full history rewriting.
4. **Prevention**: Install [[data-governance-prevention-through-pre-commit-enforcement|pre-commit hooks]] that reject files above 10MB and add comprehensive `.gitignore` rules for generated data directories.

## Consequences

- **Positive**: Root cause identification eliminated guesswork. Instead of repeatedly trying different gc configurations, the team could proceed directly to the correct remediation (reflog expiry + gc, then BFG if needed).
- **Positive**: The investigation documented exactly which commits introduced the large files, providing a precise target list for BFG cleanup.
- **Positive**: The diagnostic methodology (`verify-pack` analysis, reflog inspection) is now a documented [[safe-file-split-checklist|reusable pattern]] for future repository health investigations.
- **Negative**: The investigation itself took approximately 45 minutes of Session 55 context budget, which was significant given the session was already dealing with multiple blockers.
- **Lesson**: `git gc --aggressive` is not a universal solution for repository bloat. Understanding git's object reachability model (refs -> commits -> trees -> blobs, with reflogs as additional roots) is essential for effective cleanup.

## Alternatives Considered

- **Assume the pack files were corrupt and re-clone** -- Simply discard the local repository and re-clone from remote. Rejected because the remote also contained the bloated history (the large objects had been pushed before the problem was detected).
- **Use `git pack-redundant` to identify and remove duplicate packs** -- The [git pack-redundant](https://git-scm.com/docs/git-pack-redundant) command was considered but is now deprecated. It can only remove entire duplicate packs, not individual duplicate objects within packs.
- **Increase `gc.auto` threshold and wait** -- Let git's automatic housekeeping eventually consolidate the packs. Rejected because automatic gc has the same limitation as manual gc: it cannot remove reachable objects. Also, 12GB repositories cause immediate operational problems (failed pushes, slow clones) that cannot wait for automatic resolution.
- **Shallow clone to truncate history** -- Use `git clone --depth 1` to create a repository with only the latest commit. Rejected because commit history is a knowledge asset -- architectural decisions and their rationale are embedded in commit messages and diffs.

## See Also

- [[repository-health-monitoring-size-tracking-large-object-detection]] -- the ongoing monitoring that should have caught this earlier
- [[data-discipline-prevent-generated-data-in-git]] -- the prevention pattern adopted after this discovery
- [[2026-02-11-session-55-git-aggressive-gc-doesnt-consolidate-packs-manual-repack-forced]] -- the finding that aggressive gc was insufficient
- [[lesson-14-cleanup-is-multi-pass]] -- the broader lesson about iterative cleanup
- [[platform-issue-analysis-template]] -- this investigation is an exemplar of the diagnose-root-cause-then-fix pattern
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]] -- the GitHub migration decision motivated in part by fixing this 12GB repo size problem
- [[2026-02-11-use-escalation-staged-deployment-for-large-repository-cleanup]] -- the staged cleanup approach adopted
- [[compound-engineering]] -- investigation-before-destruction is a compound engineering principle

## Primary Sources

- [Git gc documentation](https://git-scm.com/docs/git-gc) -- garbage collection mechanics including pruning and reflog interaction
- [Git repack documentation](https://git-scm.com/docs/git-repack) -- pack file consolidation and redundant pack removal
- [Git pack-redundant documentation (deprecated)](https://git-scm.com/docs/git-pack-redundant) -- why this tool is insufficient
- [Scaling Git's garbage collection (GitHub Blog)](https://github.blog/engineering/architecture-optimization/scaling-gits-garbage-collection/) -- how GitHub handles gc at scale, including cruft packs
