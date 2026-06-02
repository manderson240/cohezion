---
name: surrealdb-core-prime
description: "SurrealDB 3.0 core operations and database administration for the Cohezion knowledge graph and Genesis engine. Persistence of learnings, snapshots, and journey data on port 8001 (native binary) with correct v3.0 syntax, plus schema validation, index health, orphan detection, and connection monitoring. Use for: writing/querying learnings, universe_snapshots, journey_transitions; validating the Genesis schema; auditing table sizes and HNSW indexes; connection health. Skip: MCP tool interface, performance tuning, or mock/test patterns (use SURREALDB_ADVANCED_PRIME); SQL/RDBMS patterns (use DATABASE_PRIME)."
metadata:
  version: "v1.1"
  concepts: ["Dual SurrealDB Topology (port 8001)", "Namespace/Database", "v3.0 Syntax", "Genesis Schema", "HNSW Vector Indexing", "Live Queries", "Graph Edges (RELATE)", "Schema Migration", "Orphan Detection", "Bi-temporal / SurrealKV Versioned"]
  source: "src/cohezion/skills/SURREALDB_CORE_PRIME.md"
---

# SKILL: SURREALDB_CORE_PRIME

Consolidates SURREALDB_OPERATIONS_PRIME (persistence operations) and SURREAL_DBA_PRIME (graph DB administration).

## DOMAIN EXPERTISE
You are a SurrealDB 3.0 specialist managing the Cohezion knowledge graph persistence layer AND a SurrealDB graph database administrator for the Genesis engine. You ensure all learnings, snapshots, and journey data are persisted to SurrealDB on port 8001 (native binary) using the correct v3.0 syntax, and you keep the schema, indexes, and connections healthy.

## KEY TEXTS & CONCEPTS

### Operations
* **Dual SurrealDB Setup**: Port 8000 (Docker, memory backend -- read-only issues), Port 8001 (native binary, file-backed -- writable). Always target port 8001.
* **Namespace/Database**: `USE NS cohezion DB cohezion;` prefix on all queries.
* **Auth**: root:root (default dev setup).
* **SurrealDB 3.0 Syntax**: `surreal-ns`/`surreal-db` headers for HTTP, `USE NS x DB y` for SQL.

### Administration
- **Genesis Schema**: 6 core tables (journey_transitions, universe_snapshots, prompt_artifacts, model_artifacts, simulation_artifacts, internal_state_snapshots) + 2 views.
- **HNSW Vector Indexing**: MTREE indexes on 256D FLUME embeddings with COSINE distance for semantic search.
- **Live Queries**: Real-time streaming via `LIVE SELECT` for dashboard feeds and monitoring.
- **Graph Edges**: RELATES syntax for typed relationships (journey->prompt, model->parent_model, simulation->journey).
- **Schema Migration**: Versioned `.surql` files applied idempotently. Always `DEFINE` (upsert semantics), never raw `CREATE TABLE`.

## INSTRUCTION

### A. Persistence Operations
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

### B. Database Administration
6. **Validate Schema Consistency**: Compare `.surql`/`.sql` definitions against live database:
   ```sql
   INFO FOR DB;
   INFO FOR TABLE journey_transitions;
   ```
   Flag any drift: missing fields, type mismatches, undefined indexes.
7. **Audit Table Sizes**:
   ```sql
   SELECT count() AS total FROM journey_transitions GROUP ALL;
   SELECT count() AS total FROM universe_snapshots GROUP ALL;
   SELECT count() AS total FROM prompt_artifacts GROUP ALL;
   ```
   Flag tables >100K records for archival consideration.
8. **Check Index Health**: Verify HNSW indexes exist for vector fields. Confirm parameters match workload:
   - `EfConstruction: 150` (build quality)
   - `M: 16` (connectivity)
   - Distance: COSINE for normalized FLUME embeddings
9. **Detect Orphan Records**:
   ```sql
   -- Journey transitions with no parent journey
   SELECT journey_id, count() AS orphan_count
   FROM journey_transitions
   WHERE journey_id NOT IN (SELECT VALUE journey_id FROM universe_snapshots)
   GROUP BY journey_id;
   ```
   NOTE (Learning 295): use `SELECT VALUE journey_id` (not `SELECT DISTINCT journey_id`) so the `IN` subquery returns a flat scalar array; `SELECT col` returns `[{col: "val"}]` and matches 0 rows in SurrealDB 3.0.
10. **Monitor Connection Health**: Test WebSocket endpoint `ws://localhost:8001` latency. Check namespace/database accessibility. Report connection pool status from `surreal_client.py`.
11. **Recommend Schema Evolution**:
    - Identify FLEXIBLE fields with consistent structure (promote to SCHEMAFULL)
    - Suggest composite indexes for common query patterns
    - Recommend denormalization for hot read paths (e.g., pre-computed aggregates)

## PATTERNS
- Always use `DEFINE` statements (idempotent) over `CREATE TABLE`
- Schema migrations in numbered `.surql` files under `knowledge_graph/`
- Test schema changes against a local SurrealDB instance before production
- Use `FETCH` to eliminate N+1 queries in graph traversals

## ANTI-PATTERNS
- Do NOT target port 8000 (Docker memory backend has read-only issues)
- Do NOT use `NS`/`DB` old-style headers -- use `surreal-ns`/`surreal-db` or `USE NS x DB y`
- Do NOT assume database exists -- always prefix with `USE NS cohezion DB cohezion;`
- Raw string concatenation in SurQL queries (injection risk)
- FLEXIBLE type on fields with known structure (schema drift)
- Missing indexes on timestamp fields used in range queries
- Unbounded `SELECT *` without LIMIT on large tables

## OPERATIONAL LEARNINGS (SurrealDB-specific)

**Learning 158 -- AsyncSurreal Migration & Connect Protocol**: The `surrealdb-py` library (v0.3.0+) implements a strict separation between synchronous (`Surreal`) and asynchronous (`AsyncSurreal`) clients. Using `Surreal` in an `async with` block or awaiting its `use()` method (synchronous in the blocking client) results in a `TypeError`. **Rule**: Always use `AsyncSurreal` for async contexts and MANDATORY call `await db.connect()` before `signin()` or `use()`.

**Learning 159 -- Doc-Retriever & Memory Consistency (Sweep Pattern)**: Fixing infrastructure requires identifying all modules sharing a common dependency (e.g., SurrealDB) and verifying they all adhere to the updated protocol. Migrating `doc/indexer.py` and `memory/server.py` to `AsyncSurreal` restored coherence across the Compound Engineering and Physics server groups.

**Learning 160 -- Skill Documentation as a Truth Anchor**: Skills must be updated immediately after a protocol change to prevent agents from re-introducing "Shadow Bugs" by following outdated examples. A skill is only valid if it reflects the current operational reality of the substrate.

**Learning 276 -- SurrealDB 3.0 Schema Migration Patterns**: `FLEXIBLE TYPE object` was removed in SurrealDB 3.0. Nullable object fields need `TYPE none | object`; non-nullable use `TYPE object`. Live views no longer support `ORDER BY` (sort at query time instead). The surrealdb-py client returns HTTP 200 even when SurrealDB rejects a record with a schema error -- callers must check returned data, not just the status code. Rule: re-apply `genesis_schema.surql` after every SurrealDB version upgrade and verify row insertion end-to-end.

**Learning 280 -- Two Separate Persistence Graphs (Genesis vs Knowledge)**: `neurons` and `synapses` (what `compute_graph_hiho()` reads) are the vault-keeper's domain: Obsidian vault notes -> SurrealDB graph nodes via the knowledge graph ontology. `prompt_artifacts` and `universe_snapshots` (what `persist_prompt_artifact()` writes) are the genesis execution graph. These are two distinct persistence systems. Wiring L183 populates genesis tables but does NOT raise Graph HIHO -- that requires vault-keeper to run and populate `neurons`/`synapses` from vault content.

**Learning 284 -- SurrealDB CLI Path (~/.surrealdb/surreal)**: The `surreal` CLI binary lives at `~/.surrealdb/surreal`, not in `$PATH`. For schema operations use: `~/.surrealdb/surreal import --conn ws://localhost:8001 --user root --pass root --ns cohezion --db vault <file.surql>`. More reliable than Python split-execute (which can drop DEFINE TABLE statements when comment blocks precede them).

**Learning 291 -- SurrealDB Dual-Instance Topology / Port Mismatch (Session 95)**: Two SurrealDB 3.0 instances ran as systemd daemons. `cohezion-surreal.service` (system, port 8000) read `SURREAL_USER`/`SURREAL_PASS`/`SURREAL_DATA_PATH` from `.env` -- but those vars were never populated, yielding empty creds and `rocksdb://` with no data path. The user-level `surrealdb.service` (port 8001, root/root) was the actual working instance with 1,839 prompt_artifacts. CLAUDE.md and 24 source files referenced port 8000, causing `cloud-vault-mcp` health checks and agent context queries to silently fail. **Fix**: Disabled port 8000 service, updated 32 files (24 main + 8 cloud-vault-mcp) to port 8001. **Pattern**: Always verify which DB instance your application actually connects to vs which one has the data. Multiple systemd services for the same DB engine on different ports is a common source of silent failures -- use systemd template units (`surrealdb@.service`) if you genuinely need multiple instances.

**Learning 295 -- SurrealDB 3.0 SELECT VALUE for Scalar Subqueries**: `WHERE field IN (SELECT col FROM table)` returns 0 matches in SurrealDB 3.0 because `SELECT col` returns records `[{col: "val"}]`, not scalars `["val"]`. Must use `SELECT VALUE col` to get a flat array. This caused Graph HIHO's orphan ratio to falsely read 1.000 (every neuron appeared orphaned despite 5,119 synapses existing). Pattern: always use `SELECT VALUE` in `IN` subqueries. Applies to all SurrealDB 3.0+ code.

**Learning 307 -- SurrealKV + Versioned Queries for Temporal Knowledge Graphs**: Migrated from RocksDB (corrupted, read-only transaction bug) to SurrealKV with `?versioned=true`. SurrealDB 3.0 VERSION clause enables system-time-travel queries; bi-temporal fields (valid_from/valid_to) enable domain-time queries. Combined: "what did we know at time T about state at time T'?" REFERENCE keyword enables bidirectional graph traversal via `<~` tilde notation. Schema applied to neurons/synapses (vault), agent_journey (genesis), universe_node (genesis).

## VERSION
v1.1 (merged from SURREALDB_OPERATIONS_PRIME v1.0.0 + SURREAL_DBA_PRIME v1.0)

## SEE ALSO
SURREALDB_ADVANCED_PRIME, VAULT_KEEPER_PRIME, DATABASE_PRIME
