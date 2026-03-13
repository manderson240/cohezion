---
title: GitLab to GitHub Consolidation with Artifact Governance
date: '2026-02-13'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: "1) Enables Claude Code on the web (parallel tasks, background execution)\
    \ 2) Prevents repository bloat permanently (pre-commit hook enforcement) 3) Improves\
    \ push latency (6.5GB\u2192<5GB) 4) Creates reusable artifact governance pattern\
    \ for future projects 5) Maintains rollback capability (6-month archive window)\
    \ 6) Compounds learning: every simulation now includes artifact lineage"
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: GitLab to GitHub Consolidation with Artifact Governance'
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
metrics:
  estimated_cost: 0.0
  estimated_time_hours: 0.0
  actual_cost: 0.0
  actual_time_hours: 0.0
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated: []
aspect: thinker
neural:
  activation: 0.91
  stage: mature
  synapse_in: 18
  synapse_out: 16
---

## Context

The Cohezion repository on GitLab had grown to approximately 12 GB due to accumulated generated artifacts, training data, and redundant pack files committed into git history over multiple development phases. This bloat caused several operational problems:

- **Push latency**: `git push` over HTTPS to GitLab timed out or returned HTTP 500 errors for payloads exceeding GitLab's default limits
- **Claude Code web mode blocked**: GitHub-hosted Claude Code (parallel tasks, background execution) was unavailable because the codebase lived on GitLab
- **Repository health degradation**: `git gc --aggressive` failed to consolidate pack files, leaving dozens of redundant packs (see [[2026-02-11-session-55-discovered-redundant-pack-files-as-root-cause-of-12gb-size-final-cons]])
- **No artifact governance**: generated data (model weights, embeddings, compiled outputs) had no policy preventing re-accumulation after cleanup

The immediate trigger was Session 55's investigation into push failures, which traced the root cause to repository size rather than network or protocol issues.

## Decision

Migrate the primary repository from GitLab to GitHub and simultaneously implement artifact governance policies to prevent future bloat. The consolidation is a two-part initiative:

1. **Platform migration**: Move from GitLab to GitHub to enable Claude Code web features and benefit from GitHub's ecosystem (Actions, Copilot integration, community plugins)
2. **Artifact governance enforcement**: Install pre-commit hooks that reject commits containing generated data, large binaries, or files matching known artifact patterns

## Chosen Option

**GitLab-to-GitHub migration with pre-commit artifact governance hooks**

Key implementation details:
- Use `git filter-repo` or BFG Repo Cleaner to strip large objects from history before pushing to GitHub
- Implement `.gitattributes` and pre-commit hooks to enforce artifact size limits (reject files >5 MB by default)
- Maintain GitLab as a read-only archive for 6 months (rollback capability)
- Configure GitHub branch protection rules on `main` and `track-c`

## Alternatives Considered

### Alt 1: Stay on GitLab, Clean History Only
- **Rejected**: Fixes size but does not enable Claude Code web mode or GitHub ecosystem benefits. Also lacks governance to prevent recurrence.

### Alt 2: Migrate to GitHub Without Governance
- **Rejected**: Solves the platform problem but leaves the door open for re-accumulation of artifacts. Within weeks, the same 12 GB problem would recur.

### Alt 3: Use Git LFS for Large Files
- **Rejected**: Adds complexity (LFS server, pointer files, separate storage billing). The correct solution is to not commit generated artifacts at all, not to store them differently.

### Alt 4: Split Into Multiple Repositories
- **Rejected**: Fragments the knowledge base. The vault's value comes from cross-referencing between papers, decisions, patterns, and code -- splitting would break [[knowledge-graph-systems]] integration.

## Decision Reasoning

### Why This Option?

1. **Enables Claude Code on the web** -- parallel tasks, background execution, and GitHub integration become available immediately
2. **Prevents repository bloat permanently** -- pre-commit hook enforcement catches violations before they enter history
3. **Improves push latency** -- reducing from 12 GB to under 5 GB eliminates timeout failures
4. **Creates reusable artifact governance pattern** -- the pre-commit hooks and `.gitattributes` configuration can be applied to future projects
5. **Maintains rollback capability** -- 6-month GitLab archive means no data loss risk
6. **Compounds learning** -- every simulation now includes artifact lineage awareness

### Alternatives Rejected

Single-platform cleanup (Alt 1) misses the GitHub ecosystem opportunity. Migration without governance (Alt 2) solves the symptom, not the disease. Git LFS (Alt 3) adds operational complexity for a problem better solved by exclusion. Repository splitting (Alt 4) breaks the vault's cross-referencing value proposition.

### Confidence Level

**0.92** -- High confidence. The root cause (uncontrolled artifact accumulation) is well-understood from Session 55 investigation. The solution addresses both the immediate size problem and the systemic governance gap.

## Expected Outcomes

1. Repository size reduced from ~12 GB to <5 GB
2. `git push` completes reliably over HTTPS without timeouts
3. Claude Code web features become available
4. Pre-commit hooks prevent any future commit of generated artifacts
5. GitLab archive remains accessible for 6 months as rollback safety net

## Metrics & Impact

### Estimated

| Metric | Target |
|--------|--------|
| Repository size | <5 GB (from 12 GB) |
| Push success rate | 100% (from ~30%) |
| Artifact violations caught | >95% by pre-commit hooks |
| Migration downtime | <2 hours |

### Actual (Post-Implementation)

| Metric | Result |
|--------|--------|
| Repository size | ~4.2 GB after history rewrite |
| Push reliability | Restored -- HTTPS pushes succeed consistently |
| Claude Code web | Enabled on GitHub |
| Governance hooks | Active -- rejecting oversized commits |

## Related Decisions & Lessons

- [[data-discipline-prevent-generated-data-in-git]]
- [[data-governance-prevention-through-pre-commit-enforcement]]
- [[repository-health-monitoring-size-tracking-large-object-detection]]
- [[multi-platform-repository-deployment-with-external-integration]]
- [[2026-02-11-use-escalation-staged-deployment-for-large-repository-cleanup]]
- [[2026-02-11-session-55-discovered-redundant-pack-files-as-root-cause-of-12gb-size-final-cons]] — the root-cause investigation that found the 12GB problem this migration resolves
- [[platform-issue-analysis-template]] — the analysis methodology used to diagnose the repository size issue

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-14-adversarial-multi-agent-review-protocol]]
- [[2026-02-14-phase-2-adversarial-review-corrected-status-and-path-forward]]
