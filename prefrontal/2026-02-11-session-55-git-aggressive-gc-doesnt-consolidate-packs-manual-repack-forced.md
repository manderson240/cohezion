---
title: Session 55 - Git aggressive GC doesn't consolidate packs; manual repack forced
date: '2026-02-11'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  reasoning_chain:
  - sequence: 1
    content: 'Context: Session 55 - Git aggressive GC doesn''t consolidate packs;
      manual repack forced'
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
  activation: 0.487
  stage: growing
  cluster: decisions
---

## Context

During Session 55's investigation into the 12 GB repository size problem, `git gc --aggressive` was run as a first-line cleanup attempt. Despite reporting success, the command did not consolidate the dozens of redundant pack files that were the root cause of the bloat. Investigation revealed that `git gc --aggressive` increases the delta search window depth but does not force a full repack when existing packs are below git's internal thresholds.

The repository contained 40+ individual pack files ranging from a few MB to several GB each. Many were redundant -- containing overlapping objects from incremental pushes and partial fetches. Git's garbage collector considered each pack individually viable and declined to merge them.

This discovery was critical: it meant the standard git maintenance workflow (`gc`, `prune`, `aggressive gc`) was insufficient for repositories that had accumulated pack file fragmentation over many sessions.

## Decision

Bypass `git gc` and execute a manual repack sequence to force consolidation:

```bash
# Force all objects into a single pack
git repack -a -d -f --depth=250 --window=250

# Remove now-redundant loose objects and old packs
git prune --expire=now

# Verify integrity
git fsck --full
```

The `-a` flag repacks all objects (not just unreachable ones), `-d` removes redundant packs after repacking, and `-f` forces recomputation of deltas even for objects already in packs. The high `--depth` and `--window` values maximize compression at the cost of CPU time.

## Consequences

**Positive:**
- Repository size reduced significantly after pack consolidation
- Single consolidated pack file is faster to clone and push than 40+ fragmented packs
- Established a known-good procedure for future repository size issues
- Identified that `git gc --aggressive` alone is insufficient for pack fragmentation

**Negative:**
- Manual repack is CPU-intensive (took 15-20 minutes on the 12 GB repository)
- The procedure must be documented and re-applied if fragmentation recurs
- Does not prevent future accumulation -- that requires [[data-discipline-prevent-generated-data-in-git|artifact governance]]

## Alternatives Considered

### Alt 1: Run `git gc --aggressive` Repeatedly
- **Rejected**: Multiple runs produced the same result -- gc does not merge packs below its internal thresholds regardless of repetition.

### Alt 2: Clone to Fresh Repository
- **Rejected**: Loses branch history and refs. A fresh clone fetches objects as a single pack, which would work, but requires re-establishing all remote tracking branches and tags.

### Alt 3: Use BFG Repo Cleaner
- **Rejected for this step**: BFG removes large objects from history but does not address pack fragmentation. BFG is the right tool for stripping artifacts from history (used in the subsequent [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance|GitHub migration]]), but pack consolidation needed to happen first.

### Alt 4: Accept the Size
- **Rejected**: 12 GB makes HTTPS push impossible (timeouts), blocks Claude Code web features, and wastes disk on every clone.

## See Also

- [[2026-02-11-session-55-discovered-redundant-pack-files-as-root-cause-of-12gb-size-final-cons]]
- [[repository-health-monitoring-size-tracking-large-object-detection]]
- [[lesson-14-cleanup-is-multi-pass]]
- [[data-discipline-prevent-generated-data-in-git]] — redundant pack files accumulated because generated data was committed to git history
- [[2026-02-09-session-46-git-unification-complete]] — the git unification session that preceded this repository cleanup effort
- [[honest-metrics-over-inflated-claims]] — git gc reporting "aggressive" cleanup while not consolidating packs is a case of misleading tool output
