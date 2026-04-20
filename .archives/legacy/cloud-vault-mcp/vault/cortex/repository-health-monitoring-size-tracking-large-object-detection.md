---
title: "Repository Health Monitoring Size Tracking Large Object Detection"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.93
  stage: growing
  synapse_in: 16
  synapse_out: 16
---
## Definition

Repository health monitoring is the practice of continuously tracking git repository size, detecting large objects in history, and alerting when repositories exceed size thresholds. Healthy repositories clone quickly, run CI efficiently, and do not waste storage on binary artifacts or generated data. Monitoring catches problems early -- before a repository grows from 500MB to 65GB and requires painful history rewriting to recover.

The three pillars are: **size tracking** (measuring `.git/` directory size and growth rate), **large object detection** (finding files above a threshold in history or working tree), and **governance enforcement** (blocking commits that would introduce large objects).

## Key Properties

- **Size thresholds**: Repositories should ideally stay under 1GB total (including `.git/`). Above 5GB triggers investigation.
- **Large object scanning**: `git rev-list --objects --all | git cat-file --batch-check` identifies the largest objects in history.
- **Pack file analysis**: Redundant pack files can silently bloat `.git/objects/pack/`. `git count-objects -vH` reveals the true size.
- **Pre-commit gates**: Hooks that reject files above a size limit (e.g., 5MB) prevent new large objects from entering.
- **Remediation tools**: `git filter-repo` (preferred) or BFG Repo-Cleaner for removing large objects from history.

## Monitoring Commands

```bash
# Repository size overview
du -sh .git/
git count-objects -vH

# Find largest objects in history
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | sort -k3 -n -r | head -20

# Check pack file count and size
ls -lh .git/objects/pack/
```

## Related Papers

- [[2026-02-11-github-repo-cleanup-with-bfg]]
- [[2026-02-11-large-repositories-26gb-with-virtual-environment-files-wi]]
- [[2026-02-11-session-55-critical-antipattern-training-data-committed-to-git-history-blocks-gi]]
- [[2026-02-11-session-55-discovered-redundant-pack-files-as-root-cause-of-12gb-size-final-cons]]
- [[2026-02-11-session-55-git-aggressive-gc-doesnt-consolidate-packs-manual-repack-forced]]
- [[2026-02-11-use-escalation-staged-deployment-for-large-repository-cleanup]]
- [[2026-02-12-prime-skill-pattern-as-governance-framework]]
- [[2026-02-12-repository-health-governance-skill-created]]
- [[2026-02-12-session-56-complete-index]]
- [[2026-02-12-session-56-documentation-extraction-complete]]
- [[2026-02-13-git-filter-repo-can-reduce-65gb-git-repository-to-5gb-by-r]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]

## Related Concepts

- [[data-discipline-prevent-generated-data-in-git]] -- the prevention discipline that monitoring enforces
- [[runbook-ci-cd-pipeline]] -- CI pipelines that degrade when repository health is poor
- [[runbook-health-checks]] -- broader health checking that includes repository monitoring
- [[2026-02-09-session-46-git-unification-complete|Session 46: Git Unification]] — post-unification monitoring ensures repository health is maintained

## Relevance to Cohezion

The Cohezion vault experienced firsthand the consequences of repository bloat -- a 65GB repository that required `git filter-repo` to reduce to 5GB. This incident led to the creation of a repository health governance skill that monitors size, detects large objects, and enforces data discipline. The monitoring patterns documented here are now part of the cohezion-engine's standard operational checks.
