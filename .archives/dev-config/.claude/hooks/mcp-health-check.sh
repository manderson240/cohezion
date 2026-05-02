#!/usr/bin/env bash
# SessionStart: MCP health check
# Pings HTTP-accessible MCP servers and warns about degraded ones.
# Non-blocking: prints warnings but never blocks session start.
# stdio-based servers are spawned on demand and cannot be proactively checked.

DEGRADED=()

# Check cohezion-vault (the only HTTP MCP server)
if ! curl -sf --max-time 3 "http://localhost:8360/health" > /dev/null 2>&1; then
    DEGRADED+=("cohezion-vault (http://localhost:8360)")
fi

# Check SurrealDB (used by multiple MCP servers)
if ! curl -sf --max-time 2 "http://localhost:8001/health" > /dev/null 2>&1; then
    DEGRADED+=("surrealdb (http://localhost:8001)")
fi

# Check Ollama (used by compound engineering)
if ! curl -sf --max-time 2 "http://localhost:11434/api/tags" > /dev/null 2>&1; then
    DEGRADED+=("ollama (http://localhost:11434)")
fi

if [ ${#DEGRADED[@]} -gt 0 ]; then
    echo "[mcp-health-check] Warning: ${#DEGRADED[@]} service(s) unreachable:"
    for svc in "${DEGRADED[@]}"; do
        echo "  - $svc"
    done
    echo "[mcp-health-check] Run vault_health_check for full diagnostics, or /wake to start services."
fi

exit 0
