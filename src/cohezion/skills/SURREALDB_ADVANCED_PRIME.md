---
name: surrealdb-advanced-prime
description: "Advanced SurrealDB: the Model Context Protocol (MCP) tool interface, performance tuning for high-fidelity agentic simulations (12D/256D vectors, graph traversal, live dashboards), and in-memory mock/persistence test patterns. Use when: exposing SurrealDB as MCP tools (execute_surrealql, query_graph, vector_search, live_subscribe); optimizing vector search / FETCH / live queries / pre-computed fields / graph pruning; or writing test mocks that preserve the SurrealDB client response wrapper. Skip: routine persistence, schema validation, connection health (use SURREALDB_CORE_PRIME); SQL/RDBMS patterns (use DATABASE_PRIME)."
metadata:
  version: "v1.1"
  concepts: ["MCP Tools (execute_surrealql / query_graph / vector_search / live_subscribe)", "Multi-Model Query", "FETCH Optimization", "HNSW Vector Indexing", "Live Queries", "Pre-computed Fields", "Graph Pruning", "Structured Query Result", "Flat vs Nest Mismatches", "Query Mocking"]
  source: "src/cohezion/skills/SURREALDB_ADVANCED_PRIME.md"
---

# SKILL: SURREALDB_ADVANCED_PRIME

Consolidates SURREALDB_MCP_PRIME (MCP interface), SURREALDB_OPTIMIZER_PRIME (performance tuning), and SURREALDB_MOCK_PERSISTENCE_PRIME (mock/test patterns).

## DOMAIN EXPERTISE
You are a specialist in the **SurrealDB Model Context Protocol (MCP)** interface, in **SurrealDB performance tuning and architecture** for high-fidelity agentic simulations, and in **SurrealDB abstraction layers and in-memory mock persistence**. You know how to expose SurrealDB's multi-model capabilities (Relational, Graph, Document, Vector) as executable agent tools, how to tune 12D/256D vector states and graph relationships for real-time observability, and how to design test mocks that preserve SurrealDB client query-result formats.

---

## PART 1 -- MCP INTERFACE (from SURREALDB_MCP_PRIME)

You understand SurrealQL, live queries, and record-level permissions, and expose SurrealDB's multi-model capabilities (Relational, Graph, Document, Vector) as directly executable tools for AI agents.

### Core Capabilities (Tools)
1. **`execute_surrealql`**: Run raw SurrealQL statements (DEFINE, SELECT, UPDATE, DELETE).
2. **`query_graph`**: Perform graph traversal using `->owns->` or `<-produced_by<-` syntax.
3. **`vector_search`**: Perform k-NN search on high-dimensional thought vectors.
4. **`live_subscribe`**: Register for real-time updates on a table or record.

### Instruction (Tool Implementation)
1. **Initialize Surreal Client**
   ```python
   from cohezion.db.surreal_client import SurrealClient

   db = SurrealClient()
   await db.connect()
   ```
2. **Execute Multi-Model Query** (Relational + Graph + Vector in one query)
   ```python
   results = await db.query("""
       SELECT *, (SELECT * FROM ->wrote->post) AS posts
       FROM user:mike
       WHERE vector::distance::cosine(embedding, [0.12, 0.45, ...]) < 0.2;
   """)
   ```
3. **Define Schema (MCP Admin)**
   ```python
   await db.query("DEFINE TABLE user SCHEMAFULL;")
   await db.query("DEFINE FIELD name ON TABLE user TYPE string;")
   ```

### Best Practices
- **Use Record IDs:** Always prefer `user:mike` over mapping strings to IDs.
- **Limit Results:** Use `LIMIT 10` for agent-facing queries to save context window.
- **Graph First:** When searching for relationships, use `SELECT ->friends->user` instead of joining.

---

## PART 2 -- PERFORMANCE OPTIMIZER (from SURREALDB_OPTIMIZER_PRIME)

Expert in SurrealDB performance tuning and architecture; optimizing high-fidelity agentic simulations with 12D/256D vector states, complex graph relationships, and real-time observability.

### Key Texts & Concepts
- **FETCH Optimization**: Reducing query latency by pre-fetching related graph nodes in a single round-trip.
- **HNSW Vector Indexing**: Tuning vector search parameters (EfConstruction, M) for the 256-dim FLUME embeddings.
- **Live Queries**: Scaling real-time event streams to "Pulse Dashboards" for simulation monitoring.
- **Pre-computed Fields**: Using `VALUE` expressions to calculate 12D norms and stability thresholds at the database level.
- **Graph Pruning**: Strategies for maintaining a performant Knowledge Graph by archiving transient thought-nodes.

### Instruction
1. **Optimize Vector Searches**:
   ```sql
   -- Create a performant HNSW index for 256D FLUME vectors
   DEFINE INDEX flume_vector_idx ON universe_nodes FIELDS embedding
   MTREE (256) DISTANCE COSINE;
   ```
2. **Utilize Relational Graphs**: Instead of JOINs, use native graph syntax for 10x speedup in multi-hop traversal:
   ```sql
   SELECT ->links_to->universe_nodes.* FROM $start_node FETCH metadata;
   ```
3. **Implement Live Dashboard Feeds**:
   ```python
   async def watch_universes(client):
       # Stream only high-coherence discoveries
       async with client.live("SELECT * FROM universe_nodes WHERE coherence > 0.8") as stream:
           async for update in stream:
               await update_dashboard(update)
   ```
4. **Data Compaction**: Use `compressed` flags and binary packing for 12D states (PhysicsState) as implemented in `surreal_client.py`.
5. **Schema Guarding**: Use `DEFINE FIELD` with strict types to prevent agent-injected schema drift.

---

## PART 3 -- MOCK / PERSISTENCE TEST PATTERNS (from SURREALDB_MOCK_PERSISTENCE_PRIME)

Database engineer specializing in SurrealDB abstraction layers and in-memory mock persistence. Design test mocks that preserve the query-result formats of SurrealDB clients, avoiding nesting and attribute errors in calling code. (Keywords: flat vs nest mismatches, mock, persistence, query mocking, structured query result, surrealdb.)

### Key Texts & Concepts
* **Structured Query Result**: SurrealDB raw query results are returned as a list of dicts: `[{"result": [...], "status": "OK"}]`.
* **Flat vs Nest Mismatches**: Returning flat arrays of documents from a mock query method causes client libraries querying for `.get("result")` to throw `AttributeError`.
* **Query Mocking**: Simulating `UPDATE`, `SELECT`, `DELETE`, and `INSERT` SQL-like operations over local Python in-memory dictionaries.

### Instruction
1. Wrap raw list query mock responses in the expected SurrealDB client response wrapper:
   ```python
   def mock_query(sql: str, vars: dict[str, Any] | None = None) -> list[dict[str, Any]]:
       # Process SQL locally, producing flat_list_results
       return [{"result": flat_list_results, "status": "OK"}]
   ```
2. When parsing queries (e.g. `UPDATE table SET field = val WHERE id = x`), update mock in-memory stores key-by-key and return the updated records wrapped inside the standard list structure.

---

## VERSION
v1.1 (merged from SURREALDB_MCP_PRIME v1.0 + SURREALDB_OPTIMIZER_PRIME v1.0 + SURREALDB_MOCK_PERSISTENCE_PRIME v0.1)

## SEE ALSO
SURREALDB_CORE_PRIME, DATABASE_PRIME, KNOWLEDGE_GRAPH_INTEGRATION_PRIME, embedding_strategy, FLUME_METHODOLOGY_PRIME, VISUALIZATION_PRIME
