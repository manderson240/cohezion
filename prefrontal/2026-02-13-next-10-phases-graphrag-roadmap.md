---
title: Next 10 Phases GraphRAG Roadmap
date: '2026-02-13'
status: accepted
tags: [decision, graphrag, roadmap, surrealdb, compound-engineering]
aspect: thinker
neural:
  activation: 0.562
  stage: mature
  cluster: decisions
---

# Next 10 Phases GraphRAG Roadmap

## Context

After [[2026-02-12-session-57-graphrag-complete-phases-1-4-delivered]] delivered the foundational GraphRAG infrastructure (vault ingestion, edge creation, semantic similarity, query interface), the project needed a structured roadmap for the next stages. Phases 1-4 proved the concept: vault notes could be ingested as graph nodes, linked by wiki-link edges and semantic similarity, and queried via a traversal API. But the graph was not yet delivering compound value — it was a data structure, not yet a reasoning tool.

The roadmap needed to follow the principle of **phased validation**: each phase builds on the previous one, can be independently verified, and delivers incremental value. This prevents the "big bang" integration pattern where 10 phases of work are combined and break in unpredictable ways.

## Decision

Define a 10-phase roadmap (Phases 5-14) that extends GraphRAG from data storage to active reasoning:

**Foundation layer (Phases 5-7):**
- **Phase 5:** Graph completion — ensure all vault notes are ingested and all wiki-links create edges (coverage audit)
- **Phase 6:** Metric computation — calculate graph metrics (betweenness centrality, clustering coefficient, PageRank) per node for the [[12d-graph-implementation]]
- **Phase 7:** 3D visualization data export — generate the `.claude/3d-graph-data.json` from SurrealDB graph metrics

**Intelligence layer (Phases 8-10):**
- **Phase 8:** Context-aware retrieval — given a query, traverse the graph to retrieve relevant notes (not just vector similarity, but graph neighborhood)
- **Phase 9:** Gap detection — identify missing edges (notes that should be linked but aren't) and sparse graph regions
- **Phase 10:** Recommendation engine — suggest notes to read or create based on graph topology and the current session's focus

**Compound layer (Phases 11-14):**
- **Phase 11:** Agent journey integration — record agent session trajectories as graph paths through the knowledge base
- **Phase 12:** Cross-session learning — identify patterns across multiple agent sessions using graph analysis
- **Phase 13:** Predictive context — pre-load likely-needed context based on graph traversal patterns from similar past sessions
- **Phase 14:** Self-improving graph — the system identifies and creates new notes to fill knowledge gaps detected in Phase 9

Each phase has explicit success criteria and can be verified independently before proceeding.

## Consequences

**Positive:**
- Phased approach enables validation at each stage — broken phases are caught before compounding
- Each phase delivers incremental value (no "all or nothing" delivery)
- Compound ROI — each phase amplifies the value of all previous phases
- Clear scope boundaries prevent the scope creep that affected pre-Phase 5 sessions

**Negative:**
- 10 phases is a substantial commitment (~20-30 session hours)
- Later phases (11-14) depend on earlier phases working correctly — cascading failure risk
- Roadmap may need revision as earlier phases reveal unexpected constraints
- Risk of over-planning — some phases may be unnecessary once the earlier phases are running

## Alternatives Considered

**All-at-once implementation:** Build all 10 phases in a single large effort. Rejected because it maximizes integration risk and delays feedback on whether the approach works.

**Only foundation layer (Phases 5-7):** Deliver graph metrics and visualization, skip intelligence and compound layers. Rejected because the intelligence layer (context-aware retrieval, gap detection) is where GraphRAG delivers differentiated value over simple vector search.

**Bottom-up discovery (no roadmap):** Let each session discover the next needed capability organically. Rejected based on experience — without a roadmap, sessions repeat discovery work and scope creep consumes 40-60% of token budget.

## Related

- [[graphrag-knowledge-graph-with-surrealdb]] — the GraphRAG system this roadmap extends
- [[surrealdb-agent-context-schema]] — the schema underlying all graph operations
- [[12d-graph-implementation]] — the 12D graph visualization that Phase 6 metrics feed into
- [[2026-02-11-adopt-graphrag-for-vault-knowledge-graph]] — the foundational adoption decision this roadmap extends
- [[2026-02-14-graphrag-verification-and-integration-session]] — the verification session that executed Phase 4 of this roadmap
- [[2026-02-13-phase-2-completion-approved-ready-for-production-deployment]] — Phase 2 sign-off that preceded this roadmap
- [[lessons-graph-integration]] — the graph integration pattern that implements the "connect vault nodes" phases
- [[compound-engineering]] — phased roadmap execution is a compound engineering methodology
- [[experience-feedback-loop]] — Phases 11-14 close the loop between agent sessions and knowledge graph improvement
