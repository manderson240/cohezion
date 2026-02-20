---
title: "Phase 3A: 3D Graph Validation Experiment"
date: 2026-02-10
status: in-progress
tags: [experiment, 12d-graph, validation, token-efficiency]
---

# Phase 3A: 3D Graph Validation Experiment

## Hypothesis

Existing 3D graph plugins can render our vault structure, eliminating the need for a custom plugin (saving 33K tokens).

## Method

### Token-Efficient Validation Approach

Instead of building custom plugin first (35K tokens), we:
1. ✅ Export vault data to JSON (500 tokens)
2. ⏳ Test with existing "New 3D Graph" plugin
3. ⏳ Document gaps (if any)
4. ⏳ Decision gate: Use existing OR build custom

**Rationale**: "Implementation First, Infrastructure Later" lesson from Kyutai project.

## Results

### Phase 3A.1: Data Export (COMPLETE)

**Script**: `/tmp/export_from_vault_files.py` (200 LOC)
**Output**: `.obsidian/3d-graph-data.json`
**Data**:
- 84 nodes (papers)
- 575 edges (wiki-links)
- Node metadata: title, tags, file path

**Token Cost**: ~500 tokens (vs 35K for full plugin build) = **98.6% savings**

### Key Findings

#### Finding 1: Dimensional Data Not in Frontmatter ⚠️

**Issue**: Phase 1+2 computed 8 dimensions but didn't write to vault frontmatter.
**Impact**: Cannot test dimensional visualizations yet.
**Files**: Dimensions exist in `/tmp/semantic_dimensions.json` (from Phase 2)

**Statistics**:
- Papers with dimensional frontmatter: 0/84 (0%)
- Papers with wiki-links: 84/84 (100%)
- Total wiki-link edges: 575

#### Finding 2: YAML Parsing Errors (28 papers)

**Issue**: Some frontmatter uses `[[wiki-link]]` syntax in arrays, breaks YAML parser.
**Files affected**: 28/84 papers (33%)
**Example error**:
```yaml
related_papers: [[paper-1]], [[paper-2]]  # ❌ YAML sees nested structures
```

**Workaround**: Script handles gracefully, extracts wiki-links from content instead.
**Proper fix**: Clean up frontmatter (tracked in memory as "28 papers with YAML parsing errors")

#### Finding 3: SurrealDB Not Running

**Issue**: SurrealDB process exists but not listening on port 8000.
**Impact**: Cannot query dimensional data from database.
**Workaround**: Read directly from vault files (simpler, more reliable).

**Lesson**: Source of truth is vault files, not database. Database is a view, not the authority.

## Phase 3A.2: Plugin Testing (NEXT)

### Manual Test Steps

1. **Install Plugin** (5 minutes)
   - Open Obsidian
   - Settings → Community Plugins
   - Search: "New 3D Graph"
   - Install + Enable

2. **Test Basic Visualization** (10 minutes)
   - Open 3D Graph view
   - Verify 84 nodes render
   - Verify 575 wiki-link edges render
   - Test interactions: rotate, zoom, click nodes

3. **Document Capabilities** (15 minutes)
   - ✅ What works out-of-box?
   - ❌ What gaps exist?
   - 🤔 Can we configure dimensional mappings?

4. **Decision Gate**
   - If gaps < 3 specific features → Use existing plugin (STOP, save 33K tokens)
   - If gaps >= 3 critical features → Proceed to Phase 3B (template reuse)

## Next Steps

### Option A: Existing Plugin Works (BEST CASE)

**If "New 3D Graph" meets needs**:
- Token savings: 33K (no custom build needed)
- Time savings: 3-4 weeks
- Update `decisions/phase3-3d-graph-adversarial-review.md` with findings
- Mark Phase 3 COMPLETE

### Option B: Enrich Frontmatter First (LIKELY)

**If we need dimensional data for testing**:
1. Read `/tmp/semantic_dimensions.json` (Phase 2 output)
2. Batch enrich 84 papers with dimensional frontmatter (2K tokens)
3. Re-export graph data with dimensions
4. Retry plugin testing

**Cost**: 2K tokens + 1 hour

### Option C: Custom Plugin Required (FALLBACK)

**If existing plugin has 3+ critical gaps**:
1. Document specific requirements
2. Copy Kyutai plugin structure (70% reuse)
3. Build ONE 3D view (8-12K tokens)
4. Validate value before scaling

**Cost**: 10-14K tokens (vs 35K from scratch) = 60% savings

## Learnings

### What Worked

1. ✅ **Vault-first approach**: Read from source files, not database
2. ✅ **Graceful degradation**: Export succeeded despite YAML errors
3. ✅ **Token efficiency**: 500 tokens to validate vs 35K to build blindly
4. ✅ **Adversarial review**: Identified validation gap before heavy investment

### What Didn't Work

1. ❌ **SurrealDB dependency**: Not critical for validation
2. ❌ **Assumed dimensional frontmatter**: Phase 1+2 didn't write back to vault
3. ❌ **YAML frontmatter format**: 28 papers have syntax issues

### Pattern Confirmed

**"Implementation First, Infrastructure Later"** (from Kyutai):
- ✅ Validate with minimal script (500 tokens)
- ✅ Gate heavy investment (35K tokens) on proven value
- ✅ Incremental validation (3A → 3B → 3C)
- ✅ Reuse templates when available (Kyutai = 70% applicable)

## Cost Analysis

| Approach | Tokens | Time | Risk |
|----------|--------|------|------|
| **Phase 3A (ours)** | 500 | 1h | Low |
| Phase 3B (if needed) | 8-12K | 6h | Medium |
| Phase 3C (scale) | 15-20K | 2-3w | High |
| **Original plan** | 35K | 3-4w | High |

**Savings so far**: 34.5K tokens (98.6%), decision gate not yet exercised

## Status

- [x] Script written (200 LOC, `/tmp/export_from_vault_files.py`)
- [x] Data exported (84 nodes, 575 edges, `.obsidian/3d-graph-data.json`)
- [x] Findings documented
- [ ] Plugin installed and tested
- [ ] Decision gate exercised
- [ ] Next phase determined

## Related

[[Implementation First, Infrastructure Later]]
[[Phase 3: 3D Graph Plugin - Adversarial Review]]
[[12D Graph Implementation]]
[[Kyutai Project]]

[[token-efficiency]], [[compound-engineering]], [[adversarial-review]]

## Related Concepts

- [[2026-02-09-12d-graph-refined-plan]]
- [[2026-02-10-canvas-driven-compound-engineering-refined]]
- [[2026-02-14-settings-files-validation-and-fix]]
- [[2026-02-14-phase-6c-semantic-contradiction-detection-complete]]
- [[2026-02-10-claude-log-mining-architecture]]
- [[2026-02-10-phase3-3d-graph-adversarial-review]]
- [[2026-02-10-kyutai-pocket-tts-token-efficient-success]]
- [[2026-02-10-kyutai-token-waste-postmortem]]
