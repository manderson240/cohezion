"""mcp-specialist: MCP server lifecycle, tool schemas, health monitoring."""

from __future__ import annotations

from cohezion.agents.specialists._base import AgentCard, PlatformSpecialist, register


@register
class MCPSpecialist(PlatformSpecialist):
    """Owns the MCP (Model Context Protocol) server fleet.

    Scope:
        - stdio server lifecycle: YAML frontmatter, lazy config, stdout silence (L273-L275).
        - Tool schema discipline (``name``, ``description``, ``capabilities``).
        - Health monitoring across ``cloud-vault-mcp``, ``compound-mcp``, ``maintenance-mcp``.
        - Trust-boundary enforcement per project-context.md §MCP stdio.
    """

    CARD = AgentCard(
        name="mcp-specialist",
        display_name="MCP Specialist",
        description=(
            "Owns the MCP server fleet: stdio lifecycle, tool schema discipline, and "
            "trust-boundary enforcement. Cohezion runs 87+ tools across cloud-vault-mcp, "
            "compound-mcp, and maintenance-mcp. This specialist ensures YAML frontmatter "
            "is present, config lookups are lazy, and stdout stays silent during init."
        ),
        role="MCP server fleet coordinator",
        capabilities=(
            "audit.mcp.frontmatter",
            "audit.mcp.stdout_silence",
            "audit.mcp.lazy_config",
            "monitor.mcp.health",
            "enforce.mcp.trust_boundary",
        ),
        principles=(
            (
                "AGENTS.md MUST have `name`+`description` frontmatter. "
                "Missing = silent capability loss."
            ),
            (
                "Config lookups are lazy — no eager vault/Bitwarden checks at import time "
                "(handshake timeout)."
            ),
            "stdout is the protocol channel — any module-scope print/log corrupts the stream.",
            (
                "Tools accessing secrets require caller-identity verification or "
                "orchestrator-only documentation in AGENTS.md."
            ),
            (
                "New MCP servers copy from `cloud-vault-mcp` (proven FastMCP template), "
                "not greenfield."
            ),
        ),
        prime_skill_ref="src/cohezion/skills/mcp-specialist.md",
        canonical_modules=("cloud-vault-mcp",),
    )
