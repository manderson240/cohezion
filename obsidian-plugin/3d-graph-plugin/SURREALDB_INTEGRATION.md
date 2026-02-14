# SurrealDB Integration: Phase 4 Architecture

## Overview

Phase 4 extends the 3D Graph plugin with decision analysis by integrating with SurrealDB, which stores decision reasoning chains, cascades, and contradictions.

```
Obsidian Vault                SurrealDB
┌──────────────────┐         ┌──────────────────┐
│ decisions/ (88)  │◄───────►│ agent_reasoning  │
│ - YAML notes     │         │ - steps          │
│ - frontmatter    │         │ - confidence     │
└──────────────────┘         └──────────────────┘
         ▲
         │
    VaultBridge.ts
         │
         ▼
  ┌──────────────────────┐
  │ SurrealDBClient.ts   │ ◄─── HTTP/REST Queries
  │ - Query methods      │      LRU Cache (50 items, 5min TTL)
  │ - Caching           │
  │ - Error handling    │
  └──────────────────────┘
         ▲
         │
    Plugin UI
  (DecisionExplorer)
```

## Data Flow

### 1. Vault Read (VaultBridge.ts)

**Source**: `/decisions/*.md` YAML frontmatter

**Fields extracted**:
```yaml
---
title: "Phase 2 Complete"
date: "2026-02-14"
status: proposed
tags: [decision]

decision_reasoning:
  chosen_option: "Deploy to production"
  rationale: "All tests pass..."
  reasoning_type: "research"
  confidence_score: 0.95
  steps:
    - sequence: 1
      content: "Reviewed test coverage"
      type: "research"
      confidence: 0.9
  assumptions:
    - "Production infrastructure ready"
  alternatives_rejected:
    - "Defer until next sprint"
---
```

**Output**: `Decision` objects cached in memory

### 2. SurrealDB Query (SurrealDBClient.ts)

**Source**: SurrealDB tables via HTTP/REST API

**Query pattern**:
```sql
SELECT * FROM agent_reasoning
WHERE decision_id = 'phase-2-complete'
ORDER BY step_number ASC
```

**Response**:
```json
[
  {
    "id": "chain-1",
    "decision_id": "phase-2-complete",
    "steps": [...],
    "reasoning_type": "hybrid",
    "confidence": 0.95,
    "timestamp": "2026-02-14T00:00:00Z"
  }
]
```

### 3. Cache Layer

**Strategy**: LRU cache with 5-minute TTL

**Benefits**:
- 90%+ hit rate after first access
- Reduces SurrealDB load
- <200ms query response time

**Example**:
```
Request 1: "Get reasoning for phase-2"
  → Not in cache
  → Query SurrealDB (~200ms)
  → Store in cache
  → Return result

Request 2: "Get reasoning for phase-2" (within 5min)
  → Found in cache
  → Return immediately (<1ms)
  → No database query
```

## SurrealDB Tables

### agent_reasoning

Stores decision reasoning chains with individual steps.

**Schema**:
```
Table: agent_reasoning
├── id: String (unique)
├── decision_id: String (foreign key)
├── steps: Array[ReasoningStep]
│   ├── sequence: Number
│   ├── content: String
│   ├── type: Enum(research, pattern, intuition, convention, hybrid)
│   └── confidence: Number(0-1)
├── reasoning_type: Enum(research, pattern, intuition, convention, hybrid)
├── confidence: Number(0-1)
├── assumptions: Array[String]
└── timestamp: DateTime
```

**Sample data**:
```json
{
  "id": "chain-1",
  "decision_id": "phase-2-complete",
  "steps": [
    {
      "sequence": 1,
      "content": "Reviewed test results - 100% pass rate",
      "type": "research",
      "confidence": 0.95
    },
    {
      "sequence": 2,
      "content": "Team consensus for deployment",
      "type": "convention",
      "confidence": 0.90
    }
  ],
  "reasoning_type": "hybrid",
  "confidence": 0.925,
  "assumptions": ["Production environment tested", "Rollback procedure ready"],
  "timestamp": "2026-02-14T10:30:00Z"
}
```

### decision_cascades

Tracks downstream impacts when one decision influences another.

**Schema**:
```
Table: decision_cascades
├── id: String (unique)
├── source_decision_id: String
├── target_decision_id: String
├── dependency_type: Enum(enables, blocks, influences, conflicts)
├── impact_level: Enum(critical, significant, minor)
└── description: String
```

### decision_contradictions

Tracks where decision conflicts with learned lessons or operational evidence.

**Schema**:
```
Table: decision_contradictions
├── id: String (unique)
├── decision_id: String
├── lesson_id: String
├── challenge_type: Enum(contradicts, undermines, requires_review)
├── severity: Enum(critical, high, medium, low)
└── description: String
```

## API Endpoints

### Query Reasoning for Decision

```bash
POST /sql
Content-Type: application/json

{
  "query": "SELECT * FROM agent_reasoning WHERE decision_id = '...' ORDER BY step_number ASC"
}
```

**Response**: Array of reasoning chains with steps

**Latency**: <200ms (cached <1ms)

### Analyze Cascades

```bash
POST /sql

{
  "query": "SELECT * FROM decision_cascades WHERE source_decision_id = '...' LIMIT 100"
}
```

**Response**: Array of cascade relationships

**Latency**: <200ms (typically 50-100 cascades per decision)

### Detect Contradictions

```bash
POST /sql

{
  "query": "SELECT * FROM decision_contradictions WHERE decision_id = '...' ORDER BY severity DESC"
}
```

**Response**: Array of contradictions

**Latency**: <200ms

## Error Handling

### SurrealDB Offline

**Problem**: User's SurrealDB instance not running

**Solution**:
1. Plugin detects connection failure
2. Falls back to vault-only mode
3. Shows warning: "Reasoning data unavailable - using cached info"
4. Cached data from previous sessions still available
5. Shows "Retry" button to reconnect

**Code**:
```typescript
try {
  const result = await surrealClient.queryReasoningForDecision(id);
  if (!result) {
    // Graceful fallback
    showWarning("Reasoning data not available");
  }
} catch (error) {
  console.error("SurrealDB query failed:", error);
  // Continue with vault data only
}
```

### Query Timeout

**Problem**: Large query takes >5 seconds

**Solution**:
1. Cancel query after 5s timeout
2. Return cached result if available
3. Show loading spinner → timeout message
4. Suggest limiting cascade depth or date range

### Invalid Decision ID

**Problem**: User searches for non-existent decision

**Solution**:
1. Query returns empty array
2. Plugin shows "No reasoning found for this decision"
3. Suggest checking decision exists in vault
4. Suggest checking decision has reasoning_chain field

## Performance Optimization

### Cache Strategy

```typescript
// LRU Cache with TTL
private queryCache: Map<string, { result: any; timestamp: number }> = new Map();
private readonly cacheSize = 50;
private readonly cacheTTL = 5 * 60 * 1000; // 5 minutes

// Enforce size limit
if (this.queryCache.size > this.cacheSize) {
  const firstKey = this.queryCache.keys().next().value;
  this.queryCache.delete(firstKey);
}
```

### Query Optimization

1. **Limit results**: `LIMIT 100` for cascades (pagination needed for >100)
2. **Index on decision_id**: Speed up `WHERE decision_id = '...'`
3. **Order by importance**: Return most impactful cascades first
4. **Batch queries**: Request multiple decisions at once (future)

## Monitoring & Debugging

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "ok": true,
  "version": "1.0.0"
}
```

### Query Debugging

Enable debug logging in plugin settings:

```typescript
if (DEBUG_MODE) {
  console.log(`SurrealDB query: ${query}`);
  console.log(`Response: ${JSON.stringify(result)}`);
  console.log(`Latency: ${Date.now() - startTime}ms`);
}
```

### Cache Statistics

View in plugin settings → Performance:
- Cache size: X items
- Hit rate: Y%
- Average latency: Zms

## Integration Checklist

For developers setting up Phase 4:

- [ ] SurrealDB running and accessible (localhost:8000)
- [ ] SurrealDBClient.ts created and compiled
- [ ] VaultBridge.ts created and compiled
- [ ] Decision types (Decision.ts) available
- [ ] MCP tools accessible (if using teleport)
- [ ] Sample decisions loaded in vault
- [ ] Sample reasoning data in SurrealDB
- [ ] SurrealDBClient tests passing
- [ ] Caching working (cache hits after first query)
- [ ] Error handling tested (SurrealDB offline scenario)

## Troubleshooting

### "Connection refused" Error

**Cause**: SurrealDB not running

**Fix**:
```bash
# Start SurrealDB
surreal start --bind 0.0.0.0:8000 \
  --user root --pass root \
  file:/path/to/data.db
```

### "CORS Error" (if using cross-origin)

**Cause**: SurrealDB CORS not configured

**Fix**: Use proxy or configure SurrealDB:
```bash
surreal start --bind 0.0.0.0:8000 \
  --cors-origins "http://localhost:*"
```

### "Query returned empty"

**Cause**: Table may not exist or be empty

**Fix**: Check SurrealDB schema:
```bash
surreal sql "INFO FOR DATABASE;"
```

### Slow queries (>500ms)

**Cause**: Large dataset or missing indexes

**Fix**: Create indexes:
```sql
DEFINE INDEX decision_id_idx ON TABLE agent_reasoning COLUMNS decision_id;
DEFINE INDEX cascade_source ON TABLE decision_cascades COLUMNS source_decision_id;
```

## Future Enhancements

1. **WebSocket subscriptions**: Real-time updates when decisions change
2. **Full-text search**: Search decision content, not just metadata
3. **Batch queries**: Load multiple decisions at once
4. **Query caching in database**: Server-side cached queries
5. **Time-based filtering**: "Show me decisions from last 30 days"
6. **Confidence filtering**: "Show only high-confidence decisions (>0.8)"
7. **Reasoning type filtering**: "Show only research-based decisions"

## See Also

- [Decision Analysis Guide](./DECISION_ANALYSIS_GUIDE.md)
- [API Reference](./API_REFERENCE.md)
- [SurrealDB Documentation](https://surrealdb.com/docs/)
