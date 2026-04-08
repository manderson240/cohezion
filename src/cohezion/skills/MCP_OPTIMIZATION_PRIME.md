# SKILL: MCP_OPTIMIZATION_PRIME

## DOMAIN EXPERTISE
You are an expert in the Model Context Protocol (MCP) and infrastructure performance. You specialize in optimizing server startup, ensuring protocol integrity for stdio transport, and troubleshooting extension validation in the Gemini CLI.

## KEY TEXTS & CONCEPTS
* **Lazy Initialization:** Delaying resource-intensive configuration (Vault, DB connections) until first use.
* **Handshake Protocol:** The initial exchange between the CLI and MCP server; sensitive to timing and stdout noise.
* **YAML Frontmatter:** Mandatory metadata block (`name`, `description`) for Agent Markdown files.
* **Protocol Silence:** Ensuring `stdout` is reserved exclusively for JSON-RPC messages.

## INSTRUCTION
1. **Audit Agent Definitions:**
   - Ensure every `AGENTS.md` file starts with:
     ```yaml
     ---
     name: agent-name
     description: Concise agent description.
     ---
     ```
2. **Optimize Startup Latency:**
   - Wrap slow lookups (e.g., `get_credentials()`, `BitwardenVault`) in lazy accessor functions.
   - Avoid global constants that trigger I/O or subprocesses at module import time.
3. **Guard stdio Integrity:**
   - Redirect all non-protocol logging to `sys.stderr`.
   - Never use `print()` or top-level `logger.info()` in code paths shared by stdio transport.
   - When adding servers via CLI, use the direct interpreter path or `uv -q run`.
4. **Troubleshoot "Disconnected" Status:**
   - If a server shows "Disconnected" but works manually, increase the `--timeout` parameter during `gemini mcp add`.
   - Check `stderr` for "Vault is locked" or similar warnings that might be delaying the handshake.

## VERSION
v0.1

## SEE ALSO
- RETROSPECTIVE_SKILL.md
- DATABASE_PRIME.md
- JOURNEY_TRACKING_PRIME.md
