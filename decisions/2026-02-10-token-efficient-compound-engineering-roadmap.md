---
title: "Token-Efficient Compound Engineering: One-Month Roadmap"
date: 2026-02-10
status: active
tags: [decision, roadmap, compound-engineering, token-efficiency, vault-enrichment]

decision_reasoning:
  chosen_option: "Systematize token-efficient compound engineering across 4 phases + vault"
  rationale: "Proven patterns from Kyutai (33% ahead) + manual linking (93% accurate) = scalable framework"
  confidence_score: 0.93
  alternatives_rejected:
    - "Ad-hoc efficiency (inconsistent, hard to repeat)"
    - "100% automation (too many false positives)"
  reasoning_chain:
    - "Kyutai project delivered 364 min vs 540 min estimate"
    - "Manual canvas linking achieved 93% accuracy vs 0% algorithmic"
    - "Realized patterns were repeatable and systematizable"
    - "Created 4-phase roadmap for vault enrichment"

metrics:
  estimated_cost: 0.0
  estimated_time_hours: 16.0  # Month of work
  actual_cost: 0.0
  actual_time_hours: 12.0
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated:
    - "lessons/lesson-token-efficient-roadmap-execution"
---

# Token-Efficient Compound Engineering Roadmap (2026-02-10 → 2026-03-10)

## Vision

Use canvas-driven manual linking pattern to systematically enrich vault while maintaining:
- **Zero API cost** (local tools + optional spot-checks only)
- **High quality** (90%+ semantic correctness)
- **Sustainable pace** (2-4 hours/week)
- **Reusable processes** (pattern validated, tools production-ready)

---

## Phase A: Complete Decision Enrichment (Week 1)

### Objective
Finish decision node linking; handle remaining 8 orphans + validate learnings

### Scope
- 8 remaining orphan decisions (identified in Phase 1 gap analysis)
- 10 already-linked decisions (optional: enrich with additional concepts)

### Execution
```bash
# Phase 1: Gap Analysis
python3 /tmp/canvas_gap_analyzer.py | grep "decisions/" | head -15

# Phase 2: Manual Review (10-15 min)
# Open Canvas + concepts/ directory
# For each orphan: assess if linking valuable (ignore if true niche)

# Phase 3: Apply + Sync (10 min)
python3 /tmp/phase5_apply_links.py --input approved_links.json
python3 /tmp/export_vault_to_canvas.py
git commit -m "enrichment-cycle-1: complete decision linking"
```

### Success Criteria
- ✅ All viable orphan decisions linked (skip niche ones with <2 relevant concepts)
- ✅ Coverage target: 95%+ for decisions
- ✅ Quality: ≥90% (optional Phase 4 spot-checks if desired)
- ✅ Cost: $0

### Effort
- Time: 30-45 min
- Cost: $0
- Expected: 5-8 additional links

### Output
- Updated decisions/ directory
- Regenerated Cohezion_KnowledgeGraph.canvas
- Git commit(s) with full traceability

---

## Phase B: Paper Enrichment (Week 2-3)

### Objective
Link orphan papers to concepts; validate pattern scales to larger corpus

### Context
- 84 papers total in vault
- Current: ~79% with concept wiki-links (66/84)
- Gap: ~18 orphan papers (0 links)
- Opportunity: Enrich thin papers (1-2 existing links) with additional concepts

### Strategy
1. **Phase 1**: Run gap analyzer on papers/ directory
2. **Phase 2**: Prioritize by cluster visibility
   - High-value: Papers in established domains (AI/ML, exoplanets, etc.)
   - Low-value: Papers in niche domains (1-2 papers each)
3. **Phase 3-4**: Manual linking (2-3 hours estimated)

### Execution
```bash
# Phase 1: Analyze gaps
python3 /tmp/canvas_gap_analyzer.py > paper_gaps.json

# Phase 2: Prepare for manual review
# Review priority list, focus on domain clusters

# Phase 3: Batch apply
# Apply links, regenerate Canvas

# Phase 4: Optional validation (if uncertainty >30%)
# Sample 5-10 papers for Haiku validation (~$0.50-1.00)
```

### Success Criteria
- ✅ 90%+ of papers linked to concepts (reduce from 79% to 90%+)
- ✅ High-value domains fully connected (AI/ML, exoplanets, materials, systems)
- ✅ Quality: ≥90% (validated via Phase 4 spot-checks)
- ✅ Cost: ≤$1 (optional validation only)

### Effort
- Time: 2-3 hours (split across 2 weeks)
- Cost: $0-1
- Expected: 15-25 additional links

### Output
- Enriched papers/ directory
- Updated Canvas (edge count +15-25)
- Optional: Paper enrichment patterns document

---

## Phase C: Automation & Sustainability (Week 3-4)

### Objective
Build recurring processes to keep Canvas fresh; enable Phase B scaling

### Components

#### C1: Weekly Canvas Maintenance Script
**Goal**: Auto-regenerate Canvas weekly; detect new orphans; track trends

```bash
#!/bin/bash
# Run weekly (Monday morning)
python3 /tmp/export_vault_to_canvas.py
python3 /tmp/canvas_gap_analyzer.py > /tmp/weekly_gap_analysis.json

# Create weekly report
cat > weekly_report.md << EOF
# Canvas Maintenance Report ($(date +%Y-%m-%d))

## Orphan Trend
- Week 1: 26 orphans
- Week 2: 11 orphans (-15)
- This week: $(jq '.stats.total_orphans' /tmp/weekly_gap_analysis.json)

## Coverage
- Target: 95%+
- Current: $(jq '.stats.linked_coverage' /tmp/weekly_gap_analysis.json)

## Action Items
- Review any new orphans
- Check for cluster changes
EOF

# Commit if changes detected
git add Cohezion_KnowledgeGraph.canvas weekly_report.md
git commit -m "maintenance: Weekly Canvas regeneration"
```

**Effort**: 10 min/week (once scripted, 2 min/week)
**Cost**: $0
**Value**: Continuous monitoring + trend tracking

#### C2: Linking Session Templates
**Goal**: Standardized process for each enrichment cycle

Template format:
```markdown
# Enrichment Cycle: [Name] ([Date])

## Phase 1: Gap Analysis
Orphans: X
Bridges: Y
Clusters: Z

## Phase 2: Manual Review
- [ ] Review high-priority orphans
- [ ] Assign 1-3 concepts per orphan
- [ ] Document uncertain links

## Phase 3: Batch Application
- [ ] Apply via script
- [ ] Regenerate Canvas
- [ ] Commit to git

## Phase 4: Validation (Optional)
- [ ] Run Haiku spot-checks if uncertainty >30%
- [ ] Document quality findings

## Results
- Links added: N
- Cost: $X
- Quality: Y%
```

**Effort**: 30 min (create template)
**Cost**: $0
**Value**: Reproducibility + learning capture

---

## Phase D: Pattern Scaling & Documentation (Week 4)

### Objective
Document learnings; prepare pattern for community sharing; identify scaling options

### D1: Lessons Learned Document
**What worked**:
- Canvas visualization essential for Phase 2 accuracy
- Manual review scalable to ~500 nodes
- 4-phase approach optimal (vs 6-phase original)

**What failed**:
- Algorithmic keyword matching (0% recall when vocabularies differ)
- Ollama for keyword extraction (60% noise)
- Trying to "compound" tools without clear amplification

**What's next**:
- Embedding-based Phase 2 automation (for >200 orphans)
- Cluster-driven discovery (why do nodes cluster?)
- Multi-source enrichment (external papers, Wikipedia)

**Effort**: 2 hours
**Output**: `decisions/2026-02-10-compound-engineering-lessons-learned.md`

### D2: Scaling Strategy

#### If Vault Grows to 200+ Nodes
**Problem**: Manual Phase 2 becomes bottleneck (>3 hours for 50+ orphans)

**Solution**: Embedding-based Phase 2 automation
- Use Ollama nomic-embed-text for semantic embeddings (768-dim, free)
- Compare paper embeddings to concept embeddings
- Auto-link high-confidence matches (>0.75 threshold)
- Human review only borderline cases (0.60-0.75)
- Haiku validates final batch

**Cost**: $0-2 (optional validation only)
**Time**: 1-1.5 hours (down from 3 hours)
**Quality**: 90%+

**Implementation**: 4-6 hours development (embedding model + matching + UI)

#### If Vault Grows to 500+ Nodes
**Problem**: Even with embedding automation, volume high

**Solution**: Cluster-driven enrichment
- Analyze Canvas structure (clusters of papers, concepts, decisions)
- Use Haiku to describe each cluster semantic meaning
- Generate cluster-specific concepts
- Link cluster nodes to new concepts automatically
- Cost: $2-5 per cluster analysis

**Or**: Delegate to specialized teams (papers team, concepts team, etc.)

### D3: Pattern Refinement
- Document edge cases (what types of notes resist linking?)
- Identify anti-patterns (over-linking, spurious links)
- Create troubleshooting guide
- Publish pattern as community contribution

**Effort**: 3-4 hours
**Output**: Refined `patterns/canvas-driven-manual-linking.md` + community docs

---

## One-Month Metrics

### Vault Coverage by Week

| Metric | Current | Week 1 | Week 2-3 | Week 4 | Target |
|--------|---------|--------|----------|--------|--------|
| **Decisions Linked** | 41% (7/17) | 88% (15/17) | 88% | 88% | 95%+ |
| **Papers Linked** | 79% (66/84) | 79% | 90%+ | 90%+ | 95%+ |
| **Experiments Linked** | 50% (1/2) | 50% | 50% | 100% | 100% |
| **Overall Coverage** | 82% | 86% | 90%+ | 95%+ | 95%+ |
| **Orphans** | 26 | 8 | 5 | <5 | <5 |

### Cost Tracking

| Phase | Budget | Actual | Notes |
|-------|--------|--------|-------|
| **A: Decisions** | $0 | $0 | Manual review only |
| **B: Papers** | $1 | $0-1 | Optional validation |
| **C: Automation** | $0 | $0 | Local scripting |
| **D: Documentation** | $0 | $0 | Analysis + writing |
| **TOTAL** | **$1** | **$0-1** | 98% savings vs Claude-only |

### Token Efficiency

| Cycle | Tokens | Cost | Quality | Time |
|-------|--------|------|---------|------|
| **Decisions (Phase A)** | 0 | $0 | 100% | 30-45 min |
| **Papers (Phase B)** | 500-1000 | $0-1 | 90-100% | 2-3h |
| **Total (1 month)** | **500-1000** | **$0-1** | **90-100%** | **3-4h** |

**Comparison**: Claude-only would cost $50-75 + 2-3 hours for same work

---

## Weekly Execution Plan

### Week 1 (Feb 10-16)
- [ ] Link remaining orphan decisions (Phase A)
- [ ] Create Canvas maintenance script
- [ ] Commit enrichments

**Time**: 1-1.5 hours
**Cost**: $0
**Outcome**: Decisions 100% linked, Canvas automated

### Week 2-3 (Feb 17-Mar 2)
- [ ] Run Phase 1 gap analysis on papers
- [ ] Manual Phase 2 review (split across 2 weeks)
- [ ] Phase 3 batch application
- [ ] Optional Phase 4 validation if needed

**Time**: 2-3 hours total
**Cost**: $0-1
**Outcome**: Papers 90%+ linked, new pattern learnings

### Week 4 (Mar 3-9)
- [ ] Create lessons learned document
- [ ] Refine canvas-driven-manual-linking pattern
- [ ] Document scaling strategy
- [ ] Plan Phase B decisions

**Time**: 2-3 hours
**Cost**: $0
**Outcome**: Documented patterns, scaling roadmap

---

## Decision Points

### DP1: Continue Paper Enrichment vs Skip?
**Criteria**:
- If papers enrichment reveals new patterns → continue
- If diminishing returns (many niche papers) → skip Phase B, focus on Phase C/D
- Recommend: Continue (papers are substantial corpus, good test case)

### DP2: Build Embedding Automation Now vs Later?
**Criteria**:
- If vault reaches 200+ nodes in next month → build now (4-6 hours)
- If vault growth slows → defer (no bottleneck yet)
- Recommend: Defer until needed (YAGNI principle)

### DP3: Publish Pattern as Community Contribution?
**Criteria**:
- Quality ✅ (proven in execution)
- Reusability ✅ (documented + tools provided)
- Uniqueness ✅ (combines Canvas + manual + optional AI)
- Recommend: Yes (after Phase B validation)

---

## Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Paper enrichment reveals 0 new links | Low | Skip to Phase C/D; papers may be too niche |
| Haiku validation costs exceed budget | Low | Skip Phase 4 validation; manual review sufficient |
| Canvas becomes too large (500+ nodes) | Low | Phase D scaling strategy addresses this |
| Weekly automation breaks (git conflicts) | Low | Build safeguards; test before deploying |

---

## Success Criteria for Month

✅ **Coverage**: 82% → 95%+ (all note types)
✅ **Quality**: 90%+ semantic correctness (validated)
✅ **Cost**: ≤$1 total (98% savings vs Claude)
✅ **Time**: ≤5 hours total (compound engineering efficiency)
✅ **Automation**: Weekly Canvas maintenance script running
✅ **Documentation**: Pattern refined + scaling strategy defined
✅ **Reusability**: Tools + templates ready for next cycles

---

## Long-Term Implications

### Phase B Vision (Next Quarter)
1. **Embedding-based automation** (4-6h dev) → Phase 2 automation for large vaults
2. **Cluster-driven discovery** → AI analysis of why nodes cluster
3. **Multi-source enrichment** → Link to external papers, Wikipedia
4. **Bidirectional tracking** → Explicit concept→paper links
5. **Community sharing** → Pattern + tools as open-source contribution

### Compound Engineering Evolution
- **Current**: Manual linking + optional AI validation ($0-2, 90-100% quality)
- **Phase B (Q2)**: Hybrid (auto-link high-confidence + human-review borderline) ($0-5, 90%+ quality)
- **Phase C (Q3)**: Cluster-driven (AI identifies missing concepts) ($5-20/month, 95%+ quality)
- **Phase D (Q4)**: Multi-source (external + internal linking) ($20-50/month, 99% quality)

---

## Recommendation

🟢 **Proceed with all phases A-D this month**

**Rationale**:
1. Pattern proven (100% quality on decisions)
2. Tools production-ready
3. Effort manageable (3-5 hours/week, sustainable)
4. Token-efficient ($0-1 total vs $50-75 Claude)
5. Enables Phase B planning with confidence
6. Community contribution potential

**Next step**: Execute Phase A this week; report results before proceeding to Phase B

---

## Relevance to Cohezion

[[compound-engineering]]
[[context-management]]

## Related Patterns

- [[canvas-driven-manual-linking]] — the canvas-driven linking approach that implements the vault enrichment roadmap here
- [[pattern-compound-engineering]] — the compound engineering pattern whose token-efficient execution this roadmap describes

## Related Decisions (Series)

- [[2026-02-09-12d-graph-next-steps]] — the 12D strategy decision whose lessons informed this roadmap

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-phases-1-3-retrospective-key-learnings]]
