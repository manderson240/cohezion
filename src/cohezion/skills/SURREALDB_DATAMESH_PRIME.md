# SKILL: SURREALDB_DATAMESH_PRIME

## DOMAIN EXPERTISE
Durable Distributed State Management, High-Performance Graph Traversals, and HNSW Vector Search across Multi-Agent Swarms using SurrealDB 3.x and the Cohezion Obsidian Vault. Specializes in dual-persistence DataMesh architectures that guarantee agent session memory, cross-session event bridges, and unbreakable audit trails.

## KEY TEXTS & CONCEPTS
* **Official SurrealDB 3.x Skill Integration**:
  - `surrealql-performance`: Record ID design for locality, composite indexes (`DEFINE INDEX ... ON TABLE ... FIELDS ...`), and query plan auditing with `EXPLAIN`.
  - `surrealdb-vector`: Native HNSW indexing (`DIST COSINE TYPE F32`) and KNN similarity querying (`<|10, 40|>`).
  - `surrealql`: Graph traversals (`->produced->`, `->verified_by->`) and atomic transactional mutations.
  - `surrealkit`: Automated schema migrations, type generation, and declarative schema synchronization.
  - `surrealdb-python`: Native async Python SDK v1.0+ connection pooling and live query subscriptions.
* **DataMesh Dual Persistence**:
  - Every significant finding, retrospective, or milestone is simultaneously written to SurrealDB tables (`kanban_item`, `event_log`, `learning`) and the Obsidian Vault (`~/vaults/cohezion-vault/kanban/`, `01-Learnings/`).
  - Guarantees data durability across host reboots, process restarts, or OOM crashes.
* **EventBus & CrossSessionEventBridge**:
  - Real-time typed event distribution (`EventType.AGENT_COMPLETE`, `EventType.SYSTEM_HEALTH`) enabling asynchronous coordination between GAIA agents, Antigravity, and Claude sessions.
* **Preexisting Condition Logging**:
  - Formal mandate to log discovered technical debt, test flakes, or memory leaks directly to `kanban_bridge.persist_item()` instead of losing them in chat transcripts.

## INSTRUCTION

1. **Dual-Persist Mission Cards to DataMesh**:
   Use `persist_item()` to record task cards to both SurrealDB and Obsidian markdown simultaneously:
   ```python
   from cohezion.data_mesh.kanban_bridge import persist_item

   persist_item({
       "id": "strix_halo_memory_stabilization",
       "title": "Strix Halo UMA Aperture Stabilized at 29.67 GB",
       "status": "done",
       "priority": "high",
       "source": "gaia_evaluator",
       "category": "hardware_safety",
       "details": "Cleared spinning ROCm process; GTT reduced to 32.2 GB; RAM recovered.",
   })
   ```

2. **Publish Typed Events via EventBus Bridge**:
   Broadcast events across sessions so peer agents can immediately react:
   ```python
   import asyncio
   from cohezion.core.event_bus import Event, EventType, get_event_bus
   from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge

   async def broadcast_metric(score: float, model: str):
       bus = await get_event_bus()
       bridge = CrossSessionEventBridge(event_bus=bus, session_id="gaia-agent-loop")
       await bridge.initialize()
       event = Event(
           type=EventType.AGENT_COMPLETE,
           source="gaia_strix_evaluator",
           priority=10,
           payload={"model": model, "metric": score},
       )
       await bus.publish(event)

   asyncio.run(broadcast_metric(0.939, "Bonsai-8B-gguf"))
   ```

3. **Query Semantic Graph & Vector Memory in SurrealQL**:
   Execute graph traversals and HNSW vector searches:
   ```sql
   -- Find all skills and verifiers connected to an active competition
   SELECT ->verified_by->harness.* AS verifiers,
          ->utilized_by->agent.* AS agents
   FROM competition:arc_agi_2;

   -- Search previous learnings via 256D/2048D vector similarity
   SELECT title, key_insight, vector::similarity::cosine(embedding, $query_vec) AS score
   FROM learning
   WHERE embedding <|5, 40|> $query_vec
   ORDER BY score DESC;
   ```

4. **Synchronize Retrospectives to the Obsidian Vault**:
   Format retrospectives as durable Markdown in `~/vaults/cohezion-vault/retros/` to ensure full human and agent readability.

## VERSION
v1.0

## SEE ALSO
- `AMD_GAIA_ORCHESTRATION_PRIME.md`
- `AUTOHARNESS_PRIME.md`
- `VAULT_KEEPER_PRIME.md`
- `COMPOUND_ENGINEERING_PRIME.md`
