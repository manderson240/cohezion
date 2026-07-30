# Graph Engineering & Cross-Session Coordination Blueprint

*Generated via Local Silicon (Lemonade :13305) & Ollama Cloud (kimi-k2.7-code:cloud on :11434)*

---

## 1. Codebase State & Architectural Linkages
Cohezion's architecture is designed to support a wide range of applications, integrating advanced technologies such as swarm orchestration, compound execution, 1D/2D manifold encoding, and real-time visualization. The `src/cohezion/swarm/` module serves as the core of the system, enabling multi-agent teams to coordinate their actions through a centralized orchestration framework. This module is built using V-Model engineering, which allows for modular and flexible modeling of complex interactions, ensuring scalability and maintainability. The `src/cohezion/flume/` module, focused on 1D/2D manifold latent state encoding, leverages advanced neural network architectures to encode and represent latent states, which are crucial for trajectory planning and visualization. The `src/cohezion/inference/` module, integrating FleetLock and LemonadeCLIMonitor, provides a robust framework for real-time monitoring and control, enabling efficient resource management and dynamic task execution.

The `src/cohezion/data_mesh/` module acts as a bridge between the swarm and inference modules, facilitating the exchange of data and state between different components. It utilizes a Kanban-based approach to manage workflow and task dependencies, while also integrating with SurrealDB for persistent storage and retrieval of complex data structures. This integration ensures that data is consistently accessible and consistent across the system, supporting scalable and reliable data processing pipelines. The `src/cohezion/inference/` module is particularly significant as it provides a unified interface for both swarm orchestration and data processing, allowing for seamless integration of different components and enabling efficient monitoring and control of the system's behavior.

In summary, Cohezion's architecture is characterized by a modular and flexible design that supports both complex swarm orchestration and high-performance data processing. The integration of V-Model engineering, 1D/2D manifold encoding, and real-time visualization modules ensures that the system can handle diverse use cases with minimal overhead. The `data_mesh` module acts as a central hub for data management, connecting the swarm and inference components through a robust data pipeline. This structure allows for scalability, maintainability, and the ability to adapt to changing requirements, making Cohezion a versatile and powerful solution for multi-agent and real-time data-driven applications.

---

## 2. 12D Latent Manifold & Cross-Session Synchronization Protocol
# Unified Graph Engineering & Cross-Session Coordination Blueprint

## Scope
This blueprint ties together the `src/cohezion/swarm/`, `src/cohezion/flume/`, `src/cohezion/inference/`, and `src/cohezion/data_mesh/` modules. It specifies how active agent sessions are encoded as 12D latent manifolds, how those states are synchronized across daemons/workers/persistent stores, and how a graph query protocol prevents redundant decision cycles.

---

## 1. FLUME 12D Latent Vector Mapping

### 1.1 Coordinate model

A **FLUME 12D manifold vector** represents the instantaneous latent state of an active agent session. It is produced by the `src/cohezion/flume/` encoder and is designed to be:

- **Disentangled** for cross-session comparison,
- **Topologically stable** under small perturbations,
- **Compressible** into the existing 1D/2D latent canvases used for trajectory planning and visualization.

| Index | Name | Symbol | Type | Range / Unit | Semantics |
|---|---|---|---|---|---|
| 0 | Spatial X | `s_x` | continuous | workspace units | Agent’s position/focus along the primary task axis |
| 1 | Spatial Y | `s_y` | continuous | workspace units | Secondary spatial/semantic coordinate |
| 2 | Spatial Z | `s_z` | continuous | workspace units | Abstraction depth or stack layer |
| 3 | Time | `t` | scalar | epoch seconds (ms precision) | Session-relative clock; monotonic within a session |
| 4 | Intent Brane | `b_i` | continuous | `[-1, 1]` | Goal direction / active objective vector |
| 5 | Context Brane | `b_c` | continuous | `[-1, 1]` | Working memory / retrieved context load |
| 6 | Attention Brane | `b_a` | continuous | `[-1, 1]` | Saliency distribution over active stimuli |
| 7 | Affective Brane | `b_f` | continuous | `[-1, 1]` | Motivation/urgency/entropy gradient |
| 8 | Capability Brane | `b_k` | continuous | `[-1, 1]` | Tool/skill availability and confidence |
| 9 | Uncertainty Brane | `b_u` | continuous | `[0, 1]` | Epistemic uncertainty / entropy |
| 10 | Session Boundary Brane | `b_s` | continuous | `{0, 1}`-weighted | Foreground vs. background daemon state |
| 11 | Lineage Brane | `b_l` | continuous | hash-derived | Cross-session ancestry fingerprint |

**Notation:**  
`v = ⟨s_x, s_y, s_z, t, b_i, b_c, b_a, b_f, b_k, b_u, b_s, b_l⟩`

### 1.2 Encoding pipeline

```
Raw telemetry & intent trace
        ↓
[FLUME 1D Manifold Ordering]   ← sorts dimensions by invariant importance
        ↓
[FLUME 2D Latent Canvas]       ← UMAP/t-SNE/SOM projection for visualization
        ↓
[12D Latent Vector]            ← canonical session state
        ↓
Trajectory buffer + SurrealDB graph node + Obsidian frontmatter
```

### 1.3 Normalization and metrics

- Spatial dimensions are normalized to the active workspace bounding box.
- Brane dimensions are z-scored per agent team, then clipped to `[-1, 1]`.
- Session similarity uses a **brane-weighted cosine**:

```
sim(v1, v2) = cos(v1, v2) + Σ(w_b · |b1 - b2| penalty)
```

Default brane weights: `intent 0.30, context 0.25, lineage 0.20, uncertainty 0.15, attention 0.10`.

---

## 2. Cross-Session Event Bus Synchronization

### 2.1 Bus topology

The `src/cohezion/data_mesh/` module operates a **Kanban-style event bus**. All participants are either **producers**, **consumers**, or **persistent sinks**.

| Participant | Role | Topics subscribed / published |
|---|---|---|
| Active daemons (`swarm/`) | Producer/Consumer | `flume.<session>.state`, `swarm.<team>.command`, `meta.checkpoint` |
| Background workers (`inference/`) | Consumer/Producer | `inference.<worker>.result`, `flume.<session>.state` |
| FleetLock | Coordinator | `meta.lock.grant`, `meta.lock.release` |
| LemonadeCLIMonitor | Observer | `meta.health`, `meta.load` |
| SurrealDB `:8001` | Authoritative graph/time-series sink | All topics |
| Obsidian Vault `~/vaults/cohezion-vault/` | Human-readable shadow | `meta.session.note`, `meta.decision.log` |

### 2.2 Event envelope schema

Every bus message is wrapped in a canonical envelope:

```json
{
  "event_id": "uuidv7",
  "session_id": "sess_abc123",
  "trace_id": "trace_xyz789",
  "vector_state": {
    "hash": "sha256:...",
    "v": [0.12, -0.05, 0.88, 1715000000.123, 0.71, -0.22, 0.55, 0.80, -0.10, 0.15, 0.00, 0.94]
  },
  "timestamp": "2025-05-06T14:23:01.123Z",
  "event_type": "DECISION_CANDIDATE",
  "provenance": "swarm/agent-7",
  "payload": { ... },
  "idempotency_key": "sess_abc123:DECISION_CANDIDATE:1715000000123",
  "vector_clock": {
    "agent-7": 14,
    "inference-3": 9
  },
  "checksum": "sha256:..."
}
```

### 2.3 Synchronization rules

1. **Delivery guarantee:** at-least-once with idempotency-key deduplication at the SurrealDB sink.
2. **Ordering:** per-`session_id` FIFO; cross-session events may be partial-ordered by vector clock.
3. **Checkpointing:** background workers write a `meta.checkpoint` watermark every 1000 events or 30 seconds, whichever comes first.
4. **Conflict resolution:** monotonic vector-clock wins; if vector clocks are incomparable, the higher `t` dimension wins, then lower `b_u`.
5. **Retention:** raw events retained 7 days; materialized graph decisions retained indefinitely; 2D canvas frames retained 30 days.

### 2.4 Dual-write persistence flow

```text
Daemon / Worker
       │
       ▼
[data_mesh Kanban bus]
       │
       ├─► SurrealDB :8001 (graph + record of truth)
       │
       └─► Obsidian Adapter ──► ~/vaults/cohezion-vault/
              ├── daily notes
              ├── atomic session notes
              └── decision logs
```

#### SurrealDB graph model

```sql
DEFINE TABLE session TYPE NODE;
DEFINE TABLE decision TYPE NODE;
DEFINE TABLE action TYPE NODE;
DEFINE TABLE artifact TYPE NODE;

DEFINE EDGE caused;
DEFINE EDGE replaced;
DEFINE EDGE depends_on;
DEFINE EDGE derived_from;
DEFINE EDGE continues_in;
```

#### Obsidian Vault schema

Each atomic note uses YAML frontmatter:

```yaml
---
session_id: sess_abc123
trace_id: trace_xyz789
vector_hash: sha256:...
event_type: DECISION_CANDIDATE
timestamp: 2025-05-06T14:23:01.123Z
tags: [decision, swarm, agent-7]
status: active   # active | superseded | stale
---
```

Links use Obsidian double-bracket syntax:

```markdown
- Continues from: [[sess_abc122]]
- Caused action: [[action_deploy_flume]]
- Supersedes: [[decision_sess_abc120]]
```

### 2.5 Coordination primitives

- **FleetLock:** grants short-lived session leases (default 10s, renewable). A daemon must hold the lease for a `session_id` before emitting state-changing events.
- **LemonadeCLIMonitor:** publishes `meta.health` events. If a daemon fails to heartbeat, FleetLock releases its leases and `data_mesh` reroutes the session to a standby worker.

---

## 3. Graph Query Protocol for Decision Retrieval & Duplicate Prevention

### 3.1 Graph ontology

| Node | Fields |
|---|---|
| `session` | `session_id`, `vector_hash`, `created_at`, `closed_at`, `agent_team` |
| `decision` | `decision_id`, `intent_fingerprint`, `decision_signature`, `vector_hash`, `status`, `valid_from`, `valid_until` |
| `action` | `action_id`, `kind`, `payload_hash`, `executed_at` |
| `artifact` | `artifact_id`, `uri`, `checksum` |

| Edge | Meaning |
|---|---|
| `caused` | `decision → action` |
| `replaced` | `new_decision → old_decision` |
| `depends_on` | `decision/artifact → decision/artifact` |
| `derived_from` | `decision → prior_session` |
| `continues_in` | `old_session → new_session` |

### 3.2 Query protocol message

```json
{
  "protocol": "COHEZION_GRAPH_QUERY_v1",
  "session_id": "sess_abc123",
  "intent_fingerprint": "sha256:<intent_hash>",
  "context_hash": "sha256:<context_hash>",
  "time_horizon_hours": 168,
  "similarity_threshold": 0.92,
  "include_superseded": false,
  "max_depth": 5,
  "response_format": "decision_tree|cycle_report|latest_only"
}
```

### 3.3 Duplicate-work prevention algorithm

For every new candidate decision:

```
1. Compute decision_signature = H(intent_fingerprint + context_hash + active_tool_set)

2. Query SurrealDB:
   - MATCH decisions WHERE signature = decision_signature
   - FILTER status IN ['active', 'committed']
   - FILTER valid_until IS NULL OR valid_until > now()
   - FILTER vector.similarity(v, candidate_v) >= threshold

3. If match found:
   - Return existing decision_id, action references, and lineage path.
   - Do NOT schedule duplicate work.
   - Optionally emit `DECISION_REDIRECTED` event.

4. If no match or superseded:
   - Insert new decision node.
   - Link depends_on / derived_from edges.
   - Proceed to execution.
```

### 3.4 SurrealQL query examples

**Retrieve past decisions for a session up to 5 hops:**

```sql
SELECT * FROM decision
WHERE <-continues_in<-session<-session_id = "sess_abc123"
   OR ->depends_on->decision
   OR ->derived_from->decision
DEPTH 5;
```

**Find active duplicate by signature:**

```sql
SELECT *, vector::similarity(v, $candidate_v) AS sim
FROM decision
WHERE decision_signature = $signature
  AND status IN ['active', 'committed']
  AND (valid_until IS NONE OR valid_until > time::now())
  AND sim >= 0.92;
```

**Detect duplicate-work loop (cycle) across sessions:**

```sql
SELECT path FROM (
  SELECT * FROM session:sess_abc123
  ->continues_in->session
  ->continues_in->session
  ->continues_in->session
) WHERE path IS NOT NONE;
```

Or, for explicit cycle detection in a stored function:

```sql
DEFINE FUNCTION fn::detect_loop($root: string, $depth: number) {
  RETURN (
    SELECT count() AS cycle_count FROM (
      SELECT * FROM session:$root ->continues_in->session
      WHERE session_id = $root DEPTH $depth
    )
  );
};
```

### 3.5 Obsidian backlink integration

The Obsidian adapter maintains a shadow graph. The query protocol can also call:

```bash
cohezion-vault-query --session sess_abc123 --tag decision --backlinks
```

This returns a local Markdown link graph. The bus then reconciles Obsidian links against SurrealDB edges on startup and after every checkpoint.

---

## 4. Operational checklist

| Concern | Rule |
|---|---|
| **State consistency** | SurrealDB is authoritative; Obsidian is read-only shadow. |
| **Idempotency** | All state-changing events carry `idempotency_key`. |
| **Ordering** | Per-session FIFO; cross-session partial order via vector clock. |
| **Failure recovery** | FleetLock releases stale leases; workers replay from last checkpoint. |
| **Duplicate prevention** | Decision signatures + vector similarity + validity window. |
| **Human inspectability** | Every decision and session has an Obsidian note with frontmatter and backlinks. |

---

## 5. Reference integration map

```text
┌─────────────────────────────────────────────────────────────┐
│                    cohezion.data_mesh                         │
│                 (Kanban Event Bus)                          │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
   ┌───────────▼──────────┐      ┌────────────▼────────────┐
   │  src/cohezion/swarm/ │      │ src/cohezion/inference/ │
   │  V-Model orchestration│      │ FleetLock + LemonadeCLI │
   └───────────┬──────────┘      └────────────┬────────────┘
               │                              │
   ┌───────────▼──────────┐      ┌────────────▼────────────┐
   │ src/cohezion/flume/  │      │   SurrealDB :8001       │
   │ 12D manifold encoder │      │   graph + time-series   │
   └───────────┬──────────┘      └────────────┬────────────┘
               │                              │
               └──────────────┬───────────────┘
                              │
                  ┌───────────▼────────────┐
                  │ Obsidian Vault Adapter │
                  │ ~/vaults/cohezion-vault/│
                  └────────────────────────┘
```

---

This blueprint provides the canonical encoding, synchronization contract, and query semantics needed to keep active sessions, background workers, and persistent graph stores aligned while preventing redundant decision cycles.
