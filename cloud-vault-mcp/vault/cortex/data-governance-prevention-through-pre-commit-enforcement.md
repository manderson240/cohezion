---
title: "Data Governance Prevention Through Pre Commit Enforcement"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.84
  stage: growing
  synapse_in: 15
  synapse_out: 10
---
## Definition

Data governance prevention through pre-commit enforcement is the practice of using git pre-commit hooks to automatically block commits that violate data governance policies before they enter the repository history. Rather than detecting and cleaning up violations after the fact (which requires history rewriting with tools like BFG Repo-Cleaner), this approach prevents violations at the point of commit, making governance a compile-time concern rather than a runtime one.

## Key Properties

- **Prevention over detection**: Blocking bad commits is cheaper and safer than rewriting git history to remove them
- **Automated enforcement**: Pre-commit hooks run automatically, removing reliance on developer discipline
- **File size limits**: Prevents large binary files, training datasets, and model weights from entering the repository
- **Secret scanning**: Detects API keys, credentials, and tokens before they reach git history
- **Pattern-based rules**: Configurable glob patterns and regex rules to match governed file types (e.g., `*.csv`, `*.pkl`, `*.h5`)
- **Non-bypassable**: Hooks should be installed via CI/CD setup to prevent `--no-verify` bypasses in production workflows

## Examples

- Blocking a 8.6MB training data file from being committed (see [[2026-02-11-session-55-critical-antipattern-training-data-committed-to-git-history-blocks-gi]])
- Repository cleanup with BFG after training data was already committed (see [[2026-02-11-github-repo-cleanup-with-bfg]])

## Related Papers

- [[2026-02-11-github-repo-cleanup-with-bfg]]
- [[2026-02-11-session-55-critical-antipattern-training-data-committed-to-git-history-blocks-gi]]
- [[2026-02-12-repository-health-governance-skill-created]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]

## Related Concepts

- [[multi-platform-repository-deployment-with-external-integration]] — pre-commit enforcement is critical during platform migration
- [[09-rust-flume-python313-incompatibility]] — pre-commit hook environments can trigger dependency incompatibilities
- [[compound-engineering-investigation-retrospection-before-destructive-operations]] — BFG cleanup is a destructive operation requiring the investigation principle
- [[safe-persistent-storage-lifecycle]] — safe storage lifecycle is the runtime complement; pre-commit enforcement is the preventive layer

## Related Patterns & Projects

- [[session-55-compound-engineering-learnings]] — Session 55 data governance learnings led to formalizing pre-commit enforcement as a standard practice
- [[repo-and-process-debt]] — Phase 1 coding standards enforcement (ruff, mypy, black) via pre-commit hooks is a form of data governance applied to code quality

## Relevance to Cohezion

This concept was born from a critical incident where training data committed to git history blocked GitHub pushes and required BFG cleanup. The resulting pre-commit governance hooks became a standard part of the Cohezion repository health skill, enforcing file size, secret, and artifact policies at commit time.
