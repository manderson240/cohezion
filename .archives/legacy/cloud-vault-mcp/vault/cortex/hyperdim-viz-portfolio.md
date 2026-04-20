---
title: "Hyperdim Viz Portfolio"
date: 2026-02-19
tags: [concept, visualization, knowledge-graph, cohezion-platform]
aspect: knower
neural:
  activation: 0.81
  stage: growing
  synapse_in: 6
  synapse_out: 9
---

# Hyperdimensional Visualization Portfolio

## Definition

The Hyperdimensional Visualization Portfolio (Hyperdim Viz) is a Cohezion project deliverable that renders the vault's knowledge graph in 3D using an Obsidian plugin built on Three.js and D3-force. It maps 8+ semantic dimensions onto visual properties like position, size, color, and edge weight, creating an interactive 3D exploration of the vault's structure.

The core insight: a knowledge graph is inherently high-dimensional (each note has connectivity, depth, recency, domain, maturity, etc.), but humans navigate 3D space intuitively. Hyperdim Viz bridges this gap by **projecting** the high-dimensional semantic space onto 3D coordinates using force-directed layout, then encoding additional dimensions as visual properties (color = domain, size = connectivity, opacity = recency).

## The 12 Semantic Dimensions

| # | Dimension | Source | Visual Encoding |
|---|-----------|--------|----------------|
| 1 | **Connectivity** | Wiki-link count | Node size |
| 2 | **Conceptual depth** | Content length + section count | Node intensity |
| 3 | **Temporal distribution** | Creation date | Color temperature (warm = recent) |
| 4 | **Cross-domain presence** | Tag diversity | Edge color variation |
| 5 | **Completion maturity** | Status field + body completeness | Opacity |
| 6 | **Recency** | Last modified timestamp | Glow/highlight |
| 7 | **Semantic similarity** | Embedding cosine distance | Edge weight / spring strength |
| 8 | **Domain clustering** | Primary tag classification | Color hue |
| 9 | **Inbound link ratio** | Hub vs. authority score | Shape variation |
| 10 | **Research depth** | Citation count + primary source density | Ring indicator |
| 11 | **Interconnection density** | Local clustering coefficient | Particle density |
| 12 | **Evolutionary stage** | neural.stage field | Pulse animation |

## Architecture

```
Vault (.md files)
    ↓ extract_3d_graph.py
.claude/3d-graph-data.json (nodes + edges + 12D vectors)
    ↓ Plugin loads on startup
Three.js Scene (Force-directed 3D layout)
    ↓ User interaction
Click → Navigate to note | Hover → Show metadata | Filter → Domain subgraph
```

## Key Properties

- **Three.js rendering**: Force-directed layout with D3-force physics simulation for natural clustering of related papers and concepts
- **Obsidian plugin**: Runs as a community plugin within Obsidian, loading graph data from `.claude/3d-graph-data.json`
- **1,000+ node scale**: Originally validated with 84 papers and 575 wiki-link edges during Phase 3A; the vault has since grown to 1,072 notes with 11,638 wiki-links
- **Interactive exploration**: Users can rotate, zoom, filter by domain, and click nodes to navigate to the underlying vault notes
- **Performance optimization**: Adjustable quality settings (particle count, edge rendering, force iterations) for smooth interaction at scale
- **Data regeneration**: `extract_3d_graph.py` re-reads all vault files and regenerates the JSON data model

## Related Papers

- [[2026-02-10-hyperdim-project-status-update]]
- [[2026-02-10-hyperdim-viz-portfolio-launch]]
- [[2026-02-10-PROJECT-COMPLETE-100-PERCENT]]
- [[2026-02-10-session-complete-final-status]]

## Related Concepts

- [[knowledge-graph-systems]] — the knowledge graph infrastructure that hyperdimensional visualization renders
- [[DecisionExplorer]] — the 3D decision graph explorer that visualizes the 12D graph data
- [[2026-02-10-phase3a-3d-graph-validation|Phase 3A: 3D Graph Validation]] — validated 3D graph visualization of vault structure with 84 nodes and 575 edges
- [[12D-Projection]] — maps FLUME latent space to 12 interpretable dimensions for Observatory visualization
- [[FLUME-Architecture]] — the VAE providing latent space representations that inform semantic similarity edges
- [[12D-Manifold]] — the 12D Manifold is the mathematical space that the hyperdimensional visualization projects from high-dimensional semantic space into 3D

## Relevance to Cohezion

The Hyperdim Viz Portfolio is the primary visual interface for the Cohezion knowledge graph, making the vault's structure explorable beyond flat text search. It demonstrates the compound value of systematic cross-linking: as wiki-link density increases through vault enrichment, the 3D graph reveals new clusters and connections that are invisible in flat file browsing. The 12D → 3D projection is also a testbed for the broader Cohezion principle that high-dimensional latent spaces can be made navigable through careful dimensionality reduction.
