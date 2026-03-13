---
title: 12D Graph System - Refined Implementation Plan (Specialist-Driven)
date: 2026-02-09
status: proposed
tags: [decision, 12d-graph, infranodus, ai-features, specialist-team, inferred]
decision_reasoning:
  reasoning_chain:
  - sequence: 1
    content: 'Context: 12D Graph System - Refined Implementation Plan (Specialist-Driven)'
    type: research
    confidence: 0.65
    assumption: Problem was clearly identified
  - sequence: 2
    content: Explored multiple implementation approaches and trade-offs
    type: pattern
    confidence: 0.6
    assumption: Multiple options were considered
  - sequence: 3
    content: Evaluated options against project constraints and criteria
    type: research
    confidence: 0.58
    assumption: Options were systematically evaluated
  reasoning_type: research
  confidence_score: 0.6
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 19
  synapse_out: 26
---

# 12D Graph System - Refined Implementation Plan

**Status**: Refined after deep analysis of InfraNodus and COHEZION requirements
**Date**: 2026-02-09
**Phase**: Design & Specialist Assembly

---

## Executive Summary

Building a **12-dimensional graph visualization system** that surpasses [InfraNodus](https://infranodus.com/obsidian-plugin) by incorporating:
- 12D analysis vs InfraNodus' 3D (4x richer dimensional space)
- Agent journey tracking (context-aware AI navigation)
- Real-time vault ↔ SurrealDB sync (live updates)
- Compound engineering workflows (multi-agent collaboration)
- Enhanced AI features (gap analysis, betweenness centrality, Claude-powered insights and planning executed with local llms)

---

## InfraNodus Feature Analysis

### Core Features to Abstract & Enhance

From [InfraNodus documentation](https://infranodus.com/about/how-it-works) and [network analysis](https://infranodus.com/docs/network-analysis):

#### 1. **Betweenness Centrality**
- **InfraNodus**: Ranks nodes by betweenness centrality (BC) - measures how often a node bridges different clusters
- **COHEZION Enhancement**: Apply BC across 12 dimensions, weight by agent journey affinity
- **Use Case**: Identify "bridge concepts" that connect disparate research domains (e.g., concepts linking quantum computing + AI agents)

#### 2. **Topical Clustering**
- **InfraNodus**: Uses Louvain community detection algorithm to identify clusters
- **COHEZION Enhancement**: Multi-dimensional clustering using domain tags + semantic similarity + temporal proximity
- **Use Case**: Auto-group papers by research themes, even across traditional domain boundaries

#### 3. **Force Atlas Layout**
- **InfraNodus**: 2D/3D Force-Atlas layout aligns connected nodes, pushes hubs apart
- **COHEZION Enhancement**: 12D Force-Atlas with projection to 3D viewable space, configurable axis mapping
- **Use Case**: Dynamic re-layout as user explores different dimensional perspectives

#### 4. **Claude Gap Analysis**
- **InfraNodus**: AI identifies content gaps - concepts that *should* be linked but aren't
- **COHEZION Enhancement**: Opus analyzes 12D topology to suggest missing papers, unexplored research directions -> implemented by local llms
- **Use Case**: "You have 5 papers on quantum computing and 7 on AI agents - explore quantum AI agent architectures?"

#### 5. **AI Research Questions**
- **InfraNodus**: GPT-4 generates research questions bridging topical clusters
- **COHEZION Enhancement**: Context-aware questions based on current agent task + vault gaps + dimensional position
- **Use Case**: During code review, suggest "How does MCP architecture compare to multi-agent systems?" based on active concepts

#### 6. **Dynamic Knowledge Graphs**
- **InfraNodus**: Real-time graph updates as notes change
- **COHEZION Enhancement**: Bidirectional sync (vault files ↔ SurrealDB), file watcher, live 3D view updates
- **Use Case**: Add wiki-link to paper → graph updates immediately, new edge appears

---

## 12-Dimensional Framework

### The 12 Dimensions

| Dimension | Purpose | InfraNodus Equivalent | COHEZION Innovation |
|-----------|---------|----------------------|---------------------|
| **1-3. Spatial (X, Y, Z)** | 3D positioning | Force-Atlas layout | Configurable projection from 12D space |
| **4. Temporal** | Time-based evolution | None | Track knowledge evolution over time |
| **5. Domain Clustering** | Research domain affinity | Topical clusters | Multi-domain bridging detection |
| **6. Connectivity Density** | Number of connections | Betweenness centrality | Weighted by connection strength |
| **7. Conceptual Depth** | Abstraction level | None | Theory ↔ Application spectrum |
| **8. Citation Impact** | Reference frequency | None | Track which papers cite this one |
| **9. Recency/Relevance** | Time-decay weighting | None | Prioritize recent + frequently accessed |
| **10. Cross-Domain Bridging** | Multi-domain papers | Gap analysis | Identify interdisciplinary opportunities |
| **11. User Interest** | Interaction tracking | None | Heat map of user attention |
| **12. Agent Journey Affinity** | Context relevance | None | **COHEZION SIGNATURE FEATURE** |

---

## Specialist-Driven Implementation

### Specialist Team Structure

#### **1. SurrealDB Specialist** ✅ COMPLETE
- **Responsibility**: Schema design, query optimization, UPSERT patterns
- **Status**: Successfully fixed sync layer, all 84 papers importing
- **Deliverable**: Production-ready bidirectional sync

#### **2. 12D Math/Geometry Specialist** (TO SPAWN)
- **Responsibility**: Dimensional projection algorithms, Force-Atlas in 12D, PCA/t-SNE for dimension reduction
- **Key Tasks**:
  - Design 12D → 3D projection engine (configurable axis mapping)
  - Implement Force-Atlas in higher dimensions
  - Create dimension reduction algorithms for auto-layout
  - Mathematical validation of dimensional independence

#### **3. Obsidian Plugin Specialist** (TO SPAWN)
- **Responsibility**: Plugin architecture, TypeScript/Three.js integration, Obsidian API usage
- **Key Tasks**:
  - Plugin scaffolding (manifest.json, main.ts, settings)
  - SurrealDB WebSocket client integration
  - Three.js scene setup + rendering pipeline
  - Obsidian command palette + UI integration

#### **4. UI/UX Specialist** (TO SPAWN)
- **Responsibility**: Interaction design, dimensional controls, visual encoding
- **Key Tasks**:
  - Design dimensional control panel (axis mapping, filters, sliders)
  - Node/edge visual encoding (color, size, opacity for dimensional values)
  - Search/filter UI (concept search, tag filters, date ranges)
  - Agent Journey Mode UI (highlight relevant nodes)
  - Accessibility (keyboard navigation, screen reader support)

#### **5. AI Features Specialist** (TO SPAWN)
- **Responsibility**: Hybrid AI architecture (Claude orchestration + local LLM execution), gap analysis, betweenness centrality, research question generation
- **Key Tasks**:
  - **Claude Opus**: Design gap analysis strategy, plan dimensional analysis workflows
  - **Claude Sonnet**: Coordinate feature implementation, review local LLM outputs
  - **Claude Haiku**: Quick concept similarity checks, batch paper categorization
  - **Local LLMs**: Execute gap analysis at scale (100+ papers), generate embeddings
  - Implement betweenness centrality calculation (NetworkX)
  - Semantic similarity pipeline: sentence-transformers → local inference
  - Agent Journey Affinity scoring: Claude designs algorithm, local LLM scores papers in real-time

#### **6. Google Sheets Specialist** (TO SPAWN)
- **Responsibility**: SheetsBridge integration, automated tracking, research workflow sync
- **Key Tasks**:
  - Sync 12D graph metrics to Google Sheets (for external analysis)
  - Track paper enrichment status (Summary, Key Findings, dimensional values)
  - Automated workflows: Sheet row → Vault note → SurrealDB → 3D Graph
  - Dashboard: Vault coverage metrics, dimensional distribution charts

#### **7. Model Wrangler Specialist** (TO SPAWN) 🌟 DAILY DRIVER
- **Responsibility**: Local LLM lifecycle management - **continuous monitoring** in fast-moving ecosystem
- **Key Tasks**:
  - **DAILY 9am**: Run automated digest (Hugging Face, Ollama, Reddit, Discord)
  - **Within 4 hours**: Benchmark critical releases (major model families)
  - **Within 24 hours**: Benchmark promising new models
  - **Same-day**: Emergency swaps for critical bugs/security issues
  - **Aggressive swapping**: If new model ≥5% better, swap within 24 hours (not quarterly)
  - **Continuous fine-tuning**: Weekly dataset refreshes, monthly full retraining
  - **Real-time monitoring**: SurrealDB metrics dashboard, Slack alerts on performance drops
  - **Rapid rollback**: < 5 minute rollback procedures if swap fails
  - **Daily reports**: Morning digest + evening production metrics summary
  - **Volatile ecosystem awareness**: Track emerging model architectures (Mamba, RWKV, etc.)

---

## COHEZION-Optimized Features

### 1. Agent Journey Mode 🌟 SIGNATURE FEATURE

**Concept**: Dynamically filter/highlight graph based on current agent context

**Use Case**:
```
Agent working on: "Implement MCP server for Obsidian vault"
Active concepts: [[mcp-model-context-protocol]], [[agentic-ai]], [[api-design]]

Graph View transforms:
- Highlights papers with high Agent Journey Affinity (dim_12)
- Fades irrelevant nodes (astrophysics, biology)
- Suggests: "Papers you might need: scaling-agent-systems.md, multi-agent-systems concept"
```

**Implementation**:
- Track agent's active concepts (from task description + recent messages)
- Compute cosine similarity between agent context embeddings + paper embeddings
- Apply real-time filtering to 3D view
- GPT-4 generates contextual suggestions

### 2. Compound Engineering Workflows

**Concept**: Multi-agent collaboration tracking in graph

**Use Case**:
```
Team of 4 agents working on 12D graph:
- Agent A (SurrealDB specialist) → modifies schema
- Agent B (UI specialist) → designs controls
- Agent C (Math specialist) → projection algorithms
- Agent D (Plugin specialist) → integrates all

Graph shows:
- Shared concepts highlighted (collaboration points)
- Agent-specific clusters (individual focus areas)
- Handoff edges (where agent B depends on agent A's work)
```

**Implementation**:
- Add `agent_journey` table tracking active agents + their focus concepts
- Create `agent_collaboration` edges showing dependencies
- Visualize as color-coded node clusters in graph
- Timeline slider showing agent activity over time

### 3. Session State Integration

**Concept**: Vault memory bridge + 12D graph

**Use Case**:
```
Pull session context from vault → Update graph:
- Last commit: "Added 12D projection math" → Highlight mathematical papers
- Active tasks: ["Implement UI controls"] → Suggest UI/UX papers
- Test status: "24/24 passing" → Show green glow on tested components
```

**Implementation**:
- Read `daily/` session notes via VaultMemoryBridge
- Parse current phase, active tasks, branch name
- Update `dim_agent_journey_affinity` in real-time
- Reflect in graph view (node colors, sizes, clusters)

### 4. Gap Analysis & Research Suggestions

**Concept**: Beyond InfraNodus - multi-dimensional gap detection

**InfraNodus**: Finds missing links between topical clusters
**COHEZION**: Finds gaps across ALL 12 dimensions

**Example Gaps**:
- **Temporal**: "You have 20 papers from 2025, only 2 from 2024 - missing historical context?"
- **Cross-Domain**: "5 quantum papers, 5 AI papers, 0 bridging them - explore quantum AI?"
- **Conceptual Depth**: "All papers are theory-heavy - add implementation examples?"
- **Citation Impact**: "Paper X cited by 8 others but not linked in graph - create [[concept]] for it?"

**Implementation (Hybrid AI Architecture)**:
1. **Claude Opus Planning Phase**:
   - Design gap detection strategy: "Analyze 12D topology, what patterns indicate gaps?"
   - Create dimensional analysis prompts for local LLMs
   - Define success criteria for gap identification

2. **Local LLM Execution Phase**:
   - Process all 84 papers through local embedding model (sentence-transformers)
   - Compute dimensional distributions, detect outliers
   - Identify sparse regions, disconnected clusters
   - Generate candidate gaps (fast, local inference)

3. **Claude Sonnet Review Phase**:
   - Review local LLM outputs: "Are these gaps meaningful?"
   - Filter false positives, prioritize high-value suggestions
   - Format results for UI display

4. **Claude Haiku Quick Checks**:
   - Real-time gap checking as user adds papers
   - "Does this new paper fill existing gaps?" (fast, cheap)

**Cost Optimization**: Opus designs once, local LLMs execute repeatedly, Haiku handles real-time checks

### 5. Live Dimensional Recomputation

**Concept**: Dimensions update automatically as vault changes

**Example**:
```
User edits paper: adds 3 new wiki-links → [[quantum-computing]], [[ai-agents]], [[mcp]]
→ File watcher detects change
→ SurrealDB sync updates paper record
→ Dimensional engine recomputes:
  - dim_connectivity: 5 → 8 (3 new links)
  - dim_cross_domain: 0.2 → 0.7 (now bridges 3 domains)
  - dim_recency: 0.5 → 1.0 (just edited)
→ 3D graph live-updates node position + size
→ User sees change immediately
```

**Implementation**:
- Watchdog file monitor in SurrealDBSync (✅ already implemented)
- Trigger dimensional recomputation on file changes
- WebSocket push to plugin: "paper X dimensions updated"
- Three.js smooth transition animation (node moves to new position)

---

## Implementation Phases (Specialist-Driven)

### **Phase 1: Foundation (Week 1-2)** - Parallel Work

**SurrealDB Specialist** ✅ DONE:
- Schema finalized, sync layer working
- 84 papers + 21 concepts imported

**12D Math Specialist**:
- Design projection matrix (12D → 3D)
- Prototype Force-Atlas in 12D
- Create dimension reduction algorithm (PCA/t-SNE)

**Obsidian Plugin Specialist**:
- Plugin scaffolding + TypeScript setup
- Basic Three.js scene (empty graph)
- SurrealDB WebSocket client stub

**Deliverable**: Math prototype + empty plugin shell

---

### **Phase 2: Core Graph (Week 2-3)** - Integration

**12D Math Specialist**:
- Implement production projection engine
- Export as library for plugin to import

**Obsidian Plugin Specialist**:
- Integrate projection engine
- Render nodes (papers as spheres, concepts as cubes)
- Render edges (links, citations as lines)
- Basic camera controls (orbit, zoom, pan)

**AI Features Specialist**:
- Compute betweenness centrality for all nodes
- Store in SurrealDB `dim_connectivity` field
- Test on 84 papers

**Deliverable**: Working 3D graph with nodes/edges, basic dimensional projection

---

### **Phase 3: Dimensional Controls (Week 3-4)** - UI Layer

**UI/UX Specialist**:
- Design control panel mockups
- Implement axis mapping dropdowns (X/Y/Z ← select from 12 dims)
- Dimension sliders (filter by value ranges)
- Search/filter inputs

**Obsidian Plugin Specialist**:
- Integrate UI components into plugin sidebar
- Wire controls to projection engine
- Implement view presets ("Temporal View", "Domain Clusters", "Agent Journey Mode")

**Google Sheets Specialist**:
- Export dimensional data to Google Sheets
- Create dashboard charts (dimensional distributions)

**Deliverable**: Fully interactive 3D graph with dimensional exploration

---

### **Phase 4: AI Features (Week 4-5)** - Intelligence Layer

**AI Features Specialist**:
- **Claude Opus**: Design gap analysis strategy, plan Agent Journey Affinity algorithm
- **Local LLM Setup**: Configure Ollama/LM Studio, install models (llama3, mistral, etc.)
- **Embedding Pipeline**: sentence-transformers → local inference for all 84 papers
- **Gap Analysis Execution**: Local LLMs process 12D topology, generate candidate gaps
- **Claude Sonnet**: Review outputs, filter high-value suggestions
- **Research Question Generation**: Claude Opus designs prompts, local LLMs execute at scale
- **Agent Journey Affinity**: Claude plans scoring algorithm, local LLM computes scores in real-time

**UI/UX Specialist**:
- Design AI insights sidebar panel
- Display gap analysis results (color-coded by confidence)
- Show research question suggestions (with "Regenerate" button)
- Agent Journey Mode toggle (with real-time affinity scores)
- Model selector: "Use Claude Opus for deep analysis" vs "Use local LLM for speed"

**Deliverable**: Hybrid AI-powered insights (Claude orchestration + local execution)

---

### **Phase 5: Real-Time Sync (Week 5-6)** - Live Updates

**Obsidian Plugin Specialist**:
- SurrealDB WebSocket subscription
- Live graph updates on file changes
- Smooth transition animations

**AI Features Specialist**:
- Trigger dimensional recomputation on changes
- Update Agent Journey Affinity in real-time

**Deliverable**: Fully live-updating 12D graph

---

### **Phase 6: Compound Engineering Features (Week 6-7)** - COHEZION Signature

**All Specialists**:
- Multi-agent collaboration tracking
- Session state integration
- Vault memory bridge connection
- Timeline slider (show vault evolution over time)

**Deliverable**: Production-ready 12D Graph System

---

## Technical Stack

| Component | Technology | Specialist Owner |
|-----------|-----------|------------------|
| **Database** | SurrealDB (native graph) | SurrealDB Specialist ✅ |
| **Sync Layer** | Python + httpx + watchdog | SurrealDB Specialist ✅ |
| **Projection Engine** | TypeScript + math.js | 12D Math Specialist |
| **3D Rendering** | Three.js + WebGL | Plugin Specialist |
| **UI Framework** | Svelte (Obsidian standard) | UI/UX Specialist |
| **AI Orchestration** | Claude Opus (planning) + Sonnet (coordination) + Haiku (quick tasks) | AI Features Specialist |
| **AI Execution** | Local LLMs (Ollama/LM Studio) for inference at scale | AI Features Specialist |
| **Embeddings** | sentence-transformers (local) | AI Features Specialist |
| **Sheets Integration** | Google Sheets API + ADC | Sheets Specialist |
| **Network Analysis** | NetworkX (Python) or custom | AI Features Specialist |

### AI Model Strategy

**Claude Models** (via Anthropic API):
- **Opus 4.6**: High-level planning, architectural decisions, complex reasoning
- **Sonnet 4.5**: Implementation coordination, code generation, specialist orchestration
- **Haiku 4.5**: Quick queries, batch processing, simple analysis (1/3 cost, 2x speed)

**Local LLMs** (via Ollama/LM Studio):
- **Inference at Scale**: Process hundreds of papers for semantic analysis
- **Embedding Generation**: sentence-transformers for similarity computation
- **Gap Analysis Execution**: After Claude Opus designs the strategy, local LLMs execute
- **Real-time Updates**: Fast local inference for live dimensional recomputation
- **Cost Optimization**: Heavy lifting done locally, Claude for orchestration only

---

## Success Metrics

### Compared to InfraNodus

| Feature | InfraNodus | COHEZION 12D Graph | Improvement |
|---------|-----------|-------------------|-------------|
| **Dimensions** | 3D (X, Y, Z) | 12D (configurable projection) | **4x richer** |
| **AI Features** | GPT-4 gap analysis | + Agent Journey + Context + Session state | **3x more context** |
| **Real-time Sync** | Manual refresh | Live WebSocket updates | **Instant** |
| **Clustering** | Louvain algorithm | Multi-dimensional + semantic | **Cross-domain detection** |
| **Agent Support** | None | Agent Journey Mode + collaboration tracking | **UNIQUE** |
| **Vault Integration** | Read-only plugin | Bidirectional sync (vault ↔ DB) | **Full integration** |

### User Experience Targets

- **Graph load time**: < 2s for 100 papers
- **Projection switch**: < 500ms (instant feel)
- **Live update latency**: < 1s (file save → graph update)
- **AI suggestion generation**: < 5s (GPT-4 call)
- **Node search**: < 100ms (instant filter)

---

## Risk Mitigation

### Technical Risks

1. **12D → 3D projection loses information**
   - Mitigation: Multiple projection presets, PCA for optimal dimension reduction, user can explore all 12 dimensions via axis mapping

2. **Performance with large graphs (1000+ nodes)**
   - Mitigation: WebGL instancing, LOD (level of detail), spatial indexing, progressive loading

3. **SurrealDB WebSocket reliability**
   - Mitigation: Reconnection logic, local caching, optimistic UI updates

4. **GPT-4 API rate limits**
   - Mitigation: Cache results, batch requests, use Haiku for simple tasks

### Coordination Risks

1. **Specialist integration conflicts**
   - Mitigation: Clear API contracts, TypeScript interfaces, weekly sync meetings

2. **Timeline dependencies (Math → Plugin → UI)**
   - Mitigation: Parallel prototyping, mock implementations, incremental integration

---

## Next Steps

1. **Spawn Specialist Team** (6 agents):
   - 12D Math/Geometry Specialist
   - Obsidian Plugin Specialist
   - UI/UX Specialist
   - AI Features Specialist
   - Google Sheets Specialist
   - Model Wrangler Specialist 🌟 (manages local LLM infrastructure)

2. **Phase 0: Model Infrastructure Setup** (Week 0):
   - **Model Wrangler**: Install Ollama, pull initial models (llama3.2:8b, nomic-embed-text, mistral:7b)
   - **Model Wrangler**: Create COHEZION benchmark suite (gap analysis, embeddings, affinity scoring)
   - **Model Wrangler**: Establish baseline performance metrics
   - **AI Features Specialist**: Define model API contracts
   - **Deliverable**: Local LLM infrastructure ready for Phase 1

3. **Phase 1 Kickoff**:
   - Math specialist: Design projection matrix
   - Plugin specialist: Setup TypeScript project
   - AI Features Specialist: Integrate with local LLMs
   - Model Wrangler: Monitor model performance, ready to swap if needed
   - Parallel work begins

4. **Weekly Coordination**:
   - All specialists report progress
   - Model Wrangler presents performance metrics
   - Integration checkpoints
   - Demo working features

---

## Sources & References

### InfraNodus Research
- [InfraNodus Obsidian Plugin](https://infranodus.com/obsidian-plugin)
- [How InfraNodus Works: AI Text Network Analysis](https://infranodus.com/about/how-it-works)
- [Network Analysis and Visualization](https://infranodus.com/docs/network-analysis)
- [Text Network Analysis and Visualization](https://infranodus.com/use-case/text-network-analysis)
- [GitHub: InfraNodus Obsidian Plugin](https://github.com/noduslabs/infranodus-obsidian-plugin)

### Related Decisions
- [[2026-02-09-12d-graph-surrealdb-integration]] - Original 12D vision
- [[3d-graph-plugin-selection]] - Plugin research (New 3D Graph recommended)

### Vault Patterns
- [[google-sheets-vault-bridge]] - SheetsBridge integration pattern
- [[automated-concept-extraction]] - Concept extraction from papers
- [[vault-completion-retrospective]] - Hybrid human-AI delivery model

---

**Status**: Ready for specialist team assembly and Phase 1 kickoff
**Next Action**: Spawn 5 specialist agents in parallel
**Timeline**: 6-7 weeks to production-ready 12D Graph System

## Related Patterns

- [[12d-graph-implementation]] — token-efficient plan implementing the specialist-driven phases designed here
- [[3-tier-hotwarmcold-model-rotation]] — the Opus/Sonnet/Haiku + local LLM model hierarchy applied in this plan

## Related Decisions (Series)

- [[2026-02-09-12d-graph-next-steps]] — next-steps strategy document
- [[2026-02-09-12d-graph-surrealdb-integration]] — original 12D SurrealDB backend decision
- [[2026-02-09-ai-model-strategy]] — detailed AI model selection strategy for 12D features

## Related Lessons

- [[lesson-11-team-agent-efficiency]] (operational validation)

- [[lesson-01-agent-has-great-content-but-claude-code-only-auto-reads]] (operational validation)

## Related Concepts

- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-adversarial-multi-agent-review-protocol]]
- [[2026-02-14-phase-2-adversarial-review-corrected-status-and-path-forward]]
