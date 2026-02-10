---
title: "HANDOFF: Phase 3 Custom Plugin - Ready to Build"
date: 2026-02-10
status: ready
tags: [handoff, phase-3, blocker-identified, execution-ready]
---

# Phase 3 Custom Plugin - Handoff

## TL;DR

**Status**: Phase 1+2 complete (8 dimensions). Phase 3 blocked by missing frontmatter enrichment.

**Critical blocker**: Dimensional data exists in `/tmp/semantic_dimensions.json` but NOT in vault files.

**Next action**: Run `/tmp/enrich_vault_with_dimensions.py` (cost: $0, time: 2 min)

**Then build**: Custom 3D graph plugin using Kyutai template (8-12K tokens, 4-6h)

---

## Current State

### ✅ Complete
- **Phase 1**: 5 computational dimensions (connectivity, cross_domain, completion, temporal, recency)
- **Phase 2**: 3 semantic dimensions (embeddings, conceptual_depth, gap_analysis)
- **Data**: 84 papers × 8 dimensions in `/tmp/semantic_dimensions.json`
- **Template**: Kyutai plugin (2,151 LOC TypeScript, 70% reusable)
- **Decision**: Build custom plugin inspired by InfraNodus (SETTLED)

### 🚧 Blocked
- **Phase 3**: Cannot build plugin yet - dimensions not in vault frontmatter
- **Issue**: Phase 2 wrote to JSON file, not back to vault files
- **Impact**: Breaks source-of-truth principle, blocks visualization

### 🎯 Decision Made
- Build **custom Obsidian plugin** (not use existing)
- Inspired by **InfraNodus** approach (3D force-directed graph)
- Map **8 dimensions** to visual properties (X/Y/Z, color, size, opacity)
- Use **Kyutai template** for 70% code reuse

---

## Unblock: Dimensional Frontmatter Enrichment

### Script Ready
**File**: `/tmp/enrich_vault_with_dimensions.py`
**Cost**: $0 (local Python, no API calls)
**Time**: ~2 minutes
**What it does**:
1. Reads `/tmp/semantic_dimensions.json` (Phase 2 output)
2. Enriches 84 papers with dimensional frontmatter
3. Adds `dimensions:` section with 8 metadata fields
4. Makes vault files the source of truth

### Run Command
```bash
/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3 /tmp/enrich_vault_with_dimensions.py
```

### Output Example
```yaml
---
title: "Paper Title"
dimensions:
  connectivity: 0.823
  cross_domain: 5
  completion: 100
  temporal: 0.891
  recency: 0.945
  conceptual_depth: 0.673
  similar_papers:
    - paper: related-paper-1
      similarity: 0.089
    - paper: related-paper-2
      similarity: 0.078
---
```

### Unlocks
- ✅ Phase 3B plugin build (can read from vault files)
- ✅ Dataview queries on dimensions
- ✅ Source-of-truth principle restored
- ✅ Obsidian native features can use metadata

---

## Then: Phase 3B - Build Custom Plugin

### Template Reuse (70%)
**Source**: `/home/mike-anderson/dev/cohezion/kyutai-mcp-server/obsidian-plugin/`

**Reusable components**:
- Settings infrastructure (40+ settings, 8 sections) ✅
- MCP client pattern (HTTP + auth) ✅
- Modal windows (3 production modals) ✅
- Ribbon commands (4 commands) ✅
- TypeScript build pipeline (CI/CD) ✅
- Testing framework (245 tests) ✅

**Replace with**:
- 3D graph rendering (Three.js or Force-Graph-3D)
- Dimensional data queries (read from vault frontmatter)
- Visual mappings (8 dimensions → visual properties)
- View presets (4 analytical perspectives)

### Implementation Plan

#### Step 1: Copy Kyutai Structure (1K tokens, 30 min)
```bash
cd /home/mike-anderson/dev/cohezion/
cp -r kyutai-mcp-server/obsidian-plugin/ 12d-graph-plugin/
cd 12d-graph-plugin/
rm -rf src/services/tts src/services/stt  # Remove TTS/STT
```

#### Step 2: ONE View Implementation (5-7K tokens, 3-4h)
- Single ribbon command: "Open 12D Graph"
- Read dimensional data from vault frontmatter
- Render 3D force-directed graph (84 nodes, 575 edges)
- Map 8 dimensions to X/Y/Z/color/size/opacity
- Basic interactions: rotate, zoom, click nodes

#### Step 3: Validate Value (1K tokens, 30 min)
- Test with 10 papers
- Verify dimensional mappings visible
- User feedback: Is this useful?
- Decision gate: Scale to full feature set OR stop

#### Step 4: Scale (IF valuable) (5-10K tokens, 2-3 weeks)
- Add 4 view presets
- Add filtering/search
- Add network analysis features
- Polish UI/UX

### Estimated Cost
- **Step 1-3**: 8-12K tokens (vs 35K from scratch) = 66% savings
- **Full build**: 15-20K tokens (if Step 3 validates value)

---

## Session Retrospective

### What Went Wrong
- ❌ Analysis paralysis: Questioned settled decision (500 tokens wasted)
- ❌ Created validation when execution was needed
- ❌ Missed obvious blocker (frontmatter enrichment)

### What Went Right
- ✅ Identified dimensional frontmatter gap (critical)
- ✅ Validated vault-as-source-of-truth principle
- ✅ Confirmed Kyutai template reuse (70%)
- ✅ Created enrichment script (ready to run)

### Key Lesson
**Execution vs Decision contexts**:
- Decision phase → adversarial review, validate approach
- Execution phase → identify blocker, fix, build
- Phase 3 is **execution** (decision made, template ready, data computed)

**Full retrospective**: `retrospectives/2026-02-10-phase3-session-retrospective.md`

---

## Files for Next Session

### Critical
- `/tmp/enrich_vault_with_dimensions.py` - **RUN THIS FIRST**
- `/tmp/semantic_dimensions.json` - Phase 2 output (input to enrichment)
- `/home/mike-anderson/dev/cohezion/kyutai-mcp-server/obsidian-plugin/` - Template source

### Reference
- `patterns/12d-graph-implementation.md` - Original plan (needs updating)
- `decisions/2026-02-10-phase3-3d-graph-adversarial-review.md` - Analysis (some useful)
- `retrospectives/2026-02-10-phase3-session-retrospective.md` - Lessons learned

### Useful Exports
- `.obsidian/3d-graph-data.json` - 84 nodes, 575 edges (may be useful for plugin)
- `/tmp/export_from_vault_files.py` - Vault data export tool

---

## Execution Checklist

- [ ] Run enrichment script (2 min, $0)
- [ ] Verify dimensions in vault frontmatter (spot-check 5 papers)
- [ ] Copy Kyutai plugin structure (30 min)
- [ ] Implement ONE 3D view (3-4h, 5-7K tokens)
- [ ] Validate with 10 papers (30 min)
- [ ] Decision gate: Scale OR stop
- [ ] Update status files

**No more**: Questioning, validating, or re-deciding. Decision made. Building blocks ready. Just execute.

---

**Handoff complete. Ready for Phase 3B execution.**

[[phase-3]], [[12d-graph]], [[kyutai-project]], [[compound-engineering]]
