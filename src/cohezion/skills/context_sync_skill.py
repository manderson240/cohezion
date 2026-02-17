"""Vault Synchronization Skill Helper."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class VaultSyncSkill:
    """Helper for syncing Antigravity context with the Obsidian Vault via MCP."""

    mcp: Any

    def __init__(self, mcp_client: Any = None):
        self.mcp = mcp_client

    async def push_current_state(
        self, branch: str, phase: str, tasks: list[str]
    ) -> str:
        """Push current session state to the vault."""
        if not self.mcp:
            return "Error: MCP client not initialized"

        try:
            result = await self.mcp.call_tool(
                "vault_push_session_state",
                {
                    "branch": branch,
                    "phase": phase,
                    "active_tasks": tasks,
                    "test_status": "N/A",
                    "last_commit": "",
                },
            )
            return str(result)
        except Exception as e:
            logger.error(f"Failed to push session state: {e}")
            return f"Error: {e}"

    async def log_decision(
        self, project: str, title: str, decision: str, rationale: str
    ) -> str:
        """Log a decision to the vault."""
        if not self.mcp:
            return "Error: MCP client not initialized"

        try:
            result = await self.mcp.call_tool(
                "vault_log_decision",
                {
                    "project": project,
                    "title": title,
                    "context": "Antigravity Session",
                    "decision": decision,
                    "rationale": rationale,
                },
            )
            return str(result)
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
            return f"Error: {e}"

if __name__ == "__main__":
    # Example usage (standalone)
    pass
