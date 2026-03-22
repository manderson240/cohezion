# Fix Vault MCP "Session not found" Error

Created: 2026-02-23
Status: VERIFIED
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)
>
> - PENDING: Initial state, awaiting implementation
> - COMPLETE: All tasks implemented
> - VERIFIED: All checks passed
>
> **Approval Gate:** Implementation CANNOT proceed until `Approved: Yes`
> **Worktree:** Set at plan creation (from dispatcher). `Yes` uses git worktree isolation; `No` works directly on current branch

## Summary

**Goal:** Fix vault MCP tools failing with "Session not found" by switching to stateless HTTP mode

**Architecture:** The MCP Python SDK's `StreamableHTTPSessionManager` runs in stateful mode by default, assigning each client a session ID stored in server memory. When the server restarts (or the systemd service crashes and a manual `run_mcp.py` takes over), Claude Code retains the old session ID and sends it — but the new server instance doesn't recognize it, returning HTTP 404 "Session not found". The fix is to enable `stateless_http=True` on the FastMCP server. In stateless mode, `_handle_stateless_request()` ignores incoming `Mcp-Session-Id` headers entirely and creates a fresh transport per request — verified in `mcp/server/streamable_http_manager.py:152-196`.

**Tech Stack:** Python, FastMCP (mcp==1.26.0), Starlette/ASGI

## Root Cause Analysis

1. **`server.py:61`** creates `FastMCP("Cloud Vault", ...)` without `stateless_http=True`
2. FastMCP defaults to stateful mode → `StreamableHTTPSessionManager(stateless=False)`
3. In stateful mode, `_handle_stateful_request()` requires clients to either:
   - Send NO session ID (creates a new session)
   - Send a VALID session ID (routes to existing session)
4. When a stale/unknown session ID is sent → HTTP 404 "Session not found" (`streamable_http_manager.py:289`)
5. Claude Code caches the session ID from a previous server instance and resends it after server restarts

**All 40+ vault tools work correctly in stateless mode** — they read/write files, query SurrealDB, call Ollama, etc. While some tools (`surrealdb_start_watching`/`stop_watching`) maintain application-layer state (a `watchdog.Observer` thread on the `SurrealDBSync` object), this state is independent of the MCP session layer. Stateless HTTP mode only removes per-request session tracking; it does not affect application objects that persist for the server's lifetime.

## Scope

### In Scope

- Switch FastMCP server to `stateless_http=True` mode
- Add `stateless_http` config option to `ServerConfig` (env: `MCP_STATELESS`)
- Fix the failed systemd service (`cohezion-vault.service`) so it manages the server properly
- Add tests verifying stateless mode works

### Out of Scope

- Changes to the tool implementations themselves
- Client-side changes (Claude Code MCP client)
- MCP protocol version changes
- Authentication/TLS changes

## Prerequisites

- `cloud-vault-mcp` project with `mcp>=1.26.0` (confirmed: 1.26.0 installed)
- Access to the running vault server for manual verification

## Context for Implementer

- **Patterns to follow:** Configuration follows env-var-to-dataclass pattern in `cloud-vault-mcp/src/mcp_server/config.py`
- **Key files:**
  - `cloud-vault-mcp/src/mcp_server/server.py` — creates `FastMCP` instance (line 61)
  - `cloud-vault-mcp/src/mcp_server/config.py` — `ServerConfig` dataclass
  - `cloud-vault-mcp/src/mcp_server/main.py` — entry point, creates server and ASGI app
  - `~/.config/systemd/user/cohezion-vault.service` — systemd unit (currently failed)
- **Gotchas:**
  - The server is currently running manually via `python3 run_mcp.py` (PID 199880), NOT via systemd
  - The systemd service failed because port 8360 was already in use by the manual process
  - In stateless mode, each request creates a fresh transport — no session ID header is needed or returned
  - `main.py` calls `mcp.streamable_http_app()` directly (line 64), which uses `self.settings.stateless_http`

## Runtime Environment

- **Start command:** `uv run python run_mcp.py` (from `cloud-vault-mcp/` dir)
- **Port:** 8360
- **Health check:** `curl http://localhost:8360/health`
- **Systemd service:** `systemctl --user restart cohezion-vault.service`
- **Restart procedure:** Kill existing process, restart via systemd or manual

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [x] Task 1: Add stateless_http config option to ServerConfig
- [x] Task 2: Enable stateless_http on FastMCP server creation
- [x] Task 3: Fix systemd service to manage server lifecycle reliably
- [x] Task 4: Add tests for stateless HTTP mode

**Total Tasks:** 4 | **Completed:** 4 | **Remaining:** 0

## Implementation Tasks

### Task 1: Add stateless_http config option to ServerConfig

**Objective:** Add a configurable `stateless_http` option to `ServerConfig` that defaults to `True`, controllable via `MCP_STATELESS` environment variable.

**Dependencies:** None

**Files:**
- Modify: `cloud-vault-mcp/src/mcp_server/config.py`
- Create: `cloud-vault-mcp/tests/test_config.py`

**Key Decisions / Notes:**
- Default to `True` (stateless) since all tools are request/response
- Environment variable: `MCP_STATELESS` (default: `"true"`)
- Follow existing pattern: `bool` field with `os.environ.get()` factory

**Definition of Done:**
- [ ] `ServerConfig` has `stateless_http: bool` field defaulting to `True`
- [ ] `MCP_STATELESS=false` overrides to stateful mode
- [ ] Test verifies default value and env override

**Verify:**
- `cd cloud-vault-mcp && uv run pytest tests/test_config.py -q`

### Task 2: Enable stateless_http on FastMCP server creation

**Objective:** Pass `stateless_http=config.stateless_http` when creating the `FastMCP` instance in `create_server()`.

**Dependencies:** Task 1

**Files:**
- Modify: `cloud-vault-mcp/src/mcp_server/server.py`
- Test: `cloud-vault-mcp/tests/test_server_stateless.py`

**Key Decisions / Notes:**
- The `FastMCP` constructor accepts `stateless_http: bool` parameter (confirmed in mcp 1.26.0)
- `create_server()` currently takes `config: ServerConfig` — use `config.stateless_http`
- In stateless mode, each request creates a fresh transport with no session tracking
- All existing tools work without modification — MCP tool statefulness is at the application layer (e.g., `SurrealDBSync` holds a watchdog `Observer` thread), not the MCP session layer. Stateless HTTP mode only affects transport/session tracking, not application objects.

**Definition of Done:**
- [ ] `create_server()` passes `stateless_http=config.stateless_http` to `FastMCP()` — no signature change needed, it already receives the full `ServerConfig`
- [ ] Test creates server with stateless_http=True and verifies tool call succeeds without a session ID header
- [ ] Test creates server with stateless_http=False and verifies session behavior

**Verify:**
- `cd cloud-vault-mcp && uv run pytest tests/test_server_stateless.py -q`

### Task 3: Fix systemd service to manage server lifecycle reliably

**Objective:** Update the systemd service unit so it properly manages the vault server, including killing stale processes on port 8360 before starting.

**Dependencies:** Task 2

**Files:**
- Modify: `~/.config/systemd/user/cohezion-vault.service`
- Modify: `cloud-vault-mcp/run_mcp.py` (if needed, to add PID file or pre-start cleanup)

**Key Decisions / Notes:**
- Current failure: systemd tries to start → port 8360 already in use by manual `run_mcp.py` → fails → retry limit → gives up
- Use a PID file approach: `run_mcp.py` writes its PID to `/tmp/cohezion-vault.pid`; `ExecStartPre` kills that specific PID if present (avoids `fuser -k` which kills any process on the port indiscriminately)
- Add `ExecStartPre=-/bin/sh -c 'kill $(cat /tmp/cohezion-vault.pid) 2>/dev/null; sleep 0.5; rm -f /tmp/cohezion-vault.pid'`
- Add `PIDFile=/tmp/cohezion-vault.pid` to service unit to let systemd track it natively

**Definition of Done:**
- [ ] `systemctl --user restart cohezion-vault.service` succeeds even if port 8360 is occupied
- [ ] Service stays running after restart
- [ ] `curl http://localhost:8360/health` returns healthy status after service restart

**Verify:**
- `systemctl --user status cohezion-vault.service` shows `active (running)`
- `curl -s http://localhost:8360/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])"`

### Task 4: Add tests for stateless HTTP mode

**Objective:** Add integration-level tests that verify the "Session not found" error no longer occurs in stateless mode.

**Dependencies:** Task 2

**Files:**
- Create: `cloud-vault-mcp/tests/test_stateless_http.py`

**Key Decisions / Notes:**
- Test that a tool call works without sending a session ID header
- Test that a tool call works even with a stale/bogus session ID header (the key fix)
- Use httpx `AsyncClient` against the ASGI app directly (no running server needed)
- MCP wire format: `POST /mcp` with `Content-Type: application/json`, `Accept: application/json, text/event-stream`, body `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}`
- The response is SSE (`text/event-stream`) — parse `data:` lines as JSON
- For the stale-session test: add `Mcp-Session-Id: stale-bogus-id` header to an initialize request; in stateless mode it should succeed (200), not return 404
- Consolidate all stateless-specific HTTP tests here (Task 2 unit tests cover the `create_server()` wiring; this file covers the HTTP behavior)

**Definition of Done:**
- [ ] Test: tool call succeeds without session ID in stateless mode
- [ ] Test: tool call succeeds with stale session ID in stateless mode (previously failed with "Session not found")
- [ ] Test: stateful mode still returns error for invalid session ID (regression guard)
- [ ] All tests pass

**Verify:**
- `cd cloud-vault-mcp && uv run pytest tests/test_stateless_http.py -q`

## Testing Strategy

- **Unit tests:** Config parsing (Task 1), server creation with stateless flag (Task 2)
- **Integration tests:** ASGI-level HTTP tests simulating stale session IDs (Task 4)
- **Manual verification:** After deployment, call vault tools from Claude Code and verify they work without "Session not found"

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Stateless mode creates overhead from fresh transport per request | Low | Low | Vault tools are lightweight file/DB operations; transport creation is negligible overhead |
| Some tool may secretly depend on session state | Low | Med | Audited all 40+ tools — all are pure request/response with no cross-request state |
| Systemd cleanup kills wrong process on port 8360 | Low | Med | Use PID file approach (`/tmp/cohezion-vault.pid`) to kill only the known vault process by PID |
| Claude Code client doesn't support stateless mode | Low | High | Verified in SDK source: `_handle_stateless_request()` never reads `Mcp-Session-Id` — stale headers are silently ignored, compliant clients work unchanged |

## Open Questions

- None — root cause is clear and fix is straightforward

### Deferred Ideas

- Add session persistence (e.g., Redis-backed) for future features that might need stateful sessions
- Add a `/status` endpoint that reports whether the server is in stateless or stateful mode
