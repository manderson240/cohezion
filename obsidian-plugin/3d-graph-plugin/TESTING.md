# Testing Guide for 3D Graph Plugin

Comprehensive testing procedures and validation checklist for the 3D Graph plugin.

## Test Categories

### 1. Unit Tests (Code-level testing)

Unit tests verify individual components in isolation. Located in `src/__tests__/`:

#### DataLoader Tests (`src/__tests__/DataLoader.test.ts`)
Tests YAML parsing, dimension validation, and edge creation.

```typescript
describe('DataLoader', () => {
  it('should load 84 papers without errors', () => {
    const loader = new DataLoader(app);
    const graphData = loader.loadPapersFromVault();
    expect(graphData.nodes).toHaveLength(84);
  });

  it('should parse YAML dimensions correctly', () => {
    const paper = graphData.nodes[0];
    expect(paper.dimensions.connectivity).toBeGreaterThanOrEqual(0);
    expect(paper.dimensions.connectivity).toBeLessThanOrEqual(1);
  });

  it('should handle missing dimensions with defaults', () => {
    const paper = { ...incompletePaper };
    const filled = loader.applyDefaults(paper);
    expect(filled.dimensions.connectivity).toBeDefined();
  });

  it('should build edges from similar_papers', () => {
    expect(graphData.edges.length).toBeGreaterThan(0);
    const edge = graphData.edges[0];
    expect(edge.source).toBeDefined();
    expect(edge.target).toBeDefined();
    expect(edge.similarity).toBeGreaterThan(0);
  });
});
```

**Run**:
```bash
npm test -- DataLoader.test.ts
```

#### ForceLayout Tests (`src/__tests__/ForceLayout.test.ts`)
Tests physics simulation convergence and position computation.

```typescript
describe('ForceLayout', () => {
  it('should converge within timeout', async () => {
    const layout = new ForceLayout(graphData);
    const positions = await layout.positionNodes(2000);
    expect(positions.size).toBe(graphData.nodes.length);
  });

  it('should map dimensions to 3D positions', async () => {
    const positions = await layout.positionNodes();
    const pos = positions.get('paper-0');

    // X-axis: connectivity range
    expect(pos.x).toBeGreaterThan(-300);
    expect(pos.x).toBeLessThan(300);

    // Y-axis: conceptual_depth range
    expect(pos.y).toBeGreaterThan(-300);
    expect(pos.y).toBeLessThan(300);

    // Z-axis: temporal range
    expect(pos.z).toBeGreaterThan(-400);
    expect(pos.z).toBeLessThan(100);
  });

  it('should prevent overlap via collision forces', async () => {
    const positions = await layout.positionNodes();
    const nodes = Array.from(positions.entries());

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dist = nodes[i][1].distanceTo(nodes[j][1]);
        expect(dist).toBeGreaterThan(5); // Minimum spacing
      }
    }
  });
});
```

**Run**:
```bash
npm test -- ForceLayout.test.ts
```

#### Filter Tests (`src/__tests__/Filters.test.ts`)
Tests filter logic and visibility computation.

```typescript
describe('Graph Filters', () => {
  it('should filter by connectivity range', () => {
    const filters: GraphFilters = {
      connectivityMin: 0.5,
      connectivityMax: 1.0,
      // ... other filters
    };

    const visible = filterPapers(graphData.nodes, filters);
    visible.forEach(paper => {
      expect(paper.dimensions.connectivity).toBeGreaterThanOrEqual(0.5);
    });
  });

  it('should filter by domain', () => {
    const filters: GraphFilters = {
      domains: ['AI', 'NLP'],
      // ... other filters
    };

    const visible = filterPapers(graphData.nodes, filters);
    visible.forEach(paper => {
      expect(paper.domains).toContainAny(['AI', 'NLP']);
    });
  });

  it('should search by title text', () => {
    const filters: GraphFilters = {
      searchQuery: 'knowledge',
      // ... other filters
    };

    const visible = filterPapers(graphData.nodes, filters);
    visible.forEach(paper => {
      expect(paper.title.toLowerCase()).toContain('knowledge');
    });
  });

  it('should combine filters with AND logic', () => {
    const filters: GraphFilters = {
      connectivityMin: 0.7,
      temporalMin: 0.8,
      searchQuery: 'graph',
    };

    const visible = filterPapers(graphData.nodes, filters);
    visible.forEach(paper => {
      expect(paper.dimensions.connectivity).toBeGreaterThanOrEqual(0.7);
      expect(paper.dimensions.temporal).toBeGreaterThanOrEqual(0.8);
      expect(paper.title.toLowerCase()).toContain('graph');
    });
  });
});
```

**Run**:
```bash
npm test -- Filters.test.ts
```

### 2. Integration Tests (Component interaction)

Integration tests verify multiple components working together:

#### Graph Loading & Rendering Test

```typescript
describe('Graph Loading & Rendering', () => {
  let plugin: GraphPlugin;
  let app: App;

  beforeEach(async () => {
    app = initializeTestVault();
    plugin = new GraphPlugin();
    await plugin.onload();
  });

  it('should load 84 papers and render them', async () => {
    const modal = new Graph3D(app);
    const graphData = loader.loadPapersFromVault();

    await modal.loadGraphData(graphData);

    expect(modal.renderedNodeCount).toBe(84);
    expect(modal.renderedEdgeCount).toBeGreaterThan(0);
  });

  it('should handle filter changes without crashing', async () => {
    const modal = new Graph3D(app);

    // Apply multiple filter changes
    modal.applyFilters({ connectivityMin: 0.5 });
    expect(modal.visibleNodeCount).toBeLessThan(84);

    modal.applyFilters({ searchQuery: 'AI' });
    expect(modal.visibleNodeCount).toBeGreaterThan(0);

    modal.applyFilters({ domains: ['NLP'] });
    expect(modal.visibleNodeCount).toBeGreaterThan(0);
  });

  it('should render selected paper metadata panel', async () => {
    const modal = new Graph3D(app);
    const paper = graphData.nodes[0];

    modal.selectPaper(paper.id);

    expect(modal.metadataPanel.isVisible).toBe(true);
    expect(modal.metadataPanel.title).toBe(paper.title);
    expect(modal.metadataPanel.authors).toEqual(paper.authors);
  });
});
```

**Run**:
```bash
npm test -- --integration
```

### 3. Performance Tests

Performance benchmarks to ensure smooth operation:

#### Rendering Performance

```typescript
describe('Rendering Performance', () => {
  it('should maintain >30 FPS with all 84 papers visible', () => {
    const modal = new Graph3D(app);
    modal.loadGraphData(graphData);

    const frameRateSamples: number[] = [];
    let lastTime = performance.now();

    for (let i = 0; i < 300; i++) { // Sample 300 frames
      const now = performance.now();
      const deltaTime = now - lastTime;
      const fps = 1000 / deltaTime;
      frameRateSamples.push(fps);
      lastTime = now;

      // Trigger render
      modal.renderer.render();
    }

    const avgFps = frameRateSamples.reduce((a, b) => a + b) / frameRateSamples.length;
    expect(avgFps).toBeGreaterThan(30);
  });

  it('should handle rapid filter changes', () => {
    const startTime = performance.now();

    for (let i = 0; i < 100; i++) {
      modal.applyFilters({
        connectivityMin: Math.random(),
        temporalMin: Math.random(),
      });
    }

    const duration = performance.now() - startTime;
    expect(duration).toBeLessThan(5000); // Should complete in <5 seconds
  });
});
```

**Run**:
```bash
npm test -- --performance
```

### 4. Manual Testing Checklist

Complete this checklist before releasing:

#### Graph Loading
- [ ] Plugin loads without errors
- [ ] Ribbon icon appears in left sidebar
- [ ] "Open 3D Graph" command appears in command palette
- [ ] Clicking ribbon or command opens modal
- [ ] All 84 papers load (no blank nodes)
- [ ] Graph renders with 3D perspective
- [ ] Performance: >30 FPS on high-quality setting

#### Navigation
- [ ] Mouse drag rotates view
- [ ] Mouse wheel zooms in/out
- [ ] Right-click pan works
- [ ] Arrow keys rotate view (if keyboard controls enabled)
- [ ] Can navigate all parts of the 3D space
- [ ] View resets with "R" key

#### Interaction
- [ ] Clicking on paper node selects it
- [ ] Metadata panel appears on selection
- [ ] Metadata panel shows correct title, authors, year
- [ ] "Open in Vault" button navigates to paper note
- [ ] Hovering over node shows label (if label visibility = "hover")
- [ ] Clicking empty space deselects paper

#### Filtering
- [ ] Connectivity slider works (papers appear/disappear)
- [ ] Conceptual depth slider works
- [ ] Temporal slider works
- [ ] Completion slider works
- [ ] Recency slider works
- [ ] Domain checkboxes work (select multiple)
- [ ] Search box filters by title
- [ ] Multiple filters combined correctly (AND logic)
- [ ] "Reset All" button clears all filters

#### Settings
- [ ] Node Size Scaling option changes node sizes
- [ ] Label Visibility option controls label display
- [ ] Physics Speed option affects layout convergence
- [ ] Performance Mode option affects rendering quality
- [ ] Settings persist after closing and reopening modal
- [ ] Settings persist after Obsidian restart

#### Error Handling
- [ ] Missing dimensions use defaults (no blank papers)
- [ ] Invalid YAML in paper notes doesn't crash
- [ ] Network disconnect doesn't crash
- [ ] Opening modal twice creates separate instances
- [ ] Closing modal cleans up resources

#### Keyboard Controls
- [ ] `?` shows help overlay
- [ ] `R` resets view
- [ ] `Space` focuses on selected paper
- [ ] `Escape` closes help/deselects
- [ ] Arrow keys rotate (if enabled)
- [ ] `+/-` zoom in/out

#### Browser/Platform Compatibility
- [ ] Works on Chrome/Chromium
- [ ] Works on Firefox
- [ ] Works on Safari (macOS)
- [ ] Works on Edge
- [ ] Mobile: Can open modal and interact
- [ ] Mobile: Touch gestures work (pinch, pan)

#### Code Quality
- [ ] No TypeScript errors: `npm run build`
- [ ] No linting errors: `npm run lint`
- [ ] All tests pass: `npm test`
- [ ] Code coverage >80%: `npm test -- --coverage`

## Running Tests

### All Tests
```bash
npm test
```

### Specific Test File
```bash
npm test -- DataLoader.test.ts
```

### Watch Mode (auto-rerun on changes)
```bash
npm test -- --watch
```

### With Coverage Report
```bash
npm test -- --coverage
```

### Integration Tests Only
```bash
npm test -- --integration
```

### Performance Tests Only
```bash
npm test -- --performance
```

## Performance Benchmarks

Target performance metrics:

| Metric | Target | Current |
|--------|--------|---------|
| Graph Load Time | <2 seconds | — |
| Render FPS (High Quality) | >30 FPS | — |
| Render FPS (Low Power) | >20 FPS | — |
| Filter Application | <100 ms | — |
| Search Response | <100 ms | — |
| Memory Usage | <100 MB | — |
| Package Size | <500 KB | — |

## Bug Reporting

When reporting bugs, include:

1. Steps to reproduce
2. Expected behavior
3. Actual behavior
4. Browser/OS
5. Plugin version
6. Console errors (Ctrl+Shift+I)
7. Screenshots (if applicable)

Example:
```
Title: Papers don't load on Firefox

Steps:
1. Open Obsidian on Firefox
2. Click 3D Graph ribbon icon
3. Wait 2 seconds

Expected: 84 papers visible
Actual: Blank white canvas

System: Firefox 121, macOS 13, Plugin 0.1.0
Error: WebGL not supported
```

## Continuous Testing

### Pre-Commit Hook
Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
npm run lint || exit 1
npm run build || exit 1
npm test || exit 1
```

### CI/CD Pipeline
Tests run automatically on:
- Pull requests (before merge)
- Main branch commits
- Release tags

## Accessibility Testing

Test with:
- [ ] Screen readers (NVDA, JAWS)
- [ ] High contrast mode
- [ ] Keyboard-only navigation
- [ ] Colorblind color palette
- [ ] Mobile screen readers

## Troubleshooting Failed Tests

**WebGL not available**
- Ensure hardware acceleration is enabled
- Use headless browser or GPU-enabled container

**Timeout errors**
- Increase timeout in test config
- Check system performance
- Verify graph data is valid

**Flaky tests (intermittent failures)**
- Use `jest.useFakeTimers()` for timing tests
- Avoid `setTimeout()` in tests
- Mock external dependencies

---

**Last Updated**: 2026-02-13
