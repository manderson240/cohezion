# SKILL: SURREALDB_VECTOR_GRAPH_ENGINE_PRIME

## DOMAIN EXPERTISE
SurrealDB v2.x advanced engineering specializing in 12D Poincaré hyperbolic HNSW vector search, native relational graph traversals (`RELATE ...->...->...`), bi-temporal audit logging, and zero-polling Live Event Triggers for multi-agent autonomous swarms.

## KEY TEXTS & CONCEPTS
- **12D Poincaré Embedding Index**: `DEFINE INDEX poincare_12d_hnsw_idx ON journey_knowledge FIELDS embedding_12d HNSW DIMENSION 12 DIST COSINE;`
- **Sub-Millisecond Vector Lookup**: `SELECT *, vector::similarity::cosine(embedding_12d, $query_vec) AS score FROM journey_knowledge WHERE embedding_12d <|5, 40|> $query_vec;`
- **Graph Edge Traversal**: `RELATE agent:antigravity->EMITTED->event_log:evt_1 SET timestamp = time::now();` and `SELECT ->EMITTED->event_log.* FROM agent;`
- **Declarative Live Triggers**: `DEFINE EVENT on_health_degraded ON TABLE event_log WHEN $event = "CREATE" AND $after.type = "DOMAIN_HEALTH_DEGRADED" THEN { ... };`

## INSTRUCTION

1. **Perform Sub-Millisecond 12D Vector Similarity Searches**:
```python
import httpx


async def find_similar_experience(embedding_12d: list[float], limit: int = 5):
    sql = """
    SELECT title, content, domain, vector::similarity::cosine(embedding_12d, $vec) AS similarity
    FROM journey_knowledge
    WHERE embedding_12d <|5, 40|> $vec
    ORDER BY similarity DESC
    LIMIT $limit;
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://127.0.0.1:8001/sql",
            headers={"surreal-ns": "cohezion", "surreal-db": "main"},
            auth=("root", "root"),
            json={"sql": sql, "vars": {"vec": embedding_12d, "limit": limit}},
        )
        return resp.json()
```

2. **Form Multi-Agent Graph Traversal Edges**:
```python
async def link_agent_action_to_kanban(agent_id: str, event_id: str, kanban_id: str):
    sql = f"""
    RELATE agent:{agent_id}->EMITTED->event_log:{event_id} SET timestamp = time::now();
    RELATE event_log:{event_id}->TRIGGERED->kanban_item:{kanban_id} SET timestamp = time::now();
    """
    # Execute graph edge creation
```

3. **Subscribe to Zero-Latency Live Queries**:
Use `LIVE SELECT * FROM event_log WHERE priority >= 8;` to stream critical cross-session messages with 0 ms polling latency.

## VERSION
v1.0

## SEE ALSO
- `FLUME_POINCARE_MANIFOLD_PRIME`
- `AUTOHARNESS_POLICY_PRIME`
- `SPINNING_PLATES_PROTOCOL_PRIME`
