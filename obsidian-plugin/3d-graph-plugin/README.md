# 3D Graph Visualization Plugin for Obsidian

A revolutionary 3D visualization plugin for Obsidian that brings your knowledge graph to life. Visualize 84 research papers and their semantic relationships across 8 dimensions of meaning in stunning three-dimensional space.

## Features

- **3D Interactive Visualization**: Navigate papers in full 3D space using intuitive mouse controls
- **8-Dimensional Semantic Analysis**: View papers across connectivity, conceptual depth, temporal distribution, cross-domain presence, completion maturity, recency, semantic similarity, and domain clustering
- **84 Research Papers**: Complete visualization of the Cohezion vault's research foundation with automatic loading
- **Real-Time Search & Filtering**: Find papers instantly by title, and filter by any dimension
- **Physics Simulation**: Force-directed layout algorithm ensures papers naturally cluster by semantic similarity
- **Performance Optimized**: High-quality rendering with adjustable quality settings
- **Responsive Design**: Scales from mobile to large displays
- **Keyboard Navigation**: Efficient controls for power users

## Installation

### From Obsidian Plugin Marketplace
1. Open Obsidian and go to **Settings** → **Community plugins**
2. Click **Browse** and search for **"3D Graph"**
3. Click **Install** and then **Enable**
4. The plugin is ready to use!

### Manual Installation
1. Download the latest release from [GitHub Releases](https://github.com/cohezion/obsidian-3d-graph-plugin)
2. Extract the `.zip` file into your vault's `.obsidian/plugins/` directory:
   ```
   ~/.obsidian/plugins/3d-graph-plugin/
   ```
3. Reload Obsidian (or restart)
4. Go to **Settings** → **Community plugins** and enable **3D Graph**

### From Source
```bash
git clone https://github.com/cohezion/obsidian-3d-graph-plugin.git
cd obsidian-3d-graph-plugin
npm install
npm run build
# Copy main.js, manifest.json to your .obsidian/plugins/3d-graph-plugin/ directory
```

## Usage Guide

### Opening the Graph

**Method 1: Ribbon Icon**
- Click the network icon on the left ribbon (looks like a connected network diagram)

**Method 2: Command Palette**
- Press `Ctrl/Cmd + P` and type "Open 3D Graph"
- Press Enter

**Method 3: Keyboard Shortcut** (default not set, configure in settings)
- Customize a hotkey in **Settings** → **Hotkeys** → Search for "3D Graph"

### Navigation Controls

#### Mouse Controls
| Action | Input |
|--------|-------|
| Rotate view | Click and drag with mouse |
| Zoom in/out | Mouse wheel or pinch gesture |
| Pan | Right-click and drag (or Shift + left-click and drag) |
| Select paper | Left-click on a node |
| Deselect | Left-click on empty space |

#### Keyboard Controls
| Key | Action |
|-----|--------|
| `↑` / `↓` / `←` / `→` | Rotate view |
| `W` / `A` / `S` / `D` | Pan up/left/down/right |
| `+` / `-` | Zoom in / out |
| `Space` | Center view on selected paper |
| `R` | Reset view to default |
| `F` | Focus on selected paper with zoom |
| `?` | Show help overlay |
| `Escape` | Close help / deselect |

#### Touch Controls (Mobile/Tablet)
- **One finger drag**: Rotate view
- **Two finger pinch**: Zoom in/out
- **Two finger pan**: Pan the view
- **Tap node**: Select paper

### Search & Filtering

#### Quick Search
1. Open the 3D graph
2. Press `Ctrl/Cmd + F` or click the search icon
3. Type a paper title or keyword
4. Matching papers highlight; click to focus

#### Advanced Filters

The filter panel (left sidebar) allows fine-grained control:

**Connectivity Filter** (0-1 scale)
- Isolated papers (0.0): Papers with few semantic connections
- Hub papers (1.0): Central, highly connected papers
- Use case: Find influential papers or niche topics

**Conceptual Depth Filter** (0-1 scale)
- Theory papers (0.0): Foundational, abstract work
- Applied papers (1.0): Practical implementations
- Use case: Find cutting-edge applications or foundational theory

**Temporal Filter** (0-1 scale)
- Historical (0.0): Classic, established papers
- Recent (1.0): Latest research
- Use case: Track research trends or find seminal works

**Completion Filter** (0-100%)
- Incomplete research (0%): Emerging topics with few linked papers
- Mature research (100%): Well-developed fields with extensive coverage
- Use case: Identify knowledge gaps or mature domains

**Recency Filter** (0-1 scale)
- Stale (0.0): Papers not recently accessed/updated
- Fresh (1.0): Recently accessed papers
- Use case: Filter your current research focus

**Domain Filter** (categorical)
- Select from 15+ domains (AI, NLP, Visualization, etc.)
- Use case: Stay within a specific research area

### Selected Paper Panel

When you click on a paper, a right-side panel shows:
- **Title**: Full paper title
- **Authors**: List of author names
- **Year**: Publication year
- **Path**: Vault note location
- **Dimensions**: Visual breakdown of the 8 dimensions
- **Similar Papers**: Top semantic neighbors with similarity scores
- **Related Notes**: Other vault notes linking to this paper

Click "Open in Vault" to navigate to the paper's note in your vault.

### Performance Settings

In **Settings** → **3D Graph Visualization**:

**Performance Mode**
- **High Quality (>30 FPS)**: Smooth rendering with full effects
  - Best for high-end systems
  - Maximum visual detail
- **Low Power (<30 FPS)**: Battery-friendly rendering
  - Best for laptops/tablets
  - Reduced particle effects and shadows

**Physics Simulation Speed**
- **Slow**: More stable, takes longer to converge
- **Normal**: Balanced (default)
- **Fast**: Quick convergence, less stable

Adjust based on your hardware and desired visual quality.

### Customization

#### Node Size Scaling
Controls the visual size range of paper nodes:
- **Small** (0.5x - 1.0x): Compact, space-efficient
- **Medium** (0.75x - 1.5x): Balanced (default)
- **Large** (1.0x - 2.0x): Larger, easier to interact with

#### Label Visibility
When to display paper titles:
- **Always On**: Titles always visible (can be cluttered)
- **On Hover**: Titles appear when you hover over nodes (default)
- **Off**: No labels (minimal clutter)

#### Color Palette
Choose a color scheme:
- **Default**: Distinct colors for each domain
- **Colorblind**: Accessible colors (deuteranopia-friendly)
- **Grayscale**: Black and white scheme

## Troubleshooting

### Graph won't load
- **Check vault location**: Ensure your vault contains papers in the standard Cohezion structure
- **Restart Obsidian**: Sometimes the plugin needs a fresh start
- **Check console**: Look at Obsidian's Developer Console (`Ctrl/Cmd + Shift + I`) for errors
- **Solution**: Click the refresh icon in the graph header

### Poor performance / lag
- **Lower quality settings**: Switch to "Low Power" mode in Settings
- **Reduce visible papers**: Use filters to hide papers (e.g., show only 1-2 domains)
- **Close other plugins**: Other plugins may compete for GPU resources
- **Update GPU drivers**: Ensure your graphics drivers are current

### Papers not visible
- **Check dimensions**: Some papers may be outside current filter ranges
- **Reset filters**: Click "Reset All" in the filter panel
- **Verify data**: Ensure papers have valid YAML frontmatter with dimension data
- **Check browser console**: Look for parsing errors

### Crashes or freezes
- **Clear cache**: Uninstall and reinstall the plugin
- **Check Obsidian version**: Ensure you're on the latest version
- **Disable hardware acceleration** (if on old system)
- **Report issue**: Post on [GitHub Issues](https://github.com/cohezion/obsidian-3d-graph-plugin/issues)

### Keyboard shortcuts not working
- **Check hotkey conflicts**: Settings → Hotkeys → search "3D Graph"
- **Other plugins may override**: Disable conflicting plugins
- **Clear hotkeys**: Remove custom hotkeys and use defaults
- **Try Command Palette**: Use `Ctrl/Cmd + P` instead

### Mobile / touch issues
- **Use two-finger gestures**: Pinch to zoom, two-finger pan
- **Tap and hold**: Use long-press to select nodes
- **Rotate device**: Landscape mode provides more screen space

## Settings Reference

All settings are located in **Obsidian Settings** → **3D Graph Visualization**:

| Setting | Default | Options |
|---------|---------|---------|
| Node Size Scaling | Medium | Small / Medium / Large |
| Label Visibility | On Hover | On / Hover / Off |
| Physics Speed | Normal | Slow / Normal / Fast |
| Color Palette | Default | Default / Colorblind / Grayscale |
| Performance Mode | High Quality | High Quality / Low Power |

Settings are saved automatically and persist across sessions.

## Keyboard Reference

### Main Controls
- `Ctrl/Cmd + P`: Open command palette
- `?`: Show in-app help
- `R`: Reset view
- `Space`: Focus on selected paper
- `Escape`: Close help/deselect

### Navigation
- Arrow keys: Rotate view
- `W/A/S/D`: Pan
- `+/-`: Zoom

### Search
- `Ctrl/Cmd + F`: Open search
- `Enter`: Focus first result

## Data Format

Papers are loaded from Obsidian vault notes with this YAML frontmatter:

```yaml
---
title: "Paper Title"
authors: ["Author 1", "Author 2"]
year: 2023
dimensions:
  connectivity: 0.75      # 0-1
  conceptual_depth: 0.6   # 0-1
  temporal: 0.8           # 0-1
  cross_domain: 5         # 1-15
  completion: 75          # 0-100
  recency: 0.9            # 0-1
  semantic_similarity: 0.25  # 0-0.5
  similar_papers:
    - title: "Related Paper 1"
      score: 0.85
    - title: "Related Paper 2"
      score: 0.72
---
```

## Performance

Typical performance on modern hardware:
- **Papers loaded**: 84
- **Edges rendered**: ~500
- **Frame rate**: 30-60 FPS (depending on settings)
- **Memory usage**: ~50-100 MB
- **Load time**: <2 seconds

For older hardware, use "Low Power" mode for improved performance.

## Known Limitations

- **Paper limit**: Optimized for ~100-200 papers; larger graphs may lag
- **Mobile**: Full feature set requires landscape orientation
- **Dimension data**: All 8 dimensions required in paper YAML (uses defaults if missing)
- **Search**: Currently searches titles only (not content)
- **Export**: Graph visualizations cannot be exported as images (workaround: screenshot)

## Contributing

Contributions welcome! See [DEVELOPMENT.md](DEVELOPMENT.md) for setup and contribution guidelines.

## License

MIT License - See LICENSE file for details.

## Support

- **Bug reports**: [GitHub Issues](https://github.com/cohezion/obsidian-3d-graph-plugin/issues)
- **Feature requests**: [GitHub Discussions](https://github.com/cohezion/obsidian-3d-graph-plugin/discussions)
- **Documentation**: Check [DEVELOPMENT.md](DEVELOPMENT.md) for architecture details

## Credits

Built by the Cohezion team with ❤️ using Three.js, D3-Force, and the Obsidian API.

---

**Version**: 0.1.0 | **Last Updated**: 2026-02-13
