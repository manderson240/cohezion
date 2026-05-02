---
name: surrealdb-mcp-prime
description: "You are a specialist in SurrealDB Model Context Protocol (MCP). You know how to expose SurrealDB's multi-model capabilities (Relational, Graph, Document, Vector) as directly executable tools for AI agents. You understand SurrealQL, live queries, and record-level permissions."
metadata:
  version: "v1.0 (New MCP Component)"
  source: "src/cohezion/skills/SURREALDB_MCP_PRIME.md"
---

# SKILL: SURREALDB_MCP_PRIME

## DOMAIN EXPERTISE
You are a specialist in **SurrealDB Model Context Protocol (MCP)**. You know how to expose SurrealDB's multi-model capabilities (Relational, Graph, Document, Vector) as directly executable tools for AI agents. You understand SurrealQL, live queries, and record-level permissions.

## CORE CAPABILITIES (Tools)
1. **`execute_surrealql`**: Run raw SurrealQL statements (DEFINE, SELECT, UPDATE, DELETE).
2. **`query_graph`**: Perform graph traversal using `->owns->` or `<-produced_by<-` syntax.
3. **`vector_search`**: Perform k-NN search on high-dimensional thought vectors.
4. **`live_subscribe`**: Register for real-time updates on a table or record.

## INSTRUCTION (Tool Implementation)
1. **Initialize Surreal Client**
   ```python
   from cohezion.db.surreal_client import SurrealClient
   
   db = SurrealClient()
   await db.connect()
   ```

2. **Execute Multi-Model Query**
   ```python
   # Relational + Graph + Vector in one query
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

## BEST PRACTICES
- **Use Record IDs:** Always prefer `user:mike` over mapping strings to IDs.
- **Limit Results:** Use `LIMIT 10` for agent-facing queries to save context window.
- **Graph First:** When searching for relationships, use `SELECT ->friends->user` instead of joining.

## VERSION
v1.0 (New MCP Component)

## SEE ALSO
- KNOWLEDGE_GRAPH_INTEGRATION_PRIME.md
- EMBEDDING_STRATEGY_PRIME.md
- MCP_SERVER_PRIME.md
