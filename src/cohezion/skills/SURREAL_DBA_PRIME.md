# SKILL: SURREAL_DBA_PRIME

## DOMAIN EXPERTISE
Expert in **SurrealDB graph database administration** for the Cohezion Genesis engine. Specializes in schema validation, index optimization, record lifecycle management, and connection health monitoring.

## KEY TEXTS & CONCEPTS
- **Genesis Schema**: 6 core tables (journey_transitions, universe_snapshots, prompt_artifacts, model_artifacts, simulation_artifacts, internal_state_snapshots) + 2 views.
- **HNSW Vector Indexing**: MTREE indexes on 256D FLUME embeddings with COSINE distance for semantic search.
- **Live Queries**: Real-time streaming via `LIVE SELECT` for dashboard feeds and monitoring.
- **Graph Edges**: RELATES syntax for typed relationships (journey->prompt, model->parent_model, simulation->journey).
- **Schema Migration**: Versioned `.surql` files applied idempotently. Always `DEFINE` (upsert semantics), never raw `CREATE TABLE`.

## INSTRUCTION

1. **Validate Schema Consistency**:
   Compare `.surql`/`.sql` definitions against live database:
   ```sql
   INFO FOR DB;
   INFO FOR TABLE journey_transitions;
   ```
   Flag any drift: missing fields, type mismatches, undefined indexes.

2. **Audit Table Sizes**:
   ```sql
   SELECT count() AS total FROM journey_transitions GROUP ALL;
   SELECT count() AS total FROM universe_snapshots GROUP ALL;
   SELECT count() AS total FROM prompt_artifacts GROUP ALL;
   ```
   Flag tables >100K records for archival consideration.

3. **Check Index Health**:
   Verify HNSW indexes exist for vector fields. Confirm parameters match workload:
   - `EfConstruction: 150` (build quality)
   - `M: 16` (connectivity)
   - Distance: COSINE for normalized FLUME embeddings

4. **Detect Orphan Records**:
   ```sql
   -- Journey transitions with no parent journey
   SELECT journey_id, count() AS orphan_count
   FROM journey_transitions
   WHERE journey_id NOT IN (SELECT DISTINCT journey_id FROM universe_snapshots)
   GROUP BY journey_id;
   ```

5. **Monitor Connection Health**:
   Test WebSocket endpoint `ws://localhost:8001` latency. Check namespace/database accessibility. Report connection pool status from `surreal_client.py`.

6. **Recommend Schema Evolution**:
   - Identify FLEXIBLE fields with consistent structure (promote to SCHEMAFULL)
   - Suggest composite indexes for common query patterns
   - Recommend denormalization for hot read paths (e.g., pre-computed aggregates)

## PATTERNS
- Always use `DEFINE` statements (idempotent) over `CREATE TABLE`
- Schema migrations in numbered `.surql` files under `knowledge_graph/`
- Test schema changes against a local SurrealDB instance before production
- Use `FETCH` to eliminate N+1 queries in graph traversals

## ANTI-PATTERNS
- Raw string concatenation in SurQL queries (injection risk)
- FLEXIBLE type on fields with known structure (schema drift)
- Missing indexes on timestamp fields used in range queries
- Unbounded `SELECT *` without LIMIT on large tables

## VERSION
v1.0

## SEE ALSO
SURREALDB_OPTIMIZER_PRIME, VAULT_KEEPER_PRIME, DATABASE_PRIME
