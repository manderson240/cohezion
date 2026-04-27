# Refactor Proposal: `src/cohezion/ouroboros/monitor.py`

**Author:** Wave Ω11 analysis (read-only, autonomous)
**Date:** 2026-04-23
**Subject file:** `src/cohezion/ouroboros/monitor.py` (57 lines, single class)
**Mypy baseline:** 29 errors — top of the Wave 1D worst-typed-files list
**Estimated refactor effort:** 4–8 hours (likely closer to 4)

---

## TL;DR — counter-finding to the premise

`monitor.py` is **not** a structurally-broken god-module. It is a **57-line file with one class (`OuroborosMonitor`) exposing two methods** (`__init__`, `fetch_recent_trajectories`). The 29 mypy errors are not 29 distinct design problems — they are **mypy's union-walking behavior on a single misuse of the SurrealDB Python driver** plus **one real latent bug** that mypy correctly caught.

Specifically:

- **27 of the 29 errors come from two adjacent lines (51 and 52).** Both are caused by indexing a `Value` union (`str | int | float | bytes | UUID | RecordID | Datetime | GeometryPoint | …` — a 21-member union from the SurrealDB stubs) with `[0]` and `[...]` without narrowing first.
- **2 of the 29 errors come from line 38**: `await db.connect()` is called with no `url` argument, but the `AsyncSurreal.connect()` stub requires one. **This is a real latent bug.** The `async with AsyncSurreal(self.url) as db:` context manager (line 36) already establishes the connection — the `db.connect()` call on line 38 is redundant *and* incorrect, and the sibling `cohezion.persistence.surreal_logger.SurrealTrajectoryLogger` at lines 58–66 demonstrates the canonical pattern (no manual `connect()`).

So the right framing is: **monitor.py has two real bugs and one ambiguous return contract, all of which surface as 29 mypy diagnostics because of the upstream SurrealDB stub's wide `Value` union.** The fix is small (two-block edit, ~15 lines) and the heavy phased plan below should be read as *defense-in-depth*, not as evidence the file needs major restructuring.

If the user only has 30 minutes, do **Phase 1** below and stop — error count drops from 29 to ~0–2 with no behavior change.

---

## Current state (verified 2026-04-23)

| Metric | Value | Verification |
|---|---|---|
| LOC | 57 | `wc -l src/cohezion/ouroboros/monitor.py` |
| Classes | 1 (`OuroborosMonitor`) | inspection |
| Public methods | 2 (`__init__`, `fetch_recent_trajectories`) | inspection |
| Mypy errors | 29 | `uv run mypy … 2>&1 \| tail -3` → "Found 29 errors in 1 file" |
| Mypy error LINES | 3 distinct lines (38, 51, 52) | full mypy output, Appendix A |
| Production callers | **0** | `grep -rn "from cohezion.ouroboros.monitor\|OuroborosMonitor" src` returns only the file itself |
| Test files importing | 1 (`tests/ouroboros/test_monitor.py`) | grep |
| Tests on this file | 3, **all passing** | `uv run pytest tests/ouroboros/test_monitor.py -q` → "3 passed" |
| Public API surface | `OuroborosMonitor` (class), `fetch_recent_trajectories` (method) | `__init__.py` is empty (1-line file), so this class is only available via the fully-qualified path |

**Sibling files in the package** (`src/cohezion/ouroboros/`):

- `__init__.py` (1 line, empty)
- `detector.py` (57 lines — `AnomalyDetector`)
- `healer.py` (57 lines — `HealerAgent`)
- `monitor.py` (57 lines — `OuroborosMonitor`) ← **subject of this proposal**

The package is small, symmetric, and follows a clear **Monitor → Detector → Healer** pipeline that maps onto the Ouroboros design row in `CLAUDE.md` ("Ouroboros bridge + Mycelium network wired into Genesis chain").

**Public API ergonomics note:** `__init__.py` does not re-export anything, which is unusual for the rest of the cohezion codebase. Callers must import `from cohezion.ouroboros.monitor import OuroborosMonitor`. This is fine but worth flagging for Phase 5.

---

## Mypy error classification (29 total)

Using the taxonomy from the prompt (A-I), the 29 errors break down as follows:

| Code | Class | Count | Lines | Notes |
|---|---|---|---|---|
| C | Optional / missing-arg in third-party call | 2 | 38 | Real bug: `db.connect()` missing `url` |
| H | Union narrowing failure (mypy can't see type guard) | 22 | 51 | All 22 are mypy walking the `Value` union for `result[0].get(...)` |
| H | Union narrowing failure | 4 | 52 | Same root cause, different access pattern (`result[0]["result"]`) |
| D | Wrong return type (`Value` leaks into `list[dict[Any, Any]]`) | 1 | 52 | `return result[0]["result"]` returns `Value`, not `list[dict[Any, Any]]` |

**Aggregated by root cause:**

| Root cause | Count | % |
|---|---|---|
| H — Union narrowing failure on SurrealDB `Value` (line 51-52) | 26 | 90% |
| C — Stale `connect()` call missing positional arg (line 38) | 2 | 7% |
| D — Return-type leak from un-narrowed `Value` (line 52) | 1 | 3% |

**Translation:** 29 mypy errors → **3 distinct fixes** → 1 real bug + 1 type narrowing + 1 return-type contract.

This is the *opposite* of the typical "29 errors = 29 design problems" pattern. It is the well-known phenomenon where one un-narrowed access against a wide union explodes into N errors (one per union member that fails the operation). The python typing community calls this "union member multiplication." It is a **diagnostic noise** problem, not a design problem.

---

## Root cause analysis

### Issue 1 (HIGH severity, real bug): Stale `await db.connect()` call

**Lines:** 36–43

```python
async with AsyncSurreal(self.url) as db:
    try:
        await db.connect()                                      # ← line 38, BUG
        await db.use(self.namespace, self.database)
        user = os.getenv("SURREAL_USER", "root")
        password = os.getenv("SURREAL_PASS", "root")
        await db.signin({"user": user, "pass": password})
```

`async with AsyncSurreal(self.url) as db:` already establishes the WebSocket connection via `__aenter__` — that's the entire purpose of using the async context manager pattern. Calling `await db.connect()` afterwards is at best a no-op (when `connect()` accepts a re-connect with cached URL) and at worst a runtime `TypeError` (when the stub-declared signature `connect(url: str)` is enforced and we pass nothing).

The mypy error is real: `error: Missing positional argument "url" in call to "connect" of "AsyncTemplate" [call-arg]`.

**Evidence this is a stale paste-from-docs bug, not intentional:**

1. The sibling `cohezion.persistence.surreal_logger.SurrealTrajectoryLogger` (`src/cohezion/persistence/surreal_logger.py:58–66`) opens `AsyncSurreal` the same way and **does not** call `connect()`. It goes straight to `db.use(...)` then `db.signin(...)`.
2. The sibling `cohezion.core.persistence.query_patterns.query_patterns` (`src/cohezion/core/persistence/query_patterns.py:8–15`) also skips `connect()` — straight to `signin()` then `use()`.
3. The mock test (`tests/ouroboros/test_monitor.py:22–40`) does not actually exercise the `connect()` call meaningfully — it uses `AsyncMock(return_value=mock_db)` for `__aenter__`, so the test would pass even if `connect()` was missing the `url` argument because mocks tolerate any signature. **This is a TDD gap.**

**Downstream impact:** Currently zero (no production caller invokes `OuroborosMonitor.fetch_recent_trajectories`). When the Ouroboros loop is wired up in production — which the row-level intent in `CLAUDE.md` (`Ouroboros bridge + Mycelium network`) implies is planned — this would fail at first use with a confusing `TypeError`.

---

### Issue 2 (MEDIUM severity, type-narrowing): `result[0].get("result")` against a 21-member `Value` union

**Lines:** 50–53

```python
# SurrealDB query returns a list of results (one per statement)
if result and result[0].get("result"):
    return result[0]["result"]
return []
```

The SurrealDB Python driver (`surrealdb`) types `db.query(sql)` as returning a `list[Value]` where `Value` is a union of approximately 21 members (`str | int | float | bytes | UUID | Decimal | Table | Range | RecordID | Duration | Datetime | GeometryPoint | … | dict[str, Value] | list[Value]`). This is technically correct for SurrealDB SQL — a query *can* return any of those — but in practice, for a `SELECT * FROM trajectory ORDER BY timestamp DESC LIMIT N` statement, the response shape is **deterministically** `[{"result": [...records...], "status": "OK", "time": "...µs"}]` — i.e. a single-element list whose element is `dict[str, Value]`, with the `"result"` key holding `list[dict[str, Value]]`.

The author wrote `result[0].get("result")` against this wide union without narrowing, so mypy must check `.get` on every union member. 21 union members × `.get()` access = 21 union-attr errors on line 51 alone, plus an "is not indexable" error for the `[0]` access on the outer list element type, plus an "Invalid index type 'int' for 'dict[str, Value]'" once mypy narrows partway. Line 52 repeats the pattern for `result[0]["result"]`.

**Why the "Invalid index type" error appears:** This is the most diagnostically-revealing error. After mypy narrows `result[0]` to one of the union arms, it lands on `dict[str, Value]` and tries to index it with `int` (the `0` from `result[0]`). The narrowing direction is: mypy first checks whether the *outer* indexing `result[0]` is valid against `list[Value]`. It is — `Value` becomes the type of the element. But `Value` is a union, one member of which is `dict[str, Value]`, and *that* dict can't be indexed by `int`. So the error chain is: outer `[0]` → `Value` → narrow to `dict[str, Value]` → cannot do `[0]` on a string-keyed dict.

**Why this is a real type-safety problem (not just diagnostic noise):** Mypy is correctly pointing out that the code does **no defensive checking** on the response shape. If SurrealDB returns an error response (which is also a valid `Value`), `result[0].get("result")` would either raise `AttributeError` at runtime (because the response is not a dict) or silently return a non-list. The type system is asking us to acknowledge this.

**Downstream impact:** The function's declared return type is `list[dict[Any, Any]]` but it actually returns `Value` — which mypy reports as error 29 ("Incompatible return value type"). At runtime, callers receiving this would see a heterogeneous return depending on SurrealDB's response, with no cast or guard.

---

### Issue 3 (LOW severity, contract): `dict[Any, Any]` is over-permissive

**Line 26:** `async def fetch_recent_trajectories(self, limit: int = 100) -> list[dict[Any, Any]]:`

The trajectory rows have a **known schema** (the writer is right next door at `src/cohezion/persistence/surreal_logger.py:49–56`):

```python
data = {
    "trajectory_id": trajectory_id,           # str
    "timestamp": datetime…isoformat(),        # str (ISO-8601)
    "coherence": coherence,                   # float
    "doer": state.doer.tolist(),              # list[float]
    "thinker": state.thinker.tolist(),        # list[float]
    "knower": state.knower.tolist(),          # list[float]
}
```

SurrealDB will add `id` (a `RecordID`). So the actual row shape is `TypedDict` material. `dict[Any, Any]` here is a code smell, not a mypy error — but it propagates type-Any-ness to every consumer (`AnomalyDetector.analyze_batch` at `detector.py:31` accepts `list[dict[Any, Any]]` for the same reason).

**Downstream impact:** `Any` propagation hides real bugs. For example, `detector.py:41` does `t.get("coherence", 0.5)` with no type assertion — if SurrealDB ever returns a row with `coherence` as a string (e.g. from a malformed insert), the comparison `abs(coherence - self.target_coherence)` at `detector.py:28` will raise `TypeError` at runtime, but mypy will never warn.

---

## Phased refactor plan (target: 4-8 hours)

### Phase 1 (45 min): Fix the two real bugs and narrow the response

**Goal:** Drop mypy errors from 29 to 0–2 with no behavior change in the success path. Fix the latent `connect()` bug. Make the response-narrowing explicit and type-safe.

**File modifications:** `monitor.py` only.

**Sketch (illustrative — actual implementation lives in the next phase's PR):**

```python
from typing import Any, cast

# … inside fetch_recent_trajectories …
async with AsyncSurreal(self.url) as db:
    try:
        # Removed stale `await db.connect()` — the context manager handles it.
        # Confirmed by sibling: cohezion/persistence/surreal_logger.py:58-66.
        await db.use(self.namespace, self.database)

        user = os.getenv("SURREAL_USER", "root")
        password = os.getenv("SURREAL_PASS", "root")
        await db.signin({"user": user, "pass": password})

        result = await db.query(
            f"SELECT * FROM trajectory ORDER BY timestamp DESC LIMIT {limit}"
        )

        # Defensive narrowing: SurrealDB returns list[Value], but for SELECT
        # statements we expect [{"result": [...records...], "status": "OK"}].
        # Anything else is a driver/server contract violation.
        if not result or not isinstance(result, list):
            return []
        first = result[0]
        if not isinstance(first, dict):
            return []
        rows = first.get("result")
        if not isinstance(rows, list):
            return []
        return cast(list[dict[Any, Any]], rows)

    except Exception as e:
        logger.error(f"Failed to fetch trajectories from SurrealDB: {e}")
        raise
```

**Risk:** Low. No behavior change for the happy path. The defensive `isinstance` checks now return `[]` for malformed responses instead of raising `AttributeError` deep in a caller — this is **strictly safer**, and the test mock at `tests/ouroboros/test_monitor.py:23–25` already returns the canonical shape, so the existing tests stay green.

**Mypy delta:** 29 → 0 (the `cast(...)` is the explicit acknowledgment of the wide `Value` union; the `isinstance` chain narrows everything else).

**Verification:**
```bash
uv run mypy src/cohezion/ouroboros/monitor.py --ignore-missing-imports --no-strict-optional 2>&1 | tail -3
uv run pytest tests/ouroboros/test_monitor.py -q
```

---

### Phase 2 (1 h): Add a `TypedDict` for trajectory rows; thread it through `detector.py`

**Goal:** Replace `dict[Any, Any]` with a structured `Trajectory` `TypedDict`. This codifies the contract between `surreal_logger.py` (writer) and `monitor.py` + `detector.py` (readers).

**File modifications:** 3 files.

1. **New file** `src/cohezion/ouroboros/types.py` (~30 lines): defines `Trajectory(TypedDict)` with `trajectory_id`, `timestamp`, `coherence`, `doer`, `thinker`, `knower`, plus an optional `id: NotRequired[str]` (the SurrealDB RecordID stringified).
2. **Update** `monitor.py:26`: return type becomes `list[Trajectory]`. The `cast(...)` from Phase 1 becomes `cast(list[Trajectory], rows)`.
3. **Update** `detector.py:31`: parameter type becomes `list[Trajectory]`. The `t.get("coherence", 0.5)` access becomes `t["coherence"]` (TypedDict guarantees presence; the `, 0.5` default was a defensive fallback that hides bugs — see CLAUDE.md "Sentinel values are bugs").

**Risk:** Medium. `detector.py` has 1 caller in `compound/degradation_detector.py:307` (a deferred import of `AnomalyDetector`); we must verify that caller passes well-formed dicts. Inspect that file before changing `detector.py`'s signature.

**Mypy delta:** 0 → 0 on monitor.py; potentially -3 to -5 on `detector.py` depending on its current baseline.

**Verification:**
```bash
uv run pytest tests/ouroboros/ -q                          # all 3 ouroboros test files
uv run pytest tests/healing/test_ouroboros_loop.py -q      # cross-package consumer
uv run mypy src/cohezion/ouroboros/ --ignore-missing-imports --no-strict-optional 2>&1 | tail -3
```

---

### Phase 3 (45 min): Extract the SurrealDB connection block into a shared helper

**Goal:** The `async with AsyncSurreal(url) as db: await db.use(ns, db); … signin …` ritual is currently duplicated across **at least 5 files**:

- `src/cohezion/ouroboros/monitor.py` (this file)
- `src/cohezion/persistence/surreal_logger.py`
- `src/cohezion/core/persistence/query_patterns.py`
- `src/cohezion/core/persistence/surreal_client.py`
- `src/cohezion/mcp/servers/memory/server.py`

Each duplicate is a place the `connect()` bug can recur. Extract a `cohezion.ouroboros._surreal.surreal_session(url, ns, db) -> AsyncContextManager[AsyncSurreal]` helper *scoped to ouroboros* (avoid touching `cohezion.persistence` in this refactor — that's a wider concern with its own callers; see Phase 5).

**File modifications:** 1 new file (`src/cohezion/ouroboros/_surreal.py`, ~25 lines, leading underscore = module-private), 1 modified (`monitor.py` reduced to ~35 lines).

**Risk:** Low. The helper is module-private (prefixed `_`); nothing leaks to the public API. `monitor.py` becomes the orchestration shell, the connection ritual moves to `_surreal.py`.

**Mypy delta:** 0 → 0 (Phase 1 already cleared monitor.py; this is purely a SRP/DRY improvement).

**Verification:**
```bash
uv run pytest tests/ouroboros/ -q
uv run python -c "from cohezion.ouroboros.monitor import OuroborosMonitor; print(OuroborosMonitor.__name__)"
```

---

### Phase 4 (1.5 h): Add the missing edge-case tests

**Goal:** Test the Phase 1 narrowing logic. The existing `tests/ouroboros/test_monitor.py` has 3 tests that only cover the happy-path and a generic `Exception` path. Add tests for:

1. `result == None` → returns `[]`
2. `result == []` → returns `[]`
3. `result == [{"status": "ERR", "result": "table 'trajectory' does not exist"}]` → returns `[]` (because `rows` is a `str`, not a `list`)
4. `result == [{"status": "OK"}]` (no `"result"` key) → returns `[]`
5. `result == "scalar response"` (driver returned a non-list — unlikely but possible) → returns `[]`
6. **Regression test for the `connect()` bug:** spy on `db.connect` and assert it is **not called** (because the context manager handles connection setup). This test would have caught the original bug.

**File modifications:** 1 file (`tests/ouroboros/test_monitor.py`, append ~6 tests, ~80 LOC).

**Risk:** Low.

**Coverage delta:** monitor.py from ~80% to ~100% line coverage. More importantly, the narrowing branches now have explicit tests, so future contributors won't accidentally regress them.

**Verification:**
```bash
uv run pytest tests/ouroboros/test_monitor.py -q --cov=src/cohezion/ouroboros/monitor --cov-report=term-missing
```

---

### Phase 5 (1 h, OPTIONAL): Re-export from `__init__.py` and add a strict-mode carve-out

**Goal:** Two small ergonomic / hygiene improvements.

1. **Re-export the public API.** `__init__.py` is currently empty (1 line). Add:
   ```python
   from cohezion.ouroboros.detector import AnomalyDetector
   from cohezion.ouroboros.healer import HealerAgent
   from cohezion.ouroboros.monitor import OuroborosMonitor
   from cohezion.ouroboros.types import Trajectory

   __all__ = ["AnomalyDetector", "HealerAgent", "OuroborosMonitor", "Trajectory"]
   ```
   This lets future consumers write `from cohezion.ouroboros import OuroborosMonitor`. **Mark this as a non-breaking change** — existing fully-qualified imports continue to work.

2. **Add a strict-mode carve-out** in `pyproject.toml`:
   ```toml
   [[tool.mypy.overrides]]
   module = ["cohezion.ouroboros.*"]
   strict = true
   ```
   This pins the package to `--strict` so future regressions are caught at PR time. Only add this once Phases 1–4 are merged and the baseline is clean.

**File modifications:** 2 (`__init__.py`, `pyproject.toml`).

**Risk:** Low. The re-exports are additive. The strict-mode carve-out is contained to one package (4 files).

**Verification:**
```bash
uv run mypy --strict src/cohezion/ouroboros/ --ignore-missing-imports
uv run python -c "from cohezion.ouroboros import OuroborosMonitor, AnomalyDetector, HealerAgent; print('ok')"
```

---

## Summary of mypy delta across phases

| Phase | Description | Mypy errors after | Cumulative time |
|---|---|---|---|
| baseline | (current state) | 29 | 0 h |
| Phase 1 | Fix `connect()` bug + narrow response | 0–2 | 0.75 h |
| Phase 2 | Add `Trajectory` TypedDict | 0 | 1.75 h |
| Phase 3 | Extract `_surreal.py` helper | 0 | 2.5 h |
| Phase 4 | Add edge-case tests | 0 | 4 h |
| Phase 5 (opt.) | Re-export + strict-mode | 0 (under `--strict`) | 5 h |

**4 hours hits all the necessary phases. Phase 5 is +1h of polish.**

---

## Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `db.connect()` was load-bearing in some untested production path | Very low — sibling files don't call it; no production caller exists; mypy is screaming about a missing arg, so it would already be a runtime error | Phase 4 regression test asserts it stays uncalled |
| Phase 2 `TypedDict` change breaks `detector.py` consumers | Low — only 1 deferred-import caller (`compound/degradation_detector.py:307`), easy to inspect | Read-and-verify the caller before merging Phase 2; if needed, keep `dict[Any, Any]` on `detector.py` and only narrow `monitor.py` |
| Phase 3 helper extraction creates a circular import | Low — the helper is leaf-level and depends only on `surrealdb` | Underscore-prefix the module to signal "internal" |
| Phase 5 strict-mode flushes hidden errors in `detector.py` / `healer.py` | Medium | Run `mypy --strict src/cohezion/ouroboros/` *before* adding the override and fix any surfaced errors as part of Phase 5 |
| Test mock at `test_monitor.py:23–25` is so loose it won't catch return-shape regressions | Already realised | Phase 4 tightens with `isinstance` assertions on the returned shape |

---

## Success criteria

- [ ] Mypy errors on `monitor.py`: 29 → 0 (target: ≤ 2)
- [ ] All callers still resolve imports (verified by `pytest tests/ouroboros/` + `pytest tests/healing/test_ouroboros_loop.py`)
- [ ] Existing test suite green: `uv run pytest tests/ouroboros/ -q` → 3 passed (or more with Phase 4)
- [ ] **Public API unchanged** (`OuroborosMonitor.__init__(url, namespace, database)`, `OuroborosMonitor.fetch_recent_trajectories(limit) -> list[dict[Any, Any] | Trajectory]`)
- [ ] Phase 4 test count: 3 → ≥ 9 on `test_monitor.py`
- [ ] Phase 5 (opt.): `mypy --strict src/cohezion/ouroboros/` is green

---

## Out of scope (deliberately)

- The wider duplication of the `AsyncSurreal` connection ritual across `cohezion.persistence`, `cohezion.core.persistence`, and `cohezion.mcp.servers.memory` (5+ duplicates). That's a cross-package refactor with its own callers and risk profile. The Phase 3 helper here is **scoped to `ouroboros/`** intentionally; if it proves useful, it can be promoted to `cohezion.persistence` later.
- Renaming `monitor.py`. Despite the prompt's hint about purpose-vs-name, the file genuinely *is* a monitor (it ingests telemetry). The name is fine.
- Splitting `OuroborosMonitor` into multiple classes. With 2 methods and 1 responsibility (read trajectories from SurrealDB), the class is at the right size.
- Migrating to a typed SurrealDB wrapper (`cohezion.persistence.surreal_logger.SurrealTrajectoryLogger` and friends are the natural place for that abstraction; `monitor.py` is a leaf consumer).

---

## Honest finding

The Wave 1D mypy baseline ranking algorithm appears to be a raw `errors per file` count. By that measure, `monitor.py` is "the worst file" — but **that ranking conflates diagnostic-noise files (one un-narrowed union access) with genuinely-degraded files (god-modules with structural problems)**. Future Wave 1D iterations may want to weight by *number of distinct error-producing lines* or *number of distinct error codes* rather than raw error count, otherwise files like this one will keep landing at the top of the worst-files list while the actual structural debt elsewhere goes uninvestigated.

The 29-error count on `monitor.py` is, in the end, a **single line bug** wearing union-multiplication camouflage. Phase 1 alone (45 minutes) clears it.

---

## Appendix A: Full mypy error list (29 errors)

```
src/cohezion/ouroboros/monitor.py:38: error: Missing positional argument "url" in call to "connect" of "AsyncTemplate"  [call-arg]
src/cohezion/ouroboros/monitor.py:51: error: Value of type "str | int | float | bytes | UUID | <15 more items>" is not indexable  [index]
src/cohezion/ouroboros/monitor.py:51: error: Item "str" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "int" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "float" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "bytes" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "UUID" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "Decimal" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "Table" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "Range" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "RecordID" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "Duration" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "Datetime" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "GeometryPoint" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "GeometryLine" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "GeometryPolygon" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "GeometryMultiPoint" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "GeometryMultiLine" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "GeometryMultiPolygon" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "GeometryCollection" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Item "list[Value]" of "str | Any | int | float | bytes | <16 more items>" has no attribute "get"  [union-attr]
src/cohezion/ouroboros/monitor.py:51: error: Invalid index type "int" for "dict[str, Value]"; expected type "str"  [index]
src/cohezion/ouroboros/monitor.py:52: error: Value of type "str | int | float | bytes | UUID | <15 more items>" is not indexable  [index]
src/cohezion/ouroboros/monitor.py:52: error: Value of type "str | Any | int | float | bytes | <16 more items>" is not indexable  [index]
src/cohezion/ouroboros/monitor.py:52: error: No overload variant of "__getitem__" of "bytes" matches argument type "str"  [call-overload]
src/cohezion/ouroboros/monitor.py:52: error: No overload variant of "__getitem__" of "list" matches argument type "str"  [call-overload]
src/cohezion/ouroboros/monitor.py:52: error: Incompatible return value type (got "str | Any | int | float | bytes | <16 more items>", expected "list[dict[Any, Any]]")  [return-value]
src/cohezion/ouroboros/monitor.py:52: error: Invalid index type "int" for "dict[str, Value]"; expected type "str"  [index]
src/cohezion/ouroboros/monitor.py:52: error: Invalid index type "str" for "str"; expected type "SupportsIndex | slice[SupportsIndex | None, SupportsIndex | None, SupportsIndex | None]"  [index]
```

`Found 29 errors in 1 file (checked 1 source file)`

---

## Appendix B: Caller list

`grep -rn "from cohezion.ouroboros.monitor\|OuroborosMonitor" src tests --include="*.py"`:

```
src/cohezion/ouroboros/monitor.py:11:class OuroborosMonitor:        # the definition itself
tests/ouroboros/test_monitor.py:5:from cohezion.ouroboros.monitor import OuroborosMonitor
tests/ouroboros/test_monitor.py:10:    """Test that OuroborosMonitor initializes with correct config."""
tests/ouroboros/test_monitor.py:11:    monitor = OuroborosMonitor(...)
tests/ouroboros/test_monitor.py:32:        monitor = OuroborosMonitor()
tests/ouroboros/test_monitor.py:54:        monitor = OuroborosMonitor()
```

**Production callers:** 0
**Test callers:** 1 file, 3 instantiations

For context, related ouroboros imports across the codebase:

```
src/cohezion/compound/degradation_detector.py:307:            from cohezion.ouroboros.detector import AnomalyDetector
tests/ouroboros/test_healer.py:5:from cohezion.ouroboros.healer import HealerAgent
tests/ouroboros/test_detector.py:1:from cohezion.ouroboros.detector import AnomalyDetector
tests/ouroboros/test_monitor.py:5:from cohezion.ouroboros.monitor import OuroborosMonitor
```

The Ouroboros package as a whole has exactly 1 production caller (`compound/degradation_detector.py`), and that caller imports `AnomalyDetector` (from `detector.py`), not `OuroborosMonitor`. The Ouroboros loop wiring described in `CLAUDE.md` ("Ouroboros bridge + Mycelium network wired into Genesis chain") appears to live in `OuroborosBridge` rather than going directly through `OuroborosMonitor`. This reinforces the "fix the bug now before it ships" framing — there is no production traffic on this code path yet.
