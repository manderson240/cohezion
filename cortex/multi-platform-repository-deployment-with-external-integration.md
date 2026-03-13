---
title: "Multi Platform Repository Deployment With External Integration"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.78
  stage: growing
  synapse_in: 6
  synapse_out: 7
---
## Definition

Multi-platform repository deployment with external integration is the practice of maintaining a codebase across multiple Git hosting platforms (e.g., GitLab and GitHub) while coordinating CI/CD pipelines, access controls, and external service integrations that differ per platform. This pattern arises when projects need to consolidate from one platform to another or maintain mirrors for different audiences, and must handle protocol-specific failures (HTTP vs SSH), platform-specific CI configurations, and artifact governance across boundaries.

## Key Properties

- **Protocol fallback**: HTTP push failures (e.g., 500 errors) may be platform-specific; SSH push provides an alternative transport path
- **Phased migration**: Investigation (audit current state) -> Planning (map integrations) -> Execution (migrate with governance) -> Verification (confirm nothing lost)
- **Artifact governance**: Large files, training data, and binary artifacts require pre-commit enforcement to prevent repository bloat during migration
- **CI/CD translation**: GitLab CI YAML and GitHub Actions workflows serve the same purpose but require platform-specific configuration
- **External integration mapping**: Webhooks, API tokens, and service connections must be recreated on the target platform

## Examples

- GitLab-to-GitHub consolidation where HTTP 500 failures during push required switching to SSH protocol
- Repository cleanup with BFG Repo-Cleaner to remove training data from git history before platform migration

## Related Papers

- [[2026-02-11-session-55-http-500-failure-may-be-protocol-specific-ssh-push-alternative-availa]]
- [[2026-02-11-session-55-phase-a-investigation-complete]]
- [[2026-02-11-session-55-phase-c-execution-ready]]
- [[2026-02-11-session-55-team-execution-summary]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]

## Related Concepts

- [[data-governance-prevention-through-pre-commit-enforcement]] — pre-commit hooks prevent artifact governance violations during deployment
- [[compound-engineering-investigation-retrospection-before-destructive-operations]] — investigation phase applied to repository migration

## Relevance to Cohezion

The Cohezion project underwent a GitLab-to-GitHub migration that surfaced multiple deployment challenges including protocol failures, large file governance, and CI pipeline translation. The lessons from this migration informed the project's pre-commit enforcement and artifact governance patterns.
