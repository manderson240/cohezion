---
title: Force-Directed Graph
date: 2026-03-04
tags: [concept, visualization, algorithm, graph-theory]
status: active
aspect: knower
neural:
  activation: 0.88
  stage: growing
  synapse_in: 8
  synapse_out: 9
---

# Force-Directed Graph

A force-directed graph is a visualization technique that positions nodes in a network by simulating physical forces — attraction between connected nodes and repulsion between all nodes — until the system reaches a low-energy equilibrium. The resulting layout reveals the natural structure, clusters, and bridges within the network without requiring manual positioning.

## Definition

Force-directed graph drawing algorithms treat nodes as charged particles and edges as springs. The simulation iteratively applies forces to each node and updates positions using numerical integration (typically velocity Verlet) until the system reaches equilibrium. The final layout minimizes a global energy function that balances edge length uniformity, node separation, and cluster cohesion.

## How It Works

### Forces

| Force | Type | Effect |
|-------|------|--------|
| Link (spring) | Attractive | Pulls connected nodes together to a target distance |
| Charge (Coulomb) | Repulsive | Pushes all nodes apart, preventing overlap |
| Center | Centering | Pulls the graph's center of mass toward the viewport origin |
| Collision | Constraint | Prevents node overlap using radius-based collision detection |
| Bounding box | Constraint | Keeps nodes within a defined area |

### Velocity Verlet Integration

The d3-force module uses velocity Verlet integration with constant unit time step and unit mass. For each tick:

1. Increment alpha by (alphaTarget - alpha) x alphaDecay
2. Apply each registered force, passing the current alpha
3. Decrement each node's velocity by velocity x velocityDecay (simulating friction)
4. Update each node's position by adding velocity

The simulation "cools" over time as alpha decays toward alphaMin, eventually stopping when the layout stabilizes.

### 3D Extension

The d3-force-3d library extends the velocity Verlet integrator to three dimensions, adding z-coordinates to all position and force calculations. Combined with Three.js (WebGL) rendering, this enables interactive 3D network visualization.

## Key Properties

- **Automatic layout:** No manual node positioning required; the physics simulation discovers structure
- **Cluster revelation:** Densely connected subgraphs naturally cluster together due to spring attraction
- **Bridge visibility:** Nodes connecting different clusters are pulled to intermediate positions, making them visually identifiable
- **Interactive:** Users can drag nodes, zoom, rotate (in 3D), and see the simulation respond in real time
- **Scalability trade-off:** O(n-squared) force computation for n-body repulsion; Barnes-Hut approximation reduces this to O(n log n) for large graphs

## Key Libraries

| Library | Description | Rendering |
|---------|-------------|-----------|
| d3-force | Core 2D force simulation | SVG/Canvas |
| d3-force-3d | 1D/2D/3D force simulation | Any renderer |
| 3d-force-graph | Full 3D graph component | Three.js (WebGL) |
| three-forcegraph | Three.js class for force graphs | Three.js |
| ngraph | Alternative physics engine | Any renderer |

## Sources

- [d3-force Documentation](https://d3js.org/d3-force)
- [d3-force-3d on GitHub](https://github.com/vasturiano/d3-force-3d)
- [3d-force-graph on GitHub](https://github.com/vasturiano/3d-force-graph)
- [Force Simulations — D3 by Observable](https://d3js.org/d3-force/simulation)

## Related

- [[12D-Manifold]] — the vault's 12D space is projected to 3D, then rendered via force-directed layout
- [[12D-Projection]] — the projection system that maps high-dimensional positions before force simulation
- [[knowledge-graph-systems]] — force-directed layout visualizes the vault's knowledge graph structure
- [[graph-databases]] — the data structures that force-directed graphs visualize
- [[knowledge-graph-densification]] — denser graphs produce richer, more clustered force layouts
- [[bidirectional-linking]] — each bidirectional link creates a spring edge in the force simulation
- [[compound-engineering]] — force-directed visualization reveals densification progress and knowledge gaps
- [[3d-graph-plugin-installation]] — installation and configuration of the force-directed 3D graph plugin
- [[12d-graph-view-presets]] — preset views that configure force simulation parameters for different analysis modes

## Relevance to Cohezion

The Cohezion vault's 3D graph plugin uses force-directed layout (d3-force-3d + Three.js) to visualize the entire knowledge graph. Each note is a node, each wiki-link is a spring edge, and the simulation reveals topic clusters, bridge papers, and orphan notes. The plugin's 8 semantic dimensions (part of the [[12D-Manifold]]) influence node size, color, and position, making the force-directed graph both a visualization tool and a diagnostic instrument for identifying knowledge gaps during compound engineering sprints.
