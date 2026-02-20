---
title: "Phase 3: 3D Graph Plugin - Adversarial Review & Token-Efficient Plan"
date: 2026-02-10
status: proposed
tags: [decision, 12d-graph, adversarial-review, token-efficiency]

decision_reasoning:
  chosen_option: "Conduct adversarial review before Phase 3 execution"
  rationale: "Kyutai's early risk identification saved massive rework; same pattern applies to 3D graph"
  confidence_score: 0.88
  alternatives_rejected:
    - "Skip review, proceed directly (high rework risk)"
    - "Proceed without token-efficiency planning (expensive)"
  reasoning_chain:
    - "Kyutai's adversarial review caught subtle architectural issues"
    - "Realized same pattern prevents 3D graph rework"
    - "Applied token-efficiency framework proactively"
    - "Secured expert review before execution"

metrics:
  estimated_cost: 0.0
  estimated_time_hours: 4.0
  actual_cost: 0.0
  actual_time_hours: 2.0
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated:
    - "lessons/lesson-adversarial-review-pattern"
---

# Phase 3: 3D Graph Plugin - Adversarial Review

## Context

We have 8/12 dimensions computed and stored in SurrealDB. Original plan: build custom Obsidian plugin inspired by InfraNodus. **But should we?**

## Adversarial Questions (Critical Review)

### Question 1: Do we even need a custom plugin?

**Challenge**: We already have visualization options that work TODAY:
- **Obsidian's native 3D graph** (already installed, zero code)
- **New 3D Graph plugin** (recommended in `decisions/3d-graph-plugin-selection.md`, 5-min install)
- **SurrealDB queries** (can export dimensional data to JSON for any viz tool)

**Why build from scratch?** What specific gap do existing solutions NOT solve?

**Answer needed**: Define 3 specific features that ONLY a custom plugin can deliver.

---

### Question 2: Can we validate value BEFORE building?

**Challenge**: 30-35K token estimate = $0.10-0.12 + 3-4 weeks dev time

**Kyutai lesson learned**: We spent 61K tokens on infrastructure before proving value.

**Alternative**: Can we validate the 8 dimensions provide visual insight using:
1. Export dimensional data to JSON
2. Use existing 3D graph plugin (5 min install)
3. Manually configure visual mappings
4. If valuable → THEN build custom automation

**Cost**: 500 tokens (export script) vs 35K tokens (full plugin)
**Time**: 30 minutes vs 3-4 weeks

---

### Question 3: Template reuse - what exists?

**We just built a complete Obsidian plugin** (Kyutai, 2,151 LOC TypeScript).

**Challenge**: Can we copy 80% of Kyutai's structure?
- Settings infrastructure: ✅ (40+ settings, 8 sections)
- MCP client pattern: ✅ (already talks to SurrealDB)
- Modal windows: ✅ (3 production-ready modals)
- Ribbon commands: ✅ (4 commands)
- TypeScript build pipeline: ✅ (CI/CD ready)

**Estimated reuse**: 70-80% of Kyutai codebase applicable
**Token cost**: 8-12K (vs 35K from scratch) = 65% savings

---

### Question 4: What's the simplest thing that could work?

**Challenge**: Do we need 3D rendering at all?

**Dimensions we computed**:
1. Connectivity (scalar 0-1)
2. Cross-domain bridging (count)
3. Completion status (%)
4. Temporal (date)
5. Recency (timestamp)
6. Semantic similarity (768-dim → top-5 list)
7. Conceptual depth (scalar 0-1)
8. Gap analysis (boolean flags)

**Question**: Can we get 80% of value with **dimensional frontmatter** + native Obsidian search/filters?

Example:
```yaml
# In paper frontmatter
dimensions:
  connectivity: 0.82
  cross_domain: 5
  completion: 100%
  conceptual_depth: 0.73  # theory-leaning
  bridging: true
```

Then use Dataview queries:
```dataview
TABLE dimensions.connectivity, dimensions.conceptual_depth
FROM "papers"
WHERE dimensions.bridging = true
SORT dimensions.connectivity DESC
```

**Cost**: 2K tokens (enrichment script) vs 35K (plugin)

---

## Proposed Token-Efficient Plan

### Phase 3A: Validation (2K tokens, 1 hour)

**Goal**: Prove 8 dimensions provide visual insight BEFORE building plugin.

1. **Export dimensional data** (`/tmp/export_dimensions_for_viz.py`)
   - Query SurrealDB for all 84 papers + 8 dimensions
   - Export to `.obsidian/3d-graph-data.json`
   - 200 lines of Python

2. **Install New 3D Graph plugin** (5 minutes)
   - Already researched, actively maintained
   - Test with our dimensional data

3. **Manual configuration experiment** (30 minutes)
   - Try to map dimensions to visual properties
   - Document what works / what doesn't
   - If plugin doesn't support our use case → proceed to Phase 3B

4. **Decision gate**:
   - ✅ If existing plugin works → STOP (save 33K tokens)
   - ❌ If gaps identified → Proceed to Phase 3B with clear requirements

**Deliverable**: `experiments/3d-graph-validation.md` with findings

---

### Phase 3B: Template Reuse (8-12K tokens, 4-6 hours)

**Only execute if Phase 3A identifies gaps that REQUIRE custom plugin.**

1. **Copy Kyutai plugin structure** (1K tokens)
   - `/home/mike-anderson/dev/cohezion/kyutai-mcp-server/obsidian-plugin/` → new project
   - Remove TTS/STT code, keep settings/MCP/modal infrastructure
   - 70% code reuse

2. **Implement ONE 3D view** (5-7K tokens)
   - Single ribbon command: "Open 12D Graph"
   - Three.js integration (copy from InfraNodus patterns)
   - SurrealDB query via MCP (already working)
   - Basic node rendering (no fancy features)

3. **Test with 10 papers** (2K tokens)
   - Validate visual mappings work
   - User feedback loop
   - If valuable → Phase 3C (scale)

4. **Decision gate**:
   - ✅ Value proven → Phase 3C (add features)
   - ❌ Not valuable → STOP (saved 20K tokens)

---

### Phase 3C: Feature Scale (15-20K tokens, 2-3 weeks)

**Only execute if Phase 3B proves value.**

- Add 4 view presets
- Add interactive controls
- Add filtering/search
- Polish UI/UX
- Write tests + docs

---

## Adversarial Review Results

### Risks Identified

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Building before validating** | CRITICAL | Phase 3A gates Phase 3B |
| **Not reusing Kyutai template** | HIGH | 70% code reuse = 20K token savings |
| **Over-engineering** | HIGH | Phase 3B builds ONE feature only |
| **Existing solutions ignored** | MEDIUM | Phase 3A tests New 3D Graph first |
| **Token waste** | MEDIUM | 3-phase gated approach (2K → 12K → 35K) |

### Critical Questions to Answer

Before ANY coding:

1. **What can existing plugins NOT do?** (specific gaps)
2. **What's the minimum viable 3D visualization?** (1 view, no fancy features)
3. **Can we reuse Kyutai's 2,151 LOC TypeScript?** (70%+ overlap?)

---

## Recommended Decision

### Option A: Validate First (RECOMMENDED)

**Phase 3A only** (2K tokens, 1 hour):
1. Export dimensional data
2. Test with New 3D Graph plugin
3. Document gaps
4. Gate Phase 3B on validated gaps

**Rationale**:
- 98% token savings if existing solution works
- Honors "Implementation First" lesson
- Minimal risk, maximum learning

---

### Option B: Template Reuse (IF Phase 3A fails)

**Phase 3A → 3B** (10-14K total):
1. Validate gaps exist
2. Copy Kyutai structure
3. Build ONE 3D view
4. Test with 10 papers
5. Gate Phase 3C on value

**Rationale**:
- 60% token savings vs building from scratch
- Proven Obsidian plugin patterns
- Incremental validation

---

### Option C: Original Plan (NOT RECOMMENDED)

**Phase 3 full build** (35K tokens, 3-4 weeks):
- Build complete custom plugin
- All features upfront
- No validation gate

**Why NOT**:
- Violates "Implementation First" lesson
- No validation before investment
- Ignores template reuse opportunity
- Kyutai postmortem warned against this

---

## Next Steps

1. **User decision**: Which option? (Recommend Option A)
2. **If Option A**: Write `/tmp/export_dimensions_for_viz.py` (500 tokens)
3. **If gaps found**: Pivot to Option B with clear requirements
4. **If no gaps**: STOP, use existing plugin (33K tokens saved)

---

## Success Criteria

### Phase 3A Success
- [ ] Dimensional data exported to JSON
- [ ] New 3D Graph plugin tested with our data
- [ ] 3+ specific gaps documented OR solution validated
- [ ] Token spend < 2K
- [ ] Time < 2 hours

### Phase 3B Success (if needed)
- [ ] Kyutai template copied (70%+ reuse)
- [ ] ONE 3D view renders 10 papers
- [ ] Visual mappings functional
- [ ] User validates value
- [ ] Token spend < 12K
- [ ] Time < 6 hours

---

## References

- [[Implementation First, Infrastructure Later]] - Critical lesson from Kyutai
- [[Kyutai Project]] - 2,151 LOC TypeScript plugin (template source)
- [[3D Graph Plugin Selection]] - New 3D Graph research
- [[12D Graph Implementation]] - Original plan (needs updating)

[[token-efficiency]], [[compound-engineering]], [[12d-graph]], [[adversarial-review]]

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-adversarial-multi-agent-review-protocol]]
