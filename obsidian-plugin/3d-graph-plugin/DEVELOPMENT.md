# Development Guide: 3D Graph Plugin

This guide covers the architecture, development setup, build process, and contribution guidelines for the Obsidian 3D Graph plugin.

## Architecture Overview

The plugin uses a modular architecture with clear separation of concerns:

```
src/
├── main.ts              # Plugin entry point, settings management
├── types/
│   └── Paper.ts         # Type definitions for graph data
├── physics/
│   └── ForceLayout.ts   # Force-directed layout simulation
├── data/
│   └── DataLoader.ts    # Load & parse papers from vault
├── renderer/
│   └── ThreeRenderer.ts # Three.js 3D rendering engine
├── ui/
│   ├── GraphModal.ts    # Main visualization UI component
│   ├── FilterPanel.ts   # Filter sidebar
│   └── MetadataPanel.ts # Selected paper info panel
└── __tests__/           # Jest test files
```

### Data Flow

```
DataLoader (papers from vault YAML)
    ↓
GraphData (structured nodes + edges)
    ↓
ForceLayout (position nodes in 3D space)
    ↓
ThreeRenderer (render to Three.js scene)
    ↓
GraphModal (UI interaction + filtering)
```

### Key Components

#### 1. DataLoader
**File**: `src/data/DataLoader.ts`

Loads and parses papers from the vault:
- Reads `.md` files from vault
- Extracts YAML frontmatter (title, authors, dimensions, similar_papers)
- Builds GraphData with nodes and edges from semantic similarity
- Handles missing dimension data with sensible defaults

**Key method**: `async loadPapersFromVault(): Promise<GraphData>`

#### 2. ForceLayout
**File**: `src/physics/ForceLayout.ts`

Physics-based spatial layout using D3-Force:
- Maps 8 dimensions to 3D coordinates (X: connectivity, Y: conceptual_depth, Z: temporal)
- Runs force simulation (repulsion, collision, links, center)
- Converges when alpha < 0.001 or max iterations reached
- Returns `Map<paperId, THREE.Vector3>` with final positions

**Key method**: `async positionNodes(timeoutMs): Promise<Map<string, THREE.Vector3>>`

#### 3. ThreeRenderer
**File**: `src/renderer/ThreeRenderer.ts`

Three.js 3D visualization:
- Creates scene, camera, renderer
- Renders paper nodes as spheres/boxes
- Renders edges as lines
- Implements raycasting for mouse selection
- Updates on each animation frame
- Supports zoom, pan, rotate camera controls

**Key methods**:
- `render(graphData, positions)`
- `setHovered(paperId)`
- `setSelected(paperId)`
- `updateFilters(filters)`

#### 4. GraphModal
**File**: `src/ui/GraphModal.ts`

Obsidian Modal component:
- Container for visualization
- Handles keyboard input
- Manages filter state
- Shows selected paper metadata
- Coordinates between DataLoader, ForceLayout, ThreeRenderer

### 8 Dimensions

Papers are enriched across 8 semantic dimensions. The visualization maps these to visual properties:

| Dimension | Type | Range | Visual Property | Use Case |
|-----------|------|-------|-----------------|----------|
| **Connectivity** | Scalar | 0-1 | Node X position | Identify hubs vs isolated papers |
| **Conceptual Depth** | Scalar | 0-1 | Node Y position | Theory vs applied distinction |
| **Temporal** | Scalar | 0-1 | Node Z position | Historical vs cutting-edge |
| **Cross Domain** | Count | 1-15 | Hue/color | Domain clustering |
| **Completion** | % | 0-100 | Node size (0.5x-2.0x) | Research maturity |
| **Recency** | Scalar | 0-1 | Opacity (30-100%) | Freshness/current focus |
| **Semantic Similarity** | Scalar | 0.0-0.5 | Edge weight | Relationship strength |
| **Similar Papers** | List | N/A | Edge presence | Create links in graph |

## Setup & Development

### Prerequisites
- Node.js 16+ and npm 8+
- Obsidian v0.15.0+
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/cohezion/obsidian-3d-graph-plugin.git
cd obsidian-3d-graph-plugin
```

2. Install dependencies:
```bash
npm install
```

3. Create symlink to your vault's plugin directory:
```bash
ln -s $(pwd) ~/.obsidian/plugins/3d-graph-plugin
# Or copy: cp -r . ~/.obsidian/plugins/3d-graph-plugin/
```

4. Reload Obsidian or restart the application

### Development Workflow

#### Watch Mode (Auto-rebuild on changes)
```bash
npm run dev
```
- Watches `src/` for changes
- Rebuilds `main.js` automatically
- Reload Obsidian to see changes (Ctrl+Shift+R)

#### Single Build
```bash
npm run build
```
- Bundles all TypeScript into `main.js`
- Creates source maps for debugging
- Ready for distribution

#### Linting
```bash
npm run lint
```
- Runs ESLint to check code style
- Fixes auto-fixable issues
- Ensure code passes before committing

#### Testing
```bash
npm run test
```
- Runs Jest test suite
- Shows coverage report
- Run with `--watch` for continuous testing:
```bash
npm test -- --watch
```

### TypeScript Configuration

The project uses strict TypeScript mode. Key rules:

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "esModuleInterop": true
  }
}
```

**Guidelines**:
- Use explicit types for all function parameters/returns
- Avoid `any` type (use `unknown` + type guard if needed)
- All interfaces in `types/Paper.ts` for type sharing
- Use `null` not `undefined` for missing values

### Debugging

#### Browser DevTools
1. Open Obsidian
2. Press `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Option+I` (macOS)
3. Check Console tab for errors
4. Set breakpoints in Sources tab
5. Reload plugin to trigger breakpoints

#### Plugin Console
Add debug logging:
```typescript
console.log('Debug message:', value);
console.warn('Warning:', error);
console.error('Error:', exception);
```

These appear in Obsidian's Developer Console.

#### Source Maps
Build includes source maps (`main.js.map`) for debugging TypeScript directly in DevTools.

## File Structure

### `src/main.ts` (136 LOC)
Plugin entry point and settings management.

**Responsibilities**:
- Plugin lifecycle (onload, onunload)
- Settings persistence (load/save)
- Ribbon icon & command registration
- Settings tab with UI controls

**Settings**:
- `nodeScaling`: 'small' | 'medium' | 'large'
- `labelVisibility`: 'on' | 'hover' | 'off'
- `physicsSpeed`: 'slow' | 'normal' | 'fast'
- `colorPalette`: 'default' | 'colorblind' | 'bw'
- `performanceMode`: 'high' | 'low'

### `src/types/Paper.ts` (120 LOC)
Type definitions used across the entire plugin.

**Key types**:
- `Dimension`: 8-dimensional properties of a paper
- `PaperNode`: A paper with position, color, size, opacity
- `GraphEdge`: Link between two papers with similarity weight
- `GraphData`: Complete graph (nodes, edges, metadata)
- `GraphFilters`: Filter state (sliders + search)
- `GraphStatistics`: Current view statistics

### `src/physics/ForceLayout.ts` (160 LOC)
D3-Force simulation for spatial layout.

**Key methods**:
- `constructor(graphData)`: Initialize simulation
- `positionNodes()`: Run simulation and return positions
- `tick(iterations)`: Manually advance simulation
- `getAlpha()`: Get current simulation velocity
- `stop()`: Stop the simulation

**Forces**:
- `forceManyBody()`: Repulsive force (keeps papers apart)
- `forceCollide()`: Collision detection (prevent overlap)
- `forceLink()`: Attractive force (semantic neighbors)
- `forceCenter()`: Center gravity

### `src/data/DataLoader.ts` (estimated ~200 LOC, in progress)
Load and parse papers from vault.

**Key methods**:
- `loadPapersFromVault()`: Discover all .md files, parse YAML
- `extractDimensions(metadata)`: Extract 8 dimensions
- `buildGraphEdges(papers)`: Create edges from similar_papers
- `applyDefaults(paper)`: Fill missing dimensions

### `src/renderer/ThreeRenderer.ts` (estimated ~300 LOC, in progress)
Three.js rendering engine.

**Key methods**:
- `render(graphData, positions)`: Create scene + geometry
- `setHovered(paperId)`: Highlight node on hover
- `setSelected(paperId)`: Show metadata for selected paper
- `updateFilters(filters)`: Hide/show papers based on filters
- `dispose()`: Clean up Three.js resources

### `src/ui/GraphModal.ts` (estimated ~250 LOC, in progress)
Main UI component (Obsidian Modal).

**Key methods**:
- `onOpen()`: Initialize UI when modal opens
- `onClose()`: Cleanup when modal closes
- `updateSelectedPaper(paperId)`: Show metadata panel
- `handleKeydown(event)`: Keyboard input handling
- `updateFilters(filters)`: Apply filter changes

## Contributing

### Code Style

- **Indentation**: 2 spaces
- **Naming**: camelCase for variables/methods, PascalCase for classes/interfaces
- **Imports**: Sort alphabetically, group by type
- **Comments**: JSDoc for public functions, inline for complex logic
- **Formatting**: Run `npm run lint` to auto-fix style issues

### Commit Message Format

```
type(scope): description

Optional longer explanation...
```

**Types**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

**Examples**:
- `feat(renderer): add node highlight on hover`
- `fix(physics): prevent NaN in force calculations`
- `docs(readme): update keybinds section`
- `test(loader): add YAML parsing tests`

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make changes and commit: `git commit -m "feat: my feature"`
4. Add tests for new functionality
5. Run `npm run lint && npm run test` to verify
6. Push to fork: `git push origin feat/my-feature`
7. Open PR against main branch
8. Address review feedback

### Testing

#### Writing Tests

Tests use Jest and are located in `src/__tests__/`:

```typescript
// src/__tests__/MyComponent.test.ts
import { MyClass } from '../MyClass';

describe('MyClass', () => {
  it('should do something', () => {
    const instance = new MyClass();
    expect(instance.method()).toBe(expected);
  });

  it('should handle errors', () => {
    expect(() => instance.badMethod()).toThrow();
  });
});
```

#### Test Coverage

Aim for >80% coverage on:
- Type definitions (100% coverage)
- DataLoader (95%+ coverage)
- ForceLayout (90%+ coverage)
- Filters (95%+ coverage)
- Error handling paths

Use `npm test -- --coverage` to see detailed reports.

## Known Limitations

### Performance
- Graph optimized for ~100-200 papers
- Larger graphs (500+) may have performance issues
- Mobile devices: Use "Low Power" mode for better performance

### Features
- **Paper limit**: Hard limit at ~500 papers due to 3D rendering
- **Search**: Currently searches titles only (not full-text)
- **Export**: No built-in image export (workaround: screenshot)
- **Mobile**: Full feature set requires landscape orientation
- **Dimensions**: All 8 dimensions required (uses sensible defaults if missing)

### Browser Compatibility
- Requires WebGL support (all modern browsers have this)
- Chrome/Chromium: Excellent support
- Firefox: Full support
- Safari: Full support (macOS 10.13+)
- Edge: Full support

## Future Enhancements

Planned features for v0.2.0+:

- [ ] Full-text search within paper content
- [ ] Semantic clustering visualization
- [ ] Graph export as PNG/SVG
- [ ] Time-based animation of papers over years
- [ ] VR/AR visualization support
- [ ] GraphRAG integration
- [ ] Custom dimension weighting
- [ ] Graph editing (add/remove papers programmatically)

## Troubleshooting Development

### Build Errors

**"Cannot find module 'obsidian'"**
- Run `npm install`
- Ensure node_modules/ is not in .gitignore

**"TypeScript strict mode errors"**
- Fix all type errors (no `any` types)
- Check `npm run lint` output
- Use proper type definitions from `types/Paper.ts`

### Hot Reload Not Working

- Try `npm run dev` again
- Manually reload Obsidian: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (macOS)
- Check browser console for errors

### Tests Failing

- Clear Jest cache: `npm test -- --clearCache`
- Ensure all mock data is up-to-date
- Run tests with verbose output: `npm test -- --verbose`

### Plugin Won't Load

1. Check Obsidian console for errors
2. Verify `manifest.json` exists and is valid JSON
3. Check `main.js` was built: `ls -la main.js`
4. Clear plugin cache and reload

## Resources

- [Obsidian Plugin Docs](https://docs.obsidian.md/Home)
- [Three.js Documentation](https://threejs.org/docs/)
- [D3-Force Documentation](https://d3js.org/d3-force)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Jest Documentation](https://jestjs.io/docs/getting-started)

## License

MIT - See LICENSE file

---

**Last Updated**: 2026-02-13

For questions, open an issue on [GitHub](https://github.com/cohezion/obsidian-3d-graph-plugin/issues).
