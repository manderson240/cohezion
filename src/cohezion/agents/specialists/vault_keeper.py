"""vault-keeper: Cohezion Bitwarden vault health + frontmatter enforcement specialist."""

from __future__ import annotations

from cohezion.agents.specialists._base import AgentCard, PlatformSpecialist, register


@register
class VaultKeeper(PlatformSpecialist):
    """Keeps the Bitwarden-backed Cohezion vault healthy and well-formed.

    Scope:
        - Bitwarden vault connectivity and session health (``BW_SESSION``, ``bw`` CLI).
        - YAML frontmatter enforcement on skill/agent markdown per MCP rules.
        - Orphan detection: vault entries referenced but not present; cortex MOCs.

    Out of scope:
        - Storing secrets inside SurrealDB (forbidden; see §Security).
        - Running LLM calls directly.
    """

    CARD = AgentCard(
        name="vault-keeper",
        display_name="Vault Keeper",
        description=(
            "Keeps the Bitwarden-backed Cohezion vault healthy. Enforces YAML frontmatter "
            "on skill/agent markdown, surfaces orphan vault entries, and audits for missing "
            "`name`+`description` fields (which silently disable capabilities)."
        ),
        role="Vault health auditor + frontmatter enforcer",
        capabilities=(
            "audit.vault.frontmatter",
            "audit.vault.orphans",
            "check.vault.connectivity",
            "report.vault.health",
        ),
        principles=(
            "Never log, print, or persist vault-returned secret values.",
            "Vault key namespace is `<service>/<name>`; reject entries outside it.",
            "Missing `name`+`description` frontmatter = silent failure — treat as P0.",
            "Vault contents are secrets; sanitize any error messages that echo them.",
        ),
        prime_skill_ref="src/cohezion/skills/vault-keeper.md",
        canonical_modules=(
            "cohezion.security.vault",
            "cohezion.core.vault_subscription",
            "cohezion.hookify.vault_writer",
        ),
    )
