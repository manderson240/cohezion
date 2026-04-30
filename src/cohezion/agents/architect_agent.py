"""
ArchitectAgent - Compositional Asset Generation (Gateway 17).

Decomposes complex, multi-component user requests into a structured
TaskGraph for parallelized swarm execution.
"""

import json
import logging
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig


logger = logging.getLogger(__name__)


class ArchitectAgent(BaseAgent):
    def __init__(self, config: SwarmConfig | None = None):
        config = config or SwarmConfig()
        super().__init__(
            model_name=config.architect_model,
            config=config,
        )

    async def decompose(self, request: str) -> list[dict[str, Any]]:
        """
        Decompose a high-level request into a list of atomic tasks.
        """
        logger.info(f"🏗️ ArchitectAgent decomposing request: {request[:50]}...")

        prompt = f"""You are the Master Architect of the Cohezion swarm.
Decompose the following user request into a set of parallelizable and sequential tasks.

REQUEST:
{request}

For each task, provide:
1. id: unique string ID
2. title: short name for the task
3. description: what needs to be done
4. suggested_agent: which specialized agent should handle this
   (e.g. AnalystAgent, HealerAgent, VisionAgent)
5. depends_on: list of task IDs that must be completed first

OUTPUT FORMAT (JSON list of objects):
[
  {{
    "id": "task_1",
    "title": "...",
    "description": "...",
    "suggested_agent": "...",
    "depends_on": []
  }}
]
"""
        response = await self._call_ollama(
            prompt=prompt,
            temperature=0.2,
            max_tokens=2048,
        )

        try:
            # Attempt to extract JSON from response
            # Sometimes models wrap it in code blocks
            text = str(response)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "[" in text:
                text = text[text.find("[") : text.rfind("]") + 1]

            tasks = json.loads(text)
            if isinstance(tasks, list):
                return tasks
            return []
        except Exception as e:
            logger.error(f"Failed to parse architect tasks: {e}")
            return []

    async def process(self, request: str, **kwargs: Any) -> str:
        """
        Generate a comprehensive architecture plan.
        """
        tasks = await self.decompose(request)
        if not tasks:
            return "Failed to generate an architecture plan."

        report = ["## Swarm Architecture Plan"]
        report.append(f"Project: {request[:100]}...\n")

        for task in tasks:
            report.append(f"### Task: {task.get('title', 'Untitled')}")
            report.append(f"- **ID**: {task.get('id')}")
            report.append(f"- **Agent**: {task.get('suggested_agent')}")
            report.append(f"- **Dependencies**: {', '.join(task.get('depends_on', [])) or 'None'}")
            report.append(f"- **Description**: {task.get('description')}\n")

        return "\n".join(report)
