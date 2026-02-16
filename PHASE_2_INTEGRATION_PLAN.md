---
title: "Phase 2: Paper Integration + Dynamic Ingestion Plan"
date: "2026-02-16"
status: ready
tags: [phase-2, paper-integration, dynamic-ingestion, planning]
---

# Phase 2 Implementation Plan

**Status**: READY TO START
**Date**: 2026-02-16
**Scope**: Paper-Decision linking + Dynamic paper ingestion + 3D graph extensions
**Target Timeline**: 8-10 hours
**Pass Criteria**: Papers dynamically appear in 3D graph <500ms after vault addition

---

## Phase 2 Objectives

### Primary: Paper-Decision Integration
- [ ] **Bidirectional Links**: Papers ↔ Decisions in SurrealDB
- [ ] **Link Extraction**: Parse decision notes for paper references
- [ ] **Link UI**: Show related papers in DecisionExplorer
- [ ] **Decision Backlinks**: Show decisions referencing a paper

### Secondary: Dynamic Paper Ingestion
- [ ] **File Watcher**: Detect new papers added to vault
- [ ] **Dimension Computation**: Extract 8 semantic dimensions (from Phase 3)
- [ ] **Cascade Recomputation**: Update cascades when new paper added
- [ ] **3D Graph Update**: Smooth fade-in of new paper nodes

### Tertiary: 3D Graph Extensions
- [ ] **Decision Overlay**: Show decision nodes in 3D space
- [ ] **Reasoning Chains**: Visualize reasoning steps as edges
- [ ] **Decision Toggle**: On/off switch for decision nodes
- [ ] **Interactive Drill-Down**: Click decision → see reasoning

---

## Architecture

```
LAYER 1: Data + Events
├─ File Watcher (monitors /papers/*.md)
├─ Decision Notes (parse frontmatter)
└─ SurrealDB (paper_decision_links table + indexes)

LAYER 2: Processing
├─ DimensionComputer (semantic analysis)
├─ CascadeEngine (recompute on new paper)
└─ LinkBuilder (extract references)

LAYER 3: UI
├─ DecisionExplorer (show related papers)
├─ 3DGraph (decision node overlay)
├─ ReasoningChainRenderer (edge visualization)
└─ Notifications (new paper detected, etc.)
```

---

## Implementation Sequence (4 Sub-Tasks)

### Task 1: Paper-Decision Link Schema (1-2 hours)

**What**: Create SurrealDB table for paper-decision relationships

**Files**:
- `scripts/surrealdb-paper-decision-links.sql`
  ```sql
  DEFINE TABLE paper_decision_links SCHEMAFULL;
  DEFINE FIELD paper_id ON TABLE paper_decision_links TYPE string;
  DEFINE FIELD decision_id ON TABLE paper_decision_links TYPE string;
  DEFINE FIELD link_type ON TABLE paper_decision_links TYPE string; -- "research", "validates", "contradicts"
  DEFINE FIELD confidence ON TABLE paper_decision_links TYPE number;
  DEFINE FIELD mentioned_in ON TABLE paper_decision_links TYPE string; -- rationale excerpt
  DEFINE FIELD extracted_at ON TABLE paper_decision_links TYPE datetime;

  DEFINE INDEX paper_links_idx ON TABLE paper_decision_links COLUMNS paper_id;
  DEFINE INDEX decision_links_idx ON TABLE paper_decision_links COLUMNS decision_id;
  ```

- `src/services/PaperDecisionLinker.ts` (150-200 LOC)
  - `extractPaperReferences(decisionText)` → paper IDs
  - `linkPaperToDecision(paperId, decisionId, type, confidence)`
  - `buildBidirectionalLinks()`

**Success Criteria**:
- [ ] Schema created and indexed
- [ ] Linker extracts references from decision notes
- [ ] Links bidirectional (paper → decision AND decision → paper)

---

### Task 2: Dynamic Paper Ingestion (2-3 hours)

**What**: Auto-detect new papers, compute dimensions, update cascades

**Files**:
- `src/services/DynamicPaperIngestor.ts` (200-250 LOC)
  - File watcher for `/papers/*.md`
  - On new file: compute 8 dimensions
  - On new file: extract paper references
  - On new file: recompute cascades (CascadeEngine)
  - Debounce: 100ms (avoid rapid file saves)

- Enhanced `src/DataLoader.ts` (50-100 LOC additions)
  - Add watcher initialization
  - Handle incremental GraphData updates
  - Smooth fade-in for new nodes

- `src/types/Paper.ts` (update existing)
  - Add `decision_ids: string[]` field
  - Add `ingestion_timestamp: datetime`

**Success Criteria**:
- [ ] File watcher detects new papers <100ms
- [ ] Dimensions computed <300ms
- [ ] GraphData updates incrementally (no full reload)
- [ ] 3D graph re-renders with new paper nodes
- [ ] <500ms total latency from file save to graph update

---

### Task 3: DecisionExplorer Integration (1.5-2 hours)

**What**: Show related papers in DecisionExplorer, create backlinks

**Files**:
- Enhanced `src/ui/DecisionExplorer.ts` (100-150 LOC additions)
  - Add "Related Papers" section below reasoning chain
  - List all papers linked to selected decision
  - Show link type + confidence
  - Link to paper note in vault

- New `src/ui/PaperBacklinksPanel.ts` (100-150 LOC)
  - Show all decisions referencing a paper
  - Click decision → jump to DecisionExplorer
  - Count of references

**Success Criteria**:
- [ ] Related papers visible when decision selected
- [ ] Papers clickable (jump to vault note)
- [ ] Link confidence displayed (user knows trust level)
- [ ] Backlinks panel functional

---

### Task 4: 3D Graph Decision Overlay (2-3 hours)

**What**: Show decision nodes in 3D graph, link to reasoning

**Files**:
- New `src/visualizations/DecisionNodeRenderer.ts` (200-250 LOC)
  - Extend ThreeRenderer with decision nodes
  - Color by reasoning_type
  - Size by confidence_score
  - Glow effect for high-confidence (>0.8)
  - Edges: decision → related papers

- New `src/visualizations/ReasoningChainEdges.ts` (150-200 LOC)
  - Render reasoning steps as animated edges
  - Color gradient: low confidence (red) → high confidence (green)
  - Hover: show step text

- Enhanced `src/visualizations/3DGraph.ts` (150-200 LOC additions)
  - Toggle button: "Show Decisions"
  - Re-render on toggle
  - Handle dynamic updates (new papers)
  - Interactive: click decision → show details

**Success Criteria**:
- [ ] Decision nodes render in 3D (>30 FPS)
- [ ] Toggle on/off works smoothly
- [ ] Clicking decision shows reasoning
- [ ] New papers trigger incremental update (no full re-render)

---

## Testing Strategy

### Unit Tests (2-3 hours)
- `test_paperDecisionLinker.ts` — Extract references correctly
- `test_dynamicIngestor.ts` — File watcher, debounce, dimension computation
- `test_decisionNodeRenderer.ts` — Render with confidence scaling

### Integration Tests
- **Paper Ingestion Flow**: Add paper → Links created → Graph updates
- **Query Performance**: <200ms for paper lookup via decision
- **Edge Cases**:
  - Paper with no links
  - Decision with 50+ linked papers
  - Rapid file saves (debounce tested)

### E2E Tests
- Add new paper → See it in 3D graph <500ms
- Click decision → See related papers
- Hover chain edge → See reasoning step
- Toggle decision overlay → Graph updates smoothly

---

## Implementation Notes

### Token Efficiency
- Reuse existing DimensionComputer from Phase 3
- Reuse existing CascadeEngine from Phase 1
- Minimal new code needed (mostly wiring + UI)
- Target: <800 LOC total new code

### Graceful Degradation
- If dimension computation fails: skip new paper (warn user)
- If cascade recomputation slow: run async, don't block UI
- If 3D graph has 100+ decision nodes: use LOD (level-of-detail)

### Performance Targets
- Paper ingestion: <500ms latency
- 3D graph with 100 decisions: >30 FPS
- Decision search: <200ms
- Link query: <100ms

---

## Success Criteria

**Phase 2 Complete When**:
- [ ] Paper-Decision links bidirectional in SurrealDB
- [ ] New papers auto-detected <500ms
- [ ] 3D graph shows decision nodes with toggle
- [ ] All integration tests pass
- [ ] E2E flow works (add paper → appears in graph)
- [ ] Documentation updated

---

## Risk Mitigation

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| File watcher triggers too often | Medium | Debounce 100ms, only .md files in /papers/ |
| Dimension computation slow | Low | Pre-compute in background, don't block rendering |
| 3D graph performance with 100 decisions | Medium | Implement LOD, fade out far nodes |
| Cascades recomputation expensive | Low | Only recompute if new paper affects existing decisions |

---

## Next Steps After Phase 2

1. **Phase 3**: Advanced cascade visualization (2nd/3rd order effects)
2. **Phase 4A**: Decision Intelligence Core (confidence scoring, recommendations)
3. **Phase 4B**: REST API + Dashboard (if needed)

---

**Status**: ✅ READY TO IMPLEMENT
**Estimated Effort**: 8-10 hours
**Team**: Can be executed by single engineer with Obsidian + TypeScript expertise
