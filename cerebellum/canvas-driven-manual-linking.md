---
title: "Canvas-Driven Manual Linking Pattern"
date: 2026-02-10
status: active
tags: [pattern, vault-enrichment, compound-engineering, token-efficiency]
aspect: thinker
neural:
  activation: 0.96
  stage: mature
  synapse_in: 14
  synapse_out: 18
---

# Canvas-Driven Manual Linking Pattern

## Problem

Vault has orphan notes (0 semantic links) that should connect to concepts but don't. Algorithmic matching fails when vocabularies differ (e.g., operational decisions vs abstract concepts). Need high-quality linking at low cost.

## Solution

Use Canvas visualization + human judgment + optional AI validation to link orphans to concepts.

**4-phase process**: Analyze gaps → Manual review → Apply + sync → Validate (optional)

**Cost**: $0-2 | **Time**: 1.5-2 hours | **Quality**: 90-100%

---

## When to Use

✅ **Use this pattern when**:
- Linking specialized notes (decisions, papers, experiments) to concepts
- Vocabulary varies between note types (operational vs abstract)
- Quality matters (90%+ correctness required)
- Human availability exists (1-2 hours)
- Vault size: 100-500 nodes

⚠️ **Don't use when**:
- Vault >1000 nodes (bottleneck on human time)
- Real-time linking needed
- Low-cost only (Phase 4 validation adds $2)

---

## Process

### Phase 1: Structural Analysis (15 min, $0)

**Goal**: Identify high-value orphans

**Steps**:
1. Run gap analyzer on vault
2. Identify orphans (0 links) + bridges (5+ links) + clusters
3. Prioritize: orphans in established clusters first

**Command**:
```bash
python3 /tmp/canvas_gap_analyzer.py > gap_analysis.json
```

**Output**: Ranked list of orphans by priority

**Decision**: Link orphans in clusters with 5+ nodes (high visibility); consider skipping niche clusters

---

### Phase 2: Manual Review (30-60 min, $0)

**Goal**: Human assigns 1-3 concept links per orphan

**Prerequisites**:
- Canvas open in Obsidian (visual context)
- List of all available concepts
- Gap analysis orphan list (from Phase 1)

**Steps**:
1. For each high-priority orphan:
   - Read title + first 200 chars of summary
   - Scan concept list (usually 2-3 candidates obvious)
   - Verify on Canvas: does this link make sense visually?
   - Record: orphan → [concept_ids]
2. Mark uncertain links for Phase 4 validation

**Time**: 2-3 min per orphan

**Example Decision**:
```
Input: decisions/2026-02-09-ollama-mcp-server
Summary: "Ollama MCP server implementation details..."
Candidates: [[mcp-infrastructure-architecture]], [[context-management]]
Decision: Both relevant → assign both
Output: ["concepts/mcp-infrastructure-architecture", "concepts/context-management"]
```

**Output Format**:
```json
{
  "decisions/xyz": ["concepts/abc", "concepts/def"],
  "papers/abc": ["concepts/xyz"],
  ...
}
```

---

### Phase 3: Batch Application (20 min, $0)

**Goal**: Apply links to vault + regenerate Canvas + commit

**Steps**:

1. **Save approved links** (from Phase 2):
```bash
cat > approved_links.json << 'EOF'
{
  "decisions/xyz": ["concepts/abc", "concepts/def"],
  ...
}
EOF
```

2. **Apply links**:
```bash
python3 /tmp/phase5_apply_links.py \
  --input approved_links.json \
  --vault /home/mike-anderson/vaults/cohezion-vault
```

3. **Regenerate Canvas**:
```bash
python3 /tmp/export_vault_to_canvas.py
```

4. **Commit**:
```bash
git add decisions/ concepts/ Cohezion_KnowledgeGraph.canvas
git commit -m "pattern: canvas-driven linking - add N links via manual review"
```

**Output**:
- Vault notes with wiki-links in "Relevance to Cohezion" section
- Canvas updated (edge count increases, orphans decrease)
- Git history preserved

---

### Phase 4: Optional Validation (15 min, $0-2)

**Goal**: Spot-check quality (if desired)

**Trigger**: Run only if Phase 2 produced ≥10 uncertain links

**Steps**:
1. Sample 5-10 uncertain links
2. Use Haiku to validate each:
   ```
   Note: [title + first 200 chars]
   Proposed link: [[concept]]
   Question: Should this note link to this concept? Why/why not?
   ```
3. Accept/reject with reasoning
4. If >20% rejection rate: recalibrate Phase 2 threshold

**Cost**: $0.05-0.10 per link
- 10 links: $0.50-1.00
- 20 links: $1.00-2.00

**Output**: Quality report + recalibration notes

---

## Example: Decision Linking (From 2026-02-10)

### Input
10 orphan decisions, 22 available concepts

### Phase 1 Output
```
High-priority orphans:
- decisions/3d-graph-plugin-selection (cluster: infrastructure)
- decisions/2026-02-09-ollama-mcp-server (cluster: infrastructure)
- decisions/2026-02-09-12d-graph-surrealdb-integration (cluster: infrastructure)
...
```

### Phase 2 Output (Manual)
```json
{
  "decisions/3d-graph-plugin-selection": [
    "concepts/mcp-infrastructure-architecture",
    "concepts/compound-engineering"
  ],
  "decisions/2026-02-09-ollama-mcp-server": [
    "concepts/mcp-infrastructure-architecture",
    "concepts/context-management"
  ],
  ...
}
```

### Phase 3 Result
- 10 decisions linked
- 16 total links applied
- Canvas orphans: 26 → 11 (58% reduction)
- Coverage: 82% → 93% (+11pp)

### Quality (Phase 4, Spot-Check)
- 16 links reviewed
- 16/16 correct (100%)

---

## File Dependencies

### Required
- `/tmp/canvas_gap_analyzer.py` — Gap analysis
- `/tmp/export_vault_to_canvas.py` — Canvas export
- `/tmp/phase5_apply_links.py` — Link applicator
- `Cohezion_KnowledgeGraph.canvas` — Visual reference

### Generated (per cycle)
- `gap_analysis.json` — Orphan list (Phase 1)
- `approved_links.json` — Manual decisions (Phase 2)
- Updated vault notes + Canvas (Phase 3)

### Optional
- Haiku validation results (Phase 4)

---

## Metrics

### Per Enrichment Cycle

| Metric | How to Measure |
|--------|-----------------|
| Orphan Reduction | Count orphans before Phase 1 vs after Phase 3 |
| Link Quality | Phase 4 spot-check: % correct |
| Cost Efficiency | Track API calls (Phase 4 only) |
| Execution Time | Phase timer stamps |
| Coverage Growth | (linked_before → linked_after) / total |

### Expected Results (Based on 2026-02-10)
- Orphan reduction: 40-60%
- Link quality: 90-100%
- Cost: $0-2
- Time: 1.5-2 hours
- Coverage gain: +10-15pp

---

## Troubleshooting

### Problem: Phase 1 finds 0 orphans
**Cause**: All notes already linked
**Solution**: Pattern not needed; continue normal work

### Problem: Phase 2 produces <1 concept per orphan average
**Cause**: Orphans are truly niche (no linking partners in vault)
**Solution**: Accept orphan status; they're low-priority

### Problem: Phase 2 takes >3 min per orphan
**Cause**: Concept list too large (>50) or vocabulary unclear
**Solution**: Reduce concept list (only core concepts), clarify vocabulary in concept titles

### Problem: Phase 4 validation finds >30% errors
**Cause**: Phase 2 threshold too lenient
**Solution**: Re-run Phase 2 with stricter manual criteria (only confident links)

---

## Scalability

### Vault Size vs. Execution Time

| Size | Phase 1 | Phase 2 | Phase 3 | Total |
|------|---------|---------|---------|-------|
| 50 orphans | 5 min | 1.5h | 10 min | ~1.75h |
| 100 orphans | 10 min | 3h | 20 min | ~3.5h |
| 200 orphans | 15 min | 6h | 30 min | ~6.75h |
| 500+ orphans | 20 min | 15h+ | 60 min | **Bottleneck** |

**Recommendation**: For >200 orphans, build embedding-based Phase 2 automation (high-confidence auto-links, human reviews borderline only)

---

## Related Decisions & Patterns

- `decisions/2026-02-10-canvas-driven-compound-engineering-refined.md` — Refinement post-execution
- `daily/2026-02-10-canvas-execution-log.md` — Implementation example
- `patterns/lessons-graph-integration.md` — Similar pattern for lessons enrichment
- `concepts/compound-engineering.md` — Conceptual foundation

---

## Next Steps

### Use This Pattern When
1. Vault has orphan notes (check Phase 1 gap analyzer)
2. Semantic linking improves discoverability
3. Quality matters (domain-specific vocabularies)
4. Human availability exists (1-2 hours)

### Build Upon This Pattern
- Embedding-based Phase 2 automation (for large vaults)
- Weekly Canvas maintenance (Phase 1 on schedule)
- Cluster-driven discovery (analyze Canvas structure)


## Decisions That Produced This Pattern

- [[2026-02-10-canvas-driven-compound-engineering]] — the original decision to use canvas-driven top-down linking
- [[2026-02-10-canvas-driven-compound-engineering-refined]] — the refined 4-phase plan this pattern extracts
- [[2026-02-10-compound-linking-plan-adversarial-review]] — adversarial review that endorsed the canvas approach over bottom-up matching
- [[2026-02-10-compound-node-linking-plan]] — the bottom-up plan superseded by this pattern
- [[2026-02-10-operational-forensics-compound-engineering]] — applied this pattern for forensic analysis linking
- [[2026-02-10-token-efficient-compound-engineering-roadmap]] — the roadmap that includes this pattern as a core vault enrichment method

## Related Concepts

- [[token-efficiency-patterns]] — this pattern is a concrete token-efficient vault enrichment technique; the concept note catalogs efficiency patterns like this one
- [[concept-caching]] — caching enrichment results prevents redundant re-linking of already-connected notes
- [[dna-origami-2d-semiconductor-patterning]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-14-phases-1-3-retrospective-key-learnings]]
- [[2026-02-10-kyutai-mcp-obsidian-plugin-plan]]
- [[2026-02-14-phase-6a-automated-reasoning-chain-inference-complete]]
- [[2026-02-14-wave-1-overnight-completion-report]]
- [[2026-02-14-compound-engineering-team-execution-retrospective]]
