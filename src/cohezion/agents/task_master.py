"""
TaskMasterAgent - Autonomous project tracking and journey persistence.
"""

import logging

from cohezion.agents.base import AgentResponse, BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class TaskMasterAgent(BaseAgent):
    """
    Agent that monitors the project's task and plan state and ensures it is
    persisted into the platform's knowledge graph.
    """

    SYSTEM_PROMPT = """You are the Cohezion Task Master.
Your goal is to ensure that the development journey is accurately recorded:
- Monitor task.md and implementation_plan.md.
- Trigger synchronization to MISSION_JOURNAL.md and SurrealDB.
- Provide high-level summaries of the project's trajectory.
- Ensure that 'Phase 0' (The Awareness of Nothing at All) is bridged correctly with other phases.
"""

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="qwen3-coder:32b",
            config=config or SwarmConfig(),
        )
        self.knowledge_repo = None  # Will be injected or initialized

    async def process(self, task: str = "sync_journey", **kwargs) -> AgentResponse:
        """
        Main entry point for the agent.
        """
        if task == "sync_journey":
            task_file = kwargs.get("task_file")
            plan_file = kwargs.get("plan_file")
            if not task_file or not plan_file:
                return AgentResponse("Error: Missing task_file or plan_file path.")

            # This would call the KnowledgeService.sync_journey
            # For now, we simulate the logic or call if available
            return AgentResponse(f"Task Master initializing sync for {task_file}")

        return AgentResponse(f"Task Master received unknown task: {task}")
