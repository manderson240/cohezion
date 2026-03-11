---
title: Repository Health Governance Skill Created
date: '2026-02-12'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Repository health governance was successfully implemented in Task #7
    but existed only as pre-commit hooks + CI/CD workflow. Codifying as PRIME skill:
    1. Makes governance reusable across projects 2. Enables automated invocation via
    skill registry 3. Documents procedures for team knowledge 4. Provides Charter-aligned
    metrics (HIHO stability) 5. Creates foundation for Task #12 (Daily Platform Health
    Digest)

    HIHO stability range (4-8GB) represents optimal repository size: small enough
    for fast operations, large enough for comprehensive history.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Repository Health Governance Skill Created'
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
  activation: 0.631
  stage: mature
  cluster: decisions
---

## Context

Session 55 revealed that the Cohezion repository had grown to 12 GB due to uncontrolled accumulation of generated artifacts, training data, and redundant pack files (see [[2026-02-11-session-55-git-aggressive-gc-doesnt-consolidate-packs-manual-repack-forced]]). Task #7 implemented pre-commit hooks and a CI/CD workflow to enforce artifact governance, but these fixes existed only as:

1. **Pre-commit hooks**: Shell scripts in `.git/hooks/` that reject oversized commits
2. **GitHub Actions workflow**: CI pipeline that checks repository health metrics
3. **Manual procedures**: Documented in scattered session notes, not codified

This left three gaps:
- **Not reusable**: Hooks were project-specific; other repositories could not benefit
- **Not discoverable**: No agent could query "how do I check repository health?"
- **Not measurable**: No metrics tracking whether governance was being followed

The [[2026-02-12-prime-skill-pattern-as-governance-framework]] decision established PRIME skills as the standard governance framework. Repository health governance was the natural first candidate for PRIME codification.

## Decision

Create a PRIME skill (`PRIME_REPOSITORY_HEALTH_GOVERNANCE`) that codifies repository health monitoring, artifact prevention, and size tracking as a reusable, indexed, MCP-discoverable procedure.

## Chosen Option

**PRIME skill codification with HIHO (Health Index for Healthy Operations) stability metric:**

The skill includes:
1. **Concepts**: Repository health indicators (size, pack count, large objects, artifact patterns)
2. **Instructions**: 8 procedural rules with decision trees for common scenarios
3. **HIHO stability range**: Target repository size of 4-8 GB -- small enough for fast operations, large enough for comprehensive history
4. **Pre-commit enforcement**: Pattern-based rejection of generated artifacts (`.pyc`, `node_modules/`, model weights, embeddings)
5. **Validation checklist**: 6-point operator checklist for verifying governance
6. **Charter alignment**: Links to Constitution principle S02 (Execution Excellence) and S05 (Observability)

## Alternatives Considered

### Alt 1: Keep Governance as Shell Scripts Only
- **Rejected**: Shell scripts are not discoverable by MCP queries, not portable to other projects, and not linked to platform governance principles. They enforce but do not educate.

### Alt 2: Document in CLAUDE.md Only
- **Rejected**: CLAUDE.md is a single file that all sessions read. Adding repository-specific governance procedures to it bloats the file and adds content irrelevant to most sessions.

### Alt 3: Create a Standalone Tool (CLI or Service)
- **Rejected**: A standalone tool requires installation, maintenance, and integration. A PRIME skill leverages existing MCP infrastructure (skill registry, `query_skills` tool) with zero additional infrastructure.

## Decision Reasoning

### Why This Option?

1. **Reusability across projects**: Any repository can benefit by importing the PRIME skill
2. **Automated discoverability**: Agents encountering repository size issues can query the MCP skill registry and find the governance procedures automatically
3. **HIHO metric creates a measurable target**: "Is the repo within 4-8 GB?" is a clear, measurable health indicator
4. **Pre-commit hooks are enforcement; PRIME skill is education**: Hooks block bad commits but do not explain why or how to fix. The PRIME skill provides the full context.
5. **Foundation for Task #12**: The Daily Platform Health Digest (Task #12) needs a codified definition of "healthy repository" -- this PRIME skill provides it.

### Alternatives Rejected

Shell scripts alone are not discoverable. CLAUDE.md alone bloats the common configuration. A standalone tool adds unnecessary infrastructure.

### Confidence Level

**0.90** -- High confidence. The PRIME skill format is proven (see [[2026-02-12-prime-skill-pattern-as-governance-framework]]). Repository health monitoring procedures are well-understood from Session 55.

## Expected Outcomes

1. Repository health governance reusable across all Cohezion projects
2. Agents can discover health procedures via MCP `query_skills("repository health")`
3. HIHO metric tracked in daily health digests
4. Pre-commit hook violations explained with links to the PRIME skill (educational, not just blocking)
5. New team members understand repository governance on first session

## Metrics & Impact

### Estimated

| Metric | Before | After |
|--------|--------|-------|
| Governance discoverability | Manual (grep docs) | Automated (MCP query) |
| Projects using governance | 1 (cohezion-vault) | All projects with PRIME skill |
| Repository health metric | Undefined | HIHO: 4-8 GB target |
| Governance violations caught | Pre-commit only | Pre-commit + PRIME education |

### Actual (Post-Implementation)

PRIME skill created and indexed. Pre-commit hooks reinforced with PRIME skill links. Repository size stabilized within HIHO range after [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance|GitHub migration]].

## Related Decisions & Lessons

- [[repository-health-monitoring-size-tracking-large-object-detection]]
- [[prime-skill-creation-governance-pattern]]
- [[data-discipline-prevent-generated-data-in-git]]
- [[data-governance-prevention-through-pre-commit-enforcement]]
- [[2026-02-12-prime-skill-pattern-as-governance-framework]]

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-adversarial-multi-agent-review-protocol]]
