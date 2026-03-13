---
title: 'GitHub Flow Appropriate for Pre-Alpha'
date: '2026-02-19'
status: accepted
tags: [decision, git, workflow, branching]
aspect: thinker
neural:
  activation: 0.7
  stage: growing
  synapse_in: 2
  synapse_out: 5
---

# GitHub Flow Appropriate for Pre-Alpha

## Context

The Cohezion project needed a clear branching strategy to support rapid iteration during the pre-alpha phase. The codebase was evolving quickly with frequent architectural changes, no external users, and a single primary contributor (with AI agent sessions as additional "contributors"). Without a defined strategy, branches proliferated and merge conflicts became a time sink.

Three mainstream branching models were evaluated: GitHub Flow (trunk-based with feature branches), GitFlow (develop/release/hotfix branches), and trunk-based development (direct commits to main). The choice needed to balance iteration speed against safety guardrails, with the understanding that the strategy could evolve as the project matured.

## Decision

Adopt **GitHub Flow** as the branching strategy for the pre-alpha phase. All work happens on short-lived feature branches created from the main working branch (`track-c`), merged back via pull request or direct merge after verification. No release branches, no develop branch, no hotfix branches.

Additionally, **worktree isolation** was added to the git workflow as a coding standard. The `/spec` workflow uses `.worktrees/` to isolate implementation from the main branch, providing GitFlow-like safety without the branching complexity.

## Consequences

**Positive:**
- Fast iteration — branches are created and merged within a single session or day
- Simple mental model — only one long-lived branch to track
- Worktree isolation provides safety for experimental work without polluting the main branch
- Compatible with AI agent sessions that create, implement, and merge within a single context window

**Negative:**
- No release tagging or versioning workflow — acceptable for pre-alpha but will need to be added
- No protected branch rules — relies on discipline rather than automation
- Risk of breaking the main branch if verification is skipped — mitigated by [[2026-02-14-3-tier-adversarial-review-protocol-for-code-quality]]

## Alternatives Considered

**GitFlow:** Full develop/release/hotfix branch hierarchy. Rejected because the overhead of maintaining multiple long-lived branches is disproportionate for a single-contributor pre-alpha project with no release cadence. The ceremony of creating release branches and hotfix branches adds friction without corresponding safety benefit at this stage.

**Trunk-based development (direct commits to main):** No feature branches at all. Rejected because it provides no isolation for experimental work. When an AI agent session goes wrong, reverting direct commits to main is more disruptive than discarding a feature branch or worktree.

**Gitflow-lite (main + develop only):** Simpler than full GitFlow but still requires maintaining two long-lived branches. Rejected because the project structure (two disconnected branches: `track-c` and `main`) already adds complexity — a third long-lived branch would compound it.

## When to Revisit

Add GitFlow-like tagging and branch protection when pain emerges:
- Post-alpha with real users requiring stable releases
- Multi-contributor scenario where merge discipline is needed
- CI/CD pipeline that requires tagged releases for deployment

## Related

- [[repo-and-process-debt]] — this decision directly addresses the repo management debt item (Phase 2: define a clear branching strategy)
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]] — the GitHub migration that this branching strategy operates within
- [[2026-02-14-adversarial-multi-agent-review-protocol]] — the review protocol that compensates for GitHub Flow's lack of branch protection
- [[2026-02-09-session-46-git-unification-complete]] — the git unification session that resolved branch proliferation issues
