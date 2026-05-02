---
title: Decision Health Dashboard
date: 2026-02-14
tags: [concept, ui, graphrag, visualization]
aspect: knower
neural:
  activation: 0.8
  stage: mature
  synapse_in: 11
  synapse_out: 12
---

# Decision Health Dashboard

The Decision Health Dashboard is a proposed UI canvas component for the GraphRAG visualization system that surfaces the health, staleness, and consequence-validation status of architectural decisions stored in the Cohezion vault. Where the [[DecisionExplorer]] provides search and browse capabilities and the [[CascadeTimeline]] shows temporal cause-effect chains, the health dashboard focuses on operational monitoring: which decisions are overdue for review, which predicted consequences have been validated or invalidated, and which dependency chains have unresolved nodes.

The dashboard treats decisions as living artefacts with a lifecycle (proposed, accepted, deprecated) rather than static records. Each decision has measurable health indicators: age since last review, percentage of predicted consequences that have been observed, and count of downstream decisions that depend on it. When a decision's health score drops below a configurable threshold, it surfaces as an alert requiring attention.

The design draws on principles from software observability dashboards (Grafana, Datadog) applied to the knowledge management domain: decisions are "services" whose health must be monitored, and consequence validation is analogous to integration test coverage. This approach makes architectural governance proactive rather than reactive.

## Intended Features

- **Decision age and review status** — Colour-coded cards showing time since last review with configurable staleness thresholds (30/60/90 days)
- **Consequence tracking** — Side-by-side comparison of predicted vs. actual outcomes for each decision, with validation status (confirmed, refuted, pending)
- **Dependency graph** — Interactive directed graph of decision dependencies, highlighting chains where upstream decisions have changed status
- **Alert surface** — Prioritised list of decisions needing review, sorted by staleness score, unvalidated consequence count, and downstream impact
- **Health score formula** — Composite metric weighing age, consequence validation rate, and dependency chain integrity

## Examples

- A decision accepted 90 days ago with 0/3 consequences validated scores critically low and appears as a red alert
- A deprecated decision with 5 downstream accepted decisions triggers a dependency warning
- A recently reviewed decision with all consequences confirmed scores green and requires no action

## Primary Sources

- Tom Sawyer Software: Timeline Graph Visualization — https://blog.tomsawyer.com/timeline-graph-visualization
- Temporal.io: Workflow Timeline Visualization — https://temporal.io/blog/lets-visualize-a-workflow
- ADR (Architecture Decision Records) practice — https://adr.github.io/

## Related

- [[CascadeTimeline]] — companion component showing temporal cascade effects of decisions
- [[DecisionExplorer]] — companion component for semantic search and faceted filtering of decisions
- [[2026-02-14-graphrag-verification-and-integration-session]]
- [[graphrag-knowledge-graph-with-surrealdb]] — the GraphRAG backend provides the decision metadata the dashboard renders
- [[compound-engineering]] — the dashboard monitors decision health in the compound engineering lifecycle
- [[concept-testing]] — staleness detection and consequence validation are analogous to concept testing applied to decisions
- [[concept-validation]] — consequence validation in the dashboard mirrors the concept validation methodology
- [[12D-Projection]] — health metrics in the dashboard draw on 12D projection dimensions including connectivity, completion maturity, and recency
- [[adversarial-review]] — adversarial review of stale decisions is triggered by dashboard health alerts
- [[knowledge-graph-systems]] — the dashboard visualises health metrics derived from knowledge graph traversal
- [[12D-Manifold]] — health metrics rendered on the dashboard draw on dimensions of the 12D manifold space

## Daily References

- [[2026-02-14-wave-1-delivery-complete]]
- [[2026-02-14-phase-7-preparation-complete]]
- [[2026-02-14-phase-7-execution-complete]]

## Relevance to Cohezion

The Decision Health Dashboard operationalises Cohezion's principle that architectural decisions are not write-once artefacts but living nodes in a knowledge graph that require ongoing validation. By surfacing staleness and unvalidated consequences, it ensures that the vault's decision layer remains trustworthy — a prerequisite for the [[adversarial-review]] and [[compound-engineering]] workflows that depend on decision accuracy.
