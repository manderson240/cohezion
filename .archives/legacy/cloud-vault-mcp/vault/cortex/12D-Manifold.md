---
title: 12D Manifold
date: 2026-03-04
tags: [concept, visualization, cohezion, hyperdimensional]
status: active
aspect: knower
neural:
  activation: 0.95
  stage: mature
  synapse_in: 44
  synapse_out: 21
---

# 12D Manifold

The 12-dimensional manifold is the mathematical space underlying the Cohezion vault's hyperdimensional visualization system. Each vault note is represented as a point in this 12D space, where each dimension encodes a distinct semantic property of the note. The [[12D-Projection]] system then projects this high-dimensional representation down to 3D for interactive visualization.

## Definition

A manifold is a topological space that locally resembles Euclidean space. The 12D Manifold in Cohezion is a 12-dimensional real-valued space where each dimension corresponds to one of the vault's semantic scoring dimensions. Every note in the vault occupies a position in this space determined by its properties, and the distances between points encode semantic similarity.

## The 12 Dimensions

The Cohezion 3D graph plugin computes 8 primary semantic dimensions, with 4 additional derived dimensions:

### Primary Dimensions
1. **Connectivity** — number of inbound and outbound wiki-links (graph degree)
2. **Conceptual Depth** — richness of content (word count, section count, frontmatter completeness)
3. **Temporal Distribution** — how the note's references span across time periods
4. **Cross-Domain Presence** — number of distinct tag domains the note connects to
5. **Completion Maturity** — status progression (stub -> active -> complete)
6. **Recency** — time since last modification, weighted by activity patterns
7. **Semantic Similarity** — embedding-based similarity to neighboring notes (via Ollama)
8. **Domain Clustering** — membership in topic clusters derived from tag co-occurrence

### Derived Dimensions (9-12)
9. **Bridge Score** — betweenness centrality in the wiki-link graph
10. **Velocity** — rate of change in connectivity over recent sessions
11. **Influence Radius** — how many notes are reachable within 2 hops
12. **Coherence** — consistency of the note's topic with its linked neighbors

## Key Properties

- **Continuous:** Each dimension is a real-valued score, not categorical, enabling smooth interpolation between notes
- **Normalized:** All dimensions are scaled to [0, 1] to prevent any single dimension from dominating distance calculations
- **Updateable:** Dimension scores are recomputed after each vault modification, making the manifold a living representation of vault state
- **Projectable:** The 12D space is reduced to 3D via t-SNE or UMAP-like projection for the [[force-directed-graph]] visualization

## Sources

- Internal Cohezion architecture — the 12D Manifold was designed as part of the 3D graph plugin
- [t-SNE: Visualizing High-Dimensional Data (van der Maaten & Hinton)](https://www.jmlr.org/papers/v9/vandermaaten08a.html)

## Related

- [[12D-Projection]] — the projection system that maps 12D manifold positions to 3D screen coordinates
- [[force-directed-graph]] — the 3D visualization uses force-directed layout after projection from 12D
- [[knowledge-graph-systems]] — the manifold is computed from the vault's knowledge graph structure
- [[semantic-search]] — semantic similarity (dimension 7) uses the same embeddings as vault search
- [[compound-engineering]] — the manifold provides a quantitative view of vault health for compound engineering sprints
- [[knowledge-graph-densification]] — densification changes manifold positions by increasing connectivity dimensions
- [[the-new-science-framework]] — Step 3: 12 parameters = the minimal specification space for a knowledge state
- [[agents-as-exotic-vacuum-objects]] — the 12D vault manifold parallels the 12 Standard Model parameters
- [[theory-of-everything-synthesis]] — 12 parameters = VR rule-set (Campbell) = Standard Model = vault manifold
- [[CascadeTimeline]] — decision cascade timeline positions decisions in the 12D manifold to visualise temporal propagation
- [[cohezion-platform-overview]] — the platform for which the 12D Manifold provides the quantitative visualization infrastructure
- [[DecisionExplorer]] — decision cluster layout in the domain cluster view derives positions from 12D manifold coordinates
- [[DecisionHealthDashboard]] — health metrics rendered on the dashboard draw on dimensions of the 12D manifold space
- [[FLUME-Architecture]] — FLUME compresses 12D trajectories into a 256D latent vector; the manifold is the input space
- [[hyperdim-viz-portfolio]] — the hyperdimensional visualization portfolio is a direct implementation of the 12D Manifold projection into 3D
- [[Ouroboros-Loop]] — the Ouroboros Loop monitors vault health by tracking trajectories through the 12D manifold during active sessions

## Daily References

- [[2026-02-09-12d-graph-foundation]] — Day 1: infrastructure complete for the 12D graph visualization system
- [[2026-02-09-3d-graph-plugin-installation-complete]] — 3D Graph plugin v2.4.1 installed and configured for 12D visualization
- [[2026-02-10-phase1-complete]] — Phase 1 complete: 5 computational dimensions implemented
- [[2026-02-10-phase2-kickoff]] — Phase 2 kickoff: semantic dimensions via Ollama
- [[2026-02-10-phase2-semantic-dimensions-complete]] — Phase 2 complete: semantic dimensions via Ollama in 8K tokens
- [[2026-02-10-phase3-kickoff]] — Phase 3 kickoff: 3D graph visualization
- [[2026-02-10-phase3-progress]] — Phase 3 progress: tasks 1-2 complete, plugin specialist active
- [[2026-02-10-phase3b-plugin-ready]] — Phase 3b: 3D graph plugin installed and ready for dimensional data
- [[2026-02-10-phase3-complete]] — Phase 3 complete: 12D graph visualization ready in 1 day vs 1 week planned

### Indigenous Cosmology Cross-Validation

- [[indigenous-cosmologies-toe-synthesis]] — Step 3 of the 10-step chain: specification space; multiple traditions independently identify a 12-parameter-class requirement
- [[vedic-hindu-cosmology-and-toe]] — 25 Tattvas as the specification space (overcomplete but converges to ~12 independent parameters)
- [[dogon-cosmology-and-toe]] — 266 signs as the complete specification basis for all creation; reducible to key dimensions

## Relevance to Cohezion

The 12D Manifold is the quantitative foundation for the Cohezion vault's visualization and analytics capabilities. By encoding multiple semantic properties as dimensions, it enables the 3D graph plugin to cluster related notes, highlight bridges between topic domains, and visually identify thin or disconnected areas of the knowledge graph that need attention during compound engineering sprints.
