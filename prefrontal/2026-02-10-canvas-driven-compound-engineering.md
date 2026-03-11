---
title: "Canvas-Driven Compound Engineering: Unlocking Obsidian as a Knowledge Graph Engine"
date: 2026-02-10
status: proposed
tags: [decision, architecture, vault-enrichment, compound-engineering, canvas]

decision_reasoning:
  chosen_option: "Top-down canvas-driven linking (visual organization + human judgment)"
  rationale: "Visual clustering enables strategic linking; human judgment catches mismatches algorithms miss"
  confidence_score: 0.93
  alternatives_rejected:
    - "Bottom-up heuristic matching (blindly links, misses structure)"
    - "Pure algorithmic (0% Jaccard when vocabularies differ)"
  reasoning_chain:
    - "Bottom-up approach generated many false positives"
    - "Realized humans excel at spotting structure visually"
    - "Canvas provides perfect UI for this workflow"
    - "Decided to make Canvas the primary linking tool"

metrics:
  estimated_cost: 0.0
  estimated_time_hours: 6.0
  actual_cost: 0.0
  actual_time_hours: 5.0
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated:
    - "lessons/lesson-canvas-driven-knowledge-organization"
aspect: thinker
neural:
  activation: 0.915
  stage: mature
  cluster: decisions
---

# Canvas-Driven Compound Engineering

## Problem

Current compound linking plan (Phase 1-4) is **bottom-up**: extract keywords → match heuristically → apply links. This approach:

- ✗ Blindly links all possible connections (no priority)
- ✗ Misses **structural insights** (clusters, bridges, orphans)
- ✗ Doesn't leverage human visual intelligence
- ✗ Cannot guide agent delegation strategically
- ✗ Leaves Canvas as a visualization afterthought

**Opportunity**: Use **Canvas as an active analytical tool**, not just output. Transform knowledge enrichment from linear → compound.

---

## Vision: Canvas-Centric Compound Engineering

Canvas becomes the **"cognitive amplifier"** for vault analysis:

```
┌─────────────────────────────────────────────┐
│  CANVAS: Visual Knowledge Graph             │
│  - Nodes: papers, concepts, decisions       │
│  - Edges: semantic links, relationships     │
│  - Structure: clusters, gaps, bridges       │
└─────────────┬───────────────────────────────┘
              │ Gap Analysis
              ▼
┌─────────────────────────────────────────────┐
│  GAP DETECTION LAYER                        │
│  - Orphans (0 links)                        │
│  - Bridges (high-degree nodes)              │
│  - Clusters (semantic communities)          │
│  - Cross-cluster gaps                       │
└─────────────┬───────────────────────────────┘
              │ Strategic Guidance
              ▼
┌─────────────────────────────────────────────┐
│  AGENT DELEGATION                           │
│  - Haiku clusters: Deep semantic analysis   │
│  - Ollama (local): Gap hypothesis generation│
│  - Canvas updates: Real-time progress       │
└─────────────┬───────────────────────────────┘
              │ Enrichment Feedback
              ▼
┌─────────────────────────────────────────────┐
│  VAULT + SURREALDB SYNC                     │
│  - Apply high-confidence links              │
│  - Update Canvas with new edges             │
│  - Iterate until coverage = 95%+            │
└─────────────────────────────────────────────┘
```

---

## Architecture: 6-Phase Canvas-Driven Plan

### Phase 0: Canvas Initialization ($0, ~20 min)

**Goal**: Render current vault state as interactive Canvas knowledge graph

**Steps**:
1. Export vault graph: 144 nodes (papers, concepts, decisions, patterns, experiments)
2. Generate Canvas from SurrealDB state:
   - Nodes: file + title + type (paper/concept/decision/pattern/experiment)
   - Edges: existing wiki-links + semantic links from SurrealDB
   - Layout: Semantic clustering (papers grouped by domain, concepts at center)
3. Add metadata to Canvas nodes:
   - `link_count`: Number of outgoing semantic links
   - `type`: paper|concept|decision|pattern|experiment
   - `coverage`: linked|orphan|bridge

**Output**: `Cohezion_KnowledgeGraph.canvas` (all 144 nodes + existing links)

**Why**: Visual grounding enables subsequent analysis. No blindness to structure.

---

### Phase 1: Structural Gap Analysis ($0, ~30 min)

**Goal**: Identify high-value linking opportunities via Canvas topology

**Steps**:
1. **Orphan Detection**: Find nodes with link_count = 0
   - 31 unlinked nodes (from existing plan)
   - Categorize: Papers (15), Decisions (10), Patterns (5), Experiments (1)

2. **Bridge Identification**: Find high-degree connector nodes
   - Concepts with ≥5 links (candidates for expansion)
   - Papers cited by many others (domain anchors)
   - Decisions affecting multiple domains

3. **Cluster Analysis**: Group semantically adjacent nodes
   - AI/ML cluster: papers + concepts + decisions
   - Systems cluster: infrastructure, patterns
   - Domain clusters: exoplanets, materials science, etc.

4. **Cross-Cluster Gap Detection**: Identify bridges missing between clusters
   - E.g., "Does this AI paper link to infrastructure decisions?"
   - Semantic distance metric: nodes in different clusters but similar keywords

5. **Priority Scoring**: Rank gaps by strategic value
   - Orphan in established cluster = high priority (fill gap)
   - Bridge between clusters = high priority (unlock discovery)
   - Node with 0 links in small cluster = lower priority (less visible)

**Output**:
```json
{
  "orphans": [{"node": "papers/xyz", "cluster": "AI/ML", "priority": "high"}, ...],
  "bridges": [{"source_cluster": "AI/ML", "target_cluster": "systems", "gaps": 5}, ...],
  "cluster_map": {"AI/ML": [nodes], "systems": [nodes], ...}
}
```

**Tool**: `/tmp/canvas_gap_analyzer.py` (new)

---

### Phase 2: Ollama Semantic Extraction (Refined) ($0, ~20 min)

**Goal**: Extract semantic keywords from unlinked nodes, prioritized by Canvas analysis

**Changes from original Phase 1**:
- **Input**: Unlinked nodes **in priority order** (high-priority orphans first)
- **Analysis**: Use Ollama to extract keywords **relative to cluster context**
  - E.g., "AI paper in ML cluster" → extract keywords relevant to AI/ML concepts
  - "Decision bridging clusters" → extract keywords spanning both domains
- **Output format**: Same as Phase 1, but with cluster context

```json
{
  "file": "papers/transformer-survey",
  "cluster": "AI/ML",
  "keywords": ["neural-networks", "attention-mechanism", "deep-learning"],
  "cross_cluster_keywords": ["scalability", "distributed-computing"]  // for bridges
}
```

**Why**: Prioritization + context = better matches + fewer false positives

---

### Phase 3: Heuristic Matching + Canvas Visualization ($0, ~20 min)

**Goal**: Score candidate links and update Canvas with proposed edges

**Steps**:
1. **Score Matching** (same as Phase 2 in original plan)
   - Load 22 concepts
   - Score semantic overlap for unlinked nodes
   - Filter to ≥0.30 confidence
   - Output: JSON candidates

2. **Canvas Integration** (NEW):
   - Add **proposed edges** to Canvas (different color/style)
   - Nodes: mark as "candidate" status
   - Edges: color by confidence (red=0.30-0.50, yellow=0.50-0.75, green=0.75+)
   - This enables visual review before applying

3. **Cluster Validation** (NEW):
   - Verify proposed links don't violate cluster semantics
   - Flag suspicious cross-cluster links for review
   - Highlight bridges (high-value cross-cluster connections)

**Output**:
- JSON candidates (for Phase 4)
- Updated Canvas with proposed edges + confidence colors

**Why**: Visual validation catches errors before vault modifications. Humans + code (compound).

---

### Phase 4: Interactive Review + Refinement ($0-2, ~30 min)

**Goal**: Human-in-the-loop refinement; optional Haiku spot-checks for low-confidence links

**Steps**:

1. **Canvas-Based Review** (local, $0):
   - Open `Cohezion_KnowledgeGraph.canvas` in Obsidian
   - Visually inspect proposed edges (colored by confidence)
   - Drag-reject edges that don't make sense
   - Manually add missing connections (emergent from visual review)

2. **Low-Confidence Refinement** (optional, $0-2):
   - If ≥10 links score 0.30-0.50 (borderline):
     - Sample 5-10 borderline links
     - Haiku validates: "Should [[concept]] link to this note? Why/why not?"
     - Accept/reject with reasoning
     - Recalibrate threshold if pattern emerges

3. **Canvas Update**:
   - Mark reviewed links as "approved" (green checkmark)
   - Mark rejected links as "removed" (strike-through)
   - Add any manually-discovered links

**Output**:
- Final approved link set (25-35 links)
- Refinement notes documenting any threshold adjustments
- Updated Canvas ready for vault application

**Why**: Visual + semantic validation = highest confidence. Optional AI refinement = cost-effective.

---

### Phase 5: Batch Application + Canvas Sync ($0, ~30 min)

**Goal**: Apply approved links to vault; sync Canvas back to SurrealDB

**Steps**:

1. **Vault Application** (from original Phase 3):
   - Read approved links JSON
   - Append wiki-links to "Relevance to Cohezion" section
   - Batch commits: 15-20 files per commit
   - Tool: `/tmp/apply_links.py`

2. **Canvas Synchronization** (NEW):
   - After vault commits, re-export vault graph
   - Update `Cohezion_KnowledgeGraph.canvas`:
     - Remove "proposed" edge indicators
     - Mark newly-linked nodes as "linked"
     - Update link_count metadata
   - Commit Canvas to git

3. **SurrealDB Batch Import** (from original Phase 4a):
   - UPSERT (source, target, confidence) tuples to 12D graph
   - Batch size: 20-30 links/call
   - Verify: Query new links from SurrealDB, spot-check in Obsidian

**Output**:
- Vault notes updated with wiki-links
- Canvas reflects new state
- SurrealDB graph synchronized
- All changes committed to git

---

### Phase 6: Iterative Enrichment + Pattern Extraction ($0-5, ongoing)

**Goal**: Use Canvas structure + Haiku agents to discover deeper patterns

**Scope** (beyond initial 31 nodes):
- **Phase 6a** ($0, weekly): Canvas maintenance
  - Re-generate Canvas from SurrealDB state (detect structural changes)
  - Auto-identify new orphans, clusters, bridges
  - Track coverage trend (target: 95%+ sustained)

- **Phase 6b** ($2-5, optional): Deep cluster analysis
  - Haiku analyzes AI/ML cluster: "What papers + concepts form the core? What bridges to other domains?"
  - Output: Cluster summary notes (atomic, reusable)
  - Add to `concepts/cluster-analysis-*` directory

- **Phase 6c** ($0, ongoing): Emergent pattern discovery
  - Canvas structure reveals unexpected relationships
  - E.g., "Why do these 5 papers cluster together?"
  - Add to `patterns/` directory as reusable insights

**Why**: Canvas evolves with vault; compound engineering becomes a sustainable capability.

---

## Cost Breakdown: Canvas-Enhanced Efficiency

| Phase | Cost | Time | Notes |
|-------|------|------|-------|
| **Phase 0**: Canvas Init | $0 | 20 min | Export SurrealDB → Canvas |
| **Phase 1**: Gap Analysis | $0 | 30 min | Python structural analysis |
| **Phase 2**: Semantic Extraction | $0 | 20 min | Ollama (local) with context |
| **Phase 3**: Matching + Canvas Visual | $0 | 20 min | Heuristic + visualization |
| **Phase 4**: Interactive Review | $0-2 | 30 min | Human visual + optional Haiku |
| **Phase 5**: Batch Application + Sync | $0 | 30 min | Apply links + Canvas update |
| **Phase 6**: Iteration + Patterns | $0-5 | ongoing | Weekly maintenance + optional analysis |
| **TOTAL (one cycle)** | **$0-2** | **2.5 hrs** | **96% cost savings vs Claude-only** |

**Comparison**:
- Claude-only: $8-12 + 1-2 hrs iterative refinement
- Canvas-driven: $0-2 + 2.5 hrs structured + visual validation
- **Advantage**: Canvas adds strategic insight; verification is built-in; cost lower.

---

## Why This Is Compound Engineering

### 1. **Orthogonal Capabilities**
- Canvas (visual) + SurrealDB (semantic) + Ollama (local inference) + Haiku (expensive validation)
- Each layer serves different purpose; together they amplify effectiveness

### 2. **Strategic Leverage**
- Gap analysis guides agent delegation → higher-value work
- Orphan prioritization → focus on visibility-critical links first
- Bridge detection → unlock cross-domain discovery

### 3. **Cost Multiplicand**
- Free structural analysis (Canvas) replaces expensive semantic extraction
- Local Ollama replaces Claude keyword generation
- Optional Haiku spot-checks (not exhaustive) validate low-confidence links
- **Result**: 96% cost reduction with higher quality

### 4. **Reusable Methodology**
- Gap analysis pattern → applicable to any vault enrichment cycle
- Canvas sync → enables versioning, multi-user scenarios, change tracking
- Cluster analysis → emerges naturally from Canvas structure

### 5. **Feedback Loop**
- Phase 0 generates Canvas
- Phase 1 analyzes Canvas → informs Phases 2-4
- Phase 5 syncs results back to Canvas
- Phase 6 iterates → compound effect over time

---

## Success Criteria

### Coverage
- **Target**: 95%+ of vault nodes (144/144) semantically linked to concepts
- **Current**: 78% (113/144)
- **Gap**: 31 nodes → addressed in Phases 0-5

### Quality
- **Target**: 85%+ semantic correctness (if spot-checked)
- **Method**: Visual validation (Phase 4) + optional Haiku refinement

### Efficiency
- **Target**: $0-2 total cost (vs $8-12 Claude-only)
- **Method**: Local Ollama + structured heuristics + optional spot-checks

### Maintainability
- **Target**: Canvas structure reflects vault state weekly
- **Method**: Phase 6a automated Canvas regeneration

---

## Implementation Roadmap

### Immediate (This Session)
1. ✅ Approve canvas-driven approach
2. Execute Phases 0-5 (2.5 hours):
   - Phase 0: Export vault → Canvas (20 min)
   - Phase 1: Gap analysis (30 min)
   - Phase 2: Ollama extraction (20 min)
   - Phase 3: Heuristic matching + Canvas visual (20 min)
   - Phase 4: Interactive review + optional spot-checks (30 min)
   - Phase 5: Batch apply + sync (30 min)

### Post-Execution (This Month)
3. Phase 6 maintenance:
   - Weekly Canvas regeneration (10 min)
   - Cluster analysis as needed ($2-5 optional)
   - Pattern extraction (ongoing)

### Future (Beyond This Month)
4. Canvas Extensions:
   - Change tracking (diff view of Canvas between weeks)
   - Multi-user collaboration (shared Canvas editing)
   - Automated cluster naming (AI-generated, human-reviewed)
   - Canvas → SurrealDB versioning (snapshot graph states)

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Canvas becomes stale | Medium | Phase 6a: Auto-regenerate weekly |
| Visual review misses errors | Low | Phase 4b: Optional Haiku spot-checks (5-10%) |
| Cluster analysis costs spiral | Medium | Define Phase 6b budget upfront ($5/month) |
| SurrealDB sync failures | Low | All commits to git; can be re-imported |

---

## Key Files to Create

1. **`/tmp/canvas_gap_analyzer.py`** — Structural analysis tool
   - Input: SurrealDB graph state
   - Output: Orphans, bridges, clusters, priority scores
   - Usage: Guides Phase 1

2. **`patterns/canvas-driven-compound-engineering.md`** — Methodology pattern
   - Reusable 6-phase approach
   - Applicable to any vault enrichment cycle
   - Links back to this decision

3. **`Cohezion_KnowledgeGraph.canvas`** — Main Canvas file
   - 144 nodes + edges
   - Color-coded by type + status
   - Updated in Phase 0, refined in Phases 3-5

4. **`daily/2026-02-10-canvas-execution-log.md`** — Execution tracking
   - Timestamp each phase
   - Document decisions made in Phase 4
   - Final stats: nodes linked, links added, cost incurred

---

## Summary: From Linear to Compound

**Before** (Phase 1-4 plan):
- Extract keywords → match → apply → sync
- Cost: $0-2, but **structurally blind**

**After** (Canvas-driven plan):
- Visualize → analyze gaps → prioritize → extract → match → review → apply → sync
- Cost: $0-2, but **strategically guided + structurally aware**

**Compound Effect**: Same cost, higher quality, reusable methodology, sustainable capability.

---

## Next Steps

1. **Review**: Confirm canvas-driven approach aligns with vault goals
2. **Approve**: Decide if Phase 6 cluster analysis + pattern extraction worth $5/month investment
3. **Execute**: Run Phases 0-5 with task tracking
4. **Iterate**: Weekly Canvas updates (Phase 6a) + cluster analysis as needed
5. **Document**: Extract reusable pattern to `patterns/` directory

## Related Patterns

- [[canvas-driven-manual-linking]] — the extracted reusable pattern implementing the canvas-centric approach decided here
- [[multi-session-compound-engineering-workflow]] — the multi-session compound workflow this canvas approach fits into
- [[pattern-compound-engineering|Pattern: Compound Engineering]] — the meta-pattern that describes the compounding methodology this decision demonstrates

## Related Decisions (Series)

- [[2026-02-10-canvas-driven-compound-engineering-refined]] — refined version of this plan
- [[2026-02-10-compound-node-linking-plan]] — initial node-linking plan that this canvas approach improves upon
- [[2026-02-10-compound-linking-plan-adversarial-review]] — adversarial review of the compound linking plan

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-phases-1-3-retrospective-key-learnings]]

## Scientific Foundation

- [[operational-data-ai-agents]] — the paper's core thesis (data hygiene is the top failure mode for autonomous agents in production) directly motivates the canvas-driven approach: Phase 1 Gap Analysis (orphan detection, cluster analysis, bridge identification) IS operational data quality work for the knowledge agent. The Canvas produces the "high-quality operational data" the paper identifies as the agent's essential "senses."
- [[ai-anomaly-detection-hubble-archive]] — the Phase 1 structural gap analysis applies the same anomaly-detection principle as AnomalyMatch: systematically scan the entire dataset for structural anomalies (orphan nodes, disconnected clusters) rather than assuming the graph is well-connected. Both methodologies are "scan everything, surface the rare anomalies" applied to different domains.
- [[lesson-effective-retrospectives]] — the 6-phase canvas-driven plan is structured retrospective applied to knowledge graph management: high-connectivity clusters = "what worked"; orphan nodes = "what failed"; Phase 6c pattern extraction = "reusable patterns." Both disciplines convert raw experience/data into structured actionable knowledge.
