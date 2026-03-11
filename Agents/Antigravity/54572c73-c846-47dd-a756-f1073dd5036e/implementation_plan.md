---
type: antigravity-artifact
session_id: 54572c73-c846-47dd-a756-f1073dd5036e
date: 2026-03-04
title: "Compound Engineering Phase 8 - Production Hardening"
tags: [agent-output, antigravity, production-hardening, caching]
aspect: doer
neural:
  activation: 0.353
  stage: embryo
  cluster: Agents
---

# Implementation Plan - Phase 7: Resilience & Scale

This plan implements connection pooling and circuit breakers to ensure the Cohezion ecosystem can scale to the "10k Universe" without cascading failures or resource exhaustion.

## User Review Required

> [!IMPORTANT]
> This change will transition `BaseAgent` from individual `httpx.AsyncClient` instances to a shared `ConnectionPool`. This reduces memory overhead and improves latency but requires careful management of pool limits.

## Proposed Changes

### [Reliability Layer]

#### [MODIFY] [pool.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/reliability/pool.py)
- Ensure the `get_pool` function is robust and handles default limits correctly.

#### [MODIFY] [base.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/base.py)
- Update `client` property to use `get_pool()`.
- Wrap `_call_ollama` logic in a circuit breaker.

---

### [Database Layer]

#### [MODIFY] [surreal_client.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/db/surreal_client.py)
- Integrate `CircuitBreaker` into `connect`, `query`, and `store_node` methods.
- (Optional) Explore pooling for SurrealDB HTTP fallbacks.

## Verification Plan

### Automated Tests
- `run_command`: `export PYTHONPATH=$PYTHONPATH:/home/mike-anderson/dev/cohezion/src && uv run python3 tests/test_phase_7_resilience.py`
- Test cases:
    - **Pool Sharing**: Verify that two agents use the same underlying client.
    - **Circuit Open**: Force failures and verify that the circuit opens and rejects calls.
    - **Circuit Recovery**: Verify that the circuit transitions to HALF_OPEN after the timeout.

### Manual Verification
- Monitor open file descriptors during a high-concurrency swarm run to confirm connection reuse.

## Related Vault Notes

- [[cohezion]]
- [[api-design]]
