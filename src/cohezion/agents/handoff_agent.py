"""
HandoffAgent - Session Synthesis and Persistence (Gateway 4/14).

Synthesizes the current session into a SESSION_SNAPSHOT in SurrealDB,
preserving key context for the next agentic session.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from cohezion.core.persistence.surreal_client import PhysicsState, UniverseNode
from cohezion.agents.base import AgentResponse, BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class HandoffAgent(BaseAgent):
    """
    Agent specialized in synthesizing session history into compact snapshots.
    """

    SYSTEM_PROMPT = """You are the Handoff Specialist.
Your goal is to summarize a complex agentic session into a "Memory Anchor".
Focus on:
1. Key Discoveries (Breakthroughs).
2. Unresolved Blockers.
3. 12D Trajectory Summary (Stability trends).
4. Concrete Next Steps.

Keep the summary concise (max 500 tokens) but high-fidelity.
"""

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="deepseek-r1:70b",  # Using high-reasoning for synthesis
            config=config or SwarmConfig(),
        )

    async def create_snapshot(self, session_data: dict[str, Any]) -> str:
        """
        Processes session data and persists it as a SESSION_SNAPSHOT.
        """
        logger.info("📡 HandoffAgent generating session snapshot...")

        prompt = f"""GENERATE SESSION SNAPSHOT:
Session Created At: {session_data.get('created_at')}
Expert Responses: {json.dumps(list(session_data.get('expert_responses', {}).keys()))}
Current Synthesis: {session_data.get('synthesis', '')[:1000]}
Confidence: {session_data.get('confidence', 0.0)}

Please synthesize the above into a standard Memory Anchor.
"""

        snapshot_content = await self._call_ollama(
            prompt, system_prompt=self.SYSTEM_PROMPT
        )

        # Persist to SurrealDB
        try:
            timestamp = datetime.now(UTC).isoformat()
            snapshot_id = f"snapshot_{int(datetime.now(UTC).timestamp())}"

            node = UniverseNode(
                id=snapshot_id,
                content=snapshot_content,
                node_type="session_snapshot",
                physics_state=PhysicsState(
                    coherence=session_data.get("confidence", 0.0),
                    time=datetime.now(UTC).timestamp(),
                ),
                metadata={
                    "session_id": session_data.get("query_id", "unknown"),
                    "created_at": timestamp,
                    "experts_involved": list(
                        session_data.get("expert_responses", {}).keys()
                    ),
                },
            )

            await self._db.connect()
            await self._db.store_node(node)
            await self._db.close()

            logger.info(f"✅ SESSION_SNAPSHOT stored: {snapshot_id}")
            return snapshot_content

        except Exception as e:
            logger.error(f"Failed to persist session snapshot: {e}")
            return snapshot_content

    async def process(self, input_data: str) -> AgentResponse:
        """
        Default process implementation for HandoffAgent.
        Takes a JSON string of session data.
        """
        try:
            session_data = json.loads(input_data)
            snapshot = await self.create_snapshot(session_data)
            return AgentResponse(snapshot)
        except Exception as e:
            logger.error(f"Handoff parsing failure: {e}")
            return AgentResponse(f"Handoff Failed: {str(e)}")
