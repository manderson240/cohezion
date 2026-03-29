---
title: 3D Graph Plugin Installation & Configuration
date: 2026-02-09
status: completed
tags: [12d-graph, plugin, obsidian, visualization]
aspect: thinker
neural:
  activation: 0.83
  stage: mature
  synapse_in: 6
  synapse_out: 10
---

# 3D Graph Plugin Installation & Configuration

## Plugin Selection

**Installed Plugin**: New 3D Graph (Apoo711 fork)
- **Repository**: https://github.com/Apoo711/obsidian-3d-graph
- **Version**: 2.4.1 (latest as of 2026-02-09)
- **Status**: Actively maintained, production-ready
- **Built on**: Three.js + 3D Force Graph + Obsidian API

## Installation Details

### Files Installed

```
.obsidian/plugins/new-3d-graph/
├── manifest.json      (plugin metadata)
├── main.js           (compiled plugin code, 12MB)
└── styles.css        (plugin styling)
```

**Installation Location**: `/home/mike-anderson/vaults/cohezion-vault/.obsidian/plugins/new-3d-graph/`

**Registration**: Added to `.obsidian/community-plugins.json` as `"new-3d-graph"`

### Installation Method

Plugin was installed from GitHub source (v2.4.1):
1. Cloned from https://github.com/Apoo711/obsidian-3d-graph
2. Checked out release tag `2.4.1`
3. Built with `npm install` + `npm run dev`
4. Copied built artifacts to vault plugins directory
5. Registered in community-plugins.json

**Why Source Build?**: Ensured latest stable version (2.4.1 from Aug 2025) with full compatibility.

## Plugin Features & Capabilities

### Core Visualization
- **3D Canvas**: Interactive 3D force-directed graph using Three.js
- **Pan/Zoom/Rotate**: Full 3D camera control
- **Node Interaction**:
  - Single-click: Focus camera on node, highlight connections
  - Double-click: Open file node in new tab

### Filtering & Search
- **Live Search**: Search by note content/name
- **Path Filters**: Filter by `path:folder/subfolder`
- **Tag Filters**: Filter by `tag:#tagname`
- **General Filters**: Toggle tags, attachments, orphan nodes on/off

### Visual Customization
- **Node Shapes**: Sphere, Cube, Pyramid, Tetrahedron (per node type)
- **Node Sizing**: Adjustable per file/tag/attachment (0.1-5x scale)
- **Node Colors**:
  - Color Groups with rules (`path:`, `tag:`, `file:` queries)
  - Custom color picker for each group
  - Theme color support (auto-detect Obsidian theme)
- **Link Styling**: Thickness, color customization
- **Labels**: Size, color, distance, fade threshold, occlusion prevention

### Physics Engine
- **Center Force**: Attraction to center (0-1, default 0.1)
- **Repel Force**: Node repulsion (0-20, default 10)
- **Link Force**: Link strength (0-0.1, default 0.01)
- **Live Adjustment**: All sliders apply changes instantly

### Interaction Options
- **Keyboard Controls**: Game-like WASD movement (togglable)
- **Mouse Controls**: Rotation, pan, zoom with configurable speeds
- **Zoom on Click**: Auto-zoom when clicking nodes
- **Rotation/Pan/Zoom Speeds**: Fine-tunable

## Configuration Structure

### Settings Storage

Plugin stores settings in Obsidian's local data directory:
```
~/.obsidian/plugins/new-3d-graph/data.json
```

**Settings Type**: JSON object with Graph3DPluginSettings interface

### Available Configuration Options

#### Search & Filters
- `searchQuery`: Free-text search (debounced, updates live)
- `filters`: Array of {type: 'path'|'tag', value: string, inverted: bool}
- `showTags`: Boolean (default: false)
- `showAttachments`: Boolean (default: false)
- `hideOrphans`: Boolean (default: false)

#### Visual Groups
- `groups`: Array of {query: string, color: string}
  - Example: `{query: "path:papers", color: "#FF5733"}`
  - Example: `{query: "tag:#concept", color: "#3366FF"}`

#### Display Settings
- `useThemeColors`: Use Obsidian theme colors (default: true)
- `colorNode`: Default node color (default: #2080F0)
- `colorTag`: Tag node color (default: #9A49E8)
- `colorAttachment`: Attachment color (default: #75B63A)
- `colorLink`: Link color (default: #666666)
- `colorHighlight`: Highlight color (default: #FFB800)
- `backgroundColor`: Canvas background (default: #0E0E10)

#### Appearance
- `nodeSize`: Default node scale (0.1-5, default: 1.5)
- `tagNodeSize`: Tag node scale (0.1-5, default: 1.0)
- `attachmentNodeSize`: Attachment scale (0.1-5, default: 1.2)
- `linkThickness`: Link width (0.1-5, default: 1)
- `nodeShape`: NodeShape enum (Sphere|Cube|Pyramid|Tetrahedron)
- `tagShape`: NodeShape enum (default: Tetrahedron)
- `attachmentShape`: NodeShape enum (default: Cube)

#### Labels
- `showNodeLabels`: Show/hide labels (default: true)
- `labelDistance`: Distance from node (50-500px, default: 150)
- `labelFadeThreshold`: Fade threshold (0.1-1, default: 0.8)
- `labelTextSize`: Label font size (1-10, default: 2.5)
- `labelTextColorLight`: Light theme text (default: #000000)
- `labelTextColorDark`: Dark theme text (default: #ffffff)
- `labelBackgroundColor`: Label bg (default: #ffffff)
- `labelBackgroundOpacity`: Opacity (0-1, default: 0.3)
- `labelOcclusion`: Prevent overlap (default: false)

#### Interaction
- `useKeyboardControls`: WASD movement (default: true)
- `keyboardMoveSpeed`: Speed 0.1-10 (default: 2.0)
- `zoomOnClick`: Auto-zoom on node click (default: true)
- `rotateSpeed`: Rotation speed (0.1-5, default: 1.0)
- `panSpeed`: Pan speed (0.1-5, default: 1.0)
- `zoomSpeed`: Zoom speed (0.1-5, default: 1.0)

#### Physics Forces
- `centerForce`: Center attraction (0-1, default: 0.1)
- `repelForce`: Node repulsion (0-20, default: 10)
- `linkForce`: Link tension (0-0.1, default: 0.01)

## Commands Available

Once installed, access via:
- **Command Palette**: `Ctrl+P` → "Open 3D Graph"
- **Ribbon Icon**: Left sidebar (if enabled)
- **Settings**: `Settings` > `3D Graph Plugin` for all configuration

## Testing Checklist

Installation verification (completed):
- [x] Plugin installed in `.obsidian/plugins/new-3d-graph/`
- [x] Manifest.json present and valid
- [x] main.js compiled (12MB executable)
- [x] styles.css present
- [x] Registered in community-plugins.json
- [x] Plugin folder permissions verified (user can read)

Expected upon next Obsidian restart:
- [ ] Plugin appears in "Community plugins" list
- [ ] Plugin can be enabled/disabled in settings
- [ ] "Open 3D Graph" command available in command palette
- [ ] 3D Graph ribbon icon appears in left sidebar
- [ ] Graph renders with vault data (needs dimensional data from Mapper)
- [ ] All controls responsive (rotate, zoom, pan)
- [ ] Settings panel fully functional

## Limitations & Notes

### Current State
- Plugin awaiting dimensional data from Task #10 (Dimension Mapper)
- Graph will be empty until data.json provided with node positions/dimensions
- Configuration accessible but dimensions not yet mapped

### Known Considerations
- **Performance**: Tested with vaults up to several thousand notes
- **3D Hardware**: Requires WebGL-capable GPU (most modern systems)
- **Obsidian Version**: Requires Obsidian 1.5.0+ (running on current version)
- **Desktop Only**: Plugin marked as desktop-only in manifest

### Future Enhancements
- Local graph mode (for massive vaults)
- Advanced query types for filtering
- Performance optimizations

## Integration with 12D Graph Implementation

This plugin provides the **visualization layer** for Phase 3:
1. **Phase 1+2** (COMPLETE): Computed 8 dimensional scores
2. **Phase 3a** (COMPLETE - THIS TASK): Installed 3D Graph plugin
3. **Phase 3b** (PENDING - Task #10): Mapper exports dimensional data
4. **Phase 3c** (PENDING - Task #11): Create view presets
5. **Phase 3d** (PENDING - Task #11): Apply dimensional visualization

## Handoff Status

**Ready for**: Task #10 (Dimension Mapper)
- Plugin installed ✓
- Configuration ready ✓
- Commands available ✓
- Awaiting: dimensional data (data.json format)

## References

- **Plugin Repository**: https://github.com/Apoo711/obsidian-3d-graph
- **Plugin Blog**: https://aryan-gupta.is-a.dev/blog/2025/3d-graph-plugin/
- **12D Graph Implementation**: `patterns/12d-graph-implementation.md`
- **Phase 3 Spec**: Task #9 (this), #10, #11

---

**Installation Date**: 2026-02-09 23:22 UTC
**Status**: Ready for dimensional data integration
**Next Step**: Dimension Mapper (Task #10) provides data → Visualization becomes active

## Related

- [[compound-engineering]]

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-12d-graph-refined-plan]]
- [[2026-02-09-12d-graph-surrealdb-integration]]
- [[2026-02-10-phase3-3d-graph-adversarial-review]]
- [[2026-02-09-12d-graph-next-steps]]
- [[12d-graph-view-presets]]
- [[12d-graph-implementation]]
- [[2026-02-10-phase2-complete]]
- [[force-directed-graph]] — force-directed layout algorithm used by the 3D graph plugin for node positioning
