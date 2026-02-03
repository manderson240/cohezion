"""
SurrealDB DBA Specialist Agent.
Guardian of the Cohezion persistence substrate.
Specializes in SurrealQL dialect correctness, schema evolution, and performance tuning.
"""

import logging
from typing import Any

from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.agents.base import AgentResponse, BaseAgent

logger = logging.getLogger(__name__)


class SurrealDBDBA(BaseAgent):
    """
    Expert agent for SurrealDB management.
    Handles dialect translation, schema migrations, and index optimization.
    """

    def __init__(self, config: Any = None):
        super().__init__(
            model_name="qwen3-coder:30b",  # Coding model for complex SQL/Dialect logic
            config=config,
        )
        self.db = SurrealClient()

    async def fix_dialect_mismatch(self, query: str, error_message: str) -> str:
        """
        Analyze a failed query and provide a SurrealQL-correct version.
        """
        prompt = f"""You are the SurrealDB DBA Specialist.
A query failed with a dialect error in SurrealDB 2.x.
FAILED QUERY: {query}
ERROR: {error_message}

Goal: Fix the query to be valid SurrealQL 2.x.
Common issues:
- Using colons in IDs without quoting: `table:id` vs `table:['id']`
- Negative hashes/numbers causing parse errors.
- Relationship syntax: `RELATE from->rel->to`.

Output ONLY the corrected SurrealQL string.
"""
        response = await self._call_ollama(prompt)
        return response.strip()

    async def propose_schema_evolution(self, data_samples: list[dict]) -> str:
        """
        Look at incoming data and propose new indices or schema modifications.
        """
        prompt = f"""Analyze these data samples from the swarm and propose a SurrealDB schema improvement (indices, relations, or fields).
SAMPLES: {str(data_samples)[:2000]}
Output a VALID SurrealQL migration script.
"""
        response = await self._call_ollama(prompt)
        return response

    async def monitor_health(self) -> dict[str, Any]:
        """
        Check database vitals, growth rates, and index density.
        """
        # Placeholder for real monitoring queries
        try:
            # Simple count query
            res = await self.db.query("SELECT count() FROM universe_nodes GROUP ALL")
            return {"node_count": res, "status": "healthy"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def process(self, context: str, **kwargs: Any) -> AgentResponse:
        """
        Process DBA requests: fix queries, optimize schema, or monitor health.
        """
        if "fix query" in context.lower():
            query = kwargs.get("query", "")
            error = kwargs.get("error", "")
            fixed = await self.fix_dialect_mismatch(query, error)
            return AgentResponse(fixed, action="query_fix")

        elif "optimize" in context.lower():
            # In a real scenario, we'd fetch samples from history
            proposal = await self.propose_schema_evolution([])
            return AgentResponse(proposal, action="schema_optimization")

        return AgentResponse("DBA Monitoring Active", status="active")
