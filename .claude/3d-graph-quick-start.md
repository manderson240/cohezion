# 3D Graph Quick Start

## Status: ✅ READY TO USE

The COHEZION semantic graph is fully loaded in Obsidian!

**157 nodes | 1,179 links | 94.9% connected**

## Open 3D Graph View

1. **In Obsidian**: Click cube icon in left sidebar, or
2. **Command Palette**: Cmd+P → type "3D Graph" → select preset

## 4 Specialized Views

| View | Icon | Purpose | Try This |
|------|------|---------|----------|
| **Domain Clusters** 🌐 | Colored | See research areas | Look for blue/red clusters |
| **Temporal** ⏳ | Timeline | Knowledge evolution | Scan left→right for trends |
| **Completion** ✅ | Traffic light | Enrichment gaps | Find red (incomplete) nodes |
| **Bridging** 🌉 | Glowing | Integration points | See multi-domain papers elevated |

## Navigation

- **Rotate**: Mouse drag (left button)
- **Pan**: Ctrl+Mouse drag
- **Zoom**: Mouse wheel
- **Focus**: Click a node
- **Open**: Double-click a node
- **Reset**: Press R
- **Pause physics**: Space
- **Toggle labels**: L

## Pro Tips

1. **Start with Domain Clusters**: Best overview of full graph structure
2. **Then Temporal View**: Understand how knowledge evolved
3. **Use Completion Status**: Find papers needing enrichment
4. **Explore Bridging Papers**: Discover integration points between domains

## What You're Seeing

- **Nodes** = Papers, Concepts, Decisions, Patterns, Experiments
- **Links** = Wiki-link relationships (wikilinks in note content)
- **Colors** = Research domain or completion status (varies by preset)
- **Position** = Physics simulation showing semantic proximity

## Key Statistics

- Papers: 84 (core research collection)
- Concepts: 22 (semantic foundations)
- Decisions: 24 (architecture choices)
- Patterns: 24 (reusable solutions)
- Experiments: 3 (hypothesis tests)

**Connectivity**: 149/157 nodes connected (94.9%)

## Common Workflows

### Find Related Research
1. Open Domain Clusters preset
2. Identify your cluster (color group)
3. Double-click papers to explore

### Track Enrichment Progress
1. Open Completion Status preset
2. Look for red (incomplete) nodes
3. Focus and open to edit

### Discover New Research Areas
1. Open Bridging Papers preset
2. Find glowing yellow elevated nodes
3. These span multiple domains - good integration points

### Understand Knowledge Flow
1. Open Temporal View preset
2. Camera positioned: past (left) → future (right)
3. Hubs (tall nodes) = central papers to that era

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| R | Reset camera |
| Space | Pause/resume physics |
| L | Toggle labels |
| 1-4 | Switch preset 1-4 |
| Esc | Deselect node |

## Troubleshooting

**Graph appears empty?**
- Press R to reset
- Check plugin is enabled (Settings → Community Plugins)

**Nodes look weird?**
- Wait for physics to settle (~3-5 seconds)
- Press Space to pause, then Space again to resume

**Can't open a note from graph?**
- Use double-click (not single-click)
- Single-click focuses the node

## Documentation

Full setup guide: `.claude/3d-graph-visualization-setup.md`
Raw graph data: `.claude/3d-graph-data.json`
Extraction script: `.claude/extract_3d_graph.py`

## Next Steps

1. ✅ Open 3D Graph view (cube icon)
2. ✅ Try each preset (Domain Clusters → Temporal → Completion → Bridging)
3. ✅ Explore papers by double-clicking nodes
4. ✅ Use Domain Clusters for regular research browsing

The graph updates when you add new files or wikilinks. Re-run extraction script to refresh.

**Happy exploring!**
