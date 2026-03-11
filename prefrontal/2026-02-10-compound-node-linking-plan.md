---
title: Compound Node Linking Plan - Token-Efficient Link Discovery & Application
date: 2026-02-10
status: proposed
tags: [decision, architecture, infrastructure, vault-enrichment]

decision_reasoning:
  chosen_option: "Multi-phase linking plan combining algorithmic + manual methods"
  rationale: "Hybrid approach leverages algorithm speed + human accuracy for 31 unlinked nodes"
  confidence_score: 0.85
  alternatives_rejected:
    - "Pure algorithmic (high false positives)"
    - "Pure manual (doesn't scale)"
  reasoning_chain:
    - "Found 31 orphaned vault nodes"
    - "Realized pure algorithmic = many false positives"
    - "Designed hybrid: Ollama ranking + manual review"
    - "Planned 4-phase execution"

metrics:
  estimated_cost: 0.0
  estimated_time_hours: 2.5
  actual_cost: 0.0
  actual_time_hours: 2.0
  tokens_used: 400
  cost_per_lesson: 0.0
  lessons_generated:
    - "lessons/lesson-hybrid-linking-combines-strengths"
aspect: thinker
neural:
  activation: 0.682
  stage: mature
  cluster: decisions
---

## Executive Summary

**Problem**: 31 unlinked vault nodes (15 papers + 10 decisions + 5 patterns + 1 experiment) lack semantic connections to concepts, reducing discoverability and graph cohesion.

**Solution**: Token-efficient 4-phase plan using local Ollama MCP ($0 cost) + proven heuristic methodology + batch SurrealDB sync.

**Cost**: ~$0 (100% local Ollama) + optional ~$1-2 Haiku verification

**Timeline**: 2-3 hours execution + 30-60 min verification

---

## Current State (2026-02-10)

| Category | Total | Linked | Unlinked | Coverage |
|----------|-------|--------|----------|----------|
| **Papers** | 84 | 69 | **15** | 82% |
| **Decisions** | 17 | 7 | **10** | 41% |
| **Patterns** | 19 | 14 | **5** | 74% |
| **Experiments** | 2 | 1 | **1** | 50% |
| **Concepts** | 22 | 22 | 0 | 100% ✓ |
| **TOTAL** | **144** | **113** | **31** | **78%** |

**SurrealDB Graph**: 84 papers + 21 concepts + 148 link relationships

---

## Phase 1: Local Semantic Analysis ($0, ~30 min)

**Goal**: Extract semantic vectors from unlinked nodes using Ollama MCP (local, free)

### Approach
- **Tool**: Ollama `query()` MCP with `qwen2.5-coder:14b` (context-aware, semantic understanding)
- **Input**: Unlinked paper title + abstract + key findings
- **Output**: JSON array of semantic keywords/concepts from each node
- **Batch Size**: Process 8-10 nodes per agent turn to stay within token budgets

### Implementation
```python
# Pseudo-code for Phase 1
for batch in chunks(unlinked_nodes, 8):
    # Call Ollama MCP: query(task="extract_concepts", input=batch)
    # Output: [{"file": "paper-x.md", "concepts": ["concept-a", "concept-b"]}]
```

### Why Ollama?
- Local execution: ~0 API cost vs $0.015/1K tokens with Claude
- Fast inference: qwen2.5-coder handles semantic extraction efficiently
- Already configured in `~/.claude/mcp.json` with proven track record
- Parallel batching: 4-8 Haiku agents can run simultaneously

---

## Phase 2: Selective Heuristic Matching ($0, ~30 min)

**Goal**: Match unlinked nodes to concepts using proven v2 selective scoring

### Methodology (Validated from Lessons Integration v2)

1. **Extract Keywords**: Get semantic keywords from Phase 1
2. **Concept Inventory**: Load 22 concept note titles + summaries
3. **Semantic Scoring**:
   - Direct title match: 1.0 score
   - Keyword overlap (30%+ threshold): semantic match
   - Cross-domain resonance: 0.7-0.9 score
4. **Filter Noise**: Only apply links with score ≥ 0.3 (lessons v2 proved this threshold minimizes false positives)
5. **Deduplication**: Skip links already in SurrealDB (query `SELECT * FROM links WHERE source=$file`)

### Why This Approach?
- **Proven**: Lessons integration v2 achieved 85%+ accuracy with 30% threshold
- **Efficient**: Heuristic matching runs locally, no external API calls
- **Quality**: Selective scoring avoids the 80% over-broad linking seen in v1
- **Reversible**: Links can be verified and removed if incorrect

### Quality Guardrail
- Keep a "candidate links" JSON log during Phase 2
- Spot-check 5-10% with Haiku in Phase 4 verification

---

## Phase 3: Batch Application to Vault ($0, ~30 min)

**Goal**: Apply wiki-links to unlinked nodes with deduplication

### Implementation

```python
# For each unlinked node:
for node in unlinked_nodes:
    # Read node content
    content = read_note(node)

    # Get matched concepts from Phase 2
    matched_concepts = lookup_matches(node)

    # Check existing links
    existing = extract_wiki_links(content)

    # Calculate new links (avoid duplicates)
    new_links = [c for c in matched_concepts if c not in existing]

    # Append to "Relevance to Cohezion" section or create one
    if new_links:
        append_wiki_links(node, new_links)
        commit_to_vault(node)
```

### Tools
- **Script**: Extend `/tmp/apply_links.py` for decisions/patterns/experiments
- **Batch Size**: 15-20 files per commit (atomic, reversible)
- **Idempotency**: Skip notes that already have links for those concepts
- **Verification**: After each batch, verify wiki-links resolve in Obsidian

---

## Phase 4: SurrealDB Sync + Verification ($0-2, ~30 min)

**Goal**: Update 12D graph + spot-check quality

### Step 4a: Batch SurrealDB Sync ($0)
```sql
-- For each new link discovered
INSERT INTO links (source, target, confidence)
VALUES (${paper_file}, ${concept_name}, 0.85)
ON DUPLICATE KEY UPDATE confidence = 0.85
```

- **Tool**: `surrealdb_import_concepts()` MCP (already implemented)
- **Idempotency**: UPSERT by (source, target) pair
- **Batch Size**: 20-30 links per call

### Step 4b: Quality Verification ($1-2 optional)

**Spot-check procedure** (if quality concerns arise):
- Sample 10% of newly-linked nodes
- Use Haiku to validate: "Does [[concept]] link make semantic sense for this paper/decision?"
- Rejection rate <5%: Ship all links ✓
- Rejection rate 5-15%: Re-tune Phase 2 threshold
- Rejection rate >15%: Revert Phase 3, debug Phase 1

### Success Metrics
- **Coverage**: 100% of 31 unlinked nodes processed
- **Quality**: 85%+ semantic correctness (validated spot-check)
- **Graph Cohesion**: All 144 notes connected to concepts
- **SurrealDB**: New link relationships imported
- **Reversibility**: All changes in git commits with full revert capability

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Ollama semantic errors | Low - heuristic filters noise | Phase 4 spot-check catches errors |
| Over-linking decisions | Medium - pollutes concept graph | Phase 2 threshold tuning (0.3 min score) |
| SurrealDB sync failures | Low - can re-run idempotently | UPSERT handles duplicates |
| Token budget overrun | Low - 100% local execution | Ollama MCP substitutes for Claude |
| Obsidian wiki-link parsing | Low - standard format tested | `/tmp/apply_links.py` proven in Phase 1 |

---

## Token Budget Breakdown

| Phase | Cost | Notes |
|-------|------|-------|
| Phase 1: Ollama Analysis | **$0** | Local qwen2.5-coder queries |
| Phase 2: Heuristic Matching | **$0** | Python + local concept inventory |
| Phase 3: Batch Application | **$0** | Local Python file operations |
| Phase 4a: SurrealDB Sync | **$0** | MCP local execution |
| Phase 4b: Spot-Check (optional) | **$1-2** | ~1000 tokens Haiku × 5-10 samples |
| **TOTAL** | **$0-2** | 98-99% cost reduction vs Claude-only approach |

**Comparison**: Claude-only semantic linking for 31 nodes would cost ~$8-12 (Sonnet) or ~$3-4 (Haiku). This plan achieves **96-99% cost savings** via local Ollama.

---

## Execution Timeline

**Sequential Phases**:
- Phase 1: 30 min (parallel Ollama batches)
- Phase 2: 30 min (keyword extraction + heuristic scoring)
- Phase 3: 30 min (batch wiki-link application)
- Phase 4a: 10 min (SurrealDB sync)
- Phase 4b: 30 min (optional spot-check)

**Total: ~2.5 hours hands-on + 30 min verification**

**Optimal Execution**:
1. Run all phases sequentially (dependencies: 1→2→3→4)
2. Create task list with 4 sequential tasks
3. Output results to `/tmp/phase-*-results.json` for tracking

---

## Success Criteria

✅ All 31 unlinked nodes receive ≥1 concept wiki-link
✅ 85%+ semantic correctness (spot-check)
✅ 0 broken wiki-links in Obsidian
✅ SurrealDB updated with new relationships
✅ Git commits document all changes (reversible)
✅ Concept notes updated with new backlinks (bidirectional)

---

## Next Steps

1. **Approval**: Review plan for token efficiency + feasibility
2. **Execution**: Run Phases 1-4 with TaskList tracking
3. **Verification**: Spot-check results in Obsidian
4. **Commit**: Document execution results in daily note
5. **Archive**: Update vault stats (target: 95%+ linked nodes)

---

## Appendix: Why Compound Engineering?

This plan is **compound** because it:
- **Leverages existing infrastructure**: Ollama MCP, SurrealDB, vault structure
- **Reuses proven patterns**: Lessons v2 heuristic methodology + v2 selective scoring
- **Chains cost-free operations**: Local analysis → heuristic matching → batch application
- **Defers external costs**: Spot-check verification optional, only if quality questionable
- **Enables compound value**: Each link improves graph density, concept discoverability, semantic search

**Result**: Maximum vault enrichment with minimum token spend ($0-2 vs $8-12 for equivalent Claude-only approach).

## Related Patterns

- [[canvas-driven-manual-linking]] — the canvas-driven pattern that replaced the bottom-up approach in this plan

## Related Decisions (Series)

- [[2026-02-10-compound-linking-plan-adversarial-review]] — adversarial review that found issues with this plan
- [[2026-02-10-canvas-driven-compound-engineering]] — alternative approach that superseded this plan

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-adversarial-multi-agent-review-protocol]]
