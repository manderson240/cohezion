# Dynamic Modularity Implementation Plan (v2 - Adversarial Hardened)

## Background & Motivation
Cohezion is transitioning from a "monolith-in-transition" to a fully decentralized architecture powered by the Model Context Protocol (MCP). Currently, `src/cohezion/__main__.py` handles a large number of disparate domains (e.g., journey, simulate, rewards) in a single synchronous process.

Following an adversarial review covering Performance, DevOps, Security, and Developer Experience (DevEx), the standard "Universal MCP Server Infrastructure" blueprint has been hardened. We will build a distributed, modular architecture that remains fast, secure, and easy to debug on localhost.

## Scope & Impact
- **Target:** Extract CLI logic from `__main__.py` into independent local MCP servers.
- **Affected Areas:** CLI command handlers, `src/cohezion/mcp/manager.py`, and `mcp_registry.json`.
- **Impact:** Decoupling of codebase operations. Commands execute asynchronously via local MCP interfaces, heavily fortified against latency, zombie processes, and unauthorized access.

## Proposed Solution (Hardened MCP Microservices)

We will implement the MCP Microservices approach with four critical adversarial mitigations:

1. **Performance (Mitigating Latency):** 
   - **Lazy-Start & UDS:** MCP servers will lazy-load only when their specific domain is invoked. To eliminate TCP overhead, internal communication will default to Unix Domain Sockets (UDS) or named pipes where the OS permits, falling back to TCP (8360-8399) only for cloud/external IDE access.
2. **DevOps (Mitigating Zombie Processes):**
   - **Strict Process Binding:** The `MCPServerManager` will bind its lifecycle to the parent CLI's Process ID (PID) using robust signaling, or utilize user-level `systemd` (`systemctl --user`) to ensure background servers are strictly managed and gracefully terminated.
3. **Security (Mitigating Localhost Attack Surface):**
   - **Ephemeral Auth Tokens:** The Manager will generate an ephemeral authentication token stored in `~/.cohezion/auth.token` (with strict `600` file permissions). All local HTTP/SSE MCP requests must include this token as a Bearer header, preventing unauthorized scripts from triggering platform actions.
4. **DevEx (Mitigating Distributed Debugging Pain):**
   - **Unified Log Aggregation:** Implement a `cohezion logs` command that tails and aggregates standard output, standard error, and internal logs from all background MCP servers into a single chronological, color-coded stream.

## Phased Implementation Plan

### Phase 1: Hardened Infrastructure Preparation
- Enhance `src/cohezion/mcp/manager.py` with the Ephemeral Auth Token generation and validation.
- Implement process lifecycle hooks (PID binding or systemd integration) to prevent zombie servers.
- Add Unix Domain Socket (UDS) support alongside TCP port allocation.

### Phase 2: Domain Server Extraction
- Create `journey_server.py` exposing tools like `start_journey`, `list_journeys`.
- Create `simulate_server.py` exposing tools like `run_simulation`.
- Create `rewards_server.py` exposing tools like `get_rewards_status`.
- Register these in `mcp_registry.json`.

### Phase 3: Thin Client & Unified Logging
- Rewrite `src/cohezion/__main__.py` to parse commands and forward them to the `MCPServerManager` securely.
- Build the `cohezion logs` unified streaming viewer.
- Include logic for the CLI to trigger a lazy-start of required background servers.

### Phase 4: Finalization & Validation
- Run the full test suite (`make test`).
- Test graceful shutdown (e.g., SIGINT/Ctrl+C) to ensure no orphaned processes remain.
- Migrate remaining smaller commands (`mycelium`, `ouroboros`).

## Validation
- Execute `cohezion journey start "Test"` and verify it securely routes through the `cohezion-journey` MCP server.
- Verify unauthorized `curl` requests to the MCP ports are rejected (HTTP 401).
- Confirm terminating the CLI cleans up child MCP processes.

## Migration & Rollback
- Retain a `--legacy-execution` flag in the CLI during the transition. If MCP is disabled, fails to initialize, or sockets are blocked, the CLI can fall back to directly importing the local Python modules.