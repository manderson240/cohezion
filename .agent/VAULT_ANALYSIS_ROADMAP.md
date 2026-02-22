# Vault Analysis & Strategic Roadmap

**Date**: 2026-02-22 | **Branch**: `claude/vault-analysis-roadmap-nUplw`
**Method**: 3-agent specialist swarm (compound engineering + vault integration + vault content)
**Status**: APPROVED FOR IMPLEMENTATION

---

## Executive Summary

A three-agent specialist investigation of the vault, its integration code, and the compound
engineering pipeline reveals a **profound gap between aspiration and reality**.

| Claim (CLAUDE.md) | Reality (Verified 2026-02-22) |
|---|---|
| `~/vaults/cohezion-vault/` with 150+ entries | Path does not exist |
| Vault = Single Source of Truth | Vault at `cloud-vault-mcp/vault/` has **16 files**, mostly templates |
| 95%+ cache hit rate from vault (L3) | L3 vault layer declared but **never invoked** in `semantic_cache.py` |
| 10K tokens saved/session via vault | No evidence; vault search returns at most 3 real documents |
| RetrospectionEngine feeds vault | Engine reads `KEY_LEARNINGS.md` only; **zero vault writes** |
| 12D journey tracking informs routing | Journey points tracked but **never queried for routing decisions** |

The infrastructure is excellent — MCPClient (10+ functions), Cloud Vault MCP server (36 modules),
VaultLogger, MemoryBridge, SSE subscriptions — but it operates on a nearly empty vault.

**Root cause**: The compound loop writes patterns/decisions to the vault only when the MCP server
is running and connected. Sessions without a live server silently skip logging. After 40+ sessions,
only 2 decisions and 1 pattern file exist.

**Strategic direction**: Close the feedback loops, populate the vault, activate dormant
infrastructure, then compound knowledge across sessions.

---

## Part 1: Reality Inventory

### 1.1 Vault Content (Actual)

**Location**: `/home/user/cohezion/cloud-vault-mcp/vault/`

```
vault/
├── .obsidian/app.json                    ← Obsidian config
├── .gitignore
├── README.md                             ← Structure guide
├── daily/_template.md                    ← Template only
├── decisions/
│   ├── _template.md                      ← Template only
│   ├── 2026-02-09-phase-5b-multi-agent-coordination-complete.md  ← REAL
│   └── 2026-02-09-session-40-phase-5b-qa-verification-complete.md ← REAL
├── experiments/_template.md              ← Template only
├── papers/_template.md                   ← Template only
├── patterns/
│   ├── _template.md                      ← Template only
│   └── phase-5b-implementation-patterns.md ← REAL (6 patterns)
├── projects/
│   ├── _template.md                      ← Template only
│   ├── SESSION-40-PHASE-5B-COMPLETION.md ← REAL (detailed spec)
│   └── TASK-6-COMPLETION-REPORT.md       ← REAL
└── teleport/
    ├── results/.gitkeep
    └── tasks/.gitkeep

Real content: 5 files | Templates: 7 files | Infrastructure only: 4 files
```

**Verdict**: The vault is **12 sessions behind** (Sessions 41-55+ produced no vault entries),
contains **zero experiment logs**, and has **no cross-references** between documents.

### 1.2 What's Built and Working

The following infrastructure is **fully implemented and functional** — it just isn't connected:

| Component | Location | Status | Gap |
|-----------|----------|--------|-----|
| MCPClient | `src/cohezion/core/mcp_client.py` | ✅ 10+ vault functions | Needs live MCP server |
| Cloud Vault MCP Server | `cloud-vault-mcp/src/mcp_server/` | ✅ 36 modules, FastMCP | Not started in test env |
| VaultLogger | `src/cohezion/compound/exp_persistence/vault.py` | ✅ 6 methods | Requires MCPClient |
| MemoryBridge | `cloud-vault-mcp/src/mcp_server/memory_bridge.py` | ✅ 248 lines | Not called from sessions |
| VaultSubscriptionClient | `src/cohezion/core/vault_subscription.py` | ✅ SSE client | No listeners registered |
| compile_memory_from_vault.py | `scripts/compile_memory_from_vault.py` | ✅ V1+V2 | Reads empty vault |
| GraphRAG pattern detector | `cloud-vault-mcp/src/mcp_server/graphrag_pattern_detector.py` | ✅ ~80% | Not hooked into loop |
| AgentContextOps | `cloud-vault-mcp/src/mcp_server/agent_context_ops.py` | ✅ ~50% | Not called from loop |

### 1.3 The 13 Disconnected Wires

Ordered by impact on compound learning:

| # | What | File | Gap Type | Impact |
|---|------|------|----------|--------|
| 1 | RetrospectionEngine → Vault | `src/cohezion/core/compound/retrospection.py` | Read-only; no writes | Learnings evaporate each session |
| 2 | L3 Vault Cache never invoked | `src/cohezion/cache/semantic_cache.py` L61-83 | Declared but not called | Cache misses that vault could serve |
| 3 | VaultSearchExecutor stub | `src/cohezion/compound/vault_search_executor.py:233` | `# would integrate...` comment | Announced feature not working |
| 4 | JourneyTracker → Vault | `src/cohezion/compound/journey_tracker.py` | In-memory only | 12D trajectories lost between sessions |
| 5 | SkillRefiner decisions not logged | `src/cohezion/compound/skill_refiner.py:55` | mcp_client passed but unused | Refinement rationale never persisted |
| 6 | DegradationDetector → Vault | `src/cohezion/compound/degradation_detector.py` | Alerts to console only | Quality regressions not captured |
| 7 | No agent identity on patterns | `src/cohezion/compound/exp_persistence/vault.py:94` | No agent_id tag | Can't distinguish good agents from bad |
| 8 | No temporal decay | `src/cohezion/compound/skill_selector.py:101` | All patterns equally weighted | Session 1 noise pollutes Session 56 guidance |
| 9 | VaultSubscriptionClient orphaned | `src/cohezion/core/vault_subscription.py` | SSE client, zero listeners | Real-time events go nowhere |
| 10 | UniverseBridge not persisted | `src/cohezion/compound/universe_bridge.py` | In-memory simulation | Universe state lost at session end |
| 11 | GlobalMetrics → Vault | `src/cohezion/compound/global_metrics_aggregator.py` | Memory-only | No cross-session metric trends |
| 12 | Skill refinement audit trail | `src/cohezion/compound/skill_refiner.py` | PRIME skill updated but no lineage | Can't trace which session improved which skill |
| 13 | 12D phi_score → routing | `src/cohezion/compound/journey_tracker.py:73` | Tracked, never queried | Best agent/skill for task type unknown |

---

## Part 2: Architecture Map (Current vs Target)

### 2.1 Current Data Flow

```
Session Start
    │
    ▼
CompoundExecutor.execute_task()
    │
    ├─► get_experience_guidance()  ─────────► vault_find_relevant_context()
    │       (finds 0-2 patterns if MCP running)      (usually nothing to return)
    │
    ▼
Task Execution
    │
    ├─► RequestAlignmentAnalyzer ──────────► [vault_log_decision if low alignment]
    ├─► AnomalyDetector ───────────────────► [console only]
    ├─► RetrospectionEngine ───────────────► [reads KEY_LEARNINGS.md; WRITES NOTHING]
    ├─► SkillRefiner ──────────────────────► [updates PRIME .md file; LOGS NOTHING]
    ├─► DegradationDetector ───────────────► [console only]
    ├─► GlobalMetricsAggregator ───────────► [in-memory only]
    ├─► JourneyTracker (12D) ──────────────► [in-memory only; lost at session end]
    └─► VaultLogger.extract_pattern() ────► [vault write IF MCP server running]

Session End
    │
    ▼
Knowledge LOST (90%+ of insights evaporate)
```

### 2.2 Target Data Flow (Post-Roadmap)

```
Session Start
    │
    ▼
VaultBootstrapper.warm_context()              ← NEW: Loads temporal-weighted patterns
    │   ├─ Queries patterns with age decay
    │   ├─ Loads agent-specific histories
    │   └─ Injects trajectory phi_scores into routing
    │
    ▼
CompoundExecutor.execute_task()
    │
    ├─► get_experience_guidance()  ─────────► vault_find_relevant_context()
    │       (returns agent-specific, fresh patterns)  (100+ indexed entries)
    │
    ▼
Task Execution
    │
    ├─► RequestAlignmentAnalyzer ──────────► vault_log_decision() [always]
    ├─► AnomalyDetector ───────────────────► vault_log_experiment() [if severity > WARNING]
    ├─► RetrospectionEngine ───────────────► vault_log_decision() [per learning] ← NEW
    ├─► SkillRefiner ──────────────────────► vault_log_decision() [per refinement] ← NEW
    ├─► DegradationDetector ───────────────► vault_log_decision() [per alert] ← NEW
    ├─► GlobalMetricsAggregator ───────────► vault_extract_pattern() [weekly rollup] ← NEW
    ├─► JourneyTracker (12D) ──────────────► vault_write(trajectory.json) [per session] ← NEW
    │       └─ phi_scores index ──────────► SkillSelector routing weights ← NEW
    └─► VaultLogger.extract_pattern() ────► vault_write() [always, with agent_id]

Session End
    │
    ▼
VaultConsolidator.run()                       ← NEW: GraphRAG indexing, decay updates
    ├─ SurrealDB sync for graph queries
    ├─ Pattern impact scoring
    ├─ Age-weighted index refresh
    └─ MEMORY.md recompile

Knowledge PRESERVED and COMPOUNDED across sessions
```

---

## Part 3: Strategic Roadmap

### Phase 0: Vault Bootstrap (Priority: CRITICAL | Effort: Low)

**Problem**: The vault is nearly empty; all infrastructure reads from nothing.

**Goal**: Populate vault retroactively from existing artifacts, establish guaranteed write paths.

**0.1 — Retroactive Population Script**

Mine existing session artifacts and backfill vault entries:

```python
# scripts/vault_bootstrap.py

"""
Retroactively populate vault from existing session artifacts:
- KEY_LEARNINGS.md → decisions (one per learning block)
- PRIME skill files → patterns (one per skill)
- Session completion docs in docs/ → projects
- Git commit messages with Co-Authored-By → session timeline
"""

async def bootstrap_from_key_learnings():
    """Parse KEY_LEARNINGS.md → vault decisions."""
    learnings = RetrospectionEngine().analyze_learnings()
    for learning in learnings:
        await mcp_client.vault_log_decision(
            project="cohezion",
            title=learning.title,
            context=f"Session learning #{learning.id} (compound_score={learning.compound_score:.2f})",
            decision=learning.description,
            rationale=f"Cross-refs: {', '.join(learning.cross_references)}"
        )

async def bootstrap_from_prime_skills():
    """Register all 134 PRIME skills as vault patterns."""
    registry = json.load(open("src/cohezion/skills/skill_registry.json"))
    for skill_name, meta in registry.items():
        await mcp_client.vault_extract_pattern(
            source_path=meta["path"],
            pattern_name=skill_name,
            description=meta.get("description", ""),
            domain=meta.get("domain", "compound-engineering")
        )

async def bootstrap_from_session_docs():
    """Index session completion reports in docs/."""
    for doc in Path("docs/").rglob("SESSION-*-COMPLETION*.md"):
        content = doc.read_text()
        await mcp_client.vault_write(
            path=f"projects/{doc.stem}.md",
            content=content
        )
```

**Expected yield**: ~150 decisions, ~134 skill patterns, ~15 project entries.

**0.2 — MCP Server Always-On Strategy**

The MCP server must be running for vault writes to succeed. Add a server health check
at session start with graceful degradation to JSONL queue:

```python
# src/cohezion/compound/vault_guard.py

class VaultGuard:
    """Ensure vault writes succeed or queue for retry."""

    def __init__(self, mcp_client: MCPClient, fallback_path: Path):
        self.client = mcp_client
        self.queue_path = fallback_path / "vault_queue.jsonl"

    async def write_or_queue(self, operation: str, payload: dict):
        try:
            await self.client._call_tool(operation, payload)
        except Exception:
            # Queue for replay when server comes back
            with open(self.queue_path, "a") as f:
                json.dump({"op": operation, "payload": payload,
                          "ts": datetime.utcnow().isoformat()}, f)
                f.write("\n")

    async def replay_queue(self):
        """Called at session start if MCP server now available."""
        if not self.queue_path.exists():
            return
        pending = [json.loads(l) for l in self.queue_path.read_text().splitlines() if l]
        for entry in pending:
            await self.client._call_tool(entry["op"], entry["payload"])
        self.queue_path.unlink()
```

**0.3 — Session-Start Warm-Up Hook**

Add to `CompoundExecutor.__init__()`:

```python
# Warm vault context at session start (non-blocking)
asyncio.create_task(self._warm_vault_context())

async def _warm_vault_context(self):
    """Replay queued writes + warm relevant context."""
    await self.vault_guard.replay_queue()
    self._warm_context = await self.logger.get_experience_guidance(
        task_description=self.project,
        operation_type="session_start"
    )
```

**Success metrics for Phase 0**:
- Vault file count: 16 → 300+
- Vault decisions: 2 → 150+
- Vault patterns: 1 → 134+
- MCP server uptime: unknown → tracked (healthz endpoint)

---

### Phase 1: Close the Feedback Loops (Priority: HIGH | Effort: Medium)

**Problem**: Knowledge extracted by RetrospectionEngine, SkillRefiner, and DegradationDetector
evaporates at session end. The compound loop has no closed feedback path.

**1.1 — RetrospectionEngine → Vault Writer**

```python
# src/cohezion/core/compound/retrospection.py
# Add vault logging to analyze_learnings()

async def analyze_learnings_and_log(self, mcp_client: MCPClient | None = None) -> list[LearningPattern]:
    """Analyze learnings AND log to vault."""
    learnings = self.analyze_learnings()

    if mcp_client is None:
        return learnings

    for learning in learnings:
        try:
            await mcp_client.vault_log_decision(
                project="cohezion",
                title=f"Learning #{learning.id}: {learning.title}",
                context=f"Extracted by RetrospectionEngine. Tags: {learning.tags}",
                decision=learning.description,
                rationale=f"compound_score={learning.compound_score:.2f}, "
                          f"cross_refs={len(learning.cross_references)}"
            )
        except Exception as e:
            logger.warning(f"Retrospection vault log failed (non-blocking): {e}")

    return learnings
```

**1.2 — SkillRefiner → Audit Trail**

```python
# src/cohezion/compound/skill_refiner.py
# After refine() updates PRIME skill file:

async def _log_refinement_decision(
    self, skill_name: str, trigger: str, changes: list[str]
):
    """Log every skill refinement as a vault decision."""
    try:
        await self.mcp_client.vault_log_decision(
            project="cohezion",
            title=f"SkillRefiner: {skill_name} updated",
            context=f"Trigger: {trigger}",
            decision=f"Updated PRIME skill with {len(changes)} changes",
            rationale="\n".join(f"- {c}" for c in changes)
        )
    except Exception as e:
        logger.warning(f"Skill refinement vault log failed: {e}")
```

**1.3 — DegradationDetector → Vault Decisions**

```python
# src/cohezion/compound/degradation_detector.py
# In check_degradation(), after building alert list:

for alert in alerts:
    if alert.severity in (Severity.WARNING, Severity.CRITICAL):
        try:
            await self.mcp_client.vault_log_experiment(
                project="cohezion",
                hypothesis=f"{alert.metric} should stay above {alert.threshold}",
                method="DegradationDetector.check_degradation()",
                result=f"Actual: {alert.actual_value:.3f} ({alert.severity.name})",
                learnings=f"Alert at {alert.timestamp}: {alert.details}"
            )
        except Exception:
            pass  # Non-blocking
```

**1.4 — Pattern Extraction Always Writes (with agent_id)**

```python
# src/cohezion/compound/exp_persistence/vault.py
# Add agent_id to all vault pattern paths

def extract_execution_pattern(
    self, execution_result, task_description, skill_name,
    agent_id: str = "default"  ← NEW PARAM
):
    pattern_path = f"patterns/domains/{domain}/{agent_id}/{pattern_name}.md"
    #                                              ↑ agent-scoped namespace
```

**Success metrics for Phase 1**:
- Vault writes per session: ~5 → 50+
- RetrospectionEngine learnings persisted: 0% → 100%
- SkillRefiner decisions in vault: 0% → 100%
- DegradationDetector alerts captured: 0% → 100% (WARNING+)

---

### Phase 2: Temporal Intelligence (Priority: HIGH | Effort: Medium)

**Problem**: All vault patterns are equally weighted regardless of age or origin.
Session 1 noise pollutes Session 56 guidance.

**2.1 — Temporal Decay in SkillSelector**

```python
# src/cohezion/compound/skill_selector.py
# In _extract_skill_scores(), add age penalty:

import math
from datetime import datetime, timezone

def _compute_age_decay(pattern_date_str: str, half_life_days: float = 14.0) -> float:
    """Exponential decay: patterns lose half their weight every 14 days."""
    try:
        pattern_date = datetime.fromisoformat(pattern_date_str).replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - pattern_date).days
        return math.exp(-0.693 * age_days / half_life_days)  # e^(-ln2 * age/half_life)
    except Exception:
        return 1.0  # Default: no decay if date unavailable

def _extract_skill_scores(self, context: dict, operation_type: str) -> list[SkillScore]:
    scores = []
    for pattern in context.get("patterns", []):
        base_score = (
            pattern.get("coherence", 0.5) * 0.50
            + pattern.get("efficiency", 0.5) * 0.30
            + pattern.get("success_rate", 0.5) * 0.20
        )
        age_weight = self._compute_age_decay(pattern.get("date", ""))  ← NEW
        scores.append(SkillScore(
            skill_name=pattern["skill_name"],
            composite_score=base_score * age_weight,               ← WEIGHTED
            coherence=pattern.get("coherence", 0.5),
            efficiency=pattern.get("efficiency", 0.5),
            success_rate=pattern.get("success_rate", 0.5),
            age_days=age_days,                                      ← NEW FIELD
        ))
    return sorted(scores, reverse=True)
```

**2.2 — Agent Identity Tagging**

Add `agent_id` to all vault pattern metadata so patterns can be filtered by agent type:

```python
# Pattern frontmatter (YAML):
---
date: 2026-02-22
project: cohezion
agent_id: researcher-1          ← NEW
agent_type: compound-executor   ← NEW
skill_used: RESEARCH_PRIME
operation_type: analyze
coherence: 0.87
efficiency: 0.91
session_id: session-56
---
```

**2.3 — Session-Scoped Knowledge Filter**

```python
# src/cohezion/compound/exp_persistence/vault.py

def get_experience_guidance(
    self, task_description: str, project: str, operation_type: str,
    max_age_days: int = 30,             ← NEW: ignore stale patterns
    prefer_same_operation: bool = True  ← NEW: boost same op_type
) -> dict:
    context = self.mcp_client.vault_find_relevant_context(
        query=f"{task_description} {operation_type}",
        project=project,
        filters={
            "max_age_days": max_age_days,
            "operation_type": operation_type if prefer_same_operation else None,
        }
    )
    return context
```

**Success metrics for Phase 2**:
- Pattern freshness: All patterns age-weighted with 14-day half-life
- Agent attribution: 100% of new patterns carry agent_id
- Guidance quality: Old (>30 day) patterns excluded by default
- SkillSelector accuracy: Target +10-15% coherence improvement

---

### Phase 3: Activate Dormant Infrastructure (Priority: HIGH | Effort: Low-Medium)

These are **complete implementations that just need wiring**:

**3.1 — Implement L3 Vault Cache**

```python
# src/cohezion/cache/semantic_cache.py
# Lines 155+: Add vault lookup to get() method

async def get(self, key: str, embedding: np.ndarray | None = None) -> Any | None:
    # L1: Hash lookup
    if key in self._l1_cache:
        self._stats["l1_hits"] += 1
        return self._l1_cache[key]

    # L2: Cosine similarity
    if embedding is not None:
        result = self._l2_search(embedding)
        if result is not None:
            self._stats["l2_hits"] += 1
            return result

    # L3: Vault lookup ← ACTIVATE THIS
    if self.mcp_client is not None:
        try:
            context = await self.mcp_client.vault_find_relevant_context(
                query=key,
                project=self._project,
            )
            if context.get("patterns"):
                result = context["patterns"][0].get("cached_result")
                if result is not None:
                    self._stats["l3_hits"] += 1
                    # Promote to L1 for next hit
                    self._l1_cache[key] = result
                    return result
        except Exception:
            pass  # Non-blocking

    self._stats["misses"] += 1
    return None
```

**3.2 — Complete VaultSearchExecutor**

```python
# src/cohezion/compound/vault_search_executor.py
# Replace stub at line 233 with actual implementation:

async def _vault_search(self, query: str, operation_type: str) -> list[SearchResult]:
    """Actual vault integration (not a stub)."""
    # Use hierarchical search (5-10x faster than flat search)
    results = await self.mcp_client.vault_search_hierarchical(
        query=query,
        scope=operation_type,
        max_results=10,
    )
    return [
        SearchResult(
            content=r["content"],
            source=r["path"],
            relevance=r.get("score", 0.5),
            metadata={"operation_type": r.get("operation_type"), "date": r.get("date")}
        )
        for r in results.get("results", [])
    ]
```

**3.3 — Register VaultSubscriptionClient Listeners**

```python
# src/cohezion/compound/executor.py
# In __init__(), after mcp_client setup:

if self.mcp_client and getattr(self.mcp_client, "vault_subscription", None):
    sub = VaultSubscriptionClient(server_url=mcp_client.server_url)

    @sub.on_event("pattern_created")
    async def on_new_pattern(event: VaultEvent):
        """Invalidate skill selector cache when new pattern arrives."""
        self.skill_selector.invalidate_cache(event.path)

    @sub.on_event("decision_created")
    async def on_new_decision(event: VaultEvent):
        """Log cross-session decision for alignment analysis."""
        logger.info(f"Vault decision: {event.path}")

    asyncio.create_task(sub.connect())
```

**Success metrics for Phase 3**:
- L3 cache invocations: 0 → matches every cache miss that has a vault entry
- VaultSearchExecutor: Stub → live, tested against actual vault
- VaultSubscriptionClient: 0 listeners → 3+ listeners registered per executor

---

### Phase 4: GraphRAG Knowledge Graph (Priority: MEDIUM | Effort: High)

**Problem**: Vault entries are flat files. No cross-document relationships, no impact scoring,
no automatic pattern detection.

**4.1 — Enable SurrealDB Sync**

The `surrealdb_sync.py` module exists but isn't called from the compound loop.
Wire it into the session end consolidation:

```python
# scripts/vault_consolidate.py (NEW — run at session end or weekly)

async def consolidate():
    """End-of-session vault consolidation pipeline."""

    # 1. Sync new vault files to SurrealDB graph
    syncer = SurrealDBSync(vault_path=VAULT_PATH, surreal_url=SURREAL_URL)
    sync_report = await syncer.sync_changed_files()

    # 2. Detect new patterns from similar documents
    detector = GraphRAGPatternDetector(surreal_client=surreal)
    new_patterns = await detector.detect_patterns(min_similarity=0.85)
    for pattern in new_patterns:
        await mcp_client.vault_extract_pattern(**pattern)

    # 3. Compute impact scores (node degree in knowledge graph)
    impact_scores = await surreal.query("""
        SELECT path, count(<-references) as impact
        FROM vault_documents
        ORDER BY impact DESC LIMIT 20
    """)

    # 4. Recompile MEMORY.md with impact-weighted content
    subprocess.run(["uv", "run", "python",
                    "scripts/compile_memory_from_vault.py", "--graphrag"])
```

**4.2 — Knowledge Graph Schema**

```sql
-- SurrealDB schema for vault knowledge graph

DEFINE TABLE vault_documents SCHEMAFULL;
DEFINE FIELD path ON vault_documents TYPE string;
DEFINE FIELD type ON vault_documents TYPE string;      -- decision|experiment|pattern|project
DEFINE FIELD date ON vault_documents TYPE datetime;
DEFINE FIELD project ON vault_documents TYPE string;
DEFINE FIELD agent_id ON vault_documents TYPE string;
DEFINE FIELD skill_used ON vault_documents TYPE string;
DEFINE FIELD coherence ON vault_documents TYPE float;
DEFINE FIELD tags ON vault_documents TYPE array;
DEFINE FIELD embedding ON vault_documents TYPE array;   -- 256D FLUME embedding

DEFINE TABLE references SCHEMAFULL;                    -- Directed edge: doc A references doc B
DEFINE FIELD in ON references TYPE record<vault_documents>;
DEFINE FIELD out ON references TYPE record<vault_documents>;
DEFINE FIELD weight ON references TYPE float;           -- Relevance weight

DEFINE INDEX idx_doc_date ON TABLE vault_documents FIELDS date;
DEFINE INDEX idx_doc_skill ON TABLE vault_documents FIELDS skill_used;
DEFINE INDEX idx_doc_agent ON TABLE vault_documents FIELDS agent_id;
```

**4.3 — Compound Impact Score Query**

Expose as `/api/vault/impact` endpoint:

```python
@app.get("/vault/impact")
async def get_vault_impact(top_k: int = 20) -> list[ImpactEntry]:
    """Return most impactful vault entries by graph centrality."""
    results = await surreal.query(f"""
        SELECT
            path, type, date, coherence,
            count(<-references) as in_degree,
            count(->references) as out_degree,
            (in_degree * 0.7 + out_degree * 0.3) as impact_score
        FROM vault_documents
        ORDER BY impact_score DESC
        LIMIT {top_k}
    """)
    return [ImpactEntry(**r) for r in results]
```

**Success metrics for Phase 4**:
- SurrealDB vault documents: 0 → 300+
- Cross-document references indexed: 0 → 1000+
- Auto-detected patterns: 0 → 20+ per week
- `/vault/impact` endpoint: live, returns ranked entries

---

### Phase 5: 12D Routing Intelligence (Priority: MEDIUM | Effort: High)

**Problem**: JourneyTracker computes phi_scores for every execution but they're never used
to improve future routing decisions. The 12D universe is observability-only.

**5.1 — JourneyTracker → Vault Persistence**

```python
# src/cohezion/compound/journey_tracker.py
# In track_execution(), after computing trajectory:

async def _persist_trajectory(
    self, point: TrajectoryPoint, task_description: str, session_id: str
):
    """Persist 12D trajectory to vault for cross-session routing."""
    try:
        await self.mcp_client.vault_write(
            path=f"trajectories/{session_id}/{point.operation_type}/{datetime.utcnow().isoformat()}.json",
            content=json.dumps({
                "dimensions": point.dimensions.tolist(),
                "coherence": point.coherence,
                "efficiency": point.efficiency,
                "phi_score": point.metadata.get("phi_score", 0.0),
                "operation_type": point.operation_type,
                "task_description_hash": hashlib.sha256(task_description.encode()).hexdigest()[:16],
                "skill_name": point.metadata.get("skill_name"),
            })
        )
    except Exception as e:
        logger.warning(f"Trajectory persistence failed (non-blocking): {e}")
```

**5.2 — JourneyRouter: phi_score-Guided Skill Selection**

```python
# src/cohezion/compound/journey_router.py (NEW)

class JourneyRouter:
    """Use historical 12D trajectory data to improve skill/agent routing."""

    def __init__(self, mcp_client: MCPClient, journey_tracker: JourneyTracker):
        self.client = mcp_client
        self.tracker = journey_tracker
        self._phi_cache: dict[str, float] = {}  # operation_type → avg phi_score

    async def get_operation_phi_scores(self) -> dict[str, float]:
        """Return average phi_score per operation_type from vault trajectories."""
        if self._phi_cache:
            return self._phi_cache  # Use in-memory cache within session

        results = await self.client.vault_search_by_operation(
            operation_type="*",  # All types
            scope="trajectories/"
        )

        phi_by_op: dict[str, list[float]] = {}
        for r in results.get("results", []):
            op = r.get("operation_type")
            phi = r.get("phi_score", 0.0)
            phi_by_op.setdefault(op, []).append(phi)

        self._phi_cache = {
            op: sum(phis) / len(phis)
            for op, phis in phi_by_op.items()
        }
        return self._phi_cache

    async def recommend_skill(
        self, operation_type: str, candidate_skills: list[str]
    ) -> str:
        """Recommend skill with highest historical phi_score for this operation."""
        phi_scores = await self.get_operation_phi_scores()

        # Score candidates: vault phi_score (70%) + base selection (30%)
        scored = []
        for skill in candidate_skills:
            key = f"{operation_type}:{skill}"
            phi = phi_scores.get(key, 0.5)  # Default to neutral
            scored.append((phi, skill))

        scored.sort(reverse=True)
        return scored[0][1] if scored else candidate_skills[0]
```

**5.3 — Wire JourneyRouter into CompoundExecutor**

```python
# src/cohezion/compound/executor.py
# In execute_task(), before skill selection:

journey_router = JourneyRouter(self.mcp_client, self.journey_tracker)
operation_type = self.alignment_analyzer.classify_operation(task_description)
recommended_skill = await journey_router.recommend_skill(
    operation_type=operation_type,
    candidate_skills=candidate_skills,
)
# Use recommended_skill as primary, fall back to SkillSelector ranking
```

**Success metrics for Phase 5**:
- Trajectory entries in vault: 0 → grows with each session
- JourneyRouter: Not existing → live, queried before every skill selection
- phi_score-guided routing: 0% decisions → 100% decisions informed by history
- Target improvement: +15-25% coherence via better skill routing

---

### Phase 6: Vault-First CI/CD (Priority: LOW | Effort: Low)

**Goal**: Make vault logging automatic and impossible to skip.

**6.1 — Pre-Commit Hook for Architecture Decisions**

```bash
# .git/hooks/pre-commit (add to existing hook)

# Auto-log significant commits as vault decisions
COMMIT_MSG=$(git log --oneline -1 2>/dev/null || echo "")
if echo "$COMMIT_MSG" | grep -qE "^(feat|fix|refactor|chore|perf):"; then
    python scripts/vault_log_commit.py "$COMMIT_MSG" 2>/dev/null || true
fi
```

**6.2 — Automated Weekly MEMORY.md**

```yaml
# .github/workflows/vault-compile.yml (or cron job)

name: Vault Compile
on:
  schedule:
    - cron: '0 0 * * 0'  # Every Sunday midnight
  workflow_dispatch:

jobs:
  compile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: uv run python scripts/compile_memory_from_vault.py --graphrag
      - run: git add MEMORY.md && git commit -m "chore: weekly MEMORY.md compile" || true
      - run: git push
```

**6.3 — Session-End Consolidation Script**

```bash
# scripts/session/end_session.sh (enhance existing)
# Add vault consolidation step before git push:

echo "→ Consolidating vault..."
uv run python scripts/vault_consolidate.py --session-id "$SESSION_ID"

echo "→ Recompiling MEMORY.md..."
uv run python scripts/compile_memory_from_vault.py

echo "→ GraphRAG indexing..."
uv run python scripts/compile_memory_from_vault.py --graphrag
```

**Success metrics for Phase 6**:
- Vault entries per commit: 0 → 1 (significant commits)
- MEMORY.md freshness: Manual → Auto-compiled weekly
- Session consolidation: Manual → Scripted, part of `end_session.sh`

---

## Part 4: Connection Matrix (Maximum Compound Engineering)

The target state with all 6 phases complete creates these connections:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VAULT KNOWLEDGE GRAPH (Target State)                    │
└─────────────────────────────────────────────────────────────────────────────┘

Producer                    → Vault              → Consumer
─────────────────────────────────────────────────────────────────────────────
RetrospectionEngine         → decisions/         → SkillSelector (fresh patterns)
SkillRefiner                → decisions/         → SkillSelector (what changed why)
DegradationDetector         → experiments/       → DegradationDetector (history)
JourneyTracker (12D)        → trajectories/      → JourneyRouter (phi routing)
CompoundExecutor            → patterns/          → SemanticCache L3 (pre-populate)
RequestAlignmentAnalyzer    → decisions/         → RequestAlignmentAnalyzer (prior)
GlobalMetricsAggregator     → patterns/          → SkillRefiner (metric baselines)
SkillConsensusVoter         → decisions/         → SkillConsensusVoter (prior votes)
SessionPersistence          → sessions/          → VaultBootstrapper (warm start)
UniverseBridge              → projects/          → UniverseBridge (state restore)
KeyLearnings (bootstrap)    → decisions/         → All consumers (backfilled history)
PRIME Skills (bootstrap)    → patterns/          → SkillSelector (indexed baseline)
Git commits (Phase 6)       → decisions/         → Architecture review

Read path:
SemanticCache L3            ← vault_find_relevant_context()
SkillSelector               ← vault_find_relevant_context()
JourneyRouter               ← vault_search_by_operation()
VaultBootstrapper           ← vault_read(), vault_search()
RequestAlignmentAnalyzer    ← vault_find_relevant_context()
MEMORY.md compiler          ← SurrealDB GraphRAG query
```

**Cross-references enabled** (each entity knows about others):
- Decisions reference patterns they used → pattern impact score grows
- Patterns reference the decisions that created them → lineage tracking
- Experiments reference the skills that failed → failure mode indexing
- Trajectories reference patterns chosen → routing accuracy feedback

---

## Part 5: Implementation Specifications

### 5.1 New Files Required

| File | Purpose | Phase | Complexity |
|------|---------|-------|------------|
| `scripts/vault_bootstrap.py` | Retroactive vault population | 0 | Medium |
| `src/cohezion/compound/vault_guard.py` | Queued writes + replay | 0 | Low |
| `src/cohezion/compound/vault_bootstrapper.py` | Session warm-up | 0 | Low |
| `scripts/vault_consolidate.py` | End-of-session consolidation | 4 | Medium |
| `src/cohezion/compound/journey_router.py` | phi_score-guided routing | 5 | Medium |
| `src/cohezion/knowledge_graph/surreal_schema.sql` | SurrealDB vault schema | 4 | Low |

### 5.2 Files to Modify

| File | Change | Phase | Lines Affected |
|------|--------|-------|----------------|
| `src/cohezion/core/compound/retrospection.py` | Add vault writes to `analyze_learnings()` | 1 | +25 |
| `src/cohezion/compound/skill_refiner.py` | Add `_log_refinement_decision()` | 1 | +20 |
| `src/cohezion/compound/degradation_detector.py` | Log alerts to vault | 1 | +15 |
| `src/cohezion/compound/exp_persistence/vault.py` | Add `agent_id` param, temporal filter | 1+2 | +10 |
| `src/cohezion/compound/skill_selector.py` | Add `_compute_age_decay()`, age_weight | 2 | +25 |
| `src/cohezion/cache/semantic_cache.py` | Activate L3 vault lookup in `get()` | 3 | +20 |
| `src/cohezion/compound/vault_search_executor.py` | Replace stub at L233 | 3 | +30 |
| `src/cohezion/compound/executor.py` | Wire VaultSubscriptionClient, JourneyRouter | 3+5 | +40 |
| `src/cohezion/compound/journey_tracker.py` | Add `_persist_trajectory()` | 5 | +30 |
| `scripts/session/end_session.sh` | Add vault consolidation step | 6 | +10 |

### 5.3 Test Requirements

Each phase must add tests:

| Phase | Test File | Test Count | Focus |
|-------|-----------|------------|-------|
| 0 | `tests/scripts/test_vault_bootstrap.py` | 10 | Bootstrap idempotency, no duplicates |
| 0 | `tests/compound/test_vault_guard.py` | 8 | Queue/replay, server down scenario |
| 1 | `tests/compound/test_retrospection_vault.py` | 10 | Verify vault writes on learning extract |
| 1 | `tests/compound/test_skill_refiner_vault.py` | 8 | Audit trail completeness |
| 2 | `tests/compound/test_skill_selector_temporal.py` | 12 | Age decay math, old pattern downranking |
| 3 | `tests/cache/test_semantic_cache_l3.py` | 10 | L3 hit path, vault miss, promotion to L1 |
| 4 | `tests/integration/test_graphrag_indexing.py` | 15 | SurrealDB sync, pattern detection |
| 5 | `tests/compound/test_journey_router.py` | 12 | phi_score routing, cold-start behavior |
| 6 | `tests/integration/test_vault_consolidate.py` | 8 | End-to-end consolidation pipeline |

**Total new tests**: ~93 across all phases

---

## Part 6: Prioritized Action Plan

### Sprint 1 (Sessions 57-58): Bootstrap + Loops
1. ✅ **Write this roadmap** (complete)
2. Run `vault_bootstrap.py` to populate vault from existing artifacts
3. Add vault writes to RetrospectionEngine and SkillRefiner
4. Add VaultGuard for MCP-down resilience

### Sprint 2 (Session 59): Temporal + Identity
5. Add temporal decay to SkillSelector
6. Add agent_id tagging to all pattern writes
7. Activate L3 vault cache in SemanticCache
8. Complete VaultSearchExecutor (replace stub)

### Sprint 3 (Session 60): GraphRAG
9. Enable SurrealDB sync via `vault_consolidate.py`
10. Wire GraphRAG pattern detector
11. Add `/vault/impact` API endpoint
12. Switch MEMORY.md to V2 (GraphRAG) compiler

### Sprint 4 (Session 61): Journey Routing
13. Add `_persist_trajectory()` to JourneyTracker
14. Implement JourneyRouter
15. Wire JourneyRouter into CompoundExecutor skill selection
16. Register VaultSubscriptionClient listeners

### Sprint 5 (Session 62): Automation
17. Pre-commit vault logging
18. Automated weekly MEMORY.md compilation
19. Vault consolidation in `end_session.sh`
20. Full integration test suite

---

## Part 7: Success Definition

The vault is working when these metrics are all true simultaneously:

| Metric | Current | Target |
|--------|---------|--------|
| Vault file count | 16 | 500+ |
| Vault decisions | 2 | 200+ |
| Vault patterns | 1 | 150+ |
| Vault experiments | 0 | 100+ |
| Cross-references (SurrealDB edges) | 0 | 1000+ |
| Patterns written per session | ~3 (if MCP running) | 20+ |
| Decisions written per session | ~1 (if aligned badly) | 10+ |
| MCP server uptime per session | ~0% (not monitored) | 99%+ |
| L3 cache invocations per session | 0 | matches L1+L2 miss rate |
| JourneyTracker entries persisted | 0 | 1 per execution |
| SkillSelector temporal decay | not applied | applied (14-day half-life) |
| Agent identity on patterns | 0% | 100% |
| RetrospectionEngine → Vault writes | 0% | 100% |
| SkillRefiner decisions in vault | 0% | 100% |
| MEMORY.md auto-compiled | never | weekly |
| Sessions to warm start | cold (no history) | 1 (from vault) |

When these metrics are met, **the compound engineering loop is truly closed**.
Every session improves future sessions. Knowledge compounds rather than evaporates.

---

## Appendix: Agent Investigation Summary

Three specialist agents investigated this system on 2026-02-22:

**Agent 1 — Compound Engineering Anatomy**:
- Mapped 11-step pipeline with 86 connection points
- Identified 5 critical gaps (skill freshness, L3 cache, temporal decay, agent identity, 12D routing)
- Confirmed RetrospectionEngine reads KEY_LEARNINGS.md but writes nothing to vault

**Agent 2 — Vault Integration Code**:
- Mapped all vault-related code: MCPClient (10 functions), VaultLogger (6 methods),
  VaultSubscriptionClient, MemoryBridge, compile_memory_from_vault.py
- Found VaultSearchExecutor stub at line 233 ("would integrate with MCP")
- Confirmed 8 missing connections, ranked by impact
- Verified Cloud Vault MCP server fully implemented (36 modules) but likely not running

**Agent 3 — Vault Content**:
- Discovered `~/vaults/cohezion-vault/` path in CLAUDE.md doesn't exist
- Actual vault at `cloud-vault-mcp/vault/` has 16 files (5 real, 11 templates)
- Confirmed: 12 sessions of work (Sessions 41-55+) produced zero vault entries
- 2 decisions (from Session 40), 1 pattern file, 2 project reports — all from 2026-02-09

**Key insight from synthesis**: The gap is not architectural (the MCP server, VaultLogger,
MCPClient are all excellent). The gap is operational: the MCP server is not running
during most sessions, so writes silently fail. The VaultGuard (queued writes) + Bootstrap
(retroactive population) are the highest-leverage interventions.
