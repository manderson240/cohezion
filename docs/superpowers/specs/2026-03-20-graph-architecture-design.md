# Cohezion Graph Architecture — Intelligence Density First

**Date:** 2026-03-20
**Status:** Approved
**Authors:** Mike Anderson + Claude Code

---

## 1. Problem Statement

The vault's SurrealDB graph is a latent asset that isn't delivering value:

- **Agents** have no token-efficient path to graph context at session start
- **Humans** query the graph with ad-hoc `urllib` HTTP calls (`scripts/graph_context.py`) that bypass the SDK
- **The 12D visualization plan** (ADR `2026-02-09-12d-graph-refined-plan.md`) is stalled because it has no stable query foundation
- **Compound engineering** — agents leaving trails that future agents inherit — is architecturally impossible today

This spec establishes the canonical graph layer that unblocks all three.

---

## 2. Goals

1. **Token-efficient context** — agents get graph orientation in <300 tokens, pre-computed, zero query cost at session start
2. **Canonical query layer** — one place where graph logic lives (SurrealDB stored functions), thin wrappers everywhere else
3. **Agentic trails** — agents write `latent` and `dream` synapses + metadata annotations; future agents inherit that signal
4. **12D plugin foundation** — `dim_*` fields on neurons ready for the visualization layer to consume
5. **Leverage existing tools** — use SurrealDB Labs components instead of building from scratch

---

## 3. Non-Goals

- Rewriting the Obsidian plugin (that's a separate /spec)
- Building a new auth/security layer for SurrealDB
- Replacing the sync daemon's structural write responsibility
- Full FLUME VAE training pipeline (Phase B uses PCA projection, not full VAE)

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   CONSUMERS                                  │
│  Claude Code session  │  MCP tools  │  CLI (graph_context)  │
└───────────┬───────────┴──────┬──────┴──────────┬────────────┘
            │                  │                  │
            ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│              INTELLIGENCE LAYER (canonical)                  │
│  metabolism/graph-briefing.md  ←  GraphReactor pre-computes │
│  fn::context_neighborhood      ←  SurrealDB stored functions │
│  fn::context_search            │                            │
│  fn::context_cluster           │                            │
│  fn::context_bridges           │                            │
│  fn::vault_stats               │                            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   SURREALDB (rocksdb)                        │
│  neuron { dim_bridging, dim_completion, dim_recency,        │
│            dim_agent_affinity (Phase B) }                   │
│  synapse { type: explicit | latent | dream }                │
└─────────────────────────────────────────────────────────────┘
```

**Key principle:** The stored functions in `scripts/dba/context_functions.surql` are the single source of truth for graph logic. MCP tools and CLI are thin I/O wrappers only.

---

## 5. Write Boundary (Agent vs. Daemon)

| What | Owner | Why |
|------|-------|-----|
| `neuron` CRUD (create, update title/tags) | sync daemon | Structural integrity, mirrors vault file state |
| `synapse` with `type: explicit` | sync daemon | Mirrors Obsidian wiki-links |
| `synapse` with `type: latent` | agents (via MCP tool) | Semantic inference, not structural |
| `synapse` with `type: dream` | agents (via MCP tool) | Cross-domain resonance (SurrealDB `dreaming/` layer) |
| `neuron.dim_agent_affinity` (12D vector) | agents (via MCP tool) | FLUME latent projection of session embedding |
| `neuron.metadata` annotations | agents (via MCP tool) | `last_accessed`, `access_count`, `agent_notes` |

Agents never overwrite structural fields. The event-sourced upgrade path (append-only `agent_event` table) is deferred to a future spec.

---

## 6. Implementation Phases

### Phase A — Foundation (Week 1)

**Goal:** Every agent session gets pre-computed dimensional context at near-zero token cost.

#### A1: SDK Migration

Replace `urllib` HTTP calls in `scripts/graph_context.py` with `surrealdb.py` SDK.

- Install: `uv add surrealdb` in `cloud-vault-mcp`
- Connection: reuse existing `SURREALDB_URL`, `SURREALDB_USERNAME`, `SURREALDB_PASSWORD` env vars
- Keep existing CLI surface (`briefing`, `neighborhood`, `search`, etc.) — only internals change
- Error handling: raise `GraphQueryError` with the original SurrealDB error message; let callers decide retry logic

#### A2: Schema Dimensions

Add three dimension fields to the `neuron` table (migration via `surrealdb-migrations`):

```surql
DEFINE FIELD dim_bridging   ON neuron TYPE option<float>;  -- betweenness centrality 0-1
DEFINE FIELD dim_completion ON neuron TYPE option<float>;  -- note completeness score 0-1
DEFINE FIELD dim_recency    ON neuron TYPE option<float>;  -- recency decay 0-1
```

Computation:
- `dim_bridging`: run betweenness centrality on synapse graph; normalize 0-1
- `dim_completion`: word count + frontmatter completeness heuristic; normalize 0-1
- `dim_recency`: `exp(-λ * days_since_modified)` with λ = 0.05 (half-life ~14 days)

GraphReactor computes these on file-change events and writes them via `surrealdb.py`.

#### A3: GraphReactor Expansion

Extend `scripts/graph_reactor.py` to write dimensional aggregates into `metabolism/graph-briefing.md` on each change cycle.

Briefing template (~275 tokens):

```markdown
## Graph State — {date}

**Vault:** {neuron_count} neurons · {synapse_count} synapses

**Hot neurons** (high bridging):
{top_5_bridging_neurons_with_titles}

**Bridges** (connect otherwise-disconnected clusters):
{top_3_bridge_neurons}

**Completion gaps** (low dim_completion, high dim_bridging):
{top_3_stubs_worth_fleshing_out}

**Recent activity** (high dim_recency):
{top_5_recently_modified}
```

The per-prompt hook (`scripts/hooks/graph_context_hook.py`) already injects this file. No hook changes needed in Phase A.

#### A4: Official SurrealDB MCP Server

Register `nsxdavid/surrealdb-mcp-server` as a second MCP server in `~/.claude/mcp.json`.

> **Package name:** The npm package name must be confirmed before implementation — try `npx -y surrealdb-mcp-server` and fall back to `npx -y github:nsxdavid/surrealdb-mcp-server` if the npm registry name differs.

```json
"surrealdb": {
  "command": "npx",
  "args": ["-y", "surrealdb-mcp-server"],
  "env": {
    "SURREALDB_URL": "http://localhost:8001",
    "SURREALDB_USER": "sdb_admin_session43",
    "SURREALDB_PASS": "<from service file>",
    "SURREALDB_NS": "cohezion",
    "SURREALDB_DB": "vault"
  }
}
```

This gives Claude Code direct SurrealQL execution capability without custom code.

---

### Phase B — Compound Trails (Week 2)

**Goal:** Agents leave a latent affinity signal that future agents inherit, creating compounding intelligence.

#### B1: FLUME Affinity Pipeline

For each agent session, compute `dim_agent_affinity` (12D vector):

```
session_text → nomic-embed-text (768D) → PCA projection (12D) → store on accessed neurons
```

- Use Ollama's `nomic-embed-text` model (already in vault stack)
- PCA matrix: pre-computed from existing neuron corpus, stored in `scripts/dba/pca_matrix.npy`
- PCA refit trigger: when neuron count grows by >10% since last fit
- Write path: `vault_graph.write_agent_affinity(neuron_id, vec_12d)` → `UPDATE neuron SET dim_agent_affinity = $vec WHERE id = $id`

**Critical constraint from ADR `2026-02-23-hash-based-journey-tracking`:** hash-based approach is rejected. Only embedding-based projection is canonical.

#### B2: Hook Enrichment

Extend `metabolism/graph-briefing.md` to include affinity signal:

```markdown
**Agent trails** (neurons with high agent affinity in this domain):
{top_3_by_dim_agent_affinity_cosine_similarity_to_current_session}
```

The hook now provides ~350 tokens total — still well within the target budget.

#### B3: Agent-Write MCP Tools

Add four tools to the existing `cloud-vault-mcp` server. These tool stubs call `scripts/graph_context.py` (pre-extraction) and are rewired to `vault_graph/` when Phase C completes — this is an explicit two-step, not a contradiction.

| Tool | Description |
|------|-------------|
| `graph_write_latent_synapse` | Create `type: latent` synapse between two neurons |
| `graph_write_dream_synapse` | Create `type: dream` synapse (cross-domain resonance) |
| `graph_write_affinity` | Write 12D affinity vector to neuron |
| `graph_annotate_neuron` | Write metadata annotations (last_accessed, agent_notes) |

All four tools validate that the caller is not overwriting `type: explicit` synapses or structural neuron fields.

---

### Phase C — Module Extraction (Weeks 2-3)

**Goal:** Clean architecture — graph logic lives in one importable module.

#### C1: `vault_graph/` Module

Extract all graph query logic from `scripts/graph_context.py` into `src/mcp_server/vault_graph/`.

> **Package root:** `cloud-vault-mcp` is the project at `~/dev/cohezion/cloud-vault-mcp`; its package root is `src/mcp_server/` (per `pyproject.toml`: `packages = ["src/mcp_server"]`). These are the same thing — `vault_graph/` lives at `src/mcp_server/vault_graph/` inside that repo.

```
vault_graph/
├── __init__.py
├── client.py        # surrealdb.py connection + auth
├── queries.py       # thin wrappers around stored functions
├── reactor.py       # GraphReactor (file-change → dimension update → briefing write)
├── affinity.py      # FLUME PCA pipeline
└── tools.py         # MCP tool implementations (calls queries.py)
```

#### C2: Six Read MCP Tools

Wrap existing stored functions as MCP tools:

| Tool | Stored Function | Description |
|------|-----------------|-------------|
| `graph_neighborhood` | `fn::context_neighborhood` | N-hop neighbors of a neuron |
| `graph_search` | `fn::context_search` | Semantic full-text search |
| `graph_cluster` | `fn::context_cluster` | Cluster a neuron's neighborhood |
| `graph_hops` | `fn::context_hops` | Shortest path between two neurons |
| `graph_bridges` | `fn::context_bridges` | Neurons bridging disconnected clusters |
| `graph_stats` | `fn::vault_stats` | Global vault statistics |

These replace the current curl-based tooling. The CLI (`scripts/graph_context.py`) becomes a thin wrapper that calls `vault_graph.queries` instead of raw HTTP.

---

## 7. Error Handling

| Failure | Behavior |
|---------|----------|
| SurrealDB unreachable at session start | Hook returns empty briefing (graceful degradation), logs warning |
| stored function returns empty result | Return empty list, never raise; callers handle optional results |
| `dim_agent_affinity` write fails | Log warning, continue session — affinity is additive, not critical |
| PCA matrix missing | Skip affinity computation for that session, log warning |
| Migration fails | Roll back via `surrealdb-migrations` rollback command, surface error |

---

## 8. Testing Strategy

| Layer | How |
|-------|-----|
| Stored functions | `scripts/dba/test_functions.surql` — run against test namespace |
| `vault_graph/` module | pytest with `surrealdb.py` test client against ephemeral SurrealDB instance |
| MCP tools | Integration tests via `mcp[cli]` test harness |
| GraphReactor | File-change event simulation; assert `graph-briefing.md` is updated |
| FLUME pipeline | Unit test PCA projection with fixed seed; assert output is 12D |
| Per-prompt hook | Assert briefing injected in <300 tokens for typical vault size |

---

## 9. Dependencies

| Component | Source | Notes |
|-----------|--------|-------|
| `surrealdb` Python SDK | `uv add surrealdb` | Replaces `urllib` HTTP calls |
| `surrealdb-mcp-server` | npm: `nsxdavid/surrealdb-mcp-server` | Direct SurrealQL from Claude Code |
| `surrealdb-migrations` | cargo or npm | Schema migration management |
| `nomic-embed-text` | Ollama (already running) | Session embedding for FLUME |
| `numpy` | already in env | PCA matrix operations |

---

## 10. Key Files Affected

| File | Change |
|------|--------|
| `scripts/graph_context.py` | Replace urllib with surrealdb.py SDK; keep CLI surface |
| `scripts/graph_reactor.py` | Add dim_bridging/completion/recency computation; expand briefing template |
| `scripts/dba/triune-schema.surql` | Add `dim_*` field definitions |
| `scripts/dba/context_functions.surql` | No changes — these are the canonical layer |
| `src/mcp_server/vault_graph/` | New module (Phase C) |
| `metabolism/graph-briefing.md` | Template expanded (auto-generated, not hand-edited) |
| `~/.claude/mcp.json` | Add surrealdb-mcp-server entry |

---

## 11. Success Criteria

- [ ] Agent sessions get graph briefing in <300 tokens with zero query cost
- [ ] `dim_bridging`, `dim_completion`, `dim_recency` populated on all existing neurons
- [ ] Agent writes latent/dream synapse via MCP tool without touching explicit synapses
- [ ] `dim_agent_affinity` vectors written after session accessing neurons
- [ ] `vault_graph/` module has >80% test coverage
- [ ] All six read MCP tools return results matching direct stored function calls
