# SKILL: SURREALDB_OPTIMIZER_PRIME

## DOMAIN EXPERTISE
Expert in **SurrealDB performance tuning and architecture**. Specializes in optimizing high-fidelity agentic simulations with 12D/256D vector states, complex graph relationships, and real-time observability.

## KEY TEXTS & CONCEPTS
- **FETCH Optimization**: Reducing query latency by pre-fetching related graph nodes in a single round-trip.
- **HNSW Vector Indexing**: Tuning vector search parameters (EfConstruction, M) for the 256-dim FLUME embeddings.
- **Live Queries**: Scaling real-time event streams to "Pulse Dashboards" for simulation monitoring.
- **Pre-computed Fields**: Using `VALUE` expressions to calculate 12D norms and stability thresholds at the database level.
- **Graph Pruning**: Strategies for maintaining a performant Knowledge Graph by archiving transient thought-nodes.

## INSTRUCTION

1. **Optimize Vector Searches**:
   ```sql
   -- Create a performant HNSW index for 256D FLUME vectors
   DEFINE INDEX flume_vector_idx ON universe_nodes FIELDS embedding
   MTREE (256) DISTANCE COSINE;
   ```
2. **Utilize Relational Graphs**:
   Instead of JOINs, use the native graph syntax for 10x speedup in multi-hop traversal:
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
4. **Data Compaction**:
   Use `compressed` flags and binary packing for 12D states (PhysicsState) as implemented in `surreal_client.py`.
5. **Schema Guarding**:
   Use `DEFINE FIELD` with strict types to prevent agent-injected schema drift.

## VERSION
v1.0

## SEE ALSO
DATABASE_PRIME, FLUME_PRIME, VISUALIZATION_PRIME
