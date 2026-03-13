---
title: SurrealDB Sync Pattern
date: 2026-02-23
tags: [pattern, surrealdb, database, architecture]
status: active
aspect: knower
neural:
  activation: 0.94
  stage: mature
  synapse_in: 10
  synapse_out: 13
---

# SurrealDB Sync Pattern

The SurrealDB sync pattern defines a reliable strategy for synchronizing agent context data from in-memory or file-based state into [[surrealdb]] as a persistent graph database. It addresses three core challenges: batching writes for throughput, resolving conflicts when multiple agents write concurrently, and maintaining graph consistency across nodes and edges (RELATE records).

In a typical Cohezion deployment, agent sessions produce a stream of context events — task completions, decisions, observations, concept references. These events are buffered in memory during the session and flushed to SurrealDB in batches at session boundaries or on a configurable interval. The pattern uses SurrealDB's UPSERT semantics and RELATE syntax to ensure idempotent writes: re-syncing the same data produces the same graph state without duplicating nodes or edges.

Conflict resolution follows a last-writer-wins strategy with timestamp ordering. When two agents update the same record concurrently, the write with the later timestamp prevails. For graph edges (RELATE records), the pattern uses composite keys (source + target + relation type) so that duplicate relationship creation is naturally deduplicated.

## Key Properties

- **Batched writes** — Events are buffered and flushed in configurable batch sizes (default: 50 records) to amortise network round-trip costs and reduce write amplification
- **Idempotent UPSERT** — All writes use SurrealDB's UPSERT (or INSERT ... ON DUPLICATE KEY UPDATE) to safely re-run sync without creating duplicates
- **Graph consistency via RELATE** — Edges between nodes use SurrealDB's RELATE syntax with composite keys, ensuring relationship integrity even under concurrent writes
- **Conflict resolution** — Last-writer-wins with monotonic timestamps; each record carries an `updated_at` field used for ordering
- **Failure recovery** — Failed batches are retried with exponential backoff; after max retries, events are persisted to a local dead-letter file for manual replay

## Examples

- **Session close sync** — When an agent session ends, all accumulated context (tasks, decisions, observations) is flushed to SurrealDB in a single batched transaction
- **Periodic heartbeat sync** — Long-running sessions flush accumulated events every 60 seconds to prevent data loss if the session crashes
- **Cross-session deduplication** — Two agents referencing the same concept node produce UPSERT operations that converge to a single node with merged metadata

## Primary Sources

- SurrealDB documentation: RELATE statement — https://surrealdb.com/docs/surrealql/statements/relate
- SurrealDB documentation: UPSERT statement — https://surrealdb.com/docs/surrealql/statements/upsert

## Related

- [[lesson-05-surrealdb]]
- [[lesson-surrealdb-schema-design]]
- [[surrealdb]] — the database this sync pattern targets, using RELATE syntax for graph consistency
- [[graph-databases]] — sync pattern addresses the graph consistency challenges inherent in graph database operations
- [[agent-context]] — the primary data synchronized via this pattern is agent context (sessions, tasks, decisions)
- [[surrealdb-graph-databases]] — research paper on SurrealDB's graph database capabilities; this sync pattern is the production implementation of the graph consistency strategies discussed there
- [[graphrag-knowledge-graph-with-surrealdb]] — the GraphRAG system relies on consistent sync to maintain graph integrity
- [[knowledge-graph-systems]] — knowledge graph consistency depends on reliable synchronization patterns

## Related Concepts

- [[event-driven-daemon-pattern]] — the sync worker operates as an event-driven daemon, triggering flushes on session events rather than polling
- [[error-handling-with-dlq]] — failed sync batches follow the DLQ pattern for deferred retry
- [[safe-persistent-storage-lifecycle]] — the sync pattern implements the "write with validation" phase of the storage lifecycle
- [[api-design]] — the sync batch protocol defines a contract between agent sessions and the database layer
- [[non-blocking-observability]] — sync operations emit metrics (batch size, latency, failures) without blocking the agent event loop

## Relevance to Cohezion

The SurrealDB sync pattern is the primary mechanism by which Cohezion agent sessions persist their work to the shared knowledge graph. Without reliable sync, the [[graphrag-knowledge-graph-with-surrealdb]] system would have inconsistent data, and cross-session queries would return stale or incomplete results. The pattern was designed after early lessons with SurrealDB (documented in [[lesson-05-surrealdb]]) revealed that naive per-event writes caused unacceptable latency and occasional graph corruption under concurrent agent load.
