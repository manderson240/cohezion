# Track C: Impact & Dependency Analyzer - Design Specification

**Status**: 🔍 **READY FOR DESIGN REVIEW**
**Lead**: [Graph Analyst - NEEDS ASSIGNMENT]
**Duration**: 6-8 days
**Target Deliverables**: 500-600 LOC, 35+ tests, 150+ dependencies identified

---

## 1. Overview & Objectives

### What We're Building
An impact analysis engine that:
- Extracts decision dependencies from vault notes
- Computes impact cascades (decision ripple effects)
- Identifies critical path decisions
- Generates dependency graphs
- Detects circular dependencies

### Key Concepts
**Dependency Types**:
- **Blocks**: Decision A must be resolved before decision B can proceed
- **Enables**: Decision A makes decision B possible
- **Refines**: Decision A improves/clarifies decision B
- **Contradicts**: Decision A opposes decision B

**Impact Levels**:
- **Critical**: Cannot proceed without resolving dependency
- **Significant**: Requires substantial redesign
- **Minor**: Minor adjustment needed

---

## 2. Technical Architecture

### Component Diagram
```
┌──────────────────────────────┐
│ Decision Vault Notes         │
│ (decisions/*.md files)       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Dependency Extractor         │
│ - Relationship parsing       │
│ - Type classification        │
│ - Dependency graph building  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Impact Cascade Engine        │
│ - Propagation algorithm      │
│ - Cycle detection            │
│ - Impact level calculation   │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Critical Path Analysis       │
│ - PERT/CPM algorithm         │
│ - Blocking dependency chains │
│ - Decision criticality calc  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ SurrealDB Storage            │
│ - relates_to_decision edges  │
│ - impact_analysis table      │
│ - critical_path table        │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Query & Visualization API    │
│ - Dependency graphs          │
│ - Critical path queries      │
│ - Impact reports             │
└──────────────────────────────┘
```

### Data Model

#### Dependency Edge
```python
{
  id: "depends:{source_id}:{target_id}",
  in: "decision:abc123",      # Source decision
  out: "decision:def456",     # Target decision
  dependency_type: "blocks|enables|refines|contradicts",
  impact_level: "critical|significant|minor",
  notes: "Explanation of dependency",
  blocked_if_unresolved: true,
  created_at: "2026-02-16T12:00:00Z"
}
```

#### Impact Cascade Record
```python
{
  id: "impact:{decision_id}",
  source_decision: "decision:abc123",
  affected_decisions: [
    {
      decision_id: "decision:def456",
      impact_level: "critical",
      distance: 1,
      path: ["decision:abc123", "decision:def456"]
    },
    {
      decision_id: "decision:ghi789",
      impact_level: "significant",
      distance: 2,
      path: ["decision:abc123", "decision:def456", "decision:ghi789"]
    }
  ],
  total_affected: 10,
  critical_count: 3,
  significant_count: 5,
  minor_count: 2,
  computed_at: "2026-02-16T12:00:00Z"
}
```

#### Critical Path Record
```python
{
  id: "critical_path:{decision_id}",
  decision_id: "decision:abc123",
  is_on_critical_path: true,
  criticality_score: 0.85,     # 0-1 scale
  blocking_decisions_count: 5,
  blocked_by_count: 3,
  estimated_impact_radius: 12, # decisions affected if blocked
  computed_at: "2026-02-16T12:00:00Z"
}
```

---

## 3. Implementation Plan (5 Steps)

### Step 1: Dependency Extraction (1.5 days)

**Tasks**:
1. Build vault note parser
2. Extract dependency relationships
3. Classify dependency types
4. Validate dependency graph

**Extraction Algorithm**:
```
For each decision in vault:
  1. Parse YAML frontmatter
  2. Extract "depends_on", "blocks", "enables", "refines" fields
  3. Classify dependency type
  4. Create depends_{type} edge in SurrealDB
  5. Validate references exist
  6. Log any broken references
  
Build dependency graph:
  1. Load all dependencies
  2. Create adjacency lists
  3. Detect cycles (DFS-based)
  4. Log any circular dependencies
```

**Success Criteria**:
- [ ] 150+ dependencies extracted
- [ ] All types classified
- [ ] Circular dependencies detected
- [ ] Zero broken references (with fixes)

### Step 2: Impact Cascade Computation (2 days)

**Tasks**:
1. Implement cascade propagation algorithm
2. Calculate impact levels
3. Build transitive dependency resolution
4. Create cycle detection

**Cascade Algorithm**:
```
For each decision D:
  1. Initialize affected = {D}
  2. Queue Q = {D}
  3. While Q not empty:
     a. Current = Q.pop()
     b. For each outgoing edge E from Current:
        - If E not already visited:
          - Add E.target to affected
          - Add E.target to Q
          - Calculate distance and impact
  4. Return all affected decisions with paths
```

**Success Criteria**:
- [ ] Cascades computed for 20+ decisions
- [ ] Impact levels assigned
- [ ] Path tracking working
- [ ] Performance: <1s for full graph

### Step 3: Critical Path Analysis (1.5 days)

**Tasks**:
1. Implement critical path algorithm
2. Calculate decision criticality scores
3. Identify blocking dependencies
4. Generate critical path visualization

**Algorithm**:
```
Critical Path (PERT-style):
  1. For each decision D:
     - Count decisions that must be resolved before D
     - Calculate urgency (blocking_count / total_dependencies)
     - Calculate impact (affected_decisions_count)
     - Criticality = urgency * impact (normalized 0-1)
  2. Identify decisions on critical path:
     - If any blocked_by_critical_decision, mark as critical
  3. Calculate impact radius:
     - All decisions reachable from D in dependency graph
```

**Success Criteria**:
- [ ] Criticality scores for all decisions
- [ ] Critical path identified
- [ ] Blocking chains resolved
- [ ] Impact radius calculated

### Step 4: Testing & Validation (1.5 days)

**Test Strategy**:
```
Unit Tests (12 tests):
- Dependency parsing
- Graph construction
- Cycle detection
- Impact calculation

Integration Tests (15 tests):
- SurrealDB read/write
- Cascade propagation
- Critical path computation
- Query API responses

Validation Tests (8 tests):
- Large graph performance
- Edge cases (circular deps, orphans)
- Data consistency
- Graph integrity
```

**Success Criteria**:
- [ ] 35/35 tests passing (100%)
- [ ] Coverage >95%
- [ ] Performance: <1s full analysis
- [ ] All edge cases handled

### Step 5: Documentation (1 day)

**Deliverables**:
- Algorithm documentation
- Dependency model docs
- Critical path explanation
- API documentation
- Example dependency graphs

---

## 4. Key Design Decisions

### Decision 1: Graph Representation
**Selected**: Adjacency list + SurrealDB edges
**Rationale**:
- Natural for SurrealDB relationship model
- Efficient for cascade propagation
- Easy to query + traverse

### Decision 2: Cycle Detection Strategy
**Selected**: DFS-based cycle detection (O(V+E))
**Rationale**:
- Fast even for large graphs
- Identifies actual cycles (not just potential)
- Minimal memory overhead

### Decision 3: Critical Path Algorithm
**Selected**: PERT-style (Urgency × Impact)
**Rationale**:
- Simpler than full critical path method
- Works with decision graphs (not just project timelines)
- Interpretable results

### Decision 4: Impact Cascade Scope
**Selected**: All reachable decisions (unbounded)
**Rationale**:
- Shows full ripple effects
- No arbitrary cutoff
- Enables impact visualization

---

## 5. Performance Targets

- **Extraction**: <1s for 84 decisions
- **Cascade computation**: <1s for full graph
- **Critical path analysis**: <500ms
- **Query**: <200ms for any dependency query
- **Memory**: <100MB process footprint

---

## 6. Success Criteria

**HARD GATES** (must pass):
- [ ] 35/35 tests passing (100%)
- [ ] 150+ dependencies identified
- [ ] 20+ impact cascades computed
- [ ] Critical path analysis complete
- [ ] Zero orphaned decisions

**SOFT GATES** (strongly desired):
- [ ] >95% code coverage
- [ ] <500ms analysis time
- [ ] Circular dependency detection
- [ ] Comprehensive documentation

---

## 7. Sign-Off Checklist

Before Track C implementation begins:

- [ ] **Design reviewed** by vault-architect
- [ ] **Graph algorithms validated**
- [ ] **SurrealDB schema confirmed**
- [ ] **Performance targets locked**
- [ ] **Test framework prepared**
- [ ] **Cycle detection strategy approved**
- [ ] **Team ready** (graph-analyst assigned)

---

**Status**: 🔍 **READY FOR DESIGN APPROVAL**
**Lead**: [Graph Analyst - NEEDS ASSIGNMENT]
**Support**: vault-architect (dependency extraction)

---
*Track C Design Specification*
*Ready for review and approval*
