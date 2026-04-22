---
title: Implementation First, Infrastructure Later
date: 2026-02-23
tags: [methodology, compound-engineering, pattern]
status: active
aspect: knower
neural:
  activation: 0.92
  stage: mature
  synapse_in: 6
  synapse_out: 12
---

# Implementation First, Infrastructure Later

The "implementation first, infrastructure later" pattern is a development methodology that prioritises proving core feature behaviour before investing in supporting infrastructure — monitoring, caching, scaling, CI/CD pipelines, or observability dashboards. The principle: don't build the runway until you know the plane will fly.

This pattern directly counters the common anti-pattern of premature infrastructure investment, where teams spend significant effort building monitoring, alerting, and scaling systems for features whose requirements are not yet validated. In agentic AI development, where iteration cycles are fast and pivots are frequent, premature infrastructure can represent 40-60% of wasted token and engineering budget on features that are later redesigned or abandoned.

The pattern was extracted through [[meta-learning]] from the Kyutai project postmortem, which revealed a 7.6x cost savings when teams deferred infrastructure until after core behaviour was validated. It formalises a YAGNI-aligned workflow: implement the minimal feature, validate it works with real inputs, then layer on infrastructure in proportion to proven need. The validation step is critical — it is not "skip infrastructure forever" but "defer infrastructure until you have evidence it is needed."

## Core Rule

Don't build the runway until you know the plane will fly.

## Key Properties

- **Validation before investment** — The core feature must demonstrate correct behaviour with real inputs before any infrastructure work begins
- **Proportional infrastructure** — Infrastructure complexity should match proven scale requirements, not hypothetical future needs
- **Fast pivot support** — By deferring infrastructure, the cost of pivoting or abandoning a feature is limited to the implementation itself
- **Token efficiency** — In agentic AI workflows, premature infrastructure consumes tokens on scaffolding that may never be used; deferral directly reduces [[token-efficiency]] waste
- **Measurable threshold** — Infrastructure investment is triggered by concrete evidence: observed latency issues, actual concurrency contention, or validated monitoring requirements

## Examples

- **Kyutai project** — Initial implementation built an elaborate monitoring dashboard before the core sync feature worked; the postmortem found 7.6x cost savings by deferring infrastructure
- **SurrealDB sync** — The [[surrealdb-sync-pattern]] was first implemented as direct writes; batching and dead-letter queues were added only after concurrent agent sessions revealed performance bottlenecks
- **Vault context hooks** — Context loading was implemented as a simple script; caching, metrics, and configuration management were added after the core load/save cycle was validated

## Primary Sources

- YAGNI principle (Martin Fowler) — https://martinfowler.com/bliki/Yagni.html
- Lean Software Development: premature optimization as waste — https://en.wikipedia.org/wiki/Lean_software_development

## Related

- [[compound-engineering]] — this pattern is a core principle in compound engineering methodology
- [[implementation-first-infrastructure-later]] — the concept this pattern codifies; the pattern adds code-level implementation guidance
- [[token-efficiency]] — implementation-first directly reduces token waste by avoiding premature infrastructure investment
- [[roi-analysis]] — the Kyutai postmortem ROI data (7.6x savings) validates this pattern quantitatively
- [[adversarial-review]] — adversarial review validates implementation before infrastructure investment begins
- [[meta-learning]] — this pattern was extracted via meta-learning from the Kyutai token waste postmortem

## Related Concepts

- [[concept-testing]] — concept testing validates that an implementation works before infrastructure is layered on
- [[experience-feedback-loop]] — the feedback loop determines when infrastructure investment is warranted based on observed behaviour
- [[agent-loop-architecture]] — agent loops should start simple (direct execution) and add orchestration infrastructure only when needed
- [[concept-optimization]] — optimisation (including infrastructure optimisation) is deferred until the implementation is stable
- [[ai-safety]] — safety infrastructure (guardrails, monitoring) is an exception — safety-critical infrastructure should not be deferred

## Relevance to Cohezion

This pattern is embedded in Cohezion's [[compound-engineering]] methodology as a first-class validation principle. Every new feature in the Cohezion framework follows the sequence: implement minimally, validate with [[adversarial-review]], then add infrastructure proportional to validated need. The Kyutai postmortem that originated the pattern is one of the most-referenced lessons in the vault, and the 7.6x ROI data point serves as quantitative evidence for the approach.
