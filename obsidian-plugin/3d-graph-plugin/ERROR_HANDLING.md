# Error Handling Guide

Comprehensive error handling patterns and recovery strategies for the 3D Graph plugin.

## Error Categories

### 1. Data Loading Errors

#### Missing Dimensions
**Problem**: Paper YAML is missing required dimension fields

**Recovery**:
```typescript
// In DataLoader.ts
private applyDefaults(paper: PaperNode): PaperNode {
  const defaults = {
    connectivity: 0.5,
    conceptual_depth: 0.5,
    temporal: 0.5,
    cross_domain: 1,
    completion: 50,
    recency: 0.5,
    semantic_similarity: 0.25,
    similar_papers: [],
  };

  return {
    ...paper,
    dimensions: {
      ...defaults,
      ...paper.dimensions,
    },
  };
}
```

**User Notification**:
```typescript
if (missingDimensions.length > 0) {
  new Notice(`Warning: ${missingDimensions.length} papers have missing dimensions. Using defaults.`);
  console.warn('Papers with missing dimensions:', missingDimensions);
}
```

#### Invalid YAML
**Problem**: YAML frontmatter is malformed

**Recovery**:
```typescript
// In DataLoader.ts
function parseFrontmatter(content: string): Record<string, any> {
  try {
    const match = content.match(/^---\n([\s\S]*?)\n---/);
    if (!match) {
      return {};
    }

    const frontmatter: Record<string, any> = {};
    // Parse logic...
    return frontmatter;
  } catch (error) {
    console.error('Failed to parse YAML:', error);
    return {}; // Return empty, will use defaults
  }
}
```

**User Notification**:
```typescript
try {
  const paper = parsePaper(file);
} catch (error) {
  new Notice(`Error parsing ${file.name}: ${error.message}. Using defaults.`);
  return createDefaultPaper(file);
}
```

#### Empty Vault
**Problem**: Vault has no papers or no dimension data

**Recovery**:
```typescript
// In main.ts
async openGraph3D(): Promise<void> {
  try {
    const graphData = await this.loader.loadPapersFromVault();

    if (graphData.nodes.length === 0) {
      new Notice('No papers found. Using sample data for demonstration.');
      return this.openSampleGraph();
    }

    // ... continue with real data
  } catch (error) {
    console.error('Failed to load graph:', error);
    new Notice('Error loading graph. Check console for details.');
  }
}
```

### 2. Rendering Errors

#### WebGL Not Supported
**Problem**: Browser doesn't support WebGL or it's disabled

**Detection**:
```typescript
// In ThreeRenderer.ts
constructor(container: HTMLElement, width: number, height: number) {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');

    if (!gl) {
      throw new Error('WebGL not supported');
    }

    // Continue with Three.js setup...
  } catch (error) {
    console.error('WebGL Error:', error);
    this.showWebGLFallback(container, error);
  }
}

private showWebGLFallback(container: HTMLElement, error: Error): void {
  container.innerHTML = `
    <div style="padding: 20px;">
      <h2>WebGL Not Supported</h2>
      <p>Your browser doesn't support WebGL, which is required for 3D visualization.</p>
      <p><strong>Solution:</strong></p>
      <ul>
        <li>Update your browser to the latest version</li>
        <li>Enable hardware acceleration in browser settings</li>
        <li>Try a different browser (Chrome, Firefox, Safari)</li>
      </ul>
      <p>Error: ${error.message}</p>
    </div>
  `;
}
```

#### Out of Memory
**Problem**: Too many papers or edges for GPU memory

**Detection & Recovery**:
```typescript
// In ThreeRenderer.ts
private createNodeGeometry(): THREE.BufferGeometry {
  try {
    const geometry = new THREE.BufferGeometry();
    const maxNodes = 500; // GPU memory limit

    if (this.graphData.nodes.length > maxNodes) {
      console.warn(`Graph has ${this.graphData.nodes.length} nodes. Performance may suffer.`);
      new Notice(`Graph is large (${this.graphData.nodes.length} papers). Performance may be reduced.`);
    }

    // Create geometry with available memory
    const positions = new Float32Array(this.graphData.nodes.length * 3);
    // ... fill positions...

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return geometry;
  } catch (error) {
    if (error.message.includes('memory')) {
      new Notice('Out of memory. Try switching to Low Power mode.');
      return this.createReducedGeometry(); // Fallback to simplified rendering
    }
    throw error;
  }
}

private createReducedGeometry(): THREE.BufferGeometry {
  // Use point cloud instead of meshes for lower memory usage
  const geometry = new THREE.BufferGeometry();
  const positions = this.graphData.nodes.map(n => n.position);
  // ... create simplified geometry...
  return geometry;
}
```

#### Animation Frame Errors
**Problem**: RequestAnimationFrame fails or callbacks error

**Recovery**:
```typescript
// In ThreeRenderer.ts
private startRenderLoop(): void {
  const animate = () => {
    try {
      this.renderer.render(this.scene, this.camera);
      this.animationFrameId = requestAnimationFrame(animate);
    } catch (error) {
      console.error('Rendering error:', error);
      new Notice('Rendering error. Please reload the graph.');
      this.stopRenderLoop();
    }
  };

  animate();
}

private stopRenderLoop(): void {
  if (this.animationFrameId !== null) {
    cancelAnimationFrame(this.animationFrameId);
    this.animationFrameId = null;
  }
}
```

### 3. Physics Simulation Errors

#### NaN in Position
**Problem**: Force simulation produces NaN values

**Detection & Recovery**:
```typescript
// In ForceLayout.ts
async positionNodes(timeoutMs = 2000): Promise<Map<string, THREE.Vector3>> {
  return new Promise((resolve) => {
    const checkConvergence = () => {
      if (this.converged) {
        const positions = new Map<string, THREE.Vector3>();

        for (const node of this.graphData.nodes) {
          if (node.position) {
            // Validate position is finite
            if (!isFinite(node.position.x) || !isFinite(node.position.y) || !isFinite(node.position.z)) {
              console.error(`NaN position for paper ${node.id}. Using default.`);
              node.position = { x: 0, y: 0, z: 0 };
            }

            positions.set(
              node.id,
              new THREE.Vector3(node.position.x, node.position.y, node.position.z)
            );
          }
        }

        resolve(positions);
      } else {
        requestAnimationFrame(checkConvergence);
      }
    };

    checkConvergence();
  });
}
```

#### Simulation Won't Converge
**Problem**: Physics simulation never reaches stable state

**Recovery**:
```typescript
// In ForceLayout.ts
async positionNodes(timeoutMs = 2000): Promise<Map<string, THREE.Vector3>> {
  return new Promise((resolve) => {
    const startTime = Date.now();

    const checkConvergence = () => {
      const elapsed = Date.now() - startTime;

      // Force stop if timeout exceeded
      if (elapsed > timeoutMs) {
        console.warn(`Physics simulation timeout after ${elapsed}ms. Stopping with alpha=${this.getAlpha()}`);
        this.simulation.stop();
        this.converged = true;
      }

      if (this.converged) {
        // Extract and validate positions...
        resolve(positions);
      } else {
        requestAnimationFrame(checkConvergence);
      }
    };

    checkConvergence();
  });
}
```

### 4. User Interaction Errors

#### Invalid Filter Values
**Problem**: User enters invalid filter values

**Validation**:
```typescript
// In FilterControls.ts
applyFilter(filterName: string, value: any): void {
  try {
    // Validate input
    if (typeof value === 'number') {
      if (isNaN(value)) {
        throw new Error('Invalid number');
      }
      // Clamp to valid range
      if (filterName.includes('Min')) {
        value = Math.max(0, value);
      }
      if (filterName.includes('Max')) {
        value = Math.min(100, value);
      }
    }

    if (typeof value === 'string') {
      value = value.trim();
      if (value.length > 100) {
        throw new Error('Search query too long');
      }
    }

    // Apply validated filter
    this.filters[filterName] = value;
    this.updateGraph();
  } catch (error) {
    new Notice(`Invalid filter: ${error.message}`);
    console.error('Filter error:', error);
  }
}
```

#### Missing Selected Paper
**Problem**: User selects paper that gets filtered out or deleted

**Recovery**:
```typescript
// In UIManager.ts
selectPaper(paperId: string): void {
  try {
    const paper = this.graphData.nodes.find(n => n.id === paperId);

    if (!paper) {
      console.warn(`Paper ${paperId} not found. Clearing selection.`);
      this.selectedPaper = undefined;
      this.metadataPanel.hide();
      return;
    }

    if (!this.isVisible(paper)) {
      console.warn(`Paper ${paperId} is filtered out. Showing anyway.`);
      new Notice(`Paper filtered out. Show it to select.`);
      return;
    }

    this.selectedPaper = paper;
    this.metadataPanel.show(paper);
  } catch (error) {
    console.error('Selection error:', error);
    new Notice('Error selecting paper');
  }
}
```

### 5. Integration Errors

#### Vault Changes While Modal Open
**Problem**: Papers added/deleted/modified while graph is open

**Solution**: Watch vault and prompt user
```typescript
// In main.ts
async onload(): Promise<void> {
  // ... existing code ...

  // Watch vault for changes
  this.registerEvent(
    this.app.vault.on('modify', (file: TFile) => {
      if (file.path.startsWith('papers/') && file.extension === 'md') {
        console.log('Paper modified:', file.path);
        new Notice('Paper data updated. Reload graph to see changes.');
        // Could auto-reload, or let user choose
      }
    })
  );

  this.registerEvent(
    this.app.vault.on('delete', (file: TFile) => {
      if (file.path.startsWith('papers/')) {
        console.log('Paper deleted:', file.path);
        new Notice('A paper was deleted. Reload graph to refresh.');
      }
    })
  );
}
```

#### SurrealDB Connection Error
**Problem**: Can't connect to SurrealDB (if integrated)

**Recovery**:
```typescript
// In SurrealDBOps.ts (future integration)
async queryPapers(): Promise<PaperNode[]> {
  try {
    const response = await fetch('http://localhost:8000/sql', {
      method: 'POST',
      body: 'SELECT * FROM paper;',
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('SurrealDB connection error:', error);
    new Notice('Could not connect to database. Using local data.');
    return this.loadLocalData(); // Fallback to cached/local data
  }
}
```

## Error Handling Patterns

### Try-Catch Pattern
```typescript
async function safeOperation(): Promise<Result> {
  try {
    const result = await riskyOperation();
    return result;
  } catch (error) {
    console.error('Operation failed:', error);
    new Notice(`Error: ${error.message}`);
    return defaultValue;
  }
}
```

### Optional Chaining
```typescript
// Safely access nested properties
const connectivity = paper?.dimensions?.connectivity ?? 0.5;
const title = selectedPaper?.title ?? 'Unknown';
```

### Validation Before Use
```typescript
function validatePaper(paper: any): paper is PaperNode {
  return (
    typeof paper === 'object' &&
    typeof paper.id === 'string' &&
    typeof paper.title === 'string' &&
    typeof paper.dimensions === 'object'
  );
}

// Use in code
if (validatePaper(unknownData)) {
  // TypeScript now knows it's a valid PaperNode
  processPaper(unknownData);
} else {
  console.error('Invalid paper data:', unknownData);
}
```

## Logging Strategy

### Log Levels

```typescript
// Debug: Development only, verbose details
console.debug('Simulation alpha:', layout.getAlpha());

// Info: General information, key events
console.info('Graph loaded:', graphData.nodes.length, 'papers');

// Warn: Potential issues, recoverable errors
console.warn('Paper missing dimensions:', paperId);

// Error: Serious problems, action needed
console.error('Failed to load graph:', error);
```

### Structured Logging

```typescript
// Instead of: console.log('Error:', error.message);
// Use:
console.error('Paper loading failed', {
  paperId: 'paper-42',
  path: 'papers/ai/knowledge-graphs.md',
  error: error.message,
  context: {
    totalAttempted: 84,
    succeededCount: 82,
  },
});
```

## User-Facing Error Messages

### Guidelines
1. **Clear**: What went wrong?
2. **Actionable**: What can user do?
3. **Friendly**: No technical jargon
4. **Helpful**: Link to documentation

### Examples

**Bad**:
```
"TypeError: Cannot read property 'dimensions' of undefined"
```

**Good**:
```
"Error loading paper: Some papers have incomplete data.
Using defaults. Check console for details."
```

**Bad**:
```
"Connection failed"
```

**Good**:
```
"Couldn't connect to database. Using cached data.
(Check your network connection or contact support)"
```

## Recovery Strategies

### Graceful Degradation
- Load without dimensions → use defaults
- Can't render WebGL → show 2D fallback
- Out of memory → reduce quality
- Simulation won't converge → use timeout

### Automatic Retry
```typescript
async function retryOperation(
  operation: () => Promise<T>,
  maxAttempts = 3,
  delayMs = 1000
): Promise<T> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      if (attempt === maxAttempts) throw error;
      console.warn(`Attempt ${attempt} failed. Retrying in ${delayMs}ms...`);
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  }
  throw new Error('Max retries exceeded');
}
```

## Testing Error Handling

### Error Simulation Tests
```typescript
it('should handle missing dimensions gracefully', () => {
  const incompletePaper = {
    id: 'test',
    title: 'Test Paper',
    // Missing dimensions
  };

  const filled = loader.applyDefaults(incompletePaper);
  expect(filled.dimensions.connectivity).toBe(0.5); // Default value
});

it('should catch YAML parsing errors', () => {
  const badYAML = '---\ninvalid yaml: [';
  const result = parseFrontmatter(badYAML);
  expect(result).toEqual({}); // Returns empty on error
});
```

---

**Last Updated**: 2026-02-13
