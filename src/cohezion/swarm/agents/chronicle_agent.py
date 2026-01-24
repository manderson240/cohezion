"""
ChronicleAgent - Repository-wide Knowledge Synthesis and Memory.

Maintains KEY_LEARNINGS.md by synthesizing Mission and Session outcomes.
Uses 12D state vectors for structured trajectory tracking.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)

LEARNING_TEMPLATE = """
### 🪐 Learning {id}: {title}
- **Mission**: {mission_name}
- **Date**: {date}
- **12D Vector**: `{vector}`
- **Synthesis**:
{synthesis}
"""

class ChronicleAgent(BaseAgent):
    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="gemma3:4b",
            config=config or SwarmConfig(),
        )
        self.learnings_file = Path("src/cohezion/knowledge_graph/KEY_LEARNINGS.md")

    async def process(self, mission_id: str) -> str:
        """
        Synthesize all learnings from a specific mission.
        """
        logger.info(f"📚 ChronicleAgent synthesizing mission {mission_id}...")

        # 1. Gather mission context
        try:
            await self._db.connect()
            mission = await self._db.query("SELECT * FROM missions WHERE id = $id", {"id": mission_id})
            thoughts = await self._db.query(
                "SELECT * FROM agent_thought WHERE metadata.mission = $id ORDER BY timestamp ASC",
                {"id": mission_id}
            )
            await self._db.close()

            if not mission or not mission[0]:
                return f"Mission {mission_id} not found."

            # Mission results are nested in SurrealDB responses
            m_res = mission[0]
            if isinstance(m_res, list) and len(m_res) > 0:
                mission_data = m_res[0]
            else:
                mission_data = m_res

            mission_name = mission_data.get('name', 'Unknown Mission')

            # Thoughts results are also nested
            thoughts_list = thoughts[0] if thoughts and isinstance(thoughts[0], list) else []
            context = "\n".join([t.get('content', '') for t in thoughts_list[:10]]) # limit context

        except Exception as e:
            logger.error(f"Failed to gather mission context: {e}")
            return f"Error: {e}"

        # 2. Distill Learning
        prompt = f"""You are the Project Historian. Synthesize the key technical learning from this mission.

MISSION: {mission_name}
SUMMARY OF THOUGHTS:
{context}

Provide:
1. A concise TITLE.
2. A 2-sentence SYNTHESIS.
3. A 12D STATE VECTOR (format: [x, y, z, t, b1, b2, b3, b4, b5, b6, b7, b8]) representing complexity and stability.
"""
        try:
            response = await self._call_ollama(prompt, temperature=0.3)
            # Parse responses (naive)
            lines = response.splitlines()
            title = lines[0].replace("TITLE:", "").strip()
            synthesis = "\n".join(lines[1:3]).replace("SYNTHESIS:", "").strip()
            vector = "[0.5, 0.5, 0.5, 1.0, 0, 0, 0, 0, 0, 0, 0, 0]" # Default
            for line in lines:
                if "[" in line and "]" in line:
                    vector = line.strip()

            # 3. Update KEY_LEARNINGS.md
            learning_entry = LEARNING_TEMPLATE.format(
                id=int(datetime.now().timestamp()),
                title=title,
                mission_name=mission_name,
                date=datetime.now().strftime("%Y-%m-%d"),
                vector=vector,
                synthesis=synthesis
            )

            with open(self.learnings_file, "a") as f:
                f.write(learning_entry)

            logger.info(f"✨ Chronicle updated learning for mission {mission_id}")
            return f"Synchronized mission {mission_id} to KEY_LEARNINGS.md"

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return f"Failed to synthesize learning: {e}"
