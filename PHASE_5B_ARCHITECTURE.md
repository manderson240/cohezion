# Phase 5B Architecture

System design, component interactions, and integration points for Phase 5B multi-agent coordination.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code (User Interaction)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  MCP Client (via ~/.claude/mcp.json)                       │ │
│  │  - vault_read, vault_write, vault_search, vault_list       │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │ HTTP/REST                         │
└─────────────────────────────┼──────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  MCP Server         │
                    │  :8360/api/vault/*  │
                    │                     │
                    │ - FastMCP Framework │
                    │ - Starlette Web     │
                    │ - APIKeyAuth        │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
        ┌─────────────┐  ┌──────────┐  ┌──────────────┐
        │ VaultOps    │  │VaultWatch│  │Inbox Process │
        │             │  │          │  │              │
        │ - read()    │  │- Monitor │  │- Classify    │
        │ - write()   │  │- Emit    │  │- Store notes │
        │ - delete()  │  │- SSE     │  │              │
        │ - atomic    │  │- Queue   │  │- Sync to AI  │
        └──────┬──────┘  └────┬─────┘  └──────────────┘
               │              │
               └──────────────┼─────────────────────┐
                              │                     │
                              ▼                     ▼
                        ┌────────────────────┐  ┌──────────────┐
                        │  Vault Repo        │  │ Anthropic    │
                        │  (.git)            │  │ API          │
                        │                    │  │ (for inbox)  │
                        │ - 161+ documents   │  │              │
                        │ - git history      │  │              │
                        │ - Backup           │  │              │
                        └────────────────────┘  └──────────────┘
```

---

## Cohezion Executor Integration

```
┌──────────────────────────────────────────────────────────────────┐
│                    CompoundExecutor Pipeline                      │
│              (11-step execution with Phase 5B components)          │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│ 1️⃣  Query Vault (SemanticCache, RedisSemanticCache)              │
│     └─ L1: Hash-based lookup (instant)                           │
│     └─ L2: Cosine similarity (25-30% better matches)             │
│     └─ L3: Redis distributed cache (team-wide)                   │
│                                                                    │
│ 2️⃣  Parse Request (extract intent, entities)                     │
│                                                                    │
│ 3️⃣  Guardrails Check (safety validation)                         │
│                                                                    │
│ 4️⃣  Execute (skill invocation)                                   │
│     └─ SkillSelector: rank skills by vault coherence             │
│     └─ SkillConsensusVoter: multi-agent voting on skill choice   │
│     └─ Execute selected skill                                     │
│                                                                    │
│ 5️⃣  Detect Anomalies (RequestAlignmentAnalyzer)                  │
│                                                                    │
│ 6️⃣  Analyze Alignment (compare predicted vs actual)              │
│                                                                    │
│ 7️⃣  Extract Patterns & Refine Skills (SkillRefiner)              │
│     └─ Update skill coherence metrics                            │
│     └─ Persist to vault (async, non-blocking)                    │
│                                                                    │
│ 7.5️⃣  Check Degradation (DegradationDetector)                    │
│     └─ Detect model quality issues                               │
│     └─ Recommend fallback models                                 │
│                                                                    │
│ 7.7️⃣  Record Model Quality (ModelQualityClassifier)              │
│     └─ Predict quality metrics (accuracy, efficiency)            │
│     └─ Persist quality assessments                               │
│                                                                    │
│ 8️⃣  Record Metrics (MetricsCollector)                            │
│     └─ GlobalMetricsAggregator: cross-instance aggregation       │
│     └─ Per-instance: executions, tokens, cache hits, latencies   │
│     └─ Vault export (for historical analysis)                    │
│                                                                    │
│ 9️⃣  Track Journey (JourneyTracker - 12D FLUME VAE)              │
│     └─ Map execution through 12D universe                        │
│     └─ Record exploration trajectory                             │
│     └─ Persist to vault                                          │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Phase 5B Components

### Component 1: RedisSemanticCache (5B.1)

**Purpose**: Distributed semantic caching across multiple executor instances

```
Request for skill "budget analysis"
│
├─ L1 (Hash): Direct lookup by exact query → MISS
│
├─ L2 (Cosine): Find similar cached queries
│  ├─ "cost analysis" (similarity: 0.92) → HIT ✅
│  └─ Result: Return cached embedding + response
│
└─ L3 (Redis): Team-wide cache if L1/L2 miss
   ├─ Check Redis: key = hash(query)
   └─ If hit: Return with TTL validation
```

**Files**:
- Primary: `src/cohezion/cache/redis_semantic_cache.py` (450+ lines)
- Tests: `tests/cache/test_redis_semantic_cache.py` (200+ lines)
- Config: TTL (3600s default), Redis host/port, DB selection

**API**:
```python
cache = RedisSemanticCache(redis_host="localhost", redis_port=6379)

# Get (tries L1 → L2 → L3)
hit, result = cache.get(query="find budget data")

# Put (stores in L1/L2, async to L3)
cache.put(query="find budget data", embedding=vec, result=data)

# Clear
cache.clear()
```

**Graceful Fallback**: If Redis unavailable, falls back to L1/L2 local cache (no degradation)

---

### Component 2: SkillConsensusVoter (5B.2)

**Purpose**: Multi-agent democratic skill selection via consensus voting

```
5 Agents evaluating which skill to use for "code review":
│
├─ Agent-1 votes: [CodeReviewPro (0.95), StaticAnalyzer (0.75), ...]
├─ Agent-2 votes: [CodeReviewPro (0.92), SecurityLinter (0.80), ...]
├─ Agent-3 votes: [CodeReviewPro (0.88), StaticAnalyzer (0.70), ...]
├─ Agent-4 votes: [StaticAnalyzer (0.85), CodeReviewPro (0.70), ...]
└─ Agent-5 votes: [CodeReviewPro (0.90), StaticAnalyzer (0.80), ...]

Voting Strategies:
│
├─ MAJORITY: 4/5 agree → CodeReviewPro wins (confidence: 0.8)
│
├─ WEIGHTED: By agent coherence history
│  └─ Agent-1 (0.95 coherence) counts more than Agent-4 (0.65 coherence)
│  └─ CodeReviewPro wins (confidence: 0.87)
│
└─ UNANIMOUS: Need all 5 to agree → FAIL → fallback to single-best
   └─ Ranking by: skill_rank × agent_coherence
   └─ CodeReviewPro wins (confidence: 0.88)

Persistence: Non-blocking vault recording
└─ voting-consensus-{strategy}-{timestamp}.md
```

**Files**:
- Primary: `src/cohezion/compound/skill_consensus_voter.py` (570+ lines)
- Tests: `tests/compound/test_skill_consensus_voter.py` (886 lines, 33 tests)

**API**:
```python
voter = SkillConsensusVoter(strategy=VotingStrategy.WEIGHTED)

# Collect agent votes
votes = [
    AgentVote(agent_id="agent-1", ranked_skills=[...], coherence=0.95),
    AgentVote(agent_id="agent-2", ranked_skills=[...], coherence=0.88),
    # ... more votes
]

# Get consensus
result = voter.vote(votes)
# ConsensusResult:
#   - consensus_skill: "CodeReviewPro"
#   - confidence: 0.87
#   - votes_for: 4
#   - votes_total: 5
#   - runner_up: "StaticAnalyzer"
#   - fallback_used: False

# Fallback for single agent
single_result = voter.fallback_single_best(votes=[one_vote])
```

---

### Component 3: GlobalMetricsAggregator (5B.3)

**Purpose**: Cross-instance distributed metrics collection and aggregation

```
Multiple Executor Instances Recording Metrics:
│
├─ Instance-1: 50 executions, 12,500 tokens, 0.92 avg coherence, 0.85 cache hit
├─ Instance-2: 45 executions, 11,000 tokens, 0.89 avg coherence, 0.82 cache hit
├─ Instance-3: 60 executions, 14,200 tokens, 0.94 avg coherence, 0.88 cache hit
│
Dashboard Query: "Show metrics for last 24 hours"
│
├─ Time Window: 24h rolling window
├─ Aggregations:
│  ├─ Total executions: 155
│  ├─ Total tokens: 37,700
│  ├─ Avg coherence: 0.92 (p50: 0.91, p95: 0.94)
│  ├─ Avg cache hit rate: 0.85
│  └─ Cost: $0.75 (if 1.5¢ per 100 tokens)
│
└─ Per-Skill Trends:
   ├─ CodeReviewPro: 45 executions, 0.95 coherence trend ↗
   ├─ BudgetAnalyzer: 40 executions, 0.88 coherence trend →
   └─ SecurityLinter: 35 executions, 0.90 coherence trend ↗
```

**Files**:
- Primary: `src/cohezion/compound/global_metrics_aggregator.py` (680+ lines)
- Tests: `tests/compound/test_global_metrics_aggregator.py` (400+ lines, 44 tests)

**API**:
```python
agg = GlobalMetricsAggregator()

# Record instance metrics
agg.record_instance_metrics(InstanceMetrics(
    instance_id="executor-1",
    total_executions=50,
    total_tokens=12500,
    avg_coherence=0.92,
    cache_hit_rate=0.85
))

# Query dashboard (5-min rolling window)
dashboard = agg.get_dashboard_snapshot()
# Returns: execution rate, token rate, coherence trend, cache performance

# Query time range
metrics = agg.query_time_window(
    start_time=datetime.now() - timedelta(days=1),
    end_time=datetime.now()
)
# Returns: p50/p95/p99 latencies, throughput, per-skill trends

# Export to vault
agg.export_to_vault(filepath="/cloud-vault-mcp/vault/metrics/...")
```

---

### Component 4: SessionPersistence (5B.4)

**Purpose**: Vault-backed session storage with hot-loading and recovery

```
Session Lifecycle:
│
├─ Start Session: Create SessionState
│  └─ Persist: snapshot to vault (fast, non-blocking)
│
├─ Execute Tasks: Record intermediate results
│  └─ Persist: incremental results to JSONL
│
├─ Complete Session: Save final state
│  └─ Persist: full state to vault + coherence tracking
│
└─ Recovery: If crash, restore from snapshot
   └─ Load: SessionSnapshot (100B metadata) in <10ms
   └─ State: Full state on-demand (~10ms from JSONL)

Crash Recovery Process:
│
├─ Detect: Mark session as "crashed"
│  ├─ cleanup_crashed_sessions()
│  └─ Resume from last checkpoint
│
└─ Coherence Tracking:
   ├─ Record skill coherence per execution
   ├─ Query: most_recent_skill_executions()
   └─ Aggregate: skill_coherence_history()
```

**Files**:
- Primary: `src/cohezion/compound/session_manager_persistence.py` (600+ lines)
- Tests: `tests/compound/test_session_manager_persistence.py` (400+ lines, 34 tests)
- Storage: Vault primary, JSONL fallback (`data/compound/sessions/`)

**API**:
```python
persist = SessionPersistence()

# Save session state (non-blocking)
persist.save_session(
    session_id="sess-123",
    state=session_state,
    cost_breakdown={"gpt-4": 0.05, "claude": 0.02}
)

# Hot-load sessions (fast startup)
snapshots = persist.list_sessions()  # 100+ sessions <400ms
snapshot = snapshots[0]  # SessionSnapshot: id, created, status, cost

# Load full state on-demand
full_state = persist.load_session(session_id="sess-123")  # 10ms

# Query skill coherence across sessions
history = persist.get_skill_history(skill_name="CodeReviewPro", limit=10)
# Most recent executions first, coherence trending

# Crash recovery
crashed = persist.cleanup_crashed_sessions()
# Marks crashed sessions as "crashed", ready for replay
```

---

### Component 5: CostAwareRouter (5B.5)

**Purpose**: Route queries to appropriate models based on cost/complexity

```
Query: "Analyze code repository for security issues"
│
├─ Complexity Analysis:
│  ├─ Code size: large (5K+ lines)
│  ├─ Scope: cross-file analysis
│  ├─ Precision: high (security critical)
│  └─ Estimated cost: $0.50 (GPT-4) vs $0.05 (Claude 3)
│
├─ Budget Check:
│  ├─ Session budget: $5.00 remaining
│  ├─ Team budget: $100.00 remaining
│  └─ Monthly budget: $1000.00 remaining
│
└─ Routing Decision:
   ├─ IF high precision AND budget OK → GPT-4 (best accuracy)
   ├─ ELIF medium precision AND budget OK → Claude 3 (good, cheaper)
   ├─ ELIF low budget AND high precision needed → GPT-3.5 (cheaper)
   └─ IF budget exhausted → Deny request or queue for later

Cost Tracking:
│
├─ SessionCostTracker: per-session costs
├─ TeamMetricsAggregator: per-team aggregation
└─ GlobalMetricsAggregator: cross-team trends
```

**Files**:
- Primary: `src/cohezion/swarm/cost_aware_router.py` (400+ lines)
- Tests: `tests/swarm/test_cost_aware_router.py` (200+ lines, 20 tests)

**API**:
```python
router = CostAwareRouter()

# Route with complexity analysis
route_result = router.route_query(
    query="Analyze code for security",
    session_budget_remaining=5.00,
    team_budget_remaining=100.00
)
# Returns: ModelRoute with selected_model, estimated_cost, rationale

# Track execution cost
router.record_execution(
    query_id="q-123",
    model="gpt-4",
    tokens_used=2000,
    cost_usd=0.12
)

# Budget enforcement
if router.is_budget_exhausted(session_id="s-123"):
    # Queue for later or deny request
    pass
```

---

## Integration Points

### Between Components

```
CompoundExecutor Pipeline:
│
├─ Step 1 (Query Vault):
│  └─ Uses: RedisSemanticCache.get()
│
├─ Step 4 (Execute):
│  └─ Uses: SkillSelector (vault-driven ranking)
│  └─ Then: SkillConsensusVoter.vote() if multi-agent
│
├─ Step 7 (Extract Patterns):
│  └─ Uses: SkillRefiner to update coherence
│
├─ Step 8 (Record Metrics):
│  └─ Uses: GlobalMetricsAggregator.record_instance_metrics()
│
├─ Step 9 (Track Journey):
│  └─ Uses: JourneyTracker with session persistence
│
└─ Session Management:
   └─ Uses: SessionPersistence.save_session()
   └─ Uses: SessionCostTracker for budget tracking
   └─ Uses: CostAwareRouter for next query routing
```

### With MCP Server

```
MCP Server ← Claude Code
│
├─ vault_read: Read vault documents
│  └─ VaultOps.read() → return JSON/text
│
├─ vault_write: Write decisions/findings to vault
│  └─ VaultOps.write() → git commit
│
├─ vault_search: Full-text search vault
│  └─ Query vault git history
│
└─ vault_list: List directory contents
   └─ Return markdown files in directory
```

---

## Data Flow Example

**Scenario**: Execute a "code review" task with Phase 5B components

```
1. Claude Code sends query to MCP server
   └─ Vault read: Get code review guidelines (via vault_read)

2. CompoundExecutor receives request
   └─ Step 1: Query vault for similar code reviews
   │  └─ RedisSemanticCache.get() → L1 (miss) → L2 (hit!) → return cached result
   └─ Step 4: Select skill (CodeReviewPro)
      ├─ SkillSelector ranks by vault coherence
      ├─ If team: SkillConsensusVoter asks 3 agents to vote
      │  └─ Result: CodeReviewPro wins (3/3 agents agree, confidence: 0.95)
      └─ Execute CodeReviewPro skill

3. Skill executes (calls Anthropic API)
   └─ CostAwareRouter checked budget first (OK, $4.50 remaining)
   └─ Execution cost: $0.30

4. After execution
   └─ Step 5-7: Update skill coherence (0.93 → 0.94)
   └─ Step 8: Record metrics
      └─ GlobalMetricsAggregator.record_instance_metrics()
   └─ Step 9: Track journey (12D FLUME)
   └─ Session: Save to vault with cost tracking ($4.20 remaining)

5. Result persisted back to vault
   └─ vault_write: Store code review findings
   └─ Decision document created with timestamp
   └─ Git commit: "code review findings - high coherence match"

6. Future queries benefit
   └─ New code review query hits RedisSemanticCache
   └─ Same findings returned (15% token savings)
```

---

## Deployment Topology

```
Production Environment:
│
├─ Executor Instance 1 (Agent-1)
│  ├─ CompoundExecutor (11-step pipeline)
│  ├─ Local SemanticCache (L1/L2)
│  └─ Session persistence (to vault + local JSONL)
│
├─ Executor Instance 2 (Agent-2)
│  ├─ CompoundExecutor (11-step pipeline)
│  ├─ Local SemanticCache (L1/L2)
│  └─ Session persistence (to vault + local JSONL)
│
├─ Executor Instance 3 (Agent-3) [Optional]
│  ├─ CompoundExecutor (11-step pipeline)
│  ├─ Local SemanticCache (L1/L2)
│  └─ Session persistence (to vault + local JSONL)
│
├─ Shared Services:
│  ├─ Redis (L3 distributed cache)
│  │  └─ Replicated across instances (optional)
│  │
│  ├─ Vault Repository (.git directory)
│  │  └─ Shared network mount or SSH access
│  │
│  ├─ MCP Server (vault gateway)
│  │  └─ Running on port 8360
│  │  └─ Listens for Claude Code requests
│  │
│  └─ Monitoring
│     ├─ Health checks (every 10s)
│     ├─ Metrics aggregation (every 1m)
│     └─ Cost tracking (every 5m)
│
└─ External Services:
   ├─ Anthropic API (GPT-4, Claude-3, GPT-3.5)
   └─ GitHub (vault git remote, if using)
```

---

## Performance Characteristics

| Operation | Latency | Throughput | Notes |
|-----------|---------|-----------|-------|
| Cache hit (L1) | <1ms | N/A | In-memory hash |
| Cache hit (L2) | 5-50ms | N/A | Cosine similarity |
| Cache hit (L3) | 20-100ms | N/A | Redis round-trip |
| Vault write | 50-200ms | 5-10/sec | Atomic with lock |
| Consensus vote (3 agents) | 10-50ms | N/A | Local aggregation |
| Metrics record | <5ms | 100+/sec | Non-blocking async |
| Session save | 10-100ms | 1-5/sec | Async to vault |
| Dashboard query | <500ms | N/A | Cached, 5m window |

---

## Scaling Considerations

### For Small Teams (1-3 agents)
- Single-machine deploymen fine
- Local SemanticCache (L1/L2) sufficient
- File locking handles concurrent access
- No Redis needed

### For Medium Teams (4-10 agents)
- Recommend Redis L3 cache
- Vault on NFS mount or SSH
- Monitor memory usage
- Daily vault backups

### For Large Teams (10+ agents)
- Redis cluster (Phase 5C)
- Vault sharding (Phase 5C)
- Dedicated MCP server farm
- Advanced monitoring/alerting
- Consider upgrade to full multi-region

---

**Status**: Architecture Documented ✅
**Scalability**: Validated for 1-10 agents, Phase 5C covers 10+ agents
**Last Updated**: 2026-02-09
