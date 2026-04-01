# SKILL: SURREALDB_OPERATIONS_PRIME

## DOMAIN EXPERTISE
You are a SurrealDB 3.0 specialist managing the Cohezion knowledge graph persistence layer. You ensure all learnings, snapshots, and journey data are persisted to SurrealDB on port 8001 (native binary) using the correct v3.0 syntax.

## KEY TEXTS & CONCEPTS
* **Dual SurrealDB Setup**: Port 8000 (Docker, memory backend — read-only issues), Port 8001 (native binary, file-backed — writable). Always target port 8001.
* **Namespace/Database**: `USE NS cohezion DB cohezion;` prefix on all queries.
* **Auth**: root:root (default dev setup).
* **SurrealDB 3.0 Syntax**: `surreal-ns`/`surreal-db` headers for HTTP, `USE NS x DB y` for SQL.

## INSTRUCTION
1. **Persist Learnings**: After each session, write all new L### entries to `learning` table:
   ```sql
   CREATE learning SET number = N, title = '...', content = '...', date = '...', tags = [...], session = N, model_id = 'retrospective';
   ```
2. **Universe Snapshots**: After each session, write metrics to `universe_snapshot`:
   ```sql
   CREATE universe_snapshot SET tick = SESSION_NUM, test_count = N, module_count = N, skill_count = N, learning_count = N, coherence = 0.5, timestamp = time::now();
   ```
3. **Journey Transitions**: Record agent state transitions in `journey_transitions`:
   ```sql
   CREATE journey_transitions SET agent_id = '...', from_state = [...], to_state = [...], operation = '...', coherence = N, timestamp = time::now();
   ```
4. **Health Check**: Before writes, verify connectivity:
   ```bash
   curl -sf http://localhost:8001/health && echo "OK"
   ```
5. **Query Patterns**:
   ```sql
   SELECT * FROM learning WHERE session = 84 ORDER BY number;
   SELECT * FROM universe_snapshot ORDER BY tick DESC LIMIT 5;
   SELECT count() FROM learning GROUP ALL;
   ```

## ANTI-PATTERNS
- Do NOT target port 8000 (Docker memory backend has read-only issues)
- Do NOT use `NS`/`DB` old-style headers — use `surreal-ns`/`surreal-db` or `USE NS x DB y`
- Do NOT assume database exists — always prefix with `USE NS cohezion DB cohezion;`

## VERSION
v1.0.0
