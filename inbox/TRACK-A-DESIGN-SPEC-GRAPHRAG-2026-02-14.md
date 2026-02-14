# Track A: GraphRAG Reasoning Engine - Design Specification

**Status**: 🔍 **READY FOR DESIGN REVIEW**
**Lead**: data-graph-specialist
**Duration**: 8-10 days
**Target Deliverables**: 600-800 LOC, 40+ tests, <500ms latency

---

## 1. Overview & Architecture

### What We're Building
A GraphRAG-powered reasoning engine that:
- Extracts decision reasoning chains from vault notes
- Classifies reasoning types (research, pattern, intuition, convention, hybrid)
- Generates natural-language explanations for decisions
- Maintains reasoning audit trail in SurrealDB

### Why GraphRAG
- LangChain integration = 2-day setup vs 2-week from scratch
- Proven for knowledge graph reasoning
- Supports multi-hop reasoning chains
- Battle-tested in production

### Integration Points
- **Input**: Decision vault notes (YAML frontmatter + content)
- **Storage**: SurrealDB `agent_reasoning` table (Phase 2 schema)
- **Output**: Reasoning chains + confidence scores + explanations
- **Query API**: HTTP REST endpoint

---

## 2. Technical Architecture

### Component Diagram
```
┌─────────────────────────────────────┐
│ Decision Vault Notes                │
│ (decisions/*.md files)              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Reasoning Extractor                 │
│ - YAML parsing                      │
│ - Content analysis                  │
│ - Chain extraction                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ GraphRAG Reasoning Engine           │
│ - LangChain integration             │
│ - Reasoning chain construction      │
│ - Type classification               │
│ - Explanation generation            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ SurrealDB Storage                   │
│ - agent_reasoning table             │
│ - informs_reasoning edges           │
│ - Confidence scores                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Query API                           │
│ - Reasoning lookup                  │
│ - Chain traversal                   │
│ - Explanation retrieval             │
└─────────────────────────────────────┘
```

### Data Model

#### Agent Reasoning Node
```python
{
  id: "agent_reasoning:{decision_id}",
  decision_id: "decision:abc123",
  reasoning_type: "research|pattern|intuition|convention|hybrid",
  reasoning_chain: [
    {step: 1, description: "...", confidence: 0.95},
    {step: 2, description: "...", confidence: 0.92},
    {step: 3, description: "...", confidence: 0.88}
  ],
  confidence_score: 0.92,  # Overall confidence
  assumptions: ["assumption1", "assumption2"],
  alternatives_rejected: [
    {option: "Option A", reason: "too risky"},
    {option: "Option B", reason: "insufficient data"}
  ],
  explanation: "This decision was made because...",
  created_at: "2026-02-16T12:00:00Z",
  updated_at: "2026-02-16T12:00:00Z"
}
```

#### Informs Reasoning Edge
```python
{
  in: "decision:abc123",
  out: "agent_reasoning:abc123",
  confidence: 0.92,
  created_at: "2026-02-16T12:00:00Z"
}
```

---

## 3. Implementation Plan (5 Steps)

### Step 1: GraphRAG Integration (1.5 days)

**Tasks**:
1. Install LangChain + GraphRAG dependencies
2. Configure SurrealDB connection
3. Build reasoning node schema extensions
4. Create GraphRAG query adapters

**Code Structure**:
```
src/
├── graphrag/
│   ├── __init__.py
│   ├── config.py          # GraphRAG configuration
│   ├── surrealdb_client.py  # SurrealDB integration
│   ├── reasoning_extractor.py
│   └── query_adapter.py    # GraphRAG query interface
├── models/
│   └── reasoning.py        # Data models
└── services/
    └── reasoning_service.py # Main service
```

**Success Criteria**:
- [ ] LangChain + GraphRAG installed
- [ ] SurrealDB connection tested
- [ ] Query adapter working
- [ ] Basic test passing

### Step 2: Reasoning Extraction (2 days)

**Tasks**:
1. Build vault note parser
2. Implement reasoning chain extraction
3. Create reasoning type classifier
4. Store extracted reasoning in SurrealDB

**Algorithm**:
```
For each decision in vault:
  1. Parse YAML frontmatter
  2. Extract reasoning section from content
  3. Classify reasoning type (ML or heuristic)
  4. Build reasoning chain (steps 1-N)
  5. Calculate confidence for each step
  6. Store in SurrealDB
  7. Create informs_reasoning edge
```

**Success Criteria**:
- [ ] 30+ decisions processed
- [ ] All reasoning types classified
- [ ] Confidence scores calculated
- [ ] SurrealDB storage verified

### Step 3: Reasoning Query API (2 days)

**Tasks**:
1. Build HTTP REST API endpoints
2. Implement reasoning chain traversal
3. Create explanation generator
4. Add LRU caching (5min TTL)

**API Endpoints**:
```
GET /api/reasoning/{decision_id}
  → Returns full reasoning chain + explanation
  → Latency: <500ms target

GET /api/reasoning/{decision_id}/chain
  → Returns step-by-step reasoning
  
GET /api/reasoning/{decision_id}/explanation
  → Returns natural language explanation
  
GET /api/reasoning/by-type/{type}
  → Returns all reasoning of specific type
  
GET /api/reasoning/high-confidence
  → Returns reasoning with >threshold confidence
```

**Success Criteria**:
- [ ] All endpoints working
- [ ] <500ms query latency (p95)
- [ ] Caching functional
- [ ] Error handling complete

### Step 4: Testing & Validation (1.5 days)

**Test Strategy**:
```
Unit Tests (15 tests):
- Reasoning extraction logic
- Type classification
- Confidence calculation
- Chain construction

Integration Tests (15 tests):
- SurrealDB read/write
- Edge creation
- Query API responses
- Cache behavior

Performance Tests (10 tests):
- Latency benchmarks
- Throughput testing
- Memory profiling
- Cache hit rates
```

**Success Criteria**:
- [ ] 40/40 tests passing (100%)
- [ ] Coverage >95%
- [ ] <500ms p95 latency
- [ ] <50MB memory footprint

### Step 5: Documentation (1 day)

**Deliverables**:
- API documentation (OpenAPI spec)
- Integration guide
- Example usage patterns
- Troubleshooting guide

---

## 4. Key Design Decisions

### Decision 1: GraphRAG Library Choice
**Selected**: LangChain GraphRAG module
**Rationale**: 
- Proven, battle-tested
- Good documentation
- 2-day integration vs 2-week from scratch
- Compatible with SurrealDB

### Decision 2: Reasoning Type Classification
**Selected**: YAML frontmatter metadata + ML heuristic
**Rationale**:
- YAML provides explicit type when available
- Heuristic (keyword matching) as fallback
- No external ML service required
- Fast classification (<10ms per decision)

### Decision 3: Confidence Calculation
**Selected**: Step-by-step confidence + aggregate
**Rationale**:
- Granular confidence per reasoning step
- Aggregate confidence = mean of steps
- Allows visualization of confidence degradation
- Ready for advanced models later

### Decision 4: Query API Design
**Selected**: REST HTTP endpoints
**Rationale**:
- Simple, cacheable
- Compatible with existing infrastructure
- Easy integration with UI/dashboard
- Standard web patterns

---

## 5. Dependencies & Requirements

### External Libraries
- **langchain**: ^0.1.0+ (GraphRAG module)
- **surrealdb**: Python client
- **pydantic**: Data validation
- **pytest**: Testing framework

### SurrealDB Schema
- `agent_reasoning` table (Phase 2 schema) ✅
- `informs_reasoning` edge table (Phase 2 schema) ✅
- Existing `agent_decision` table ✅

### Performance Targets
- Extraction: <2s per decision (84 decisions = <3 min total)
- Query: <500ms p95 latency
- Throughput: 40+ queries/sec
- Memory: <100MB process footprint

---

## 6. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| GraphRAG integration issues | Medium | 1-day spike investigation |
| Reasoning classification accuracy | Low | Multiple validation methods |
| Query performance degradation | Low | Caching + query optimization |
| SurrealDB compatibility | Low | Early integration testing |

---

## 7. Success Criteria

**HARD GATES** (must pass):
- [ ] 40/40 tests passing (100%)
- [ ] <500ms query latency (p95)
- [ ] 300+ decision relationships extracted
- [ ] Zero Phase 1-2 breaking changes

**SOFT GATES** (strongly desired):
- [ ] >95% code coverage
- [ ] <100MB memory footprint
- [ ] Comprehensive documentation
- [ ] Example integration with Phase 3 plugin

---

## 8. Sign-Off Checklist

Before Track A implementation begins:

- [ ] **Design reviewed** by vault-architect
- [ ] **Schema validated** against SurrealDB
- [ ] **Dependencies approved** (LangChain version)
- [ ] **Test framework prepared** (40+ test templates)
- [ ] **API endpoints finalized** (no breaking changes during implementation)
- [ ] **Performance targets confirmed** (<500ms acceptable)
- [ ] **Team ready** (data-graph-specialist + vault-architect support)

---

## 9. Timeline & Milestones

**Day 1**: GraphRAG integration (Step 1)
**Days 2-3**: Reasoning extraction (Step 2)
**Days 4-5**: Query API (Step 3)
**Days 6-7**: Testing & optimization (Step 4)
**Day 8**: Documentation + sign-off (Step 5)

**Target Completion**: 8-10 calendar days from 2026-02-16

---

**Status**: 🔍 **READY FOR DESIGN APPROVAL**
**Lead**: data-graph-specialist
**Support**: vault-architect

---
*Track A Design Specification*
*Ready for review and approval*
