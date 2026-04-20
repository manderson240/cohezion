---
title: 'AsyncMock for Subprocess Calls — Prevent Network Hangs in Tests'
date: 2026-02-23
tags: [pattern]
aspect: thinker
neural:
  activation: 0.67
  stage: growing
  synapse_in: 6
  synapse_out: 8
---
# Pattern: AsyncMock for Subprocess Calls — Prevent Network Hangs in Tests

**Domain**: testing, async, python
**Source**: `tests/unit/test_emergency_shutdown_logic.py`
**Discovered**: Session 70 — 2026-02-22

## Problem

1. **Subprocess hang**: Production code calling `asyncio.create_subprocess_exec` (e.g., `curl` to Ollama) hangs indefinitely when the service is unavailable. Tests that don't mock it hang in CI.

2. **asyncio.Future anti-pattern**: `MagicMock(side_effect=asyncio.Future)` creates Futures that are never resolved — `await mock.method()` hangs forever.

## Solution

### For subprocess calls — mock at call site
```python
mock_proc = MagicMock()
mock_proc.communicate = AsyncMock(return_value=(b'{"models": []}', b""))

with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
    await system_under_test.method_that_calls_curl(vitals)

# Verify the mock was called if needed:
# assert mock_proc.communicate.called
```

### For async semaphore/lock — use AsyncMock, not Future
```python
# ❌ BAD — Future never resolved, await hangs forever
monitor.semaphore.acquire = MagicMock(side_effect=asyncio.Future)

# ✅ GOOD — AsyncMock returns immediately
monitor.semaphore = MagicMock()
monitor.semaphore.acquire = AsyncMock(return_value=None)
await monitor.wait_for_capacity()  # Completes immediately
```

### For production code — always add timeouts
```python
process = await asyncio.create_subprocess_exec(
    "curl", "-s",
    "--max-time", "5",          # curl gives up after 5s
    "--connect-timeout", "3",   # TCP connect timeout 3s
    url,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
stdout, _ = await asyncio.wait_for(process.communicate(), timeout=8.0)
```

## Detection

Symptom: pytest test hangs indefinitely (not failing with error, just frozen). Usually involves:
- `asyncio.create_subprocess_exec` calls to external services
- `await` on something that uses `asyncio.Future` incorrectly

## Anti-Pattern Table

| Anti-Pattern | Symptom | Fix |
|---|---|---|
| Real curl in tests | Hangs when service down | `patch("asyncio.create_subprocess_exec", ...)` |
| `side_effect=asyncio.Future` | await hangs forever | `AsyncMock(return_value=None)` |
| No timeout on subprocess | Hangs indefinitely | `--max-time N` + `wait_for(timeout=M)` |
| `vitals["key"]` (no .get) | KeyError if key missing | `vitals.get("key", default)` |

## Related Decisions

- [[2026-02-22-asyncio-lock-in-init-not-class-level]] — sibling async testing decision from the same session
- [[2026-02-23-always-set-pytest-timeouts-for-async-tests]] — timeouts catch the hangs that mocking should prevent
- [[2026-02-24-anti-pattern-zombie-test-processes-from-async-event-loop-teardown]] — zombie processes arise from the same hang patterns this pattern prevents

## Related Patterns

- [[async-singleton-lock-isolation]] — async lock patterns that complement subprocess mocking
- [[test-mocking-pattern]] — general mocking patterns that this async-specific pattern extends
- [[service-initialization-checklist]] — subprocess calls to external services during init must be mocked in tests

## Related Concepts

- [[concept-testing]] — async subprocess mocking ensures concept tests do not depend on external service availability
- [[non-blocking-observability]] — properly mocked async calls enable non-blocking test execution
- KEY_LEARNINGS.md L133-134
