# Hyperdimensional Compound Visualization Plugin

Obsidian plugin for visualizing 12-dimensional compound engineering graphs in interactive 3D space.

## Features

### Phase 1 (Complete) ✅

- **3D Graph Rendering**: 84 paper nodes + 575 wiki-link edges rendered with Three.js
- **Interactive Navigation**: Orbit, zoom, pan camera controls with mouse
- **Node Interaction**: Hover for tooltips, click to open notes in Obsidian
- **12D → 3D Projections**: Three preset dimensional mappings with animated transitions
  1. **Temporal Evolution**: Publication Date × Connectivity × Cross-Domain
  2. **Semantic Landscape**: Conceptual Depth × Recency × Connectivity
  3. **Theory-Applied Balance**: Theory/Applied × Completion × Impact
- **Configurable Settings**: Node size, edge opacity, animation speed, render quality

### Future Phases (Planned)

- **Phase 2**: Agent journey tracking - visualize AI agent navigation paths through knowledge graph
- **Phase 3**: Capability measurement dashboard - real-time metrics from Claude interaction logs
- **Phase 4**: Universe simulation - decision fork exploration, task optimization, knowledge gap analysis

## Installation

### Development

```bash
cd /home/mike-anderson/dev/cohezion/hyperdim-viz-plugin
npm install
npm run build
```

### Deploy to Obsidian

```bash
mkdir -p ~/.obsidian/plugins/hyperdim-viz
cp manifest.json styles.css main.js ~/.obsidian/plugins/hyperdim-viz/
```

Then enable the plugin in Obsidian → Settings → Community Plugins.

## Usage

1. **Open Graph**: Click ribbon icon (graph symbol) or run command "Open 12D Graph Visualization"
2. **Navigate**: Left-click drag to orbit, scroll to zoom, right-click drag to pan
3. **Interact**: Hover over nodes for tooltips, click nodes to open notes
4. **Switch Projections**: Use dropdown menu in graph view header to change dimensional mapping
5. **Configure**: Settings → Hyperdimensional Compound Visualization

## Architecture

```
src/
├── main.ts                  # Plugin entry point
├── types.ts                 # Type definitions (12D dimensions, projections)
├── services/
│   └── mcp-client.ts        # Cloud Vault MCP client (port 8360)
├── graph/
│   ├── GraphView.ts         # Three.js 3D rendering engine
│   ├── CameraController.ts  # Custom camera controls (orbit/zoom/pan)
│   └── DimensionMapper.ts   # 12D→3D projection system with animations
└── ui/
    ├── modals.ts            # Full-screen graph modal
    └── settings.ts          # Plugin settings UI
```

## Technical Details

- **Framework**: Obsidian Plugin API + Three.js 0.169.0
- **Language**: TypeScript 4.7.4 (strict mode)
- **Build**: esbuild (single bundle: 888KB)
- **Performance**: Renders 105 nodes in <100ms
- **Data Source**: `.obsidian/3d-graph-data.json` (fallback to Cloud Vault MCP)

## 12 Dimensions

| Dimension | Description | Range | Usage |
|-----------|-------------|-------|-------|
| `connectivity` | Wiki-link density | 0-1 | Hub identification |
| `cross_domain` | Unique domain tags | 0-1 | Interdisciplinary bridges |
| `completion` | Section coverage | 0-1 | Note maturity |
| `temporal` | Publication date | 0-1 | Knowledge timeline |
| `recency` | Last modified | 0-1 | Active areas |
| `conceptual_depth` | Theory vs Applied | 0-1 | Abstract/practical balance |
| `agent_visits` | AI agent tracking | 0-∞ | Future (Phase 2) |
| `capability_score` | Agent performance | 0-1 | Future (Phase 3) |
| `innovation_potential` | Simulation score | 0-1 | Future (Phase 4) |
| `knowledge_gap` | Gap analysis | 0-1 | Future (Phase 4) |
| `impact_score` | Citation/influence | 0-1 | Future |
| `semantic_density` | Concept richness | 0-1 | Future |

## Data Schema

Graph data is loaded from `.obsidian/3d-graph-data.json`:

```json
{
  "meta": {
    "export_date": "2026-02-10T09:12:34",
    "nodes_count": 84,
    "edges_count": 575
  },
  "nodes": [
    {
      "id": "paper-id",
      "label": "Paper Title",
      "file_path": "papers/paper-name.md",
      "type": "paper",
      "connectivity": 0.13,
      "cross_domain": 0.5,
      "completion": 0.67,
      "temporal": 1.0,
      "recency": 1.0,
      "conceptual_depth": 0.5
    }
  ],
  "edges": [
    {
      "source": "paper-1",
      "target": "paper-2",
      "weight": 1.0,
      "type": "wiki_link"
    }
  ]
}
```

## Settings

| Setting | Description | Default |
|---------|-------------|---------|
| Cloud Vault MCP URL | MCP server endpoint | http://localhost:8360 |
| Enable Real-Time Sync | Live graph updates | false |
| Default Projection | Initial view | Temporal |
| Node Size | Base node scale | 5.0 |
| Edge Opacity | Link transparency | 0.3 |
| Animation Speed | Transition speed | 1.0 |
| Max Nodes | Render limit | 500 |
| Enable LOD | Level of detail | true |
| Render Quality | Graphics quality | high |

## Contributing

This plugin is part of the Cohezion compound engineering framework. For issues or feature requests, see the main repository.

## License

MIT

---

**Built for Anthropic Research Engineer portfolio** | Phase 1 Complete: 2026-02-10
