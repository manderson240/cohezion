# Plan: MCP Stabilization & Unification (2026-04-02)

## 1. Objective
Unify the MCP infrastructure (legacy `aiohttp` servers vs. new `FastMCP` servers) into a single, `uv`-managed ecosystem. This ensures stability, standardizes the `stdio` transport for Gemini CLI, and resolves dependency conflicts (Python 3.14 vs. 3.12).

## 2. Key Files & Context
- `pyproject.toml`: The single source of truth for dependencies.
- `.python-version`: To lock `uv` to Python 3.12 for this project.
- `src/cohezion/mcp/`: The target directory for unified server entry points.
- `.gemini/settings.json`: The configuration for Gemini CLI tools.
- `mcp_servers.json`: The configuration for external discovery.

## 3. Implementation Steps

### Phase 1: Environment Stabilization (The Foundation)
1.  **Lock Python Version**: Create `.python-version` with `3.12` to ensure `uv` always uses the compatible interpreter.
2.  **Verify `uv` Sync**: Run `uv sync --all-extras` to ensure all `ml`, `audio`, and `dev` dependencies are correctly resolved in the local `.venv`.
3.  **Clean Legacy State**: Stop any lingering Docker or Python processes from previous attempts (`pkill -f cohezion.mcp`).

### Phase 2: Unified Server Architecture (The Structure)
1.  **Audit Server Modules**: Map all existing servers in `src/cohezion/mcp/` and `src/cohezion/mcp/servers/`.
2.  **Standardize `FastMCP`**: Update any legacy `aiohttp` servers to use the `FastMCP` decorator pattern if they aren't already. This provides built-in `stdio` and `http` support.
3.  **Fleet Management**: Create `src/cohezion/mcp/fleet.py` as a central dispatcher that can start any server using `uv run python -m cohezion.mcp.fleet [server_name]`.

### Phase 3: Configuration Synchronization (The Interface)
1.  **Derive Configs**: Create a script `scripts/generate_mcp_configs.py` that generates both `.gemini/settings.json` and `mcp_servers.json` from the `src/cohezion/mcp/fleet.py` registry.
2.  **Update `start-mcp-servers.sh`**: Refactor this script to be a simple wrapper around `uv run python -m cohezion.mcp.fleet --all`.

### Phase 4: Verification (The Proof)
1.  **Health Check Script**: Create `tests/mcp/test_fleet_health.py` to programmatically verify each server starts and responds to a `list_tools` request via `stdio`.
2.  **HIHO Coherence**: Use the `cohezion-coherence` server to verify the system's own alignment after the changes.

## 4. Verification & Testing
- `uv run pytest tests/mcp/test_fleet_health.py`
- `uv run ruff check src/cohezion/mcp/`
- `uv run mypy src/cohezion/mcp/`

## 5. Security & Safety
- **No Secrets**: Ensure all `env` variables in generated configs use placeholders or system env vars, never hardcoded keys.
- **Principle of Least Privilege**: Each MCP server will only have the `env` variables it strictly requires.
