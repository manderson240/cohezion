---
title: "Role-Based Multi-Agent Coordination"
date: "2026-02-26"
tags: [pattern, multi-agent, coordination, agent-architecture]
aspect: thinker
neural:
  activation: 0.76
  stage: mature
  synapse_in: 8
  synapse_out: 11
---

# Role-Based Multi-Agent Coordination

## Problem

When multiple AI agents work on the same task (code review, plan verification, complex analysis), uncoordinated agents produce redundant work: they check the same things, miss the same blind spots, and generate conflicting recommendations. A general-purpose "review this code" prompt given to 3 identical agents yields 3 similar reviews that overlap by 80%, while leaving critical perspectives unexamined.

The core issue is that **identical agents have identical blind spots**. Three generalist reviewers will all catch obvious issues and all miss the same subtle ones.

## Solution

Assign each agent a **specialized role** with a distinct perspective, evaluation criteria, and focus area. Roles are defined by:

1. **Persona** — a named role with domain expertise (e.g., "security reviewer", "performance critic", "test quality auditor")
2. **Evaluation criteria** — specific checklist items the role must assess
3. **Focus area** — the subset of the codebase or plan the role examines
4. **Output format** — structured findings with severity levels (must_fix, should_fix, suggestion)

### Role Definition Template

```yaml
role:
  name: "correctness-reviewer"
  persona: "Senior engineer focused on functional correctness"
  criteria:
    - Does the implementation match the specification?
    - Are edge cases handled (null, empty, boundary values)?
    - Are error paths tested?
    - Do types match across function boundaries?
  focus: "src/ directory — production code only"
  output: "Structured findings with file:line references"
```

### Coordination Patterns

**Parallel independent review:** Each role runs independently on the same input, produces findings, then findings are merged and deduplicated. Used in [[2026-02-14-adversarial-multi-agent-review-protocol]] for code review.

```
Task → [correctness-reviewer] → findings-A
     → [test-quality-reviewer] → findings-B  → Merge → Final Report
     → [architecture-reviewer] → findings-C
```

**Sequential handoff:** Each role processes in order, passing enriched context to the next. Used when later roles depend on earlier roles' findings.

```
Task → [researcher] → context → [planner] → plan → [implementer] → code
```

**Adversarial pairing:** Two roles with opposing objectives review the same artifact. One advocates for the approach, the other challenges it. Used in [[2026-02-10-compound-linking-plan-adversarial-review]].

```
Plan → [advocate: "why this works"] → support-case
     → [challenger: "why this fails"] → risk-case → Decision
```

### Example: 4-Role Adversarial Review

From the compound linking plan review:

| Role | Perspective | Focus |
|------|------------|-------|
| Cost Critic | "Is this worth the token investment?" | ROI analysis |
| QA Expert | "Will this actually work in production?" | Testability, reliability |
| Infrastructure Skeptic | "Does the infra support this?" | Dependencies, scaling |
| Timeline Skeptic | "Can this be delivered on schedule?" | Scope, complexity |

## When to Use

- **Code review** — assign correctness, testing, and architecture roles for comprehensive coverage
- **Plan verification** — assign advocate and challenger roles for balanced assessment
- **Complex analysis** — assign domain-specific roles (e.g., security, performance, accessibility)
- **Multi-agent task execution** — assign researcher, planner, and executor roles for structured delivery

**Do not use for:**
- Simple tasks where a single agent suffices
- Tasks with no meaningful decomposition into perspectives
- Time-critical work where parallel overhead exceeds the benefit

## Related Decisions

- [[2026-02-14-adversarial-multi-agent-review-protocol]] — foundational example: assigns correctness-reviewer, test-quality-reviewer, and architecture-reviewer roles to parallel agents
- [[2026-02-14-agent-orchestration-design-3-tier-hotwarmcold-model-rotation]] — role-based model selection (routing agent to execution agent tiers)
- [[2026-02-10-compound-linking-plan-adversarial-review]] — example of 4-role adversarial review (cost-critic, QA-expert, infrastructure-skeptic, timeline-skeptic)
- [[2026-03-03-vault-knowledge-graph-densification-complete-via-parallel-agent-teams]] — parallel agent teams (Alpha/Beta/Gamma/Delta) with batch-scoped roles

## Related Patterns

- [[mini-adversarial-review-checkpoints]] — checkpoint pattern that uses role-based agents inline during implementation
- [[3-tier-hotwarmcold-model-rotation]] — tier-based model assignment is a form of role-based coordination at the infrastructure layer
- [[pattern-compound-engineering]] — compound engineering sessions use role-based coordination for extraction and review phases

## Related Concepts

- [[multi-agent-systems]] — role-based coordination is a foundational design pattern for multi-agent system architectures
- [[agent-architecture]] — role specialization (researcher, planner, executor, reviewer) is a key agent architecture design decision
- [[workflow-orchestration]] — the orchestration layer routes tasks to role-specific agents based on task characteristics
- [[adversarial-review]] — adversarial review is the quality assurance application of role-based coordination
