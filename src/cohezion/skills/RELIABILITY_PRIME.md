---
name: reliability
description: "System reliability patterns: circuit breakers, connection pooling, graceful degradation for AI services. Use when implementing fault tolerance, handling cascading failures, or when user mentions 'circuit breaker', 'connection pool', 'graceful degradation', or 'reliability'. Skip: for persistence-layer fallback (primary/buffer duality) use RELIABILITY_FALLBACK_PRIME; for API multi-provider fallback use API_ERROR_RESILIENCE_PRIME."
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

## SEE ALSO
- SELF_HEALING_PRIME.md
