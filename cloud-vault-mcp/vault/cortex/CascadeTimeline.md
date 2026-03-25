---
title: Cascade Timeline
date: 2026-02-14
tags: [concept, ui, graphrag, visualization]
aspect: knower
neural:
  activation: 0.96
  stage: mature
  synapse_in: 11
  synapse_out: 14
---

# Cascade Timeline

The Cascade Timeline is a proposed UI canvas component for the GraphRAG visualization system that renders the temporal propagation of architectural decisions through the Cohezion vault. Unlike the [[DecisionExplorer]] (which provides search and filtering) or the [[DecisionHealthDashboard]] (which monitors health metrics), the cascade timeline focuses specifically on cause-effect chains: how one decision at time T influences downstream decisions, experiments, and patterns at T+1, T+2, and beyond.

The visualisation draws on temporal data visualisation research — particularly timeline graph visualisation techniques such as non-linear branching timelines, event droplines for clarifying temporal sequencing, and interactive brushing-and-linking for coordinated views. In the cascade timeline, each node is a decision record positioned on a horizontal time axis, with directed edges showing influence relationships (e.g., "Decision A led to Decision B"). Branching structures show where a single decision spawned multiple downstream effects, while convergence points show where independent decision chains merged.

The component is designed for two primary use cases: retrospective analysis (understanding how a past architectural choice propagated through the system) and prospective planning (predicting downstream impact before making a new decision by examining historical cascade patterns for similar decision types).

## Intended Features

- **Temporal cascade view** — Horizontal timeline with decision nodes positioned by date, connected by directed influence edges showing propagation paths
- **Cause-effect highlighting** — Selecting a decision node highlights its full downstream cascade and upstream ancestry, dimming unrelated nodes
- **Branching and convergence** — Multi-tier layout showing parallel cascade branches and convergence points where independent decision chains interact
- **Filter by decision type or domain** — Toggle visibility by decision status (proposed/accepted/deprecated), domain tags, or author
- **Zoom and brush** — Interactive time-range slider for focusing on specific periods; brushing a time window in the overview updates the detail view
- **Impact scoring** — Node size scaled by downstream impact count, making high-influence decisions visually prominent

## Examples

- Selecting the "use event-driven daemon for IO" decision shows its cascade: the SurrealDB sync pattern, the non-blocking observability pattern, and the error-handling-with-DLQ pattern all trace back to it
- Zooming to the Phase 4-7 period reveals a dense cascade cluster where universe simulation decisions triggered experiment, pattern, and compound engineering decisions in rapid succession
- Convergence view shows how two independent decision chains (database schema design and agent context model) converge at the GraphRAG integration point

## Primary Sources

- Tom Sawyer Software: Timeline Graph Visualization — https://blog.tomsawyer.com/timeline-graph-visualization
- Temporal.io: Workflow Visualization with Timeline View — https://temporal.io/blog/lets-visualize-a-workflow
- Timeline Navigators: UI Design Patterns for Time (Rubio & Gilbert, 2023) — https://journals.sagepub.com/doi/10.1177/21695067231192451
- Map Library: Data Visualization Techniques for Temporal Mapping — https://www.maplibrary.org/1582/data-visualization-techniques-for-temporal-mapping/

## Related

- [[DecisionHealthDashboard]] — companion component monitoring decision staleness and consequence validation
- [[DecisionExplorer]] — companion component for semantic search and faceted filtering of decisions
- [[2026-02-14-graphrag-verification-and-integration-session]]
- [[graphrag-knowledge-graph-with-surrealdb]] — the GraphRAG system provides the decision graph data the cascade timeline visualizes
- [[knowledge-graph-systems]] — cascade visualization depends on the typed relationship edges in the knowledge graph
- [[compound-engineering]] — the cascade view makes visible how compound engineering decisions influence downstream outcomes
- [[12D-Manifold]] — decision nodes in the cascade are positioned using 12D manifold coordinates encoding semantic properties
- [[12D-Projection]] — the Decision Cascade lens in the 12D Projection system implements the Cascade Timeline visualization

## Related Concepts

- [[semantic-search]] — the cascade timeline can be filtered by semantically similar decisions, leveraging the vault's embedding index
- [[experience-feedback-loop]] — cascade visualisation reveals feedback loops where downstream outcomes feed back into upstream decision revisions
- [[agent-journey-tracking]] — the cascade timeline parallels agent journey tracking by showing decision propagation paths over time
- [[concept-automation]] — automated cascade analysis could trigger review alerts when a deprecated decision has active downstream dependents
- [[session-retrospective]] — session retrospectives generate the cascade data by recording which decisions influenced which outcomes

## Daily References

- [[2026-02-14-wave-1-delivery-complete]]
- [[2026-02-14-phase-7-preparation-complete]]
- [[2026-02-14-phase-7-execution-complete]]

## Relevance to Cohezion

The Cascade Timeline operationalises Cohezion's commitment to decision traceability. In a compound engineering workflow, decisions accumulate rapidly and their downstream effects can be difficult to track manually. The cascade timeline makes these propagation paths visible, enabling the team to identify high-impact decision points, detect orphaned cascades from deprecated decisions, and validate that the consequences predicted in ADRs actually materialised. It complements the [[DecisionHealthDashboard]] (which monitors individual decision health) with a systemic view of decision interdependencies.
