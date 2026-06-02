---
name: reliability
description: "System reliability patterns: circuit breakers, connection pooling, graceful degradation, and high-availability persistence fallback (primary/buffer duality, reconciliation, checksum integrity) for AI services. Use when implementing fault tolerance, handling cascading failures, designing persistence-layer fallback when the primary DB is offline, or when user mentions 'circuit breaker', 'connection pool', 'graceful degradation', 'fallback buffer', or 'reliability'. Skip: for API multi-provider fallback use API_ERROR_RESILIENCE_PRIME."
metadata:
  version: "1.0"
  legacy-name: RELIABILITY_PRIME
---

# SKILL: RELIABILITY_PRIME

## DOMAIN EXPERTISE
You are a specialist in **system reliability** - circuit breakers, connection pooling, and failure handling.

## KEY CONCEPTS
- **Circuit Breaker** - Stop cascading failures
- **Connection Pool** - Reuse HTTP connections
- **Graceful Degradation** - Fail safely
- **Primary-Buffer Duality** - Write to a high-speed local buffer (Obsidian/JSONL) when the primary DB is unreachable
- **Reconciliation Loop** - Sync buffered contents back to the primary DB once connectivity is restored
- **Checksum Integrity** - Use SHA-256 (or similar) to verify replayed data hasn't drifted

## INSTRUCTION

### 1. Circuit Breaker
```python
from cohezion.reliability import get_circuit

breaker = get_circuit("ollama", failure_threshold=5)

if breaker.allow_request():
    try:
        result = make_request()
        breaker.record_success()
    except Exception:
        breaker.record_failure()
else:
    return fallback_response()
```

### 2. Connection Pool
```python
from cohezion.reliability.pool import get_pool

pool = get_pool("ollama", "http://localhost:11434", max_connections=20)
response = await pool.post("/api/generate", json=payload)
```

### 3. States
| State | Behavior |
|-------|----------|
| CLOSED | Normal operation |
| OPEN | Reject all, wait for recovery |
| HALF_OPEN | Test with limited calls |

## HIGH-AVAILABILITY PERSISTENCE FALLBACK (Hermetic Persistence Pattern)

For persistence layers that must maintain integrity even when the primary database
(SurrealDB, Postgres, etc.) is offline or unreachable. Implements "Asynchronous
Dual-Write" buffering and "Linear Replay" recovery.

1. **Detect Failure Mode**
   ```python
   try:
       await self.primary_db.write(data)
   except PersistenceError:
       logger.warning("Primary DB offline. Falling back to buffer.")
       self.fallback_active = True
   ```

2. **Execute Buffered Write**
   Always append to a robust, line-delimited format (JSONL) to prevent corruption.
   ```python
   with open(self.buffer_path, "a") as f:
       f.write(json.dumps(data) + "\n")
   ```

3. **Trigger Recovery Sync**
   Check health periodically and replay missed transactions sequentially.
   ```python
   if await self.primary_db.is_healthy():
       await self.replay_buffer()
   ```

### Persistence Fallback Best Practices
- **Atomic Fallbacks**: Ensure the fallback logic itself doesn't depend on complex external state.
- **Conflict Resolution**: Use timestamps (Time-1 dimension) to resolve "Last Write Wins" conflicts during sync.
- **HIHO 0.5 Compliance**: Maintain 0.5 coherence overlap between primary and buffer states.

## SEE ALSO
- SELF_HEALING_PRIME.md
- API_ERROR_RESILIENCE_PRIME.md
- SURREALDB_MCP_PRIME.md
- AUTONOMOUS_RESILIENCE_PRIME.md
- RECOVERY_PRIME.md
