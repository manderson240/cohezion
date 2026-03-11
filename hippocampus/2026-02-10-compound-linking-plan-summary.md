---
title: "Compound Node Linking Plan Summary (2026-02-10)"
date: 2026-02-10
tags: [daily, planning, vault-enrichment, infrastructure]
aspect: doer
neural:
  activation: 0.446
  stage: growing
  cluster: daily
---

## The Challenge

31 vault nodes lack semantic connections to concepts, creating **discovery gaps** in the knowledge graph:

```
Papers:      69/84 linked (82%) → 15 unlinked ❌
Decisions:    7/17 linked (41%) → 10 unlinked ❌
Patterns:    14/19 linked (74%) →  5 unlinked ❌
Experiments:  1/2 linked (50%) →  1 unlinked ❌
───────────────────────────────────────────────
TOTAL:      113/144 (78%) → 31 unlinked nodes
```

**Current State**: Graph has poor connectivity; semantic search & cross-linking limited.
**Target State**: 95%+ linked (144/144 nodes), dense semantic graph, full discoverability.

---

## The Compound Engineering Solution

**Token-Efficient 4-Phase Plan**: Local Ollama ($0) → Heuristic Matching ($0) → Batch Application ($0) → SurrealDB Sync ($0-2)

### Phase 1: Ollama Semantic Analysis ($0, ~30 min)
Extract semantic keywords from 31 unlinked nodes using **local** qwen2.5-coder:14b
- Input: Note titles + abstracts + key findings
- Output: Semantic keyword vectors for each node
- Cost: $0 (local execution, no API calls)
- Why: Ollama MCP already configured, proven track record

### Phase 2: Heuristic Matching ($0, ~30 min)
Apply proven **v2 selective scoring** (from lessons integration) with 30% confidence threshold
- Load 22 concept notes (inventory)
- Score semantic overlap for each unlinked node
- Filter noise: Only keep matches ≥0.30 score
- Output: [{"file": "...", "add_links": ["[[concept-1]]", "[[concept-2]]"]}]
- Why: 85%+ accuracy validated, minimal false positives

### Phase 3: Batch Application ($0, ~30 min)
Apply wiki-links to vault notes with deduplication & reversibility
- Read unlinked nodes from vault
- Append wiki-links to "Relevance to Cohezion" section
- Batch commits: 15-20 files per commit (atomic)
- Tool: Extend `/tmp/apply_links.py`
- Why: Idempotent, reversible, preserves vault integrity

### Phase 4: SurrealDB Sync + Verification ($0-2, ~30-60 min)

**Step 4a**: Batch import new links to 12D graph ($0)
- UPSERT (source, target, confidence) tuples
- Batch size: 20-30 links/call
- Tool: MCP `surrealdb_import_concepts()`

**Step 4b**: Optional spot-check verification ($1-2)
- Sample 10% of new links (5-10 nodes)
- Haiku validates: "Does [[concept]] link make sense for this note?"
- Success: <5% rejection rate
- Only if quality concerns arise

---

## Cost Breakdown: Token Efficiency

| Approach | Cost | Tokens | Notes |
|----------|------|--------|-------|
| **Claude-only (Sonnet)** | $8-12 | 50-60K | Semantic extraction for 31 nodes |
| **Claude-only (Haiku)** | $3-4 | 20-25K | Cheaper but less capable |
| **This Plan** | $0-2 | ~500 | 100% local Ollama + optional spot-check |
| **SAVINGS** | **96-99%** | **40-60K** | ✓ **Compound Engineering Win** |

### Why 96-99% Savings?

1. **Local Semantic Analysis** (Phase 1-2): Ollama MCP replaces $8 Claude extraction
2. **Proven Heuristic Methodology** (Phase 2): Lessons v2 eliminated need for iterative Claude refinement
3. **Batch Operations** (Phase 3): Local Python applies links in bulk (no API overhead)
4. **Optional Verification** (Phase 4b): Only pay $1-2 for spot-checks if truly needed
5. **SurrealDB Sync** (Phase 4a): Already local, MCP handles it free

---

## Execution Timeline

```
Phase 1: 30 min (Ollama batch extraction)
Phase 2: 30 min (Keyword matching + scoring)
Phase 3: 30 min (Apply wiki-links to vault)
Phase 4: 30-60 min (SurrealDB sync + optional spot-check)
─────────────────────────────────
TOTAL: ~2.5 hours hands-on work
```

**Key Insight**: All phases can run sequentially with clear hand-offs:
- Phase 1 → Phase 2 (JSON output from Ollama feeds into heuristic)
- Phase 2 → Phase 3 (Match candidates feed into link applicator)
- Phase 3 → Phase 4 (Applied links ready for SurrealDB import)

---

## Expected Outcomes

✅ **Coverage**: All 31 unlinked nodes receive ≥1 semantic wiki-link
✅ **New Links**: ~25-35 new concept connections added
✅ **Quality**: 85%+ semantic correctness (if spot-checked)
✅ **Graph State**: 95%+ vault nodes now connected to concepts
✅ **Reversibility**: All changes in git, fully reversible
✅ **Cost**: $0-2 vs $8-12 (96-99% savings)

---

## Why This Is "Compound Engineering"

This plan **compounds** value by:

1. **Leveraging existing infrastructure**: Ollama MCP, SurrealDB, vault structure all ready
2. **Reusing proven patterns**: Lessons v2 heuristic methodology transferred directly
3. **Chaining cost-free operations**: Each phase builds on prior ($0 → $0 → $0 → $0-2)
4. **Enabling future optimization**: Dense semantic graph enables Phase B optimizations (indexing, caching, inference)
5. **Creating operational knowledge**: Documented methodology reusable for future enrichment

**Compound Effect**: Maximum enrichment (31 nodes linked) with minimum token spend, enabling future scaling.

---

## Next Steps

1. **Review**: Detailed plan in `decisions/2026-02-10-compound-node-linking-plan.md`
2. **Approve**: Confirm token-efficiency approach & timeline
3. **Execute**: Run phases 1-4 with task tracking
4. **Verify**: Spot-check results in Obsidian
5. **Commit**: Document execution in git + daily summary
6. **Archive**: Update vault stats (target: 95%+ linked)

---

## Key Files

- **Detailed Plan**: `decisions/2026-02-10-compound-node-linking-plan.md` (4 phases + risk analysis)
- **Execution Framework**: `/tmp/node_linking_execution_framework.py` (simulation + reporting)
- **Application Tool**: `/tmp/apply_links.py` (batch wiki-link applicator)
- **Vault State**: 144 total notes, 113 linked (78%), 31 unlinked

---

## Rationale: Why "Compound" Over "Simple"?

**Simple Approach**: Use Claude to link each node one-at-a-time → $8-12, 1-2 hours, generic extraction
**Compound Approach**: Orchestrate Ollama (free) + proven heuristics (zero calibration) + batch operations → $0-2, 2.5 hours, domain-specific linking

The compound approach **trades linear time for exponential value**: Same time investment yields 96% cost savings + proven methodology + reusable framework.

