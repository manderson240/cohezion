---
title: "12D Graph Visualization + SurrealDB Integration Plan"
date: 2026-02-09
status: proposed
tags: [decision, architecture, visualization, surrealdb, graph, 12d, obsidian-plugin]

decision_reasoning:
  chosen_option: "Custom 12D graph plugin with SurrealDB backend for multi-dimensional knowledge exploration"
  rationale: "3D graph insufficient for complex knowledge relationships; 12D framework enables theory→practice→validation linking across multiple analytical axes"
  confidence_score: 0.85
  alternatives_rejected:
    - "Standard 3D graph plugin (insufficient dimensional analysis, single spatial view)"
    - "Traditional relational database (no native graph support, poor relationship performance)"
    - "File-based JSON graph (not scalable for real-time subscriptions)"
  reasoning_chain:
    - "Vault reached 123+ wiki-links; standard 3D visualization insufficient"
    - "Identified 12 distinct analytical dimensions needed for knowledge exploration"
    - "SurrealDB provides native graph + embeddings + real-time subscriptions"
    - "Plugin architecture enables rich interactive exploration"

metrics:
  estimated_cost: 0.0  # Research + architecture phase
  estimated_time_hours: 60.0  # Full implementation estimate (5 phases)
  actual_cost: 0.0  # Design phase only
  actual_time_hours: 8.0  # Design and specification
  tokens_used: 0  # Local analysis
  cost_per_lesson: 0.0
  lessons_generated:
    - decisions/2026-02-09-12d-graph-next-steps
---

# 12D Graph Visualization + SurrealDB Integration

**Initiative**: Custom 12-dimensional graph plugin for Cohezion vault with SurrealDB backend
**Status**: Proposed - Design & Planning Phase
**Complexity**: High (custom plugin development + database integration)

---

## Context

### Current State
- ✅ Vault has 123 wiki-links across 66 papers establishing bidirectional connectivity
- ✅ 21 concepts fully cross-linked
- ✅ 3D Graph plugin researched (New 3D Graph recommended for immediate use)
- 🎯 **New Direction**: Design custom 12D graph visualization for richer multi-dimensional exploration

### Vision: Why 12 Dimensions?

**Beyond 3D Spatial Visualization** - Each dimension represents a different analytical axis:

1. **Spatial (X, Y, Z)** - Traditional 3D positioning
2. **Temporal** - Time/chronological axis (paper publication dates, concept evolution)
3. **Domain Clustering** - Research domain affinity (AI, Physics, Biology, etc.)
4. **Connectivity Density** - Number of connections/links
5. **Conceptual Depth** - Abstraction level (theory ↔ application)
6. **Citation Impact** - Reference frequency/importance
7. **Recency/Relevance** - Time-decay weighted importance
8. **Cross-Domain Bridging** - Papers that connect multiple domains
9. **User Interest** - Interaction frequency/bookmarks
10. **Semantic Similarity** - NLP-derived content similarity
11. **Completion Status** - Enrichment level (summary, links, metadata)
12. **Agent Journey Affinity** - Relevance to current agent context/goals

### Why SurrealDB?

**Graph Database Advantages**:
- ✅ Native graph relationships (papers ↔ concepts ↔ domains)
- ✅ Multi-model (documents + relations + graph queries)
- ✅ Real-time subscriptions (live graph updates)
- ✅ Built-in full-text search
- ✅ Spatial indexing capabilities
- ✅ Embeddings support (for semantic similarity)
- ✅ GraphQL + SurrealQL queries

---

## Architecture Overview

### Component Stack

```
┌─────────────────────────────────────────────────────────┐
│ Obsidian Vault (Markdown Files - Source of Truth)      │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ├─> Vault Watcher (File System Events)
                      │
┌─────────────────────▼───────────────────────────────────┐
│ Cloud Vault MCP Server (Python)                         │
│  - VaultOps: CRUD operations                            │
│  - Graph Builder: Extract relationships                 │
│  - Embeddings Generator: Semantic vectors              │
│  - SurrealDB Sync: Bidirectional sync                  │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│ SurrealDB Instance (Graph Database)                     │
│  - Nodes: Papers, Concepts, Tags, Authors              │
│  - Edges: Links, Citations, Similarity, Domains        │
│  - Properties: All 12 dimensions as queryable fields   │
│  - Live Queries: Real-time graph subscriptions        │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│ Obsidian Plugin: Cohezion 12D Graph                     │
│  - TypeScript/React visualization layer                 │
│  - WebGL/Three.js for rendering                        │
│  - Dimensional sliders (12 axes)                       │
│  - Real-time updates via SurrealDB subscriptions      │
│  - Intelligent projection (12D → 3D viewable space)   │
└─────────────────────────────────────────────────────────┘
```

---

## Design Approach: Dimensional Projection

### The Challenge
**Problem**: Humans can only visualize 3D space directly

**Solution**: Dynamic dimensional projection with user control

### Projection Strategy

1. **Primary Axes** (X, Y, Z) - Always visible
   - User selects which 3 dimensions map to X/Y/Z
   - Default: Spatial positioning (domain clustering)

2. **Secondary Encoding** - Visual properties
   - **Dimension 4-6**: Node size, color, opacity
   - **Dimension 7-9**: Edge thickness, color, pattern
   - **Dimension 10-12**: Animation, glow, particle effects

3. **Interactive Slicing** - Filter/constrain dimensions
   - Slider for each dimension (12 total)
   - Constrain to range (e.g., "show only papers from 2025-2026")
   - Live filter updates

### Dimensional Mapping Table

| Dimension | Default Axis | Visual Encoding | Filter Control |
|-----------|-------------|-----------------|----------------|
| 1. X Position | Domain cluster | X-axis position | Domain selector |
| 2. Y Position | Connectivity | Y-axis position | Min/max links |
| 3. Z Position | Temporal | Z-axis position | Date range |
| 4. Domain Affinity | Color | Node color hue | Domain filter |
| 5. Depth Level | Size | Node radius | Theory ↔ Applied |
| 6. Citation Impact | Glow | Node glow intensity | Min citations |
| 7. Recency | Opacity | Node alpha | Age filter |
| 8. Cross-Domain | Edge thickness | Connection width | Bridge score |
| 9. User Interest | Animation | Pulse rate | Interaction count |
| 10. Semantic Sim | Edge color | Connection hue | Similarity threshold |
| 11. Completion | Border | Node outline style | Enrichment % |
| 12. Agent Affinity | Particles | Node particle count | Relevance score |

---

## Implementation Plan

### Phase 1: SurrealDB Integration (Week 1-2)

**Objective**: Get vault data into SurrealDB with graph relationships

#### 1.1: SurrealDB Setup
- [ ] Install SurrealDB locally (Docker or binary)
- [ ] Design schema for papers, concepts, domains
- [ ] Define relationship types (LINKS, CITES, BELONGS_TO, SIMILAR_TO)
- [ ] Test basic graph queries

#### 1.2: Vault → SurrealDB Sync
- [ ] Extend Cloud Vault MCP with SurrealDB client
- [ ] Create `SurrealDBSync` class in MCP server
- [ ] Parse markdown frontmatter → SurrealDB records
- [ ] Extract wiki-links → relationship edges
- [ ] Initial bulk import of all 84 papers + 21 concepts

#### 1.3: Real-Time Sync
- [ ] File watcher integration (detect vault changes)
- [ ] Incremental updates (only changed files)
- [ ] Bidirectional sync (SurrealDB metadata → vault frontmatter)
- [ ] Conflict resolution strategy

**Deliverable**: SurrealDB instance with live-synced vault graph

---

### Phase 2: Dimensional Computation (Week 2-3)

**Objective**: Calculate all 12 dimensions for each node/edge

#### 2.1: Static Dimensions (Computed Once)
```python
# Dimension computations in Cloud Vault MCP

def compute_temporal_dimension(paper):
    """Dimension 3: Temporal - Publication date normalized"""
    pub_date = paper.frontmatter.get('date')
    return normalize_date_to_axis(pub_date)

def compute_connectivity_dimension(paper):
    """Dimension 6: Connectivity Density - Link count"""
    links = count_wiki_links(paper.content)
    return normalize(links, min=0, max=100)

def compute_domain_dimension(paper):
    """Dimension 1/4: Domain affinity - Multi-hot encoding"""
    tags = paper.frontmatter.get('tags', [])
    return map_tags_to_domain_vector(tags)

def compute_conceptual_depth(paper):
    """Dimension 5: Theory ↔ Application"""
    # NLP analysis of abstract/summary
    theory_keywords = ['theoretical', 'framework', 'model', 'principle']
    applied_keywords = ['implementation', 'application', 'results', 'experiment']
    return calculate_theory_vs_applied_score(paper)
```

#### 2.2: Dynamic Dimensions (Computed on Query)
```python
def compute_semantic_similarity(paper1, paper2):
    """Dimension 10: NLP-based content similarity"""
    embedding1 = get_paper_embedding(paper1)  # via OpenAI/Anthropic
    embedding2 = get_paper_embedding(paper2)
    return cosine_similarity(embedding1, embedding2)

def compute_agent_affinity(paper, agent_context):
    """Dimension 12: Relevance to current agent journey"""
    current_goals = agent_context.get('goals')
    current_concepts = agent_context.get('active_concepts')
    return calculate_relevance_score(paper, current_goals, current_concepts)
```

#### 2.3: User Interaction Tracking
- [ ] Track vault navigation patterns
- [ ] Record bookmarks/favorites
- [ ] Log time-on-page for papers
- [ ] Update Dimension 9 (User Interest) based on interactions

**Deliverable**: All nodes have 12-dimensional coordinates in SurrealDB

---

### Phase 3: Obsidian Plugin Development (Week 3-5)

**Objective**: Create custom Obsidian plugin for 12D graph visualization

#### 3.1: Plugin Scaffolding
```bash
# Create plugin from template
npm init obsidian-plugin cohezion-12d-graph
cd cohezion-12d-graph

# Dependencies
npm install three @react-three/fiber @react-three/drei
npm install surrealdb.js  # SurrealDB client
npm install zustand  # State management
```

#### 3.2: Core Architecture

**File Structure**:
```
cohezion-12d-graph/
├── src/
│   ├── main.ts                    # Plugin entry point
│   ├── graphView.tsx              # Main graph view component
│   ├── db/
│   │   ├── surrealClient.ts       # SurrealDB connection
│   │   └── queries.ts             # Graph queries
│   ├── viz/
│   │   ├── GraphRenderer.tsx      # Three.js scene
│   │   ├── NodeRenderer.tsx       # Individual node visualization
│   │   ├── EdgeRenderer.tsx       # Relationship visualization
│   │   └── projectionEngine.ts    # 12D → 3D projection logic
│   ├── controls/
│   │   ├── DimensionSliders.tsx   # 12 dimension controls
│   │   ├── AxisSelector.tsx       # Choose which dims → X/Y/Z
│   │   └── FilterPanel.tsx        # Dimensional filtering
│   └── settings/
│       └── SettingsTab.tsx        # Plugin configuration
└── manifest.json
```

#### 3.3: Key Components

**Graph Renderer** (Three.js/WebGL):
```typescript
// src/viz/GraphRenderer.tsx
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stats } from '@react-three/drei';

export const GraphRenderer = ({ nodes, edges, projection }) => {
  return (
    <Canvas camera={{ position: [0, 0, 100], fov: 75 }}>
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} />

      {/* Nodes */}
      {nodes.map(node => (
        <NodeRenderer
          key={node.id}
          position={projection.project(node.dimensions)}
          dimensions={node.dimensions}
          onClick={() => openFile(node.file)}
        />
      ))}

      {/* Edges */}
      {edges.map(edge => (
        <EdgeRenderer
          key={edge.id}
          start={projection.project(edge.source.dimensions)}
          end={projection.project(edge.target.dimensions)}
          thickness={edge.dimensions[7]}  // Cross-domain bridging
        />
      ))}

      <OrbitControls />
      <Stats />
    </Canvas>
  );
};
```

**Projection Engine**:
```typescript
// src/viz/projectionEngine.ts
export class ProjectionEngine {
  constructor(
    private axisMapping: { x: number; y: number; z: number }
  ) {}

  project(dimensions: number[]): [number, number, number] {
    // Map selected dimensions to 3D coordinates
    const x = dimensions[this.axisMapping.x] * 100;  // Scale factor
    const y = dimensions[this.axisMapping.y] * 100;
    const z = dimensions[this.axisMapping.z] * 100;

    return [x, y, z];
  }

  setAxisMapping(axis: 'x' | 'y' | 'z', dimension: number) {
    this.axisMapping[axis] = dimension;
    // Trigger re-projection
  }
}
```

**SurrealDB Live Query**:
```typescript
// src/db/surrealClient.ts
import Surreal from 'surrealdb.js';

export class GraphDatabase {
  private db: Surreal;

  async connect() {
    this.db = new Surreal('http://localhost:8000/rpc');
    await this.db.signin({ user: 'root', pass: 'root' });
    await this.db.use('cohezion', 'vault');
  }

  async subscribeToGraph(callback: (data) => void) {
    // Live query for real-time updates
    await this.db.live('SELECT * FROM paper, concept, RELATES', (action, result) => {
      callback({ action, data: result });
    });
  }

  async queryGraph(filters: DimensionFilters) {
    // Query with dimensional constraints
    const query = `
      SELECT *,
        ->links->concept AS concepts,
        <-links<-paper AS related_papers
      FROM paper
      WHERE domain CONTAINS $domain
        AND temporal BETWEEN $start AND $end
        AND connectivity >= $min_links
    `;

    return await this.db.query(query, filters);
  }
}
```

**Deliverable**: Working Obsidian plugin with basic 12D graph visualization

---

### Phase 4: Advanced Features (Week 5-6)

#### 4.1: Intelligent Recommendations
- [ ] "Papers you might like" based on current view
- [ ] "Explore this cluster" suggestions
- [ ] "Bridge concepts" - find connecting papers

#### 4.2: Agent Journey Integration
- [ ] Track current agent goals in SurrealDB
- [ ] Highlight relevant papers (Dimension 12)
- [ ] Show "agent path" through graph over time
- [ ] Goal-driven filtering

#### 4.3: Collaborative Features
- [ ] Multi-user annotations
- [ ] Shared dimensional views (bookmark 12D configurations)
- [ ] Team knowledge maps

#### 4.4: Export & Analysis
- [ ] Export graph as JSON/GraphML
- [ ] Generate metrics reports
- [ ] Network analysis (centrality, communities)

**Deliverable**: Production-ready plugin with advanced capabilities

---

## Technical Specifications

### SurrealDB Schema

```sql
-- Define tables
DEFINE TABLE paper SCHEMAFULL;
DEFINE TABLE concept SCHEMAFULL;
DEFINE TABLE domain SCHEMAFULL;

-- Paper fields (12 dimensions + metadata)
DEFINE FIELD title ON paper TYPE string;
DEFINE FIELD file_path ON paper TYPE string;
DEFINE FIELD content ON paper TYPE string;
DEFINE FIELD tags ON paper TYPE array;
DEFINE FIELD date ON paper TYPE datetime;

-- Dimensional fields
DEFINE FIELD dim_spatial_x ON paper TYPE float;
DEFINE FIELD dim_spatial_y ON paper TYPE float;
DEFINE FIELD dim_spatial_z ON paper TYPE float;
DEFINE FIELD dim_temporal ON paper TYPE float;
DEFINE FIELD dim_domain ON paper TYPE array<string>;
DEFINE FIELD dim_connectivity ON paper TYPE int;
DEFINE FIELD dim_depth ON paper TYPE float;
DEFINE FIELD dim_citations ON paper TYPE int;
DEFINE FIELD dim_recency ON paper TYPE float;
DEFINE FIELD dim_bridging ON paper TYPE float;
DEFINE FIELD dim_interest ON paper TYPE float;
DEFINE FIELD dim_similarity ON paper TYPE object;  -- Sparse similarity matrix
DEFINE FIELD dim_completion ON paper TYPE float;
DEFINE FIELD dim_agent_affinity ON paper TYPE object;  -- Context-dependent

-- Relationships
DEFINE TABLE links TYPE RELATION FROM paper TO concept;
DEFINE TABLE cites TYPE RELATION FROM paper TO paper;
DEFINE TABLE belongs_to TYPE RELATION FROM paper TO domain;
DEFINE TABLE similar_to TYPE RELATION FROM paper TO paper;

-- Indexes
DEFINE INDEX idx_paper_date ON paper FIELDS date;
DEFINE INDEX idx_paper_tags ON paper FIELDS tags;
DEFINE INDEX idx_paper_connectivity ON paper FIELDS dim_connectivity;
```

### Plugin Manifest

```json
{
  "id": "cohezion-12d-graph",
  "name": "Cohezion 12D Graph",
  "version": "0.1.0",
  "minAppVersion": "1.0.0",
  "description": "12-dimensional graph visualization powered by SurrealDB",
  "author": "Cohezion Team",
  "authorUrl": "https://github.com/cohezion",
  "isDesktopOnly": false,
  "main": "main.js"
}
```

---

## Integration with Existing Infrastructure

### Cloud Vault MCP Extensions

**New Tools** (add to `server.py`):
```python
@mcp.tool()
def graph_query_12d(
    dimension_filters: dict,
    projection_axes: dict
) -> str:
    """Query 12D graph with dimensional filtering.

    Args:
        dimension_filters: Dict of dimension constraints
        projection_axes: Which dims map to X/Y/Z

    Returns:
        JSON graph data ready for visualization
    """
    # Connect to SurrealDB
    # Apply filters
    # Project to selected axes
    # Return graph JSON

@mcp.tool()
def compute_dimensional_values(
    file_path: str
) -> str:
    """Compute all 12 dimensions for a paper.

    Returns:
        JSON with 12-dimensional coordinates
    """
    # Read paper
    # Compute each dimension
    # Store in SurrealDB
    # Return coordinates
```

### Agent Journey Tracking

```python
# In agent code
def update_agent_context(agent_id: str, goals: list, concepts: list):
    """Update agent journey in SurrealDB for dimension 12 calculation."""
    surreal.query("""
        UPDATE agent:$agent_id SET
            current_goals = $goals,
            active_concepts = $concepts,
            timestamp = time::now()
    """, {'agent_id': agent_id, 'goals': goals, 'concepts': concepts})
```

---

## Rollout Strategy

### Milestones

| Phase | Duration | Deliverable | Success Metric |
|-------|----------|-------------|----------------|
| **Phase 1** | 2 weeks | SurrealDB sync | All vault data in DB, live sync working |
| **Phase 2** | 1 week | 12D coordinates | All nodes have dimensional values |
| **Phase 3** | 2 weeks | Basic plugin | Can visualize graph in 3D with dimension controls |
| **Phase 4** | 1 week | Advanced features | Recommendations, agent integration working |
| **Phase 5** | 1 week | Polish & docs | Production-ready, documented |

**Total Timeline**: 6-7 weeks to production

### Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|-----------|
| SurrealDB performance with large graphs | High | Medium | Index optimization, pagination, clustering |
| 12D projection UX complexity | Medium | High | Clear defaults, guided tours, presets |
| Plugin compatibility issues | Medium | Low | Test with multiple Obsidian versions |
| Real-time sync lag | Low | Medium | Debouncing, background sync, conflict detection |
| Embeddings API cost | Medium | Medium | Cache embeddings, batch requests, use local models |

---

## Alternative: Incremental Approach

If full 12D seems too ambitious initially:

### Phased Rollout

**Phase 1-Lite**: 4D Graph (Week 1-2)
- Dimensions: X (domain), Y (connectivity), Z (temporal), Color (completion)
- Simpler to implement
- Proves concept

**Phase 2-Lite**: 8D Graph (Week 3-4)
- Add: Size (depth), Opacity (recency), Edge thickness (bridging), Glow (citations)
- More informative, still manageable

**Phase 3-Full**: 12D Graph (Week 5-7)
- Add final 4 dimensions
- Full feature set

---

## Success Criteria

1. ✅ **SurrealDB Integration**: Vault data syncs bidirectionally in real-time
2. ✅ **12D Coordinates**: All papers/concepts have 12-dimensional positions
3. ✅ **Interactive Visualization**: Can explore graph with dimension controls
4. ✅ **Agent Integration**: Graph highlights papers relevant to agent journeys
5. ✅ **Performance**: Renders smoothly with 100+ nodes, 500+ edges
6. ✅ **User Adoption**: Team finds it more useful than standard graph view

---

## Next Steps

### Immediate (This Week)
1. **Research & Prototyping**
   - [ ] Install SurrealDB locally
   - [ ] Test basic graph queries
   - [ ] Prototype dimensional projection math
   - [ ] Sketch UI mockups

2. **Architecture Decision Record**
   - [ ] Finalize 12 dimension definitions
   - [ ] Choose embedding model (OpenAI vs local)
   - [ ] Decide on projection defaults

3. **Spike: Proof of Concept**
   - [ ] Create minimal SurrealDB schema
   - [ ] Import 5 papers as test data
   - [ ] Compute 3-4 dimensions
   - [ ] Render simple 3D visualization (HTML + Three.js)

### Short-Term (Next 2 Weeks)
1. Implement Phase 1 (SurrealDB Integration)
2. Validate dimensional computation algorithms
3. Begin plugin scaffolding

---

## Open Questions

1. **Embeddings**: OpenAI API vs local sentence-transformers model?
   - Cost vs control tradeoff
   - Privacy considerations

2. **SurrealDB Hosting**: Local vs cloud instance?
   - Multi-device sync implications
   - Backup strategy

3. **Dimension Prioritization**: Which 3 dims should be default X/Y/Z?
   - Domain, Connectivity, Temporal seems natural
   - But may not be most useful

4. **Agent Context**: How to capture "agent journey" automatically?
   - Explicit goals tracking vs implicit behavior analysis
   - Privacy/observability balance

---

## References

- SurrealDB Docs: https://surrealdb.com/docs
- Obsidian Plugin API: https://docs.obsidian.md/Plugins
- Three.js: https://threejs.org/docs
- React Three Fiber: https://docs.pmnd.rs/react-three-fiber

---

**Status**: Ready for spike/prototype phase
**Approval Required**: Yes - Confirm 12D approach vs simpler 4D/8D incremental rollout
**Estimated Complexity**: 7-10 person-weeks for full implementation

## Related
**Domains**: ai-ml, architecture, data, infrastructure, integration, performance
**Categories**: strategic, technical


[[graph-databases]], [[knowledge-graph-systems]], [[mcp-infrastructure-architecture]]

## Relevance to Cohezion

[[MCP Infrastructure Architecture]]
[[Compound Engineering]]
[[Context Management]]

## Related Lessons

- [[lesson-11-team-agent-efficiency]] (operational validation)

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-14-phase-6b-cascade-impact-computation]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
