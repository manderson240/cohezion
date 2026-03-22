# Fix Outstanding Technical Debt Implementation Plan

Created: 2026-02-23
Status: COMPLETE
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)

## Summary

**Goal:** Fix four categories of outstanding technical debt: RUF012 mutable class defaults (43 instances), RUF006 asyncio dangling tasks (15 instances), SurrealDB integration test event loop failures (6 failed + 23 errors), and persistent memory MCP replacement (extend cloud-vault-mcp with search/save/get/timeline tools).

**Architecture:** Incremental fixes across existing modules. No new packages or major restructuring. RUF012/RUF006 are mechanical fixes with `ClassVar` annotations and task reference storage. SurrealDB tests need fixture scope fix. Memory tools extend the existing cloud-vault-mcp FastMCP server with a new `memory_store.py` module backed by JSONL + vault search.

**Tech Stack:** Python 3.13+, ruff, pytest-asyncio, FastMCP, SurrealDB, JSONL

## Scope

### In Scope

- Fix all 43 RUF012 violations by adding `ClassVar` type annotations
- Fix all 15 RUF006 violations by storing `asyncio.create_task()` return values
- Fix SurrealDB integration test event loop mismatch (`scope="module"` fixture issue)
- Add 4 new MCP tools to cloud-vault-mcp: `memory_search`, `memory_save`, `memory_get`, `memory_timeline`
- Update `~/.claude/rules/memory.md` to reference new vault memory tools
- Tests for each change

### Out of Scope

- New MCP server (extending cloud-vault-mcp instead)
- SurrealDB schema changes beyond what tests need
- Fixing E501 line-length violations (47 remaining)
- Any refactoring beyond the specific fixes

## Prerequisites

- SurrealDB running locally (confirmed: `ws://localhost:8000` with `sdb_admin_session43`)
- `.env` loaded via `cohezion.__init__` dotenv auto-load
- cloud-vault-mcp server accessible at `http://127.0.0.1:8360`

## Context for Implementer

- **Patterns to follow:** RUF012 fix uses `ClassVar[type]` annotation from `typing`. See ruff docs for RUF012.
- **Patterns to follow:** RUF006 fix stores task references in `self._background_tasks: set[asyncio.Task]` with `task.add_done_callback(self._background_tasks.discard)` to avoid preventing GC.
- **Conventions:** All source in `src/cohezion/`, tests in `tests/`. Run tests with `uv run pytest`.
- **Key files:**
  - `src/cohezion/core/persistence/surreal_client.py` — SurrealDB client with dotenv auto-load
  - `tests/integration/test_surreal_persistence.py` — failing integration tests
  - `cloud-vault-mcp/src/mcp_server/server.py` — MCP server tool registration
  - `cloud-vault-mcp/src/mcp_server/agent_context.py` — existing session/decision tracking
- **Gotchas:**
  - Never use `ruff --unsafe-fixes` (L138: TC001 moves imports to TYPE_CHECKING, breaking `patch()`)
  - asyncio primitives must be in `__init__`, not class-level (L130)
  - `pytest-asyncio` `scope="module"` fixtures create event loop mismatches with per-test loops

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [x] Task 1: Fix RUF012 mutable class defaults (43 violations across 21 files)
- [x] Task 2: Fix RUF006 asyncio dangling tasks (15 violations across 11 files)
- [x] Task 3: Fix SurrealDB integration test event loop issues
- [x] Task 4: Add persistent memory tools to cloud-vault-mcp
- [x] Task 5: Update memory rules and verify integration
- [x] Task 6: Fix cz context percentage calculation bug

**Total Tasks:** 6 | **Completed:** 6 | **Remaining:** 0

## Implementation Tasks

### Task 1: Fix RUF012 Mutable Class Defaults

**Objective:** Add `ClassVar` type annotations to all 43 mutable class-level defaults across 21 files. These are lists and dicts defined on the class body that should be marked as class variables to prevent shared-state bugs.

**Dependencies:** None

**Files (21 files, all Modify):**

- `src/cohezion/branding.py` (3 violations: Identity.EXPERTS, Motifs.NEXUS_AVATAR_FRAMES, Motifs.IGNITION_SEQUENCE)
- `src/cohezion/compound/batch_sizer.py` (2: DEFAULT_BATCH_SIZES, BASELINE_THROUGHPUT)
- `src/cohezion/compound/prompt_optimizer.py` (2: FILLER_WORDS, REDUNDANCY_PATTERNS)
- `src/cohezion/compound/thermal_predictor.py` (2: THERMAL_THRESHOLDS, PREDICTION_WEIGHTS)
- `src/cohezion/compound/universe_bridge.py` (1)
- `src/cohezion/flume/tokenizer.py` (1)
- `src/cohezion/gateway/demo_gateway.py` (1)
- `src/cohezion/gateway/ngrok_adapter.py` (1)
- `src/cohezion/physics/dimension_extractor.py` (3)
- `src/cohezion/rl/environment.py` (1)
- `src/cohezion/security/guardrail_adapters.py` (2)
- `src/cohezion/security/log_redactor.py` (1)
- `src/cohezion/simulation/enhanced_simulator.py` (4)
- `src/cohezion/simulation/rl_framework.py` (1)
- `src/cohezion/swarm/agent_factory.py` (2)
- `src/cohezion/swarm/cost_aware_router.py` (7)
- `src/cohezion/swarm/fallback_strategy.py` (3)
- `src/cohezion/swarm/model_fallback_strategy.py` (2)
- `src/cohezion/swarm/model_pool_manager.py` (1)
- `src/cohezion/swarm/model_ranker.py` (2)
- `src/cohezion/swarm/workflows/debate_protocol.py` (1)
- Create: `tests/lint/__init__.py` (new directory)
- Create: `tests/lint/test_ruf012_classvar.py` (new)

**Key Decisions / Notes:**

- Fix pattern: Add `from typing import ClassVar` import, then annotate `ATTR: ClassVar[list[str]] = [...]` or `ATTR: ClassVar[dict[str, float]] = {...}`
- These are all true class constants (uppercase names, never mutated after class definition). `ClassVar` is the correct annotation.
- Do NOT move these to `__init__` — they are intentional class-level constants shared across all instances
- Verify each file's existing imports before adding `ClassVar`

**Definition of Done:**

- [ ] `uv run ruff check src/cohezion/ --select RUF012` reports 0 errors
- [ ] All existing tests still pass (`uv run pytest tests/ -q -o "addopts="`)
- [ ] New regression test verifies RUF012 count is 0

**Verify:**

- `uv run ruff check src/cohezion/ --select RUF012 2>&1 | tail -1` — "Found 0 errors"
- `uv run pytest tests/ -q -o "addopts=" -p no:cacheprovider --tb=line 2>&1 | tail -3` — 0 failures

### Task 2: Fix RUF006 Asyncio Dangling Tasks

**Objective:** Store references to all 15 fire-and-forget `asyncio.create_task()` calls to prevent tasks from being garbage-collected mid-execution. Each class needs a `_background_tasks: set[asyncio.Task]` attribute and the pattern `task = asyncio.create_task(...); self._background_tasks.add(task); task.add_done_callback(self._background_tasks.discard)`.

**Dependencies:** None (can run in parallel with Task 1)

**Files (11 files, all Modify):**

- `src/cohezion/agents/base.py` (3 violations: lines 129, 560, 819)
- `src/cohezion/cache/semantic_cache.py` (1: line 293)
- `src/cohezion/compound/executor.py` (1: line 840 — uses `asyncio.ensure_future`)
- `src/cohezion/compound/thermal_history_persistence.py` (1: line 93)
- `src/cohezion/compound/thermal_trend_predictor.py` (1: line 113)
- `src/cohezion/core/connection_pool.py` (2: lines 106, 277)
- `src/cohezion/core/multimodal_bridge.py` (1: line 46)
- `src/cohezion/core/task_manager.py` (1: line 166)
- `src/cohezion/cost_optimization/budget_enforcer.py` (1: line 303)
- `src/cohezion/cost_optimization/cost_tracker.py` (1: line 186 — uses `loop.create_task`)
- `src/cohezion/reliability/quantum_performance_monitor.py` (2: lines 263, 467)
- Create: `tests/lint/test_ruf006_dangling_tasks.py` (new — `tests/lint/__init__.py` created in Task 1)

**Key Decisions / Notes:**

- Standard pattern for async methods (most sites):
  ```python
  def __init__(self):
      self._background_tasks: set[asyncio.Task] = set()

  # Then at each create_task site inside async methods:
  task = asyncio.create_task(self._some_coroutine())
  self._background_tasks.add(task)
  task.add_done_callback(self._background_tasks.discard)
  ```
- **Special case — `base.py:129` and `connection_pool.py:106` (create_task called from `__init__`):** These sites call `asyncio.create_task()` directly from synchronous `__init__` code, which raises `RuntimeError: no current event loop` in sync contexts. Fix: wrap with `try: loop = asyncio.get_running_loop(); task = loop.create_task(...)` so it only fires when a loop is already running. Move actual startup logic to a separate `async def start()` if needed. The task-reference storage fix alone does NOT fix the structural sync-context problem.
- **Special case — `connection_pool.py:_initialize_pool`:** This sync method calls `asyncio.create_task()` in a loop from `__init__`. Convert `_initialize_pool` to `async def _initialize_pool()` and call it lazily on first `acquire()` call instead of from `__init__`. This is a structural async fix that must precede the task-reference storage fix.
- For `executor.py` line 840 which uses `asyncio.ensure_future`: convert to `asyncio.create_task` and apply same pattern
- For `cost_tracker.py` line 186 which uses `loop.create_task`: convert to `asyncio.create_task` (deprecated in Python 3.10+, project targets 3.13+) and apply same pattern
- For `connection_pool.py` line 277: apply standard pattern once line 106 structural fix is in place
- Some classes already have `__init__` methods — add the set there. Some don't — add `__init__` or use class-level `_background_tasks: set = set()` (but this would trigger RUF012, so must be in `__init__`)
- **BaseAgent subclass check:** `src/cohezion/agents/base.py` violations (lines 129, 560, 819) add `self._background_tasks` in `BaseAgent.__init__`. Before implementing, verify that all known subclasses (`src/cohezion/agents/generated/skill_0_agent.py`, `skill_1_agent.py`, and factory-created agents) call `super().__init__()`. Add a defensive `self._background_tasks = getattr(self, '_background_tasks', set())` fallback if any subclass omits `super().__init__()`.

**Definition of Done:**

- [ ] `uv run ruff check src/cohezion/ --select RUF006` reports 0 errors
- [ ] All existing tests still pass
- [ ] New regression test verifies RUF006 count is 0

**Verify:**

- `uv run ruff check src/cohezion/ --select RUF006 2>&1 | tail -1` — "Found 0 errors"
- `uv run pytest tests/ -q -o "addopts=" -p no:cacheprovider --tb=line 2>&1 | tail -3` — 0 failures

### Task 3: Fix SurrealDB Integration Test Event Loop Issues

**Objective:** Fix the 6 failures + 23 errors in `tests/integration/test_surreal_persistence.py` caused by `scope="module"` async fixture creating a SurrealDB client on one event loop while individual tests run on different loops.

**Dependencies:** None (can run in parallel with Tasks 1-2)

**Files:**

- Modify: `tests/integration/test_surreal_persistence.py`

**Key Decisions / Notes:**

- Root cause (part 1): `@pytest.fixture(scope="module") async def surreal_client()` creates the client+connection in one event loop. With `pytest-asyncio`, each test function gets its own event loop. The SurrealDB client's internal websocket Future is bound to the fixture's loop, causing "Future attached to a different loop" errors.
- Root cause (part 2): The project's `pyproject.toml` does not set `asyncio_mode`, which defaults to `strict` mode. In strict mode, every async test function must be explicitly marked with `@pytest.mark.asyncio`. Without it, async tests fail to run.
- Fix 1: Change fixture from `scope="module"` to `scope="function"` (default). Each test gets its own client+connection on its own event loop.
- Fix 2: Add `pytestmark = [pytest.mark.asyncio, pytest.mark.integration]` at module level — this provides the required asyncio mark for all async tests AND allows running with `-m integration`. **Both fixes are required; neither alone is sufficient.**
- To avoid reconnecting for every test (slow), add a pre-check at module level that attempts a real authenticated query (not just TCP socket connect) and skips the entire module if it fails. TCP port open ≠ auth works — use `asyncio.run(probe_auth())` with a try/except that marks the module as skipped.
- Keep the `SKIP_INTEGRATION` env var check alongside the auth probe
- **Data isolation:** With `scope="function"`, sequential tests share the `test_persistence` database unless explicitly cleaned. Either use unique per-test DB names (`f"test_persistence_{uuid4().hex[:8]}"`) or have each test clean up its own records in teardown. The plan chose function scope; implement with unique DB names per test to prevent inter-test data leakage.

**Definition of Done:**

- [ ] `uv run pytest tests/integration/test_surreal_persistence.py -v --tb=short` — all tests pass (0 failures, 0 errors)
- [ ] Tests still skip cleanly when SurrealDB is not running
- [ ] Full test suite still passes

**Verify:**

- `uv run pytest tests/integration/test_surreal_persistence.py -q --tb=short 2>&1 | tail -5` — 0 failures
- `uv run pytest tests/ -q -o "addopts=" -p no:cacheprovider --tb=line 2>&1 | tail -3` — 0 failures

### Task 4: Add Persistent Memory Tools to cloud-vault-mcp

**Objective:** Add 4 new MCP tools (`memory_search`, `memory_save`, `memory_get`, `memory_timeline`) to the cloud-vault-mcp server to replace the lost PILOT `mem-search` functionality. These tools store observations as JSONL entries in `~/vaults/cohezion-vault/memory/observations.jsonl` and support search by text, retrieval by ID, and timeline navigation.

**Dependencies:** None

**Files:**

- Create: `cloud-vault-mcp/src/mcp_server/memory_store.py` — MemoryStore class with JSONL backend
- Modify: `cloud-vault-mcp/src/mcp_server/server.py` — register 4 new tools
- Create: `cloud-vault-mcp/tests/test_memory_store.py` — unit tests for MemoryStore

**Key Decisions / Notes:**

- **Storage format:** JSONL file at `{vault_path}/memory/observations.jsonl`. Each line is a JSON object:
  ```json
  {"id": 1, "timestamp": "2026-02-23T10:00:00Z", "text": "...", "title": "...", "type": "discovery", "project": "cohezion", "tags": []}
  ```
- **ID assignment:** Auto-incrementing integer (max ID from file + 1). Thread-safe via file lock.
- **Search:** Full-text substring match on `text` + `title` fields, with optional filters: `type`, `project`, `dateStart`, `dateEnd`, `limit`. Returns index entries (id, title, timestamp, snippet) for token efficiency.
- **Get:** Fetch full observation details by list of IDs.
- **Timeline:** Given an anchor ID or query, return chronological observations around it (configurable `depth_before`, `depth_after`).
- **Tool signatures** (matching old mem-search API from `~/.claude/rules/memory.md`):
  - `memory_search(query: str, limit: int = 20, type: str = "", project: str = "", dateStart: str = "", dateEnd: str = "") → str`
  - `memory_save(text: str, title: str = "", project: str = "cohezion", type: str = "discovery") → str` — validates `type` against allowed enum (`bugfix`, `feature`, `refactor`, `discovery`, `decision`, `change`); raises `ValueError` on invalid value
  - `memory_get(ids: list[int]) → str`
  - `memory_timeline(anchor: int | None = None, query: str = "", depth_before: int = 5, depth_after: int = 5) → str` — requires either `anchor` or `query`; raises `ValueError` if both are None
- Follow existing server.py pattern: import module, create instance, register tools with `@mcp.tool()`
- JSONL chosen over SurrealDB to avoid adding another DB dependency and to ensure the memory file is portable/inspectable
- **Thread/async safety:** MemoryStore I/O uses `filelock.FileLock` wrapping the **entire read-compute-append critical section** (not just ID increment) to prevent duplicate IDs from concurrent writes. Since MCP tools are called from an async context, all blocking I/O in MemoryStore must be wrapped with `asyncio.to_thread()` inside the tool handlers in `server.py`. MemoryStore itself stays synchronous (simpler, fully testable); the async wrapper lives in server.py.
- **JSONL corruption handling:** Iterate lines with per-line `try/except json.JSONDecodeError`, logging a warning and skipping malformed entries. Add a `MemoryStore.repair()` method that rewrites the file with only valid lines. Include a corruption test (inject a bad line, verify store still returns valid results).
- **Existing VaultMemoryBridge overlap:** `server.py` already registers a `push_memory` tool via `VaultMemoryBridge`. The new `memory_save`/`memory_search`/`memory_get`/`memory_timeline` tools provide a different capability (ID-based searchable observation log vs. session-state sync). Add a clear docstring to each new tool explaining the distinction: memory tools store cross-session observations; `push_memory` syncs MEMORY.md to vault sections. Do not deprecate `push_memory`.
- **max_entries default:** Implement FIFO eviction at `max_entries=10_000` (default). Document O(N) search behaviour at that ceiling in the module docstring.

**Definition of Done:**

- [ ] 4 new MCP tools registered in cloud-vault-mcp server
- [ ] MemoryStore handles save, search, get, timeline operations
- [ ] JSONL file created at `{vault_path}/memory/observations.jsonl`
- [ ] Unit tests cover all 4 operations + edge cases (empty store, missing IDs, date filtering)
- [ ] Tools return JSON matching the 3-layer workflow from `memory.md`

**Verify:**

- `uv run pytest cloud-vault-mcp/tests/test_memory_store.py -q` — all tests pass
- `uv run ruff check cloud-vault-mcp/src/mcp_server/memory_store.py` — 0 lint errors

### Task 5: Update Memory Rules and Verify Integration

**Objective:** Update `~/.claude/rules/memory.md` to reference the new cloud-vault-mcp memory tools instead of the old PILOT mem-search tools. Update `~/.claude/rules/mcp-cli.md` to remove the stale `mem-search` reference. Verify end-to-end that the MCP server exposes the new tools.

> ⚠️ **Post-merge manual step.** The files `~/.claude/rules/memory.md` and `~/.claude/rules/mcp-cli.md` live outside the repository entirely. This task **cannot** be completed inside the worktree. It must be performed manually on the host filesystem **after** the spec-verify phase syncs Task 4 changes back to the main branch. The implementer should execute Task 5 edits in their normal shell session after `cz worktree sync` completes.

**Dependencies:** Task 4

**Files:**

- Modify: `~/.claude/rules/memory.md` — update tool names and examples
- Modify: `~/.claude/rules/mcp-cli.md` — remove `mem-search` from the Pilot Core Servers list
- Modify: `memory/MEMORY.md` — update Ongoing Issues to mark mem-search as resolved

**Key Decisions / Notes:**

- Tool name mapping: `search` → `memory_search`, `get_observations` → `memory_get`, `save_memory` → `memory_save`, `timeline` → `memory_timeline`
- The 3-layer workflow (search → timeline → get) stays the same
- Update examples to use the new tool names accessible via ToolSearch (`mcp__cohezion-vault__memory_search`, etc.)
- Remove `mem-search` from the "Pilot Core Servers" row in `mcp-cli.md`
- **Worktree constraint:** `~/.claude/rules/memory.md` and `~/.claude/rules/mcp-cli.md` live outside the repository. These files must be edited directly in the host filesystem, not inside the worktree checkout. Perform this step after Task 4 changes are synced to the base branch via worktree sync.

**Definition of Done:**

- [ ] cloud-vault-mcp server restarted and live integration verified: `memory_save` + `memory_search` round-trip works via `mcp-cli` before touching global rules
- [ ] `~/.claude/rules/memory.md` references new tool names
- [ ] `~/.claude/rules/mcp-cli.md` no longer mentions `mem-search`
- [ ] `memory/MEMORY.md` updated — mem-search marked resolved

**Verify:**

- `mcp-cli cohezion-vault/memory_save '{"text": "test observation", "title": "Integration test"}'` — returns id
- `mcp-cli cohezion-vault/memory_search '{"query": "test observation"}'` — returns that entry
- `grep -c "mem-search" ~/.claude/rules/memory.md ~/.claude/rules/mcp-cli.md` — 0 matches
- `grep "memory_search\|memory_save\|memory_get\|memory_timeline" ~/.claude/rules/memory.md` — all 4 present

## Testing Strategy

- **Unit tests:** Each task has targeted unit/lint regression tests
- **Integration tests:** Task 3 directly fixes integration test suite; Task 4 tests MemoryStore with real JSONL I/O
- **Manual verification:**
  1. After Task 1+2: `uv run ruff check src/cohezion/ --select RUF012,RUF006` → 0 errors
  2. After Task 3: `uv run pytest tests/integration/test_surreal_persistence.py -v` → all pass
  3. After Task 4: Restart cloud-vault-mcp, call `memory_save` then `memory_search` via ToolSearch
  4. Full suite: `uv run pytest tests/ -q -o "addopts="` → 0 failures

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ClassVar annotation breaks Pydantic model serialization | Low | Med | Confirmed safe: Pydantic excludes ClassVar from schema. None of the 21 affected files are Pydantic models. |
| Storing task references prevents GC of completed tasks | Low | Low | `add_done_callback(set.discard)` auto-removes completed tasks; set stays bounded. |
| SurrealDB fixture change makes tests slower (reconnect per test) | Med | Low | Auth probe at module level skips all tests early if SurrealDB unavailable; ~50ms per connect is acceptable. |
| JSONL memory file grows unbounded | Low | Low | Add `max_entries=10000` default with FIFO eviction (drop oldest on overflow). |
| asyncio.to_thread() not available or overhead too high | Low | Low | `asyncio.to_thread()` available since Python 3.9; project targets 3.13+. |
| BaseAgent subclass skips super().__init__() | Med | Med | Inspect generated agents before implementing; add `getattr` fallback as safety net. |
| create_task called in sync __init__ (base.py:129, connection_pool:106) | High | Med | Wrap with `asyncio.get_running_loop()` check; convert `_initialize_pool` to async with lazy init. |
| JSONL concurrent write produces duplicate IDs | Med | Med | FileLock wraps entire read-compute-append section; integration test with `asyncio.gather`. |
| JSONL corruption from mid-write crash | Low | Med | Per-line `json.JSONDecodeError` catch + `repair()` method; corruption test included. |

### Task 6: Fix cz Context Percentage Calculation Bug

**Objective:** Fix the `cz context --json` tool that returns absurd percentages (e.g., 45,951%) because it sums three incompatible token fields. Only `input_tokens` counts toward the context window.

**Dependencies:** None

**Files:**

- Modify: `~/vaults/cohezion-vault/tools/cohezion-engine/src/cohezion_engine/context.py`
- Modify: `~/vaults/cohezion-vault/tools/cohezion-engine/tests/` (existing test file for context)

> ⚠️ **Outside-repo file.** Like Task 5, this file lives outside the Cohezion repo. Must be edited directly in the host filesystem. The worktree will not contain this file. Apply this fix after worktree sync.

**Key Decisions / Notes:**

- Root cause: the JSONL usage records contain three token fields:
  - `input_tokens` — actual context window tokens consumed (correct, count this)
  - `cache_creation_input_tokens` — tokens written to cache (billing cost, not context)
  - `cache_read_input_tokens` — cumulative cache hits across session (reuse counts, not context)
- Fix: remove the two lines summing `cache_creation_input_tokens` and `cache_read_input_tokens`; only sum `input_tokens`
- Correct percentage at time of fix: ~24% (48K / 200K limit)

**Definition of Done:**

- [ ] `cz context --json` returns a percentage between 0 and 100
- [ ] Existing tests pass (`uv run pytest ~/vaults/cohezion-vault/tools/cohezion-engine/tests/ -q`)

**Verify:**

- `cz context --json | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['percentage'] < 200, f'Still wrong: {d}'; print('OK:', d)"` — passes

---

## Open Questions

- None — all design decisions resolved via user input.

### Deferred Ideas

- SurrealDB-backed memory store (could replace JSONL for better search performance at scale)
- Embedding-based semantic search for memory observations (using Ollama embeddings)
- Memory compaction/summarization for old observations
