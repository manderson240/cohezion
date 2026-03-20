---
title: "12D Projection"
date: 2026-03-04
tags: [concept, cohezion, visualization, dimensionality-reduction, latent-space]
aspect: knower
neural:
  activation: 0.89
  stage: mature
  synapse_in: 6
  synapse_out: 15
---

# 12D Projection

## Definition

The 12D Projection is Cohezion's dimensionality reduction layer that maps the FLUME VAE's 256-dimensional latent space down to 12 interpretable dimensions for visualization in the Observatory UI. Each of the 12 dimensions corresponds to a named semantic property of vault content -- connectivity, conceptual depth, temporal distribution, cross-domain presence, completion maturity, recency, semantic similarity, domain clustering, algorithm complexity, implementation difficulty, interdisciplinary transfer, and impact score -- making the projection both visualizable and human-interpretable.

## Key Properties

- **Named dimensions:** Unlike generic dimensionality reduction (PCA, t-SNE, UMAP) which produces opaque axes, the 12D Projection assigns each axis a specific semantic meaning derived from vault frontmatter and graph topology metrics. This makes the visualization self-documenting.
- **Honest about projection loss:** The Observatory displays a persistent depth indicator -- "Viewing 12D projection of 2048D semantic state" -- acknowledging that the visualization is necessarily a lossy compression of the full latent space.
- **JourneyTracker integration:** The JourneyTracker component records a 12D coordinate for every agent execution step, producing trajectories that can be visualized as paths through the 12-dimensional space. These trajectories reveal how agent sessions navigate across conceptual, temporal, and complexity dimensions.
- **Three-lens visualization:** The 12D coordinates feed into three Observatory lenses: Semantic Terrain (knowledge graph topology), Git Trajectory (codebase paths through latent space), and Decision Cascade (compound engineering decisions over time).
- **Graph presets:** The 3D graph plugin supports configurable projection presets that select subsets of the 12 dimensions for focused visualization -- for example, projecting onto connectivity/depth/recency for a "knowledge health" view.

## The 12 Dimensions

| Dimension | Measures |
|-----------|----------|
| Connectivity | Number of inbound/outbound wiki-links |
| Conceptual depth | Depth of explanation (surface vs. deep analysis) |
| Temporal distribution | When the content was created relative to project timeline |
| Cross-domain presence | How many different domain tags the content touches |
| Completion maturity | Percentage of expected sections filled |
| Recency | How recently the content was modified |
| Semantic similarity | Embedding-based similarity to related content |
| Domain clustering | Degree of clustering within a domain |
| Algorithm complexity | Complexity of algorithms discussed |
| Implementation difficulty | Practical difficulty of implementation |
| Interdisciplinary transfer | Applicability across different fields |
| Impact score | Composite measure of influence within the knowledge graph |

## Examples

- A research paper with high connectivity, high cross-domain presence, and high impact score appears near the center of the Semantic Terrain lens, indicating it is a hub concept.
- An agent session trajectory that moves rapidly along the algorithm complexity axis while staying low on implementation difficulty suggests theoretical exploration without practical implementation.
- The hash-based journey tracking experiment produced meaningless 12D trajectories because the hash function distributed points randomly rather than semantically, validating that FLUME latent vectors are necessary for meaningful projections.

## Primary Sources

- Internal: [[2026-02-09-12d-graph-surrealdb-integration]] -- the integration plan for 12D projections with the SurrealDB graph backend
- Internal: [[2026-02-09-12d-graph-refined-plan]] -- the refined plan for 12D projection implementation
- Internal: [[12d-graph-implementation]] -- implementation pattern for the 12D graph visualization

## Related Concepts

- [[FLUME-Architecture]] -- the VAE that produces the high-dimensional latent space that 12D Projection reduces
- [[agent-journey-tracking]] -- records the 12D coordinates at each agent execution step, producing visualizable trajectories
- [[surrealdb]] -- stores the 12D trajectory data and graph relationships for efficient query
- [[semantic-search]] -- the semantic similarity dimension directly leverages embedding-based search
- [[knowledge-graph-systems]] -- the connectivity and domain clustering dimensions are computed from the vault's knowledge graph structure
- [[VAE-Encoder]] -- the encoder produces the 256D latent vectors that the 12D Projection reduces to interpretable dimensions
- [[Ouroboros-Loop]] -- the Ouroboros Loop reads 12D coordinates to assess system health across interpretable dimensions
- [[cohezion]] -- the 12D Projection is the bridge between Cohezion's internal representations and human understanding
- [[cohezion-platform-overview]] — the platform whose Observatory UI depends entirely on the 12D Projection for its three visualization lenses
- [[DecisionExplorer]] — Decision Explorer uses 12D coordinates to cluster related decisions in semantic space
- [[DecisionHealthDashboard]] — health metrics in the dashboard draw on 12D projection dimensions (connectivity, maturity, recency)
- [[universe-simulation]] -- simulation trajectories are projected into the 12D space for visualization and analysis
- [[data-analysis]] -- the 12D dimensions (connectivity, depth, recency, etc.) are derived from quantitative analysis of vault metadata
- [[12D-Manifold]] — the 12-dimensional mathematical space that this projection reduces to 3D
- [[force-directed-graph]] — the 3D visualization layout applied after projection
- [[CascadeTimeline]] — the Decision Cascade lens in the 12D Projection system implements the Cascade Timeline visualization for temporal decision propagation

## Relevance to Cohezion

The 12D Projection is the bridge between Cohezion's internal latent representations and human understanding. Without it, the FLUME manifold would be a useful but opaque embedding space. With it, developers and researchers can visually explore how their knowledge base is structured, identify underconnected concepts, track agent behavior through interpretable dimensions, and discover cross-domain patterns that would be invisible in flat file browsing. The Observatory UI depends entirely on this projection layer for its three-lens visualization.
