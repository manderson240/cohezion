---
title: "3D Graph Plugin Selection for Cohezion Vault"
date: 2026-02-09
status: proposed
tags: [decision, architecture, visualization, obsidian]
---

# 3D Graph Plugin Selection Decision

## Context

The Cohezion vault currently contains 83 paper notes, 21 concept notes, 7 pattern documents, and multiple decision records. As the vault grows, understanding relationships between concepts, papers, and patterns becomes increasingly complex. The native 2D graph view provides limited perspective on multi-dimensional connections. A 3D graph visualization would enable:

- **Better concept relationship visualization**: Exploring how papers, concepts, and patterns interconnect in three-dimensional space
- **Improved pattern discovery**: Visually identifying clusters of related research areas and architectural patterns
- **Enhanced navigation**: Rotating and zooming to explore vault structure from multiple perspectives
- **Research context**: Understanding the scope and interconnectedness of the knowledge base at a glance

## Options Evaluated

### Option 1: New 3D Graph (RECOMMENDED)

**Repository**: [Apoo711/obsidian-3d-graph](https://github.com/Apoo711/obsidian-3d-graph)

**Status**: Actively maintained as of August 2025 (v2.4.1)

**Stats**:
- GitHub Stars: 33
- Open Issues: 3
- Last Commit: August 1, 2025
- 15 total releases with regular updates
- 74 commits since creation (May 2025)

**Features**:
- Highly customizable 3D force-directed graph
- Interactive canvas: pan, zoom, rotate in real-time
- Advanced filtering using `path:`, `tag:`, and `file:` queries
- Color-coded node groups
- Granular physics tuning: adjust center force, repel force, link force
- Live settings updates without reload
- Intelligent node position caching for smooth performance
- Double-click nodes to open files in new tabs
- Search functionality to find and focus on specific notes

**Tech Stack**: TypeScript (95.2%), MIT Licensed

**Installation**:
1. Open Obsidian Settings → Community Plugins
2. Click "Browse" and search for "New 3D Graph"
3. Click "Install"
4. Close the community plugins window and enable the plugin
5. Open 3D Graph from the ribbon icon (left sidebar) or Command Palette (Ctrl/Cmd + P → "Open 3D Graph")

**Best For**:
- Production vaults requiring stable, well-maintained visualization
- Users wanting extensive customization options
- Large vaults where performance matters

---

### Option 2: InfraNodus 3D Graph View

**Repository**: [noduslabs/infranodus-obsidian-plugin](https://github.com/noduslabs/infranodus-obsidian-plugin)

**Status**: Actively maintained (supports advanced AI features)

**Features**:
- 3D force-directed graph using Force Atlas layout
- Network science insights and pattern analysis
- AI-powered text analysis and topic modeling
- Automatic clustering and gap detection
- Integration with InfraNodus cloud service for extended analytics
- Interactive filtering and focus capabilities

**Pricing**:
- Free basic version (local plugin only)
- Cloud premium: €9/month (includes AI workflows, extended quotas)
- Special code: `INFRANODUSOBSIDIAN2024` for lifetime 50% discount (limited availability)

**Installation**:
1. Open Obsidian Settings → Community Plugins
2. Search for "InfraNodus 3D Graph View" and install
3. Go to plugin settings and add your InfraNodus API key (from https://infranodus.com/subscription)
4. For basic usage, create a free InfraNodus account
5. For advanced features, subscribe to InfraNodus Cloud

**Best For**:
- Research-focused vaults requiring network science analysis
- Users interested in AI-powered insights
- Organizations willing to invest in cloud services

---

### Option 3: 3D Graph View Plugin (chthollyphile)

**Repository**: [chthollyphile/obsidian-3d-graph-view-plugin](https://github.com/chthollyphile/obsidian-3d-graph-view-plugin)

**Status**: Archived (not maintained as of April 30, 2023)

**Stats**:
- GitHub Stars: 33
- Last Commit: July 31, 2022
- 44 total commits
- Project archived and read-only

**Features**:
- 3D force-directed graph using react-force-graph
- Pan, zoom, rotate capabilities
- Early-stage implementation

**Issues**:
- Creator explicitly warns against production use
- Numerous unresolved issues
- No active maintenance
- Incompatible with recent Obsidian versions

**Recommendation**: NOT RECOMMENDED for vault use due to lack of maintenance and stability concerns.

---

## Decision

**Recommended Primary Solution**: **New 3D Graph** (Apoo711/obsidian-3d-graph)

**Rationale**:
1. **Active Maintenance**: Latest update August 2025 with regular releases shows commitment to compatibility
2. **Stability**: Established plugin with 74 commits and 15 releases indicates production-readiness
3. **Feature Set**: Comprehensive customization options for filtering, physics, and appearance
4. **Performance**: Built-in caching and memory safeguards prevent slowdowns in large vaults
5. **Ease of Use**: Straightforward installation from community plugins with intuitive interface
6. **No External Dependencies**: Standalone plugin with no cloud service requirements

**Alternative for Advanced Research**: InfraNodus 3D Graph View if network science analysis and AI insights become priorities in future.

---

## Installation Guide

### For New 3D Graph (Recommended)

1. **Open Obsidian Settings**
   - Click the gear icon in bottom-left corner or press Ctrl/Cmd + Comma

2. **Enable Community Plugins** (if not already enabled)
   - Navigate to: Settings → Community Plugins
   - Toggle "Community Plugins" to ON if disabled

3. **Install New 3D Graph**
   - Click the "Browse" button in the Community Plugins section
   - Search for "New 3D Graph"
   - Click the plugin result
   - Click "Install"

4. **Enable Plugin**
   - Close the browse window
   - Find "New 3D Graph" in your installed plugins list
   - Toggle the plugin to ON

5. **Open 3D Graph**
   - Click the 3D Graph icon in the left ribbon (should appear after installation)
   - OR use Command Palette: Ctrl/Cmd + P → type "Open 3D Graph" → Enter

6. **Configure (Optional)**
   - Click settings gear in the 3D Graph window for customization options
   - Adjust: physics forces, node sizing, link length, colors, filters

### First-Time Usage Tips

- **Filter by Tag**: Use queries like `tag:concept` to highlight specific vault sections
- **Focus on Node**: Click a node to center the view on it and highlight connections
- **Open Files**: Double-click any file node to open it in a new tab
- **Search**: Use the search bar to locate notes and jump to them in the graph
- **Physics Tweaking**: Adjust sliders in settings for different layout styles:
  - Higher repel force = more spread-out nodes
  - Higher center force = tighter clustering
  - Higher link force = tighter connections

---

## Risks and Benefits

### Benefits

| Benefit | Impact |
|---------|--------|
| **Multi-perspective exploration** | Reveals patterns not visible in 2D graph |
| **Better understanding of vault scale** | See actual interconnectedness at a glance |
| **Research navigation** | Jump between papers and concepts visually |
| **Engagement** | 3D visualization makes exploring vault more intuitive |
| **No external dependencies** | New 3D Graph runs locally; no cloud required |

### Risks and Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Performance on large vaults** | Medium | New 3D Graph has caching and node limits; test before critical use |
| **GPU requirements** | Low | 3D rendering may strain older hardware; monitor performance |
| **Learning curve** | Low | Intuitive interface; physics settings optional for basic use |
| **Plugin abandonment** | Low | Apoo711 maintains actively; community forks available if needed |
| **Obsidian version conflicts** | Low | Actively maintained for latest Obsidian; check releases for updates |

---

## Next Steps

1. **User Review**: Verify this decision aligns with vault exploration goals
2. **Installation**: Follow installation guide above
3. **Configuration**: Test different filter queries and physics settings
4. **Feedback Integration**: Document observations about useful visualization patterns
5. **Documentation**: Update vault navigation guide with 3D Graph workflows

---

## References

- [New 3D Graph - Obsidian Community Plugins](https://www.obsidianstats.com/plugins/new-3d-graph)
- [Apoo711/obsidian-3d-graph GitHub Repository](https://github.com/Apoo711/obsidian-3d-graph)
- [InfraNodus Obsidian Plugin Documentation](https://support.noduslabs.com/hc/en-us/articles/14964937162524)
- [Obsidian Plugin Hub - 3D Graph Resources](https://publish.obsidian.md/hub/)

## Related
**Domains**: architecture, integration


[[graph-databases]], [[knowledge-graph-systems]]

## Relevance to Cohezion

[[MCP Infrastructure Architecture]]
[[Compound Engineering]]
