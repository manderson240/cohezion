---
title: Charter-Aligned Scoring Formula
date: '2026-02-12'
status: accepted
tags: [decision, inferred]
decision_reasoning:
  reasoning_chain:
  - sequence: 1
    content: 'Context: Charter-Aligned Scoring Formula'
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
  activation: 0.514
  stage: growing
  cluster: decisions
---

## Context

As the Cohezion vault grew beyond 80+ research papers, architectural decisions, and experiment records, the need emerged for a systematic method to evaluate and prioritize work items against the project's charter objectives. Without a scoring formula, prioritization was ad hoc -- driven by recency bias or whichever task was most salient in the current session. The charter defines Cohezion's mission as building a [[compound-engineering]] system where each unit of work makes subsequent work easier, but there was no quantitative way to measure whether a proposed task actually advanced that mission.

Strategic alignment scoring is a well-established practice in portfolio management. The [Balanced Scorecard Institute](https://balancedscorecard.org/bsc-basics-overview/) framework evaluates performance across financial, customer, internal process, and organizational capacity dimensions. [PMI's strategic alignment research](https://www.pmi.org/learning/library/strategic-alignment-projects-selection-process-1421) demonstrates that projects aligned to strategy are 57% more likely to deliver business benefit. The challenge was adapting these enterprise-scale concepts to a single-developer agentic AI project.

## Decision

Adopt a charter-aligned scoring formula that evaluates each proposed task or feature against three weighted dimensions:

1. **Compound Value (40%)** -- Does completing this task make future tasks measurably easier? Measured by reusable artifacts produced (patterns, tools, knowledge graph density).
2. **Knowledge Density (35%)** -- Does this task increase the vault's knowledge graph connectivity and reduce information silos? Measured by new cross-links created and concept coverage expanded.
3. **Token Efficiency ROI (25%)** -- Does the expected [[token-efficiency]] gain justify the implementation cost? Measured by estimated tokens saved per future session versus tokens invested.

Each dimension is scored 0-10, then weighted and summed to produce a composite alignment score (0-10). Tasks scoring below 4.0 are deferred; tasks above 7.0 are prioritized for immediate execution.

## Consequences

- **Positive:** Prioritization becomes repeatable and auditable. The scoring formula is itself a compound asset -- once defined, every future prioritization decision is faster. Session retrospectives can compare predicted scores against actual outcomes, creating a feedback loop.
- **Positive:** Forces explicit articulation of why a task matters, reducing impulse-driven work.
- **Negative:** The formula introduces overhead for small tasks. Trivial fixes and documentation updates should bypass scoring entirely.
- **Negative:** Weights are initially subjective and require calibration over multiple sessions.

## Alternatives Considered

- **Unweighted checklist** -- Simple yes/no for each dimension. Rejected because it loses granularity needed for close prioritization calls.
- **Pure ROI calculation** -- Score only by [[roi-analysis|token efficiency ROI]]. Rejected because it ignores knowledge density and compound value, which are harder to quantify but equally important.
- **OKR-based alignment** -- Quarterly objectives with key results. Rejected as too heavyweight for a single-developer project with weekly iteration cycles. The [OKR alignment approach](https://mooncamp.com/blog/organizational-alignment) works well for teams but adds unnecessary ceremony here.
- **No formula (intuition-based)** -- Continue with ad hoc prioritization. Rejected because it produced inconsistent results and made session handoffs harder when context about "why this task?" was lost.

## See Also

- [[roi-analysis]] -- the ROI dimension of the scoring formula
- [[compound-engineering]] -- the philosophical foundation: each unit of work compounds into the next
- [[token-efficiency]] -- the efficiency dimension measuring cost-per-task improvement
- [[token-efficiency-patterns]] -- concrete patterns that score high on the token efficiency dimension
- [[experience-feedback-loop]] -- scoring calibration happens through the feedback loop comparing predicted vs actual value
- [[session-retrospective]] -- retrospectives provide the data to validate and adjust formula weights
- [[concept-validation]] -- scoring formula itself requires validation against real outcomes
- [[alignment]] -- charter alignment is a domain-specific application of the broader alignment concept
