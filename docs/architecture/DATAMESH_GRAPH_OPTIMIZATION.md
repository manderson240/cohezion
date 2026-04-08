# Datamesh & Graph Architecture Optimization

## Current State Analysis

### Existing Components

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| **WorkflowEngine** | `graph/engine.py` | DAG-based execution | ✅ Active |
| **SurrealClient** | `core/persistence/surreal_client.py` | 12D physics state DB | ✅ Active |
| **KnowledgeGraph** | `knowledge_graph/` | Learnings & PRIME docs | ✅ Active |
| **BidirectionalLinker** | `knowledge_graph/bidirectional_linker.py` | Wiki-style linking | ✅ Active |
| **WikiSystem** | `integrations/obsidian_wiki.py` | Karpathy pattern | ✅ New |
| **MIRIX Bridge** | `integrations/wiki_mirix_bridge.py` | 6-agent memory | ✅ New |
| **FLUME Bridge** | `integrations/flume_wiki_bridge.py` | 256D embeddings | ✅ New |

### Identified Gaps

1. **No unified schema** - Each system has its own data format
2. **Redundant persistence** - Multiple backends without coordination
3. **No federation layer** - Systems can't query across boundaries
4. **Missing lineage tracking** - Hard to trace data flow
5. **No optimization layer** - Query performance not prioritized

---

## Proposed Architecture: Cohezion Datamesh

### 1. Unified Schema Layer (Star Schema)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        COHEZION DATAMESH                                │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │   SOURCES    │  │   ENTITIES   │  │   EVENTS     │  │ CONTEXTS │  │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤  ├──────────┤  │
│  │ raw_sources  │  │ wiki_pages   │  │ executions   │  │ sessions │  │
│  │ embeddings   │  │ concepts     │  │ exhausts     │  │ journeys │  │
│  │ trajectories │  │ agents       │  │ rewrites     │  │ skills   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────┬─────┘  │
└───────┬────────────────┬────────────────┬────────────────┬────────────┘
        │                │                │                │
        ▼                ▼                ▼                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    UNIFIED RELATION GRAPH                           │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Relations: derives_from | relates_to | precedes | transforms | │  │
│  │           authored_by | executes_in | learns_from | improves | │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2. Domain Boundaries (Data Products)

| Domain | Owner | Data Products | Interface |
|--------|-------|---------------|-----------|
| **Knowledge** | Wiki System | Pages, Concepts, Relations | GraphQL |
| **Memory** | MIRIX | Episodic, Semantic, Core | gRPC |
| **Execution** | Compound Loop | Tasks, Results, Exhaust | REST |
| **Physics** | FLUME | Embeddings, Trajectories | Vector API |
| **Learning** | Ouroboros | Patterns, Rules, Improvements | Event Stream |

### 3. Query Federation Layer

```python
# Unified query interface across all domains
@dataclass
class DatameshQuery:
    """Cross-domain federated query."""
    
    sources: list[str]  # ["wiki", "mirix", "surreal", "flume"]
    filter: dict        # Unified filter criteria
    embedding: Optional[torch.Tensor]  # For semantic search
    lineage: bool       # Include data lineage
    
    async def execute(self) -> DatameshResult:
        # Parallel fan-out to all sources
        # Result aggregation
        # Lineage augmentation
        pass
```

### 4. Optimization Strategies

#### A. Graph Query Optimization

```sql
-- Materialized Views for Common Patterns
DEFINE INDEX wiki_concept_clusters ON wiki 
    FIELDS embedding TYPE vector(256) 
    METRIC cosine;

-- Pre-computed relation traversals
DEFINE INDEX exhaust_to_rewrite ON relates_to 
    WHERE from.type = 'exhaust' AND to.type = 'rewrite';

-- Time-series partitioning for events
DEFINE TABLE execution_events CHRONOS;
```

#### B. Caching Strategy

| Cache Level | Data | TTL | Eviction |
|-------------|------|-----|----------|
| L1 Memory | Hot queries | 5 min | LRU |
| L2 Redis | Embeddings | 1 hour | LFU |
| L3 Surreal | Full graph | Persistent | None |
| L4 Wiki | Markdown | Persistent | Manual |

#### C. Batch Processing

```python
# Aggregate writes for burst tolerance
class DatameshIngestion:
    """Batch writer with backpressure handling."""
    
    batch_size: int = 100
    flush_interval: float = 30.0
    max_queue_size: int = 10000
    
    async def write(self, record: Record) -> None:
        # Buffer in queue
        # Flush on batch size OR interval
        # Handle backpressure with circuit breaker
```

### 5. Lineage Tracking

```python
@dataclass
class DataLineage:
    """Complete provenance for any data point."""
    
    origin: str           # Source system
    transformations: list[Transform]
    upstream: list[UUID]  # Parent records
    downstream: list[UUID]  # Child records
    checksum: str         # Content hash
    timestamp: datetime
    
    def trace(self, depth: int = 5) -> LineageGraph:
        """Walk lineage graph for impact analysis."""
```

### 6. Performance Targets

| Metric | Current | Target | Strategy |
|--------|---------|--------|----------|
| Graph query latency | ~100ms | <20ms | Pre-computed paths |
| Embedding search | ~500ms | <50ms | HNSW index + cache |
| Cross-domain query | ~1s | <200ms | Parallel fan-out |
| Ingest throughput | ~100/s | ~1000/s | Batch + async |
| Storage efficiency | baseline | -50% | Compression + dedup |

---

## Implementation Roadmap

### Phase 1: Schema Unification (Week 1)
- [ ] Define unified schema for all domains
- [ ] Create schema migration scripts
- [ ] Implement validation layer

### Phase 2: Query Federation (Week 2)
- [ ] Build DatameshQuery interface
- [ ] Implement parallel source dispatch
- [ ] Add result aggregation

### Phase 3: Optimization Layer (Week 3)
- [ ] Materialized views in SurrealDB
- [ ] Multi-tier caching
- [ ] Batch ingestion pipeline

### Phase 4: Lineage System (Week 4)
- [ ] Implement provenance tracking
- [ ] Add lineage queries
- [ ] UI for lineage visualization

---

## Charter Compliance

| Principle | Implementation |
|-----------|---------------|
| **Idempotency** | Schema migrations are reversible; writes use idempotency keys |
| **0.5 Coherence** | CQRS split: read-optimized views, write-optimized events |
| **Transparency** | All queries logged; lineage fully exposed |
| **Artifact Persistence** | Every transformation stored; nothing ephemeral |

---

## Next Actions

1. **Schema Design** - Unified types across wiki/FLUME/Surreal
2. **Benchmark Suite** - Establish current performance baseline
3. **Migration Plan** - Move existing data to unified schema
4. **Monitor Setup** - Track query performance and lineage coverage

---
*Architecture v1.0 - 2026-04-08*
