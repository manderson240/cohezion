"""Vault-Guided Router for intelligent task offloading."""

import logging
from typing import Any

from cohezion.core.mcp_client import MCPClient, get_mcp_client
from cohezion.core.persistence.surreal_client import SurrealClient

logger = logging.getLogger(__name__)


class VaultGuidedRouter:
    """
    Intelligent router that uses the Obsidian Vault and SurrealDB knowledge graph
    to recommend optimal model routing and offloading.
    """

    def __init__(self, surreal_url: str = "ws://localhost:8000/rpc"):
        self.surreal = SurrealClient(url=surreal_url)
        self._mcp: MCPClient | None = None

    @property
    def mcp(self) -> MCPClient:
        if self._mcp is None:
            self._mcp = get_mcp_client()
        return self._mcp

    async def get_routing_recommendation(
        self, task_type: str, context: str
    ) -> dict[str, Any]:
        """
        Query for context in both KBs and recommend a routing strategy.
        """
        # 1. Search Vault for patterns/learnings
        vault_patterns = []
        vault_learnings = []
        try:
            vault_patterns = self.mcp.vault_search(f"{task_type} pattern")
            vault_learnings = self.mcp.vault_search(f"{task_type} learning")
        except Exception as e:
            logger.warning(f"Vault search failed: {e}")

        # 2. Search SurrealDB for mission context
        surreal_context = []
        try:
            # Simple keyword extraction
            keywords = [k for k in context.split() if len(k) > 4][:3]
            if keywords:
                q = keywords[0]
                # Query universe_nodes for relevant thoughts
                # The mock handles FROM universe_nodes or FROM agent_thought sometimes
                res = await self.surreal.query(
                    "SELECT * FROM universe_nodes WHERE node_type = 'agent_thought' LIMIT 10"
                )
                if res and isinstance(res, list) and len(res) > 0:
                    result_data = res[0].get("result", [])
                    surreal_context = [
                        n
                        for n in result_data
                        if q.lower() in n.get("content", "").lower()
                    ]
        except Exception as e:
            logger.warning(f"SurrealDB context retrieval failed: {e}")

        # 3. Analyze context for offload candidates
        offload_recommended = False
        reason = "No matching pattern found in Vault."

        # If we find a high-fidelity learning or pattern for this specific task, recommend local
        if vault_learnings:
            offload_recommended = True
            reason = f"High-fidelity learning found in Vault for {task_type}."
        elif vault_patterns:
            offload_recommended = True
            reason = f"Reusable pattern found in Vault for {task_type}."
        elif len(surreal_context) > 3:
            # Lots of similar thoughts in SurrealDB might also justify local if we have a pattern
            offload_recommended = True
            reason = f"High density of similar thoughts ({len(surreal_context)}) in SurrealDB suggests pattern stability."

        suggested_model = "qwen3-coder-32b" if offload_recommended else "gemini-3-pro"

        recommendation = {
            "offload_recommended": offload_recommended,
            "reason": reason,
            "vault_context_count": len(vault_patterns) + len(vault_learnings),
            "surreal_context_count": len(surreal_context),
            "suggested_model": suggested_model,
        }

        logger.info(f"Routing recommendation for {task_type}: {recommendation}")
        return recommendation


def get_guided_router() -> VaultGuidedRouter:
    return VaultGuidedRouter()
