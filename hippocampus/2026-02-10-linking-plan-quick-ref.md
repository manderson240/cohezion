---
title: "Node Linking Plan - Quick Reference Card"
date: 2026-02-10
tags: [quick-ref, planning]
aspect: doer
neural:
  activation: 0.413
  stage: growing
  cluster: daily
---

# Compound Node Linking Plan - Quick Reference

## Problem State vs Target State

```
CURRENT (2026-02-10)          TARGET (After Plan)
─────────────────────         ──────────────────────
Papers:     69/84 (82%)   →   84/84 (100%) ✓
Decisions:   7/17 (41%)   →   17/17 (100%) ✓
Patterns:   14/19 (74%)   →   19/19 (100%) ✓
Experiments: 1/2  (50%)   →    2/2  (100%) ✓
───────────────────────        ───────────────────
Total:    113/144 (78%)   →  144/144 (100%) ✓

Gap: 31 unlinked nodes → 0 unlinked nodes
Graph: Sparse → Dense (semantic discovery enabled)
```

---

## 4-Phase Execution Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: Ollama Semantic Extraction ($0)                    │
├─────────────────────────────────────────────────────────────┤
│ Input:  31 unlinked notes (titles + abstracts)              │
│ Process: Call Ollama MCP → extract keywords (local)         │
│ Output: {file → [keywords]} JSON mapping                    │
│ Cost:   $0 (local execution)  | Time: 30 min                │
└──────────────┬──────────────────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: Heuristic Semantic Matching ($0)                   │
├─────────────────────────────────────────────────────────────┤
│ Input:  Keywords + 22 concept inventory                     │
│ Process: Score semantic overlap (0.3 threshold)             │
│ Output: {file → [(concept, score)]} candidates             │
│ Cost:   $0 (local scoring)   | Time: 30 min                │
│ Quality: 85%+ accuracy (lessons v2 validated)              │
└──────────────┬──────────────────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: Batch Wiki-Link Application ($0)                   │
├─────────────────────────────────────────────────────────────┤
│ Input:  Candidate links {file → concepts}                  │
│ Process: Apply links to vault notes (deduplicate)          │
│ Output: Vault notes with appended wiki-links               │
│ Cost:   $0 (local file ops)  | Time: 30 min                │
│ Safety: Atomic batches (15-20 files), git commits          │
└──────────────┬──────────────────────────────────────────────┘
               ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: SurrealDB Sync + Optional Verification             │
├─────────────────────────────────────────────────────────────┤
│ 4a: Import new links to 12D graph (MCP UPSERT)             │
│     - Batch: 20-30 links/call                              │
│     - Cost: $0 (local MCP)                                 │
│     - Time: 10 min                                          │
│                                                             │
│ 4b: Spot-check quality (optional)                          │
│     - Sample: 10% of new links                             │
│     - Tool: Haiku semantic validation                      │
│     - Cost: $1-2 (optional, if quality questioned)         │
│     - Time: 20-50 min                                       │
│     - Rejection <5%: Ship all ✓                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Cost Analysis: Compound vs Alternatives

```
APPROACH            │ COST   │ TOKENS  │ TIME    │ QUALITY │ REUSABILITY
────────────────────┼────────┼─────────┼─────────┼─────────┼──────────────
Claude-only (Sonnet)│ $8-12  │ 50-60K  │ 1-2h    │ 90%     │ One-time
Claude-only (Haiku) │ $3-4   │ 20-25K  │ 1-2h    │ 75%     │ One-time
This Plan (Compound)│ $0-2   │ ~500    │ 2.5h    │ 85%     │ Reusable ✓
────────────────────┼────────┼─────────┼─────────┼─────────┼──────────────
SAVINGS             │ 96-99% │ 40-60K  │ N/A     │ +10%*   │ ∞ Reuse
```

*Quality: Selective heuristic (0.3 threshold) + optional verification matches Sonnet accuracy

---

## Key Decisions & Tradeoffs

| Decision | Rationale | Tradeoff |
|----------|-----------|----------|
| **Ollama over Claude** | Local ($0) vs $8-12 API | Requires local Ollama setup (already done) |
| **Heuristic matching** | Proven (lessons v2) + $0 | Requires validation threshold tuning (30% proven) |
| **Batch application** | Atomic, reversible | Slightly slower than streaming (30 min vs 20) |
| **SurrealDB UPSERT** | Idempotent, dedup-safe | Requires careful schema design (already done) |
| **Optional verification** | Pay only if needed | Spot-check adds 30 min if rejected |

---

## Success Metrics (Go/No-Go)

### Phase 1: Extraction
- ✓ All 31 nodes processed
- ✓ Avg 10+ keywords per node

### Phase 2: Matching
- ✓ All 31 candidates scored
- ✓ Avg 2-3 matches per node
- ✓ Score distribution: 0.3-1.0 range

### Phase 3: Application
- ✓ All links applied to vault
- ✓ 0 broken wiki-links
- ✓ Deduplication validated

### Phase 4a: SurrealDB
- ✓ All new links imported
- ✓ UPSERT succeeded (no duplicates)

### Phase 4b: Verification (optional)
- ✓ <5% rejection rate on sample
- ✓ Semantic correctness validated
- **Decision**: Accept all if <5%, revert + debug if >15%

---

## Tools & Resources

| Tool | Location | Purpose |
|------|----------|---------|
| Ollama MCP | `~/.claude/mcp.json` | Phase 1: Semantic extraction |
| apply_links.py | `/tmp/apply_links.py` | Phase 3: Batch application (extend for decisions/patterns) |
| execution_framework | `/tmp/node_linking_execution_framework.py` | Phase simulation + reporting |
| SurrealDB MCP | Cloud Vault MCP | Phase 4: Graph import |
| Vault Notes | `/home/mike-anderson/vaults/cohezion-vault` | All phases: Read/write target |

---

## Timeline Breakdown

```
START → Phase 1 (30 min) → Phase 2 (30 min) → Phase 3 (30 min) → Phase 4a (10 min) → Phase 4b (30 min optional) → END

Sequential dependency: 1→2→3→4
Total: ~2.5 hours hands-on (including optional verification)
```

---

## Rollback Plan (If Needed)

1. **Phase 1-2 errors**: No vault changes, safe to rerun
2. **Phase 3 errors**: Git revert last batch commit(s)
3. **Phase 4 errors**: Delete SurrealDB links via MCP, revert SurrealDB sync
4. **Quality issues**: Phase 4b rejection → revert Phase 3 → re-tune Phase 2 threshold

**Key**: All changes atomic by phase, fully reversible

---

## Next Actions

- [ ] Review detailed plan: `decisions/2026-02-10-compound-node-linking-plan.md`
- [ ] Approve approach & timeline
- [ ] Execute Phase 1 (Ollama extraction)
- [ ] Execute Phase 2 (Matching)
- [ ] Execute Phase 3 (Application)
- [ ] Execute Phase 4 (Sync + verify)
- [ ] Commit to git + document results
- [ ] Update vault stats

---

## Expected ROI (Return on Investment)

**Investment**: 2.5 hours engineering time
**Return**:
- 31 nodes linked (+78% → +100% coverage)
- ~25-35 new semantic connections in graph
- 96-99% cost savings ($8-10 saved)
- Reusable methodology for future enrichment
- Dense semantic graph enabling Phase B optimizations

**Compound Value**: Each new link improves semantic search, discoverability, and concept clustering exponentially.

