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

        # 4. Check Budget Status (Fiscal Sovereignty)
        try:
            from cohezion.compound.telemetry import get_tracker

            budget_status = get_tracker().get_budget_status()

            if budget_status["is_exhausted"]:
                offload_recommended = True
                suggested_model = "phi3:mini"  # Force extreme economy
                reason = f"BUDGET EXHAUSTED (${budget_status['total_spent_usd']:.2f}). Emergency offload triggered."
            elif budget_status["is_critical"]:
                offload_recommended = True
                suggested_model = "qwen3-coder-32b"  # Force local
                reason = f"BUDGET CRITICAL (${budget_status['total_spent_usd']:.2f}). Throttling to local experts."
        except Exception as e:
            logger.warning(f"Budget check failed: {e}")

        recommendation = {
            "offload_recommended": offload_recommended,
            "reason": reason,
            "vault_context_count": len(vault_patterns) + len(vault_learnings),
            "surreal_context_count": len(surreal_context),
            "suggested_model": suggested_model,
        }

        logger.info(f"Routing recommendation for {task_type}: {recommendation}")
        return recommendation

    async def prune_context(
        self, messages: list[dict[str, str]], task_type: str, limit: int = 5
    ) -> list[dict[str, str]]:
        """
        Prune and summarize context using local SLM if density is high.
        """
        if len(messages) <= limit:
            return messages

        # 1. Rank messages
        ranker = SemanticContextRanker()
        ranked = ranker.rank_messages(messages, query=task_type)

        # 2. Keep top N most relevant
        keep_indices = {r["index"] for r in ranked[:limit]}

        # 3. Summarize the rest (Dynamic Pruning)
        pruned_messages = [m for i, m in enumerate(messages) if i not in keep_indices]

        if not pruned_messages:
            return [m for i, m in enumerate(messages) if i in keep_indices]

        # Summarization prompt
        pruned_text = "\n".join(
            [f"{m['role']}: {m['content'][:200]}..." for m in pruned_messages]
        )
        summary_prompt = f"""Summarize the following historical context into 3 key bullet points for a {task_type} mission.
Be extremely concise to save tokens.

PRUNED CONTEXT:
{pruned_text}
"""
        try:
            from cohezion.core.routing.router import LOCAL_ROUTER

            summary = await LOCAL_ROUTER.route_task(
                task_type="summarization", prompt=summary_prompt
            )
        except Exception as e:
            logger.warning(f"Context summarization failed: {e}")
            summary = "Historical context pruned due to length."

        final_messages = []
        # Reconstruct with summary as a single system message at the beginning
        final_messages.append(
            {"role": "system", "content": f"CONTEXT SUMMARY:\n{summary}"}
        )

        # Add the 'kept' messages in their original order to maintain flow
        for i, m in enumerate(messages):
            if i in keep_indices:
                final_messages.append(m)

        return final_messages


class SemanticContextRanker:
    """
    Ranks message relevance based on current task context and keywords.
    """

    def rank_messages(
        self, messages: list[dict[str, str]], query: str
    ) -> list[dict[str, Any]]:
        """Rank messages by relevance to the query."""
        ranked = []
        keywords = set(query.lower().split())

        for idx, msg in enumerate(messages):
            content = msg.get("content", "").lower()
            score = 0.0

            # Keyword matches
            if any(kw in content for kw in keywords):
                score += 1.0

            # Recency bias (0.0 to 0.5)
            if messages:
                score += (idx / len(messages)) * 0.5

            ranked.append({"index": idx, "message": msg, "score": score})

        # Sort by score descending
        return sorted(ranked, key=lambda x: x["score"], reverse=True)


def get_guided_router() -> VaultGuidedRouter:
    return VaultGuidedRouter()
