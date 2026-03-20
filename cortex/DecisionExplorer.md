---
title: Decision Explorer
date: 2026-02-14
tags: [concept, ui, graphrag, visualization]
aspect: knower
neural:
  activation: 0.8
  stage: mature
  synapse_in: 4
  synapse_out: 11
---

# Decision Explorer

The Decision Explorer is a proposed interactive UI component for the GraphRAG visualization system that provides semantic search, faceted filtering, and comparison capabilities across all architectural decisions stored in the Cohezion vault. While the [[DecisionHealthDashboard]] monitors decision health metrics and the [[CascadeTimeline]] visualises temporal cause-effect chains, the Decision Explorer focuses on discovery and analysis: finding relevant decisions, understanding their context, and comparing alternatives.

The explorer treats the vault's decision directory as a structured dataset with rich metadata: status (proposed, accepted, rejected, deprecated), domain tags, creation date, last review date, consequence predictions, and relationship edges to other decisions, experiments, and patterns. [[semantic-search]] over decision content enables natural-language queries like "how did we handle database schema migration?" rather than requiring exact keyword matches.

The component is designed for three workflows: onboarding (new team members exploring the decision history), pre-decision research (checking whether a similar decision has already been made), and audit (verifying that decisions in a domain are consistent and up-to-date). Cluster views group related decisions by domain, revealing patterns in decision-making across the project.

## Intended Features

- **Full-text semantic search** — Natural-language queries over decision content using the vault's embedding index, returning ranked results by relevance
- **Faceted filtering** — Multi-select filters by status (proposed/accepted/rejected/deprecated), domain tags, date range, and author
- **Domain cluster view** — Force-directed graph layout grouping decisions by domain, with edge thickness indicating relationship strength
- **Side-by-side comparison** — Split-panel view for comparing related decisions, highlighting differences in context, rationale, and consequences
- **Decision lineage** — Trace a decision's ancestry (what prompted it) and descendants (what it influenced), linking to the [[CascadeTimeline]] for temporal context

## Examples

- Searching "event-driven architecture" returns the daemon decision, the SurrealDB sync decision, and the non-blocking observability decision, clustered by their shared domain
- Filtering by status "deprecated" reveals decisions that have been superseded, with links to their replacements
- Comparing two competing authentication decisions side-by-side shows which trade-offs each optimised for

## Primary Sources

- ADR (Architecture Decision Records) — https://adr.github.io/
- Elastic App Search: faceted search patterns — https://www.elastic.co/guide/en/app-search/current/facets.html

## Related

- [[DecisionHealthDashboard]] — companion component monitoring decision staleness and consequence validation
- [[CascadeTimeline]] — companion component showing temporal cascade effects of decisions
- [[2026-02-14-graphrag-verification-and-integration-session]]
- [[hyperdim-viz-portfolio]] — the hyperdimensional visualization portfolio this explorer is part of
- [[decision-linker]] — the decision linker populates the relationships that the decision explorer renders

## Related Concepts

- [[12D-Projection]] — the domain cluster layout in the Decision Explorer uses 12D projection coordinates to position decisions in semantic space

- [[semantic-search]] — the explorer's primary search mechanism uses embedding-based semantic similarity ranking
- [[graphrag-knowledge-graph-with-surrealdb]] — the GraphRAG backend provides the decision graph data the explorer queries
- [[knowledge-graph-systems]] — the explorer renders a subset of the knowledge graph focused on decision nodes and their relationships
- [[concept-testing]] — the explorer could surface decisions whose consequences have not been validated, flagging them for concept testing
- [[adversarial-review]] — the explorer supports adversarial review by making it easy to find and compare prior decisions on the same topic
- [[compound-engineering]] — the explorer enables compound engineering teams to discover relevant prior decisions before making new ones
- [[12D-Manifold]] — decision cluster positions in the domain cluster view are derived from 12D manifold coordinates

## Relevance to Cohezion

The Decision Explorer is a key component of Cohezion's decision governance infrastructure. As the vault accumulates hundreds of architectural decisions, the ability to search, filter, and compare them becomes essential for maintaining decision consistency. The explorer ensures that new decisions are informed by historical context — preventing redundant or contradictory decisions — and supports the [[adversarial-review]] workflow by making prior art easily discoverable.
