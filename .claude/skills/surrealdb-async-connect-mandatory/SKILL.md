---
name: surrealdb-async-connect-mandatory
description: |
  Fix for TypeError or silent failures with surrealdb-py v0.3.0+ in async code.
  Use when: (1) removing or skipping `await db.connect()` inside `async with AsyncSurreal()`,
  (2) code review flags db.connect() as "redundant" after async context manager,
  (3) TypeError on `await db.use()` or `await db.signin()`, (4) migrating from
  `Surreal` (sync) to `AsyncSurreal` (async). Key rule: `await db.connect()` is
  MANDATORY even when using `async with AsyncSurreal(...)` — __aenter__ does NOT connect.
---

# SurrealDB AsyncSurreal — Mandatory connect()

## Problem

In `surrealdb-py` v0.3.0+, using `AsyncSurreal` as an async context manager does
**not** automatically call `connect()`. Code that skips `await db.connect()` after
`async with AsyncSurreal(...) as db:` will fail with `TypeError` or silent errors
when calling `await db.signin()` or `await db.use()`.

This looks like a false positive during code review — Python async context managers
conventionally handle setup in `__aenter__`. But this library does not follow that
convention.

## Rule (from KEY_LEARNINGS.md Learning 158)

```python
# CORRECT — always call connect() explicitly
async with AsyncSurreal("ws://localhost:8000") as db:
    await db.connect()        # MANDATORY — __aenter__ does NOT connect
    await db.signin({"user": "root", "pass": "root"})
    await db.use("myns", "mydb")
    # ... queries ...

# WRONG — skipping connect() causes TypeError on signin/use
async with AsyncSurreal("ws://localhost:8000") as db:
    await db.signin(...)  # TypeError: no connection
```

## Also Important

The sync `Surreal` client's `use()` method is synchronous — don't `await` it.
Use `AsyncSurreal` for all async contexts, `Surreal` for sync:

```python
# Sync client (Surreal): use() is synchronous
db = Surreal("ws://localhost:8000")
db.connect()
db.signin({"user": "root", "pass": "root"})
db.use("myns", "mydb")           # NOT awaited

# Async client (AsyncSurreal): all methods async
async with AsyncSurreal("ws://localhost:8000") as db:
    await db.connect()           # mandatory
    await db.signin(...)
    await db.use(...)            # awaited
```

## Code Review Gotcha

When reviewing this codebase, do **not** flag `await db.connect()` inside
`async with AsyncSurreal()` as redundant. It is required per Learning 158 and
the surrealdb-py v0.3.0+ API.

## Verification

```bash
# If connect() is missing, you'll see:
# TypeError: argument should be a str or an Awaitable, got ...
# or queries silently return empty results

# Correct pattern check:
grep -A3 "async with AsyncSurreal" src/cohezion/mcp/servers/doc/server.py
# Should show: await db.connect() on the next line
```

## References

- `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` — Learning 158
- Applied in PR #38: migrated `doc/indexer.py`, `memory/server.py`, `scripts/*.py`
  to `AsyncSurreal` with mandatory `connect()` call
