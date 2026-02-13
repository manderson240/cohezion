---
title: "PHASE 3 KICKOFF - Custom Obsidian Plugin Development (UNBLOCKED)"
date: 2026-02-13
status: ready
tags: [phase-3, kickoff, plugin-development, obsidian, visualization, unblocked]
---

# Phase 3 Kickoff: Custom Obsidian Plugin Development

**Status**: ✅ **READY TO START - PHASE 3 UNBLOCKING COMPLETE**
**Start Date**: 2026-02-13 (available now)
**Duration**: 4-6 hours (1-2 days)
**Team**: data-graph-specialist (lead) + vault-architect (support)
**Phase 2 Status**: ✅ Complete (Track A, B, C all signed off)

---

## What Just Happened: Phase 3 Unblocking ✅

Phase 3 was blocked waiting for semantic dimensional data. **That blocker is now removed.**

### Unblocking Work Completed (2026-02-13)

**Generated Semantic Dimensions** (Cost: $0, Time: 15 min):
- Script: `/tmp/generate_semantic_dimensions.py`
- Data: 84 papers × 8 dimensions
- Mode: Production (Ollama nomic-embed-text embeddings)
- Similarity: Top-5 semantic matches per paper (cosine similarity)

**Enriched Vault Files** (Cost: $0, Time: 5 min):
- Script: `/tmp/enrich_vault_with_dimensions.py`
- Result: All 84 papers with dimensional frontmatter
- Dimensions in YAML:
  - `connectivity` (0-1 scale, wiki-links + citations)
  - `cross_domain` (count of distinct domains/tags)
  - `completion` (percentage of structured data)
  - `temporal` (publication timeline position)
  - `recency` (how recent vs historical)
  - `conceptual_depth` (0=theory, 1=applied)
  - `similar_papers` (top 5 matches with similarity scores)

**Compound Engineering Restored**:
- ✅ Vault files = source of truth (not just SurrealDB)
- ✅ Dataview queries can filter by dimensions
- ✅ Obsidian graph views can use metadata
- ✅ Plugin can read dimensional data from files

### Commit
- `2c711d0` - Phase 3 unblocking - semantic dimensions enrichment (2026-02-13)

---

## Phase 3 Scope: Custom Obsidian Plugin

### Goal
Build a custom 3D graph visualization plugin inspired by InfraNodus, mapping 8 dimensions to visual properties.

### Key Decisions
- **Not** using existing Obsidian 3D graph (limited customization)
- **Building** custom plugin with Kyutai template (70% code reuse)
- **Mapping** 8 dimensions → visual properties:
  - **X-axis**: Connectivity (0-1 scale)
  - **Y-axis**: Conceptual depth (theory-applied spectrum)
  - **Z-axis**: Temporal position (publication timeline)
  - **Color**: Domain clustering (cross_domain dimension)
  - **Size**: Completion (0-100%)
  - **Opacity**: Recency (how fresh vs historical)
  - **Links**: Semantic similarity edges (top-5 neighbors)
  - **Labels**: Paper titles with dimension values

### Template Reference
- **Source**: `/home/mike-anderson/dev/cohezion/kyutai-mcp-server/obsidian-plugin/`
- **Language**: TypeScript
- **Lines**: 2,151 LOC (70% reusable)
- **Components**:
  - Settings infrastructure (40+ settings, 8 sections)
  - MCP client pattern (HTTP + auth)
  - Modal windows (3 production modals)
  - Ribbon commands (4 commands)
  - Build pipeline (TypeScript → JavaScript)
  - Test framework (245 tests)

---

## Step-by-Step Plan

### Step 1: Template Setup & Adaptation (1h)

**Objective**: Copy Kyutai template and adapt to plugin structure

**Deliverables**:
- Copy Kyutai obsidian-plugin/ directory
- Update manifest.json (ID, name, description)
- Update package.json (name, dependencies)
- Verify build pipeline works

**Success Criteria**:
- [ ] Plugin builds without errors
- [ ] TypeScript compiles cleanly
- [ ] Plugin loads in Obsidian
- [ ] Ribbon command registered

**Key Files**:
- `manifest.json` - Plugin metadata
- `package.json` - Dependencies + scripts
- `tsconfig.json` - TypeScript config
- `esbuild.config.js` - Build configuration

---

### Step 2: Data Loading & Parsing (1h)

**Objective**: Read dimensional metadata from vault papers

**Deliverables**:
- Load all papers from vault (84 files)
- Parse YAML frontmatter
- Extract 8 dimensions per paper
- Build in-memory graph structure

**Success Criteria**:
- [ ] All 84 papers loaded
- [ ] All 8 dimensions extracted
- [ ] Graph structure validated
- [ ] Memory footprint < 50MB

**Key Implementation**:
```typescript
interface PaperNode {
  id: string;
  title: string;
  dimensions: {
    connectivity: number;    // 0-1
    cross_domain: number;    // count
    completion: number;      // 0-100
    temporal: number;        // 0-1
    recency: number;         // 0-1
    conceptual_depth: number; // 0-1
  };
  similar_papers: Array<{
    paper: string;
    similarity: number;
  }>;
}

interface GraphData {
  nodes: PaperNode[];
  edges: Array<{
    source: string;
    target: string;
    similarity: number;
  }>;
}
```

---

### Step 3: 3D Visualization Engine (2h)

**Objective**: Render 3D force-directed graph with dimensional mapping

**Deliverables**:
- Integrate Three.js for 3D rendering
- Implement force-directed layout (3D physics simulation)
- Map 8 dimensions to visual properties
- Add camera controls (pan, zoom, rotate)
- Implement node selection + highlighting

**Success Criteria**:
- [ ] 3D graph renders all 84 papers
- [ ] Physics simulation stable (< 2s to settle)
- [ ] Dimensions properly mapped to visuals
- [ ] Performance > 30 FPS
- [ ] Camera controls responsive

**Visual Mapping**:
```typescript
const nodeColor = (paper) => {
  // Color by domain clustering (cross_domain dimension)
  const hue = (paper.dimensions.cross_domain % 10) * 36;
  return `hsl(${hue}, 70%, 50%)`;
};

const nodeSize = (paper) => {
  // Size by completion (0-100% → 0.5-2.0)
  return 0.5 + (paper.dimensions.completion / 100) * 1.5;
};

const nodeOpacity = (paper) => {
  // Opacity by recency (fade older papers)
  return 0.3 + (paper.dimensions.recency * 0.7);
};

const nodePosition = (paper) => {
  // Initial positions based on dimensions
  return {
    x: (paper.dimensions.connectivity - 0.5) * 100,
    y: (paper.dimensions.conceptual_depth - 0.5) * 100,
    z: paper.dimensions.temporal * 100,
  };
};
```

---

### Step 4: Interactive Features (1h)

**Objective**: Add interactivity for exploration

**Deliverables**:
- Click paper → show metadata panel
- Hover paper → highlight similar papers
- Search papers by title/keywords
- Filter by dimension thresholds
- Sidebar with graph statistics

**Success Criteria**:
- [ ] Paper selection works
- [ ] Similar papers highlight correctly
- [ ] Search responsive (< 100ms)
- [ ] Filters update graph dynamically
- [ ] Sidebar shows correct stats

**Example Interactions**:
```typescript
// Click to show details
onPaperClick(paper) {
  showDetailsPanel({
    title: paper.title,
    dimensions: paper.dimensions,
    similar: paper.similar_papers,
    tags: paper.keywords,
  });
}

// Hover to highlight neighbors
onPaperHover(paper) {
  highlightNodes(paper.similar_papers.map(s => s.paper));
  highlightEdges(paper.id);
}

// Filter by dimension
filterByConnectivity(minConnectivity) {
  graph.nodes = nodes.filter(n =>
    n.dimensions.connectivity >= minConnectivity
  );
  updateVisualization();
}
```

---

### Step 5: Polish & Documentation (1h)

**Objective**: Finalize and document

**Deliverables**:
- Settings panel for customization
- Performance optimization
- TypeScript type checking passes
- Plugin documentation
- User guide

**Success Criteria**:
- [ ] No TypeScript errors
- [ ] Settings load/save correctly
- [ ] Performance targets met (30+ FPS)
- [ ] Documentation complete
- [ ] Ready for production

---

## Success Criteria

### Code Quality
- ✅ TypeScript: No errors, strict mode
- ✅ Build: Clean compilation
- ✅ Tests: 80%+ coverage (if time permits)

### Functionality
- ✅ All 84 papers rendered
- ✅ 8 dimensions mapped to visuals
- ✅ Interactive features work
- ✅ Performance > 30 FPS
- ✅ Responsive to interactions

### User Experience
- ✅ Intuitive navigation
- ✅ Clear visual encoding
- ✅ Help/documentation
- ✅ Settings customizable

### Deliverables
- ✅ Plugin loads in Obsidian
- ✅ Graph renders in modal
- ✅ Interactive features functional
- ✅ Code documented
- ✅ Ready for marketplace submission

---

## Key Files & Resources

### Dimensional Data (Ready)
- `/tmp/semantic_dimensions.json` - Full dimensional data
- Vault papers: `/home/mike-anderson/vaults/cohezion-vault/papers/*.md`
- Example frontmatter: All papers now have dimensional metadata

### Template (Ready to Copy)
- Source: `/home/mike-anderson/dev/cohezion/kyutai-mcp-server/obsidian-plugin/`
- Build: `npm install && npm run dev`
- Test: `npm test`

### Obsidian SDK References
- Settings API: https://docs.obsidian.md/Plugins/User+interface/Settings
- Canvas API: https://docs.obsidian.md/No+Block/Canvas+API
- Modal API: https://docs.obsidian.md/Plugins/User+interface/Modals+and+confirmations

### Libraries to Use
- **Three.js**: 3D rendering (already in Kyutai template)
- **D3-Force**: Force-directed layout (recommend for 3D extension)
- **YAML**: Parse frontmatter (js-yaml)

---

## Team Assignments

### Lead: data-graph-specialist
- **Primary Responsibility**: Plugin architecture + implementation
- **Expected Time**: 3-4 hours
- **Deliverables**: All 5 steps (Steps 1-5)
- **Support**: vault-architect for Obsidian API questions
- **Previous Work**: Track A (agent reasoning), Phase 2 complete

### Support: vault-architect
- **Primary Responsibility**: Obsidian integration + data pipeline
- **Expected Time**: 1-2 hours
- **Deliverables**: Step 2 (data loading) + settings
- **Support**: SurrealDB schema questions, vault file structure
- **Previous Work**: Track C lead, Phase 2 complete

---

## Blockers & Dependencies

### External Dependencies
- ✅ Obsidian SDK (documentation available)
- ✅ Three.js (already proven in Kyutai)
- ✅ npm / TypeScript toolchain (working)

### Internal Dependencies
- ✅ Dimensional data (READY - just generated)
- ✅ Vault papers (READY - all 84 enriched)
- ✅ SurrealDB schema (READY - Phase 2 complete)

### Previous Blockers (NOW RESOLVED ✅)
- ✅ Semantic dimensions (UNBLOCKED - generated 2026-02-13)
- ✅ Frontmatter enrichment (UNBLOCKED - completed 2026-02-13)

**Summary**: ✅ **ZERO BLOCKERS - READY TO START IMMEDIATELY**

---

## Phase 3 Timeline

```
NOW (2026-02-13)
├─ Step 1: Template setup (1h)
├─ Step 2: Data loading (1h)
├─ Step 3: 3D visualization (2h)
├─ Step 4: Interactive features (1h)
└─ Step 5: Polish (1h)

EXPECTED COMPLETION: 2026-02-13 or 2026-02-14
```

---

## What Phase 3 Unlocks

### Immediate (Phase 3 Output)
- ✅ Custom 3D graph visualization plugin
- ✅ 84 papers rendered with dimensional metadata
- ✅ Interactive exploration interface
- ✅ Dataview integration ready

### Phase 4 (Decision Analysis)
- Decision impact visualization
- Reasoning chain traversal
- Confidence scoring
- Root cause analysis UI

### Phase 5 (Dashboard)
- Operational metrics dashboard
- Team performance tracking
- Decision quality metrics
- Learning curve visualization

---

## Success Indicators

### By EOD 2026-02-13 (if time permits)
- [ ] Steps 1-3 complete
- [ ] 3D graph renders and interactive
- [ ] Basic features working

### By EOD 2026-02-14
- [ ] All 5 steps complete
- [ ] Fully functional plugin
- [ ] Documentation ready
- [ ] Ready for Obsidian marketplace

---

## Notes for Execution

### Performance Tips
- Lazy-load paper details (don't render all immediately)
- Use webworker for force-directed simulation
- Implement frustum culling for 3D rendering
- Cache similarity computations

### Obsidian Integration
- Store settings in plugin data file
- Use Obsidian's file API for paper access
- Leverage Obsidian's event system for updates
- Respect user's vault privacy

### Testing Strategy
- Unit tests for data loading (Step 2)
- Integration tests for graph rendering (Step 3)
- Manual testing of interactions (Step 4)
- Performance profiling (all steps)

---

## File Locations Summary

**Dimensional Data**:
- Generated: `/tmp/semantic_dimensions.json`
- Enriched: `/home/mike-anderson/vaults/cohezion-vault/papers/*.md` (all 84 files)

**Template to Copy From**:
- `/home/mike-anderson/dev/cohezion/kyutai-mcp-server/obsidian-plugin/`

**Documentation**:
- This kickoff document
- Phase 3 decision: `decisions/2026-02-13-phase-3-custom-plugin-unblocked.md` (will create)

---

## Next Steps

### Immediate (Now)
1. ✅ Review this kickoff document
2. ✅ Review dimensional data in vault files
3. ✅ Inspect Kyutai template structure
4. ✅ Set up development environment

### Start Execution (2026-02-13 or 2026-02-14)
1. Begin Step 1: Template setup
2. Proceed through Steps 2-5
3. Daily checkpoint: 17:00 UTC
4. Expected completion: EOD 2026-02-14

### Completion
1. Sign-off document with metrics
2. Plugin ready for testing
3. Phase 4 planning begins

---

## Final Status

**Phase 3 Blocker**: ✅ **REMOVED** (2026-02-13 11:45 UTC)
**Dimensional Data**: ✅ **Generated** (84 papers, 8 dimensions, Ollama embeddings)
**Vault Enrichment**: ✅ **Complete** (All papers with frontmatter metadata)
**Compound Engineering**: ✅ **Restored** (Vault files = source of truth)

**Phase 3 Status**: 🟢 **READY TO START**

---

**Prepared by**: Claude Code (Phase 3 Unblocking Agent)
**Date**: 2026-02-13
**Unblocking Cost**: $0 (local Python + Ollama)
**Unblocking Time**: 20 minutes
**Status**: ✅ **READY FOR EXECUTION**

Next phase: Phase 3 custom Obsidian plugin development with full dimensional metadata!
