---
title: "Data Discipline Prevent Generated Data In Git"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.91
  stage: mature
  synapse_in: 2
  synapse_out: 35
---
## Definition

Data discipline is the practice of preventing generated, derived, or binary artifacts from being committed to git repositories. Generated data includes build outputs, virtual environments, model weights, training data, compiled binaries, and any file that can be reproduced from source. Once committed, these files persist in git history permanently (even after deletion from the working tree) and cause repository bloat that degrades clone times, CI performance, and developer experience.

The discipline is enforced through `.gitignore` rules, pre-commit hooks, repository size monitoring, and governance policies. Remediation of existing violations requires history-rewriting tools like `git filter-repo` or BFG Repo-Cleaner.

## Key Properties

- **Prevention over remediation**: `.gitignore` rules must be established before generated data is created, not after.
- **History permanence**: Git never forgets -- a 500MB file committed and then deleted still lives in pack files forever.
- **Compounding cost**: Each large object multiplies across clones, forks, CI runners, and backups.
- **Governance automation**: Pre-commit hooks can reject files above a size threshold or matching known generated-data patterns.
- **Remediation complexity**: Cleaning history requires `git filter-repo`, force-pushes, and coordinating all downstream clones.

## Examples

- Virtual environment directories (`.venv/`, `node_modules/`) committed to git history, inflating a repository from 500MB to 26GB
- Training data or model weights checked in alongside source code, blocking CI pipelines
- Redundant git pack files accumulating to 12GB because aggressive GC does not consolidate packs

## Related Papers

- [[2026-02-11-github-repo-cleanup-with-bfg]]
- [[2026-02-11-large-repositories-26gb-with-virtual-environment-files-wi]]
- [[2026-02-11-session-55-critical-antipattern-training-data-committed-to-git-history-blocks-gi]]
- [[2026-02-11-session-55-discovered-redundant-pack-files-as-root-cause-of-12gb-size-final-cons]]
- [[2026-02-12-repository-health-governance-skill-created]]
- [[2026-02-13-git-filter-repo-can-reduce-65gb-git-repository-to-5gb-by-r]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-13-use-versioning-headers-instead-of-file-suffixes]]
- [[ai_for_good]]
- [[benchmarking]]
- [[conclusion]]
- [[data_engineering]]
- [[dl_primer]]
- [[dnn_architectures]]
- [[efficient_ai]]
- [[frameworks]]
- [[frontiers]]
- [[hw_acceleration]]
- [[introduction]]
- [[ml_systems]]
- [[ondevice_learning]]
- [[ops]]
- [[optimizations]]
- [[privacy_security]]
- [[responsible_ai]]
- [[robust_ai]]
- [[sustainable_ai]]
- [[training]]
- [[workflow]]

## Related Concepts

- [[repository-health-monitoring-size-tracking-large-object-detection]] -- monitoring that detects violations of this discipline
- [[runbook-ci-cd-pipeline]] -- CI pipelines that suffer when this discipline is not followed
- [[concept-automation]] -- automation that must respect gitignore rules when generating vault content
- [[2026-02-11-session-55-http-500-failure-may-be-protocol-specific-ssh-push-alternative-availa|Session 55: HTTP 500 Push Failure]] — repository size issues caused by training data in git history drove this push failure
- [[2026-02-09-session-46-git-unification-complete|Session 46: Git Unification]] — diverged histories requiring unification were partly caused by data discipline violations
- [[2026-02-11-session-55-git-aggressive-gc-doesnt-consolidate-packs-manual-repack-forced|Session 55: Git GC Failure]] — redundant pack files accumulated from generated data committed to git history

## Agent Outputs

- **Clean up Git Bloat (SurrealDB ingestion)** — `Agents/Antigravity/5d3a7b1d-804d-4bff-ace4-a5c887f109b7/task.md`
- **Resolve Git Bloat** — `Agents/Antigravity/86dfeb15-82f2-494d-b004-f30027f17347/task.md`
- **Git Bloat from universe_nodes** — `Agents/Antigravity/37bc3653-31e7-4142-abb1-23f30c9a3726/task.md`
- **Enable Git Worktrees for Multi-Session Work** — `Agents/Antigravity/1c6f7603-f5d6-433e-978f-b9d299ca934d/task.md`

## Relevance to Cohezion

The Cohezion vault generates derived data (3D graph JSON, embeddings, SurrealDB exports) that must never enter git history. The `.gitignore` in this repository explicitly excludes these artifacts. Lessons learned from a 65GB repository incident (reduced to 5GB via `git filter-repo`) directly informed the governance rules enforced by the cohezion-engine's pre-commit hooks.
