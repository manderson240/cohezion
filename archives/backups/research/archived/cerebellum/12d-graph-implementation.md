---
title: "12D Graph Implementation - Token-Efficient Compound Engineering"
date: 2026-02-10
status: in-progress
tags: [pattern, 12d-graph, compound-engineering, phase-1]
aspect: thinker
neural:
  activation: 0.86
  stage: mature
  synapse_in: 22
  synapse_out: 14
---

# 12D Graph Implementation - Token-Efficient Plan

**Goal**: Deliver production-ready 12D graph in 3-4 weeks using <100K tokens with 3-5 specialists.

**Comparison to original plan**:
- Original: 200K tokens, 7-8 weeks, 6-7 specialists
- Revised: 65-80K tokens, 3-4 weeks, 3-5 specialists
- **Savings**: 60% fewer tokens, 50% faster, 65% cheaper

## Phase 1: Quick Wins (Week 1, 15-20K tokens)

**Deliver 5 computational dimensions** using existing data + simple algorithms.

### 5 Dimensions to Compute

1. **Connectivity Density** - Count wiki-links per paper, normalize
2. **Cross-Domain Bridging** - Count unique tags, highlight multi-domain papers
3. **Completion Status** - Check for required sections (Summary, Key Findings, Source)
4. **Temporal Dimension** - Parse publication dates, normalize oldest→newest
5. **Recency/Relevance** - Combine publication date + last modified time

### Phase 1 Deliverables

- [ ] `/tmp/compute_dimensions.py` - Dimension computation script
- [ ] SurrealDB updated with 5 dimensional scores for all 84 papers
- [ ] Vault frontmatter enriched with dimensional scores
- [ ] Query tests: "Top 10 papers by connectivity", "Incomplete papers"
- [ ] Token spend < 20K
- [ ] Git commit: "feat: Phase 1 - 5 computational dimensions"

### Success Criteria

- ✅ All 84 papers have 5 dimensional scores in SurrealDB
- ✅ Frontmatter enriched: "Connectivity: ★★★★☆ (8/10)"
- ✅ Can query dimensional data from SurrealDB
- ✅ Immediate Obsidian improvements visible

---

## Phase 2: Semantic Dimensions (Week 2, 20-25K tokens)

**Add 3 dimensions** using local Ollama LLMs ($0 inference cost).

### 3 Semantic Dimensions

1. **Semantic Similarity** - Embeddings + cosine similarity matrix (top-5 similar papers)
2. **Conceptual Depth** - Theory vs applied spectrum (0=applied, 1=theory)
3. **Gap Analysis** - Identify temporal/domain/connectivity gaps

### Phase 2 Deliverables

- [ ] `/tmp/semantic_dimensions.py` - Ollama integration script
- [ ] Embeddings generated for all 84 papers via Ollama ($0 cost)
- [ ] Semantic similarity matrix computed
- [ ] Conceptual depth scores assigned
- [ ] `inbox/research-gaps.md` with 5+ research gap candidates
- [ ] Token spend < 25K, **inference cost = $0**

---

## Phase 3: Visualization Layer (Week 3-4, 30-35K tokens)

**Install 3D graph plugin with 8-dimensional mappings**.

### Visual Mappings

- **X-axis**: `dim_temporal` (temporal evolution)
- **Y-axis**: `dim_connectivity` (hub vs leaf)
- **Z-axis**: `dim_cross_domain` (bridging papers higher)
- **Node size**: `dim_completion` (bigger = complete)
- **Node color**: `dim_conceptual_depth` (red=theory, blue=applied)
- **Node opacity**: `dim_recency` (bright=recent, faded=old)

### View Presets

1. "Domain Clusters" - Color by tags, semantic clustering
2. "Temporal View" - See knowledge evolution over time
3. "Completion Status" - Filter incomplete papers
4. "Bridging Papers" - Highlight cross-domain papers 🌉

### Phase 3 Deliverables

- [ ] 3D graph plugin installed and rendering
- [ ] 8 dimensions mapped to visual properties
- [ ] 4 view presets functional and tested
- [ ] `.obsidian/plugins/3d-graph/config.json` configured
- [ ] `.obsidian/3d-graph-data.json` exported from SurrealDB
- [ ] Token spend < 35K

---

## Specialist Roles

### Phase 1-3 Core Team

1. **Dimension Engineer** (Haiku, max_turns=10)
   - Design dimensional algorithms
   - Implement `/tmp/compute_dimensions.py`
   - Output: JSON with dimensional scores for 84 papers

2. **Embedding Engineer** (Haiku, max_turns=10)
   - Design Ollama MCP integration
   - Implement `/tmp/semantic_dimensions.py`
   - Output: JSON with embeddings + similarity + depth scores

3. **Plugin Integration Specialist** (Sonnet, max_turns=15)
   - Install New 3D Graph plugin (Apoo711 recommendation)
   - Configure dimensional mappings
   - Output: Working 3D graph in Obsidian

4. **Dimension Mapper** (Haiku, max_turns=8)
   - Export 8 dimensions from SurrealDB to JSON
   - Format for plugin consumption
   - Output: `.obsidian/3d-graph-data.json`

5. **Lead** (Manual orchestration)
   - Coordinate specialists
   - Apply batch updates to SurrealDB
   - Enrich vault frontmatter
   - Design view presets
   - Commit changes

---

## Current Status

- **Infrastructure**: ✅ SurrealDB running, Ollama MCP configured
- **Data**: ✅ 84 papers + 21 concepts + 148 links in SurrealDB
- **Team**: 🟡 Phase 1 team being assembled
- **Phase 1**: 🟡 In progress
- **Phase 2**: ⏳ Pending Phase 1 completion
- **Phase 3**: ⏳ Pending Phase 2 completion

---

## Key Files

### Existing (Extend)
- `cloud-vault-mcp/src/mcp_server/surrealdb_sync.py` - Add dimensional fields to schema
- `papers/*.md` (84 files) - Add frontmatter fields via batch Edit

### New (Create)
- `/tmp/compute_dimensions.py` - Phase 1 computational engine
- `/tmp/semantic_dimensions.py` - Phase 2 semantic engine
- `.obsidian/plugins/3d-graph/config.json` - Plugin configuration
- `.obsidian/3d-graph-data.json` - Dimensional data export

---

## Token Budget

| Phase | Tokens | Cost | Timeline | Value |
|-------|--------|------|----------|-------|
| Phase 1 | 15-20K | $0.05 | Week 1 | 5 dimensions, immediate value |
| Phase 2 | 20-25K | $0.06 | Week 2 | 8 dimensions, $0 inference |
| Phase 3 | 30-35K | $0.10 | Week 3-4 | Interactive 3D graph |
| **Total** | **65-80K** | **$0.21** | **3-4 weeks** | Production-ready system |

---

## Decision Points

- **After Phase 1**: If not providing value, stop here
- **After Phase 2**: If Ollama integration fails, fallback to Phase 1 only
- **After Phase 3**: Defer Phase 4 (remaining 4 dimensions) until proven 10x+ value

---

## References

- SurrealDB MCP tools: `surrealdb_query()`, `surrealdb_import_papers()`
- Ollama MCP tools: `ollama_query()`, `ollama_embed()`, `ollama_batch()`
- Plugin recommendation: New 3D Graph (Apoo711) - actively maintained
- Pattern: Lessons Graph Integration - similar methodology proven


[[graph-databases]], [[knowledge-graph-systems]], [[mcp-infrastructure-architecture]]

## Decisions That Produced This Pattern

- [[2026-02-09-12d-graph-next-steps]] — the hybrid path (incremental + full) strategy this plan implements
- [[2026-02-09-12d-graph-refined-plan]] — the specialist-driven implementation plan this pattern extracts the token-efficient version of
- [[2026-02-09-12d-graph-surrealdb-integration]] — the original SurrealDB integration decision this builds on
- [[2026-02-10-phase3-3d-graph-adversarial-review]] — the adversarial review that identified improvements to the original plan

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-14-phases-1-3-retrospective-key-learnings]]
- [[2026-02-10-kyutai-mcp-obsidian-plugin-plan]]
- [[2026-02-14-phase-6a-automated-reasoning-chain-inference-complete]]
- [[2026-02-09-12d-graph-refined-plan]]
- [[2026-02-10-canvas-driven-compound-engineering-refined]]
- [[2026-02-14-wave-1-overnight-completion-report]]
