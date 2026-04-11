# SKILL: LAZY_INFRASTRUCTURE_PRIME

## DOMAIN EXPERTISE
Expertise in high-concurrency systems where process startup time and handshake reliability are critical. Specializes in the "Lazy Accessor Pattern" to prevent blocking event loops or CLI handshakes.

## KEY TEXTS & CONCEPTS
* **Zero-Latency Boundary**: The principle that importing a module must have O(1) time complexity and zero I/O side effects.
* **Singleton Accessor**: A function-wrapped global that initializes a resource only on its first call.
* **Handshake Integrity**: Specifically for MCP/stdio, ensuring the first 100ms of process life are reserved for protocol negotiation.

## INSTRUCTION
1. **Identify Slow Resources**: Flag any call to Vaults (Bitwarden), Databases (SurrealDB), or external APIs (`httpx`, `requests`).
2. **Refactor Constants to Accessors**:
   - **Vulnerable**: `TOKEN = get_vault().get_secret("KEY")`
   - **Stable**:
     ```python
     _token = None
     def get_token():
         global _token
         if _token is None:
             _token = get_vault().get_secret("KEY")
         return _token
     ```
3. **Audit during CI**: Use `make mcp-guard` to ensure no new top-level assignments from accessor functions are introduced.

## VERSION
v1.0 (Hermetic Standard)

## SEE ALSO
- MCP_OPTIMIZATION_PRIME.md


## AUTO-REFINEMENT (Learning 158)
*   **Insight**: AsyncSurreal Migration & Connect Protocol
*   **Details**: The `surrealdb-py` library (v0.3.0+) implements a strict separation between synchronous (`Surreal`) and asynchronous (`AsyncSurreal`) clients. Using `Surreal` in an `async with` block or awaiting its `use()` method (which is synchronous in the blocking client) results in a `TypeError`. **Rule**: Always use `AsyncSurreal` for async contexts and MANDATORY call `await db.connect()` before `signin()` or `use()`.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 159)
*   **Insight**: Doc-Retriever & Memory Consistency
*   **Details**: Fixing infrastructure requires a "Sweep Pattern"—identifying all modules sharing a common dependency (e.g., SurrealDB) and verifying they all adhere to the updated protocol. The migration of `doc/indexer.py` and `memory/server.py` to `AsyncSurreal` restored coherence across the "Compound Engineering" and "Physics" server groups.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 277)
*   **Insight**: L183 Total Artifact Persistence — Wiring Pattern
*   **Details**: `persist_prompt_artifact()` and `persist_universe_snapshot()` in `genesis_persistence.py` were never called anywhere in the codebase (zero call sites). Wired into `CompoundExecutor.execute_task()` as Step 9.1 (universe snapshot, after JourneyTracker at line ~1036) and Step 10.7 (prompt artifact, before return at line ~1131). Async boundary: `execute_task()` is synchronous — use `asyncio.ensure_future()` when a loop is running, `asyncio.run()` otherwise. Both calls wrapped in `try/except Exception` (non-blocking). Result: 586 prompt_artifacts + 578 universe_snapshots populated in one session.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 279)
*   **Insight**: anyio Event Loop Hang — ResourceMonitor Heartbeat Anti-Pattern
*   **Details**: `ResourceMonitor.__init__` calls `loop.create_task(self._heartbeat_loop())` when a running event loop is detected. anyio's test runner provides a live loop, so the heartbeat spawns. When anyio shuts down the loop at test end, the still-running heartbeat blocks `loop.run_until_complete()` indefinitely. Two fix patterns: (1) `async` autouse fixture calling `await monitor.stop()` after each test (for tests that own the monitor), (2) monkeypatch `_register_with_monitor` / `_deregister_from_monitor` to no-ops so the monitor is never instantiated (for tests that only incidentally touch it). Root fix (deferred): move heartbeat start to an explicit `start()` method — constructors must not spawn background tasks.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 158)
*   **Insight**: AsyncSurreal Migration & Connect Protocol
*   **Details**: The `surrealdb-py` library (v0.3.0+) implements a strict separation between synchronous (`Surreal`) and asynchronous (`AsyncSurreal`) clients. Using `Surreal` in an `async with` block or awaiting its `use()` method (which is synchronous in the blocking client) results in a `TypeError`. **Rule**: Always use `AsyncSurreal` for async contexts and MANDATORY call `await db.connect()` before `signin()` or `use()`.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 159)
*   **Insight**: Doc-Retriever & Memory Consistency
*   **Details**: Fixing infrastructure requires a "Sweep Pattern"—identifying all modules sharing a common dependency (e.g., SurrealDB) and verifying they all adhere to the updated protocol. The migration of `doc/indexer.py` and `memory/server.py` to `AsyncSurreal` restored coherence across the "Compound Engineering" and "Physics" server groups.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 277)
*   **Insight**: L183 Total Artifact Persistence — Wiring Pattern
*   **Details**: `persist_prompt_artifact()` and `persist_universe_snapshot()` in `genesis_persistence.py` were never called anywhere in the codebase (zero call sites). Wired into `CompoundExecutor.execute_task()` as Step 9.1 (universe snapshot, after JourneyTracker at line ~1036) and Step 10.7 (prompt artifact, before return at line ~1131). Async boundary: `execute_task()` is synchronous — use `asyncio.ensure_future()` when a loop is running, `asyncio.run()` otherwise. Both calls wrapped in `try/except Exception` (non-blocking). Result: 586 prompt_artifacts + 578 universe_snapshots populated in one session.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 279)
*   **Insight**: anyio Event Loop Hang — ResourceMonitor Heartbeat Anti-Pattern
*   **Details**: `ResourceMonitor.__init__` calls `loop.create_task(self._heartbeat_loop())` when a running event loop is detected. anyio's test runner provides a live loop, so the heartbeat spawns. When anyio shuts down the loop at test end, the still-running heartbeat blocks `loop.run_until_complete()` indefinitely. Two fix patterns: (1) `async` autouse fixture calling `await monitor.stop()` after each test (for tests that own the monitor), (2) monkeypatch `_register_with_monitor` / `_deregister_from_monitor` to no-ops so the monitor is never instantiated (for tests that only incidentally touch it). Root fix (deferred): move heartbeat start to an explicit `start()` method — constructors must not spawn background tasks.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 305)
*   **Insight**: Asynchronous Workforce via A2A Protocol
*   **Details**: Decentralizing the swarm requires moving away from synchronous chat interfaces. Extending the GitHub MCP with a dedicated polling daemon (`github_scout.py`) allows agents to process issues asynchronously. Combining this with the A2A protocol (`.well-known/agent.json`) ensures agents can discover and dispatch each other over HTTP.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 309)
*   **Insight**: SIGReg-HIHO Equivalence (LeWM Correspondence)
*   **Details**: LeWM's Gaussian regularizer (SIGReg → N(0,I) → maximum entropy) is provably equivalent to HIHO (coherence 0.5 → all brane dims at 0.5 → maximum Shannon entropy → minimum computation). Isotropic Gaussian ↔ uniform brane dimensions ↔ maximum entropy ↔ minimum computation. LeWM discovers temporal latent path straightening through training; Cohezion encodes it by construction via constant-metric Christoffel precomputation (Γ=0 at HIHO).

## Session 98: Agentic Ascension & Asynchronous Workforce (2026-04-10)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 318)
*   **Insight**: Asynchronous Workforce via A2A Protocol
*   **Details**: Decentralizing the swarm requires moving away from synchronous chat interfaces. Extending the GitHub MCP with a dedicated polling daemon (`github_scout.py`) allows agents to process issues asynchronously. Combining this with the A2A protocol (`.well-known/agent.json`) ensures agents can discover and dispatch each other over HTTP.
*   **Date**: 2026-04-11
