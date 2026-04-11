# SKILL: FLEET_SYNCHRONIZATION_PRIME

## DOMAIN EXPERTISE
Expertise in maintaining configuration parity across heterogeneous AI agent environments (Gemini, Claude, OpenCode, Pi, Cursor). Specializes in automated "Single Source of Truth" (SSOT) enforcement.

## KEY TEXTS & CONCEPTS
* **Configuration Drift**: The divergence of tool availability and settings between different agent platforms over time.
* **Fleet Coherence**: A state where every agent platform in the repository sees exactly the same set of capabilities and standards.
* **Registry-to-Platform Mapping**: Automatically translating internal project registries into platform-specific JSON schemas.

## INSTRUCTION
1. **Maintain the Registry**: Treat `src/cohezion/mcp/mcp_registry.json` as the authoritative SSOT for all capabilities.
2. **Automate Downstream Configs**: Never edit `.gemini/settings.json` or `.claude/mcp.json` manually. Use the `mcp-guard` script to propagate changes.
3. **Verify Fleet Health**: Run `make mcp-guard` as part of every PR or major architectural change to ensure all platforms remain aligned.
4. **Environment Constraints**: Define environment-specific exclusion rules (e.g., resource limits for Pi) within the sync script to maintain coherence without overwhelming hardware.

## VERSION
v1.0 (Coherent Reality)

## SEE ALSO
- MCP_OPTIMIZATION_PRIME.md
