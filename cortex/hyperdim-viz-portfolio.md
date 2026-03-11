---
title: "Hyperdim Viz Portfolio"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.440
  stage: growing
  cluster: concepts
---
## Definition

The Hyperdimensional Visualization Portfolio (Hyperdim Viz) is a Cohezion project deliverable that renders the vault's knowledge graph in 3D using an Obsidian plugin built on Three.js and D3-force. It maps 8+ semantic dimensions (connectivity, conceptual depth, temporal distribution, cross-domain presence, completion maturity, recency, semantic similarity, domain clustering) onto visual properties like position, size, color, and edge weight, creating an interactive 3D exploration of the vault's structure.

## Key Properties

- **12D graph data**: The underlying data model encodes 12 semantic dimensions per node, sourced from vault frontmatter and link analysis
- **Three.js rendering**: Force-directed layout with physics simulation for natural clustering of related papers and concepts
- **Obsidian plugin**: Runs as a community plugin within Obsidian, loading graph data from `.claude/3d-graph-data.json`
- **84+ node scale**: Validated with 84 papers and 575 wiki-link edges during Phase 3A testing
- **Interactive exploration**: Users can rotate, zoom, filter by domain, and click nodes to navigate to the underlying vault notes

## Related Papers

- [[2026-02-10-hyperdim-project-status-update]]
- [[2026-02-10-hyperdim-viz-portfolio-launch]]
- [[2026-02-10-PROJECT-COMPLETE-100-PERCENT]]
- [[2026-02-10-session-complete-final-status]]

## Related Concepts

- [[knowledge-graph-systems]] — the knowledge graph infrastructure that hyperdimensional visualization renders
- [[DecisionExplorer]] — the 3D decision graph explorer that visualizes the 12D graph data
- [[2026-02-10-phase3a-3d-graph-validation|Phase 3A: 3D Graph Validation]] — validated 3D graph visualization of vault structure with 84 nodes and 575 edges

## Relevance to Cohezion

The Hyperdim Viz Portfolio is the primary visual interface for the Cohezion knowledge graph, making the vault's structure explorable beyond flat text search. It demonstrates the compound value of systematic cross-linking: as wiki-link density increases through vault enrichment, the 3D graph reveals new clusters and connections that are invisible in flat file browsing.
