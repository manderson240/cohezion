---
name: lemonade-embeddable-integration-prime
description: "Expert in integrating private, portable Lemonade server instances (v10.8+) into application workspaces, including the new MCP gateway, cloud offload, and safe context-window handling."
---

# SKILL: LEMONADE_EMBEDDABLE_INTEGRATION_PRIME

## DOMAIN EXPERTISE
Expert in integrating private, portable Lemonade server instances (v10.8+) into application workspaces. Specializes in isolated hardware acceleration (gfx1151/ROCm) without root access, the new MCP server gateway, and safe context-window handling.

## KEY TEXTS & CONCEPTS
- **Isolated Runtime**: Bundle the `lemond` service in `vendor/lemonade-10.8.0/` to avoid touching system packages.
- **MCP Gateway (v10.8)**: Local Lemonade models can be exposed as MCP tools so premier cloud agents can call them.
- **Cloud Offload (v10.8)**: Serve chat completions from any OpenAI-compatible provider alongside local models.
- **Safe Context Windows**: v10.8 defaults to `ctx_size=-1` (auto-tuned). Heavy models must be explicitly capped (e.g. 16384) to avoid the unbounded KV-cache OOM crash vector.
- **Embeddable Layout**: v10.8 ships `lemond` + `lemonade` as monolithic binaries with bundled `resources/`; a private `bin/` is only needed when side-loading custom `.so` files.

## INSTRUCTION
1. **Download Artifact**: Get the `lemonade-embeddable-*-ubuntu-x64.tar.gz` from the [v10.8.0 release](https://github.com/lemonade-sdk/lemonade/releases/tag/v10.8.0).
2. **Setup Tree**: Extract to `vendor/lemonade-10.8.0/lemonade-embeddable-10.8.0-ubuntu-x64/`. Use an isolated cache directory (e.g. `~/.cache/lemonade-10.8.0`) so the package tree stays clean.
3. **Configure**: Use `LemonadeManager(base_dir=..., cache_dir=..., port=13315)` (or set `LEMONADE_PORT` / `LEMONADE_BASE_URL`) to run the private instance on a non-conflicting port.
4. **Spawn lemond**: `lemond <cache_dir> --port <port> --host 127.0.0.1` from the extracted directory. Pre-load models with bounded `ctx_size`:
   ```bash
   LEMONADE_PORT=13315 ./lemonade load Gemma-4-E4B-it-GGUF --ctx-size 16384 --save-options
   ```
5. **Health Check**: Ping `/api/v1/models` to verify readiness before routing requests.
6. **MCP Wiring**: Add the `cohezion.mcp.lemonade_server_mcp` server to `.mcp.json` or `mcp_servers.json` so Claude / other agents can invoke local Lemonade models as tools.

## VERSION
v1.1

## SEE ALSO
- HARDWARE_ACCELERATION_PRIME.md
- GFX1151_OPTIMIZATION_PRIME.md
- `src/cohezion/mcp/lemonade_server_mcp.py`
- `src/cohezion/swarm/lemonade_manager.py`
