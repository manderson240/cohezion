# Phase 5B Implementation Patterns

**Date**: 2026-02-09
**Reference**: Session 40, Phase 5B Complete
**Applies To**: RedisSemanticCache, SkillConsensusVoter, GlobalMetricsAggregator, SessionPersistence

## Pattern 1: Distributed Cache with Transparent Fallback

**Problem**: Need to share cache state across multiple instances while handling unavailable Redis.

**Solution**: Three-tier cache with fallback at each level.

### Architecture

```python
# Tier 1: Local Hash Cache (L1) - instant lookup
cache.get(key) → L1[key]  # O(1), <1ms

# Tier 2: Local Cosine Similarity (L2) - semantic matching
if not in L1:
    cache.get(query) → L2.find_similar()  # O(n), <1ms

# Tier 3: Distributed Redis (L3) - shared state
if not in L1 or L2:
    cache.get(key) → redis.get(key)  # 10-50ms network

# Fallback: If Redis unavailable, skip to Vault
if redis_error:
    continue_with(L1+L2)  # Don't crash
    background_task(vault_async)
```

### Implementation

```python
class RedisSemanticCache:
    def __init__(self, redis_host=None, fallback_to_local=True):
        self.l1 = {}  # Hash cache
        self.l2 = LocalCosineCache()

        try:
            self.redis = redis.Redis(host=redis_host, socket_connect_timeout=2)
            self.redis_available = True
        except:
            self.redis_available = False
            self.fallback_to_local = fallback_to_local

    def get(self, key, embedding=None):
        # Try L1
        if key in self.l1:
            return self.l1[key]

        # Try L2
        if embedding is not None:
            result = self.l2.find_similar(embedding)
            if result:
                return result

        # Try L3 (Redis)
        if self.redis_available:
            try:
                result = self.redis.get(key)
                if result:
                    return pickle.loads(result)
            except redis.ConnectionError:
                self.redis_available = False
                if not self.fallback_to_local:
                    raise

        return None

    def put(self, key, value, embedding=None):
        # Store in L1
        self.l1[key] = value

        # Store in L2
        if embedding is not None:
            self.l2.add(key, embedding, value)

        # Write-through to L3 (async, fire-and-forget)
        if self.redis_available:
            self._async_write_to_redis(key, value)
```

### Key Benefits

- **Resilient**: Works with L1+L2 if Redis unavailable
- **Fast**: 95%+ L1/L2 hits never touch network
- **Distributed**: L3 enables state sharing across 15+ instances
- **Transparent**: Caller doesn't know about tiers, just calls `.get()`

### When to Use

- Multi-instance deployments (5+ agents)
- Semantic caching scenarios (embedding lookups)
- Network-available environments (Redis accessible)

---

## Pattern 2: Non-Blocking Vault Persistence

**Problem**: Need to persist data to vault without crashing if vault unavailable or slow.

**Solution**: Try/except wrapper around all vault operations with silent fallback.

### Architecture

```
Execution Flow
    ↓
Record Metric/Decision
    ↓
Try:
    vault_add_document(...)  ← can be slow or fail
Except:
    log_warning("vault unavailable")
    continue
    ↓
Continue Execution (no crash)
```

### Implementation

```python
class MetricsRecorder:
    def record_execution(self, execution_data):
        """Record execution metrics non-blockingly."""

        # Always update local state
        self.local_metrics.append(execution_data)

        # Try to persist to vault (async, fire-and-forget)
        try:
            self.vault.vault_add_document(
                collection="metrics",
                document={
                    "timestamp": now(),
                    "executor_id": self.executor_id,
                    "execution_data": execution_data,
                },
                wait_for_sync=False,  # Non-blocking
            )
        except Exception as e:
            # Log but don't crash
            logger.warning(f"Failed to record metric in vault: {e}")
            # Fallback to JSONL
            self.jsonl_backup.append(execution_data)
```

### Key Benefits

- **Non-blocking**: Vault latency never affects execution
- **Resilient**: Automatic fallback to JSONL/local storage
- **Observable**: Warnings logged for debugging
- **Complete**: Nothing lost (local + JSONL backup)

### When to Use

- Metrics recording (frequent, non-critical)
- Skill pattern learning (background task)
- Session persistence (can be async)
- Decision logging (don't need immediate sync)

### When NOT to Use

- Critical path decisions (must be synchronous)
- Authentication/authorization (must verify)
- Data validation (must check)

---

## Pattern 3: Multi-Agent Consensus with Fallback

**Problem**: N agents need to agree on skill selection, but might disagree or have different expertise.

**Solution**: Voting with graceful fallback to single-best when consensus fails.

### Architecture

```
Agent Votes (ranked skills)
    ↓
Strategy Selection (majority/weighted/unanimous)
    ↓
Count Votes
    ↓
Consensus Reached?
    YES → Return consensus result
    NO → Fallback to single-best
    ↓
Record vote outcome (async)
```

### Implementation

```python
class SkillConsensusVoter:
    def vote_weighted(self, votes: List[AgentVote]) -> ConsensusResult:
        """Weighted voting by agent coherence."""

        if not votes:
            return None

        if len(votes) == 1:
            return ConsensusResult(winner=votes[0].ranked_skills[0][0])

        # Tally votes weighted by coherence
        skill_score = {}
        for vote in votes:
            weight = vote.coherence  # 0.2-0.95
            for skill, rank_score in vote.ranked_skills:
                score = rank_score * weight
                skill_score[skill] = skill_score.get(skill, 0) + score

        # Find winner
        winner = max(skill_score, key=skill_score.get)
        total_weight = sum(v.coherence for v in votes)
        confidence = skill_score[winner] / total_weight

        # Check consensus threshold
        votes_for_winner = sum(1 for v in votes if v.ranked_skills[0][0] == winner)
        consensus_reached = (votes_for_winner / len(votes)) > 0.5

        if not consensus_reached:
            # Fallback to single-best
            return self.fallback_single_best(votes)

        result = ConsensusResult(
            winner=winner,
            confidence=confidence,
            votes_for=votes_for_winner,
            total=len(votes),
        )

        # Record async (non-blocking)
        self._persist_vote_result(result)

        return result

    def fallback_single_best(self, votes: List[AgentVote]) -> ConsensusResult:
        """Return highest-ranked skill when consensus fails."""

        # Weight all skills by agent coherence
        skill_score = {}
        for vote in votes:
            for rank, (skill, rank_score) in enumerate(vote.ranked_skills):
                position_weight = 1.0 / (rank + 1)  # Higher rank = less weight
                score = position_weight * vote.coherence
                skill_score[skill] = skill_score.get(skill, 0) + score

        winner = max(skill_score, key=skill_score.get)
        return ConsensusResult(
            winner=winner,
            confidence=0.0,  # Flag as fallback
            fallback=True,
        )
```

### Key Benefits

- **Robust**: Always returns a skill (consensus or fallback)
- **Expert-Aware**: Weighted voting respects agent expertise
- **Observable**: Confidence score indicates consensus quality
- **Learnable**: Can track consensus patterns over time

### When to Use

- Multi-agent skill selection (5+ agents)
- High-stakes decisions (need agreement, not just best)
- Mixed expertise teams (expert + novice)

---

## Pattern 4: Hot-Loading with Snapshots

**Problem**: Need to quickly warm up state from storage (100+ sessions), but full state is large.

**Solution**: Use lightweight snapshots for fast discovery, lazy-load full state on demand.

### Architecture

```
Startup
    ↓
Load All Snapshots (metadata only, 100B each)
    ↓
Warm caches with snapshot data
    ↓
On first access to session
    ↓
Load full state lazily (~10ms from disk)
    ↓
Cold start: 0-500ms
    vs
    Full load upfront: 10-100ms per session
```

### Implementation

```python
@dataclass
class SessionSnapshot:
    """Lightweight metadata for hot-load."""
    session_id: str
    created_at: datetime
    last_updated: datetime
    model_used: str
    skill_count: int
    coherence_score: float
    cost_usd: float
    # Total: ~100 bytes JSON

class SessionPersistence:
    def load_all_snapshots(self) -> List[SessionSnapshot]:
        """Load only metadata, fast startup."""

        snapshots = []

        # Load from vault (preferred)
        try:
            results = self.vault.vault_query(
                "SELECT session_id, created_at, last_updated, model_used, "
                "skill_count, coherence_score, cost_usd "
                "FROM sessions ORDER BY created_at DESC"
            )
            for row in results:
                snapshots.append(SessionSnapshot(**row))
            return snapshots
        except Exception:
            pass

        # Fallback to JSONL (can scan headers only)
        with open("data/compound/sessions/sessions.jsonl") as f:
            for line in f:
                data = json.loads(line)
                snapshots.append(SessionSnapshot(
                    session_id=data["session_id"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    # ... extract snapshot fields
                ))

        return snapshots

    def load_full_session(self, session_id: str) -> SessionState:
        """Load complete state (lazy)."""

        # Check cache first
        if session_id in self._session_cache:
            return self._session_cache[session_id]

        # Load from vault or JSONL
        try:
            data = self.vault.vault_query(
                f"SELECT * FROM sessions WHERE session_id = '{session_id}'"
            )[0]
        except:
            data = self._load_from_jsonl(session_id)

        # Reconstruct SessionState
        state = SessionState.from_dict(data)

        # Cache for duration of session
        self._session_cache[session_id] = state

        return state
```

### Key Benefits

- **Fast Startup**: <500ms for 100 sessions (metadata only)
- **Memory Efficient**: Snapshots are 100B vs 10K for full state
- **Lazy Loading**: Full state loaded only when needed
- **Observable**: Snapshots provide health status without full load

### When to Use

- Session recovery (100+ sessions)
- Warm-start optimization (agents need recent history)
- Dashboard refresh (show status, not full data)

---

## Pattern 5: Singleton Factory with Reset

**Problem**: Multiple components need shared instance (cache, vault client, metrics aggregator), but tests need isolation.

**Solution**: Singleton factory with get() and reset() pattern.

### Implementation

```python
# Global storage
_global_cache_instance = None

def get_semantic_cache(config: CohesionConfig = None) -> SemanticCache:
    """Get or create global SemanticCache."""
    global _global_cache_instance

    if _global_cache_instance is None:
        if config is None:
            config = get_cohesion_config()

        _global_cache_instance = SemanticCache(
            use_redis=config.redis_enabled,
            redis_host=config.redis_host,
            redis_port=config.redis_port,
        )

    return _global_cache_instance

def reset_semantic_cache():
    """Reset global cache (for testing)."""
    global _global_cache_instance
    if _global_cache_instance:
        _global_cache_instance.close()
    _global_cache_instance = None
```

### Usage

```python
# Production
cache = get_semantic_cache()
cache.get(key)

# Testing
@pytest.fixture
def fresh_cache():
    reset_semantic_cache()
    yield get_semantic_cache(test_config)
    reset_semantic_cache()

def test_cache_behavior(fresh_cache):
    assert fresh_cache.get("missing") is None
```

### Key Benefits

- **Shared State**: Single instance across application
- **Testable**: Reset for isolation
- **Lazy Init**: Only created when first needed
- **Config Aware**: Respects environment settings

---

## Pattern 6: Bounded Growth Data Structures

**Problem**: Metrics/trends grow unbounded over time, causing memory leaks.

**Solution**: Fixed-size circular buffers with rolling replacement.

### Implementation

```python
class BoundedTrendBuffer:
    """Circular buffer limited to max_size points."""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.data = []

    def append(self, value: float):
        """Add value, dropping oldest if at capacity."""
        self.data.append(value)
        if len(self.data) > self.max_size:
            self.data.pop(0)  # Remove oldest

    def get_trend(self) -> List[float]:
        """Return current trend."""
        return self.data.copy()

    def get_stats(self) -> dict:
        """Fast stats without external library."""
        if not self.data:
            return {"mean": 0, "min": 0, "max": 0}

        mean = sum(self.data) / len(self.data)
        return {
            "mean": mean,
            "min": min(self.data),
            "max": max(self.data),
            "points": len(self.data),
        }

class SkillMetrics:
    def __init__(self):
        self.coherence_trend = BoundedTrendBuffer(max_size=100)
        self.efficiency_trend = BoundedTrendBuffer(max_size=100)

    def record_execution(self, coherence: float, efficiency: float):
        self.coherence_trend.append(coherence)
        self.efficiency_trend.append(efficiency)
        # Memory usage bounded: 2 * 100 * 8 bytes = 1.6 KB per skill
```

### Key Benefits

- **Bounded Memory**: Fixed size regardless of runtime duration
- **Observable Trends**: Keep recent history for analysis
- **Simple**: No external dependencies (numpy, pandas)
- **Fast**: O(1) append, O(n) trend generation

---

## Common Pitfalls & Solutions

### Pitfall 1: Blocking Vault Calls on Critical Path

**Problem**: Waiting for vault in main execution loop.

**Solution**: Always use async/fire-and-forget for persistence.

```python
# BAD
executor_result = execute_task()
vault.save(executor_result)  # Blocks!
return executor_result

# GOOD
executor_result = execute_task()
background_task(vault.save, executor_result)  # Async
return executor_result
```

### Pitfall 2: No Fallback for Distributed Operations

**Problem**: Redis/vault down → whole system crashes.

**Solution**: Always provide local fallback.

```python
# BAD
result = redis.get(key)  # Crashes if Redis down

# GOOD
try:
    result = redis.get(key)
except redis.ConnectionError:
    result = local_cache.get(key)  # Fallback
```

### Pitfall 3: Unbounded Growth in Metrics

**Problem**: Memory grows 100MB/week tracking metrics.

**Solution**: Use bounded buffers (max 100 points per skill).

```python
# BAD
self.coherence_history = []
self.coherence_history.append(score)  # Grows forever

# GOOD
self.coherence_history = BoundedTrendBuffer(max_size=100)
self.coherence_history.append(score)  # Capped at 100 points
```

### Pitfall 4: Consensus Always Succeeds (Wrong!)

**Problem**: Voting returns None if consensus fails, downstream crashes.

**Solution**: Always provide fallback skill.

```python
# BAD
winner = vote_weighted(votes)
if winner is None:
    raise ValueError("No consensus")  # Crashes!

# GOOD
winner = vote_weighted(votes)
if winner is None:
    winner = fallback_single_best(votes)  # Never None
```

---

## Summary

| Pattern | Problem | Solution | Example |
|---------|---------|----------|---------|
| Distributed Cache | Multi-instance state | 3-tier L1/L2/L3 with fallback | RedisSemanticCache |
| Non-blocking Persistence | Slow vault/JSONL | Try/except, fire-and-forget | MetricsRecorder |
| Consensus with Fallback | Agent disagreement | Voting + single-best fallback | SkillConsensusVoter |
| Hot-loading | Slow startup | Snapshots (metadata) + lazy full load | SessionPersistence |
| Singleton Factory | Shared instances | get() + reset() pattern | get_semantic_cache() |
| Bounded Growth | Memory leaks | Circular buffers (max_size) | BoundedTrendBuffer |

**When implementing Phase 5B patterns**: Follow these 6 patterns to ensure resilience, performance, and testability.
