import asyncio
import logging
import random

from cohezion.agents.base import BaseAgent
from cohezion.core.time_keeper import get_time_keeper

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [DREAMER] - %(message)s")
logger = logging.getLogger("DreamerAgent")


class DreamerAgent(BaseAgent):
    """
    The Dreamer: A background agent that wakes up during low-load periods to
    consolidate memories by finding hidden connections between disparate topics.
    """

    def __init__(self):
        super().__init__(model_name="phi3:mini")
        self.min_grade = 0.9

    async def run_loop(self):
        logger.info("🌙 Dreamer Agent Sleeping... Waiting for the night.")

        while True:
            # In a real system, we'd check system load.
            # Here we just sleep for a bit and then dream.
            await asyncio.sleep(60)

            try:
                await self.dream()
            except Exception as e:
                logger.error(f"Nightmare encountered: {e}")

    async def dream(self):
        """
        The Core Dreaming Loop:
        1. Recall two high-quality memories.
        2. Synthesize a connection.
        3. Crystallize the insight.
        """
        logger.info("✨ Entering REM Cycle...")

        # 1. Recall Memories (Fetch High Grade Research)
        # Random sort using UUID is hard in SQL, so we fetch a chunk and sample in python
        query = f"SELECT * FROM universe_nodes WHERE node_type = 'research_paper' AND metadata.grade >= {self.min_grade} LIMIT 50"
        response = await self._db.query(query)

        candidates = []
        if isinstance(response, list) and response and isinstance(response[0], dict):
            candidates = response[0].get("result", [])

        if len(candidates) < 2:
            logger.info("💤 Not enough high-quality memories to dream yet.")
            return

        # Pick two distinct memories
        memory_a, memory_b = random.sample(candidates, 2)

        topic_a = memory_a["metadata"].get("topic", "Unknown")
        topic_b = memory_b["metadata"].get("topic", "Unknown")

        logger.info(f"🧠 Connecting: '{topic_a}' <--> '{topic_b}'")

        # 2. Synthesize (Lateral Thinking)
        prompt = (
            f"TASK: You are a lateral thinking engine. Find a hidden, metaphorical, or structural connection between these two concepts.\n"
            f"CONCEPT A: {topic_a}\n"
            f"CONCEPT B: {topic_b}\n\n"
            f"OUTPUT: A single short paragraph explaining the deep connection or shared principle."
        )

        insight_text = await self._call_ollama(
            prompt, model="phi3:mini", temperature=0.8
        )

        # 3. Crystallize (Store Insight)
        insight_id = (
            f"insight_{memory_a['id'].split(':')[-1]}_{memory_b['id'].split(':')[-1]}"
        )

        # Store as an 'edge' or a new node type 'insight'
        from cohezion.core.persistence.surreal_client import UniverseNode

        node = UniverseNode(
            id=insight_id,
            node_type="insight",
            content=insight_text,
            metadata={
                "source_a": memory_a["id"],
                "source_b": memory_b["id"],
                "topic_a": topic_a,
                "topic_b": topic_b,
                "dream_time": str(get_time_keeper().now()),
            },
        )

        await self._db.store_node(node)
        logger.info(f"💡 Dream Insight Crystallized: {insight_id}")
        logger.info(f"   > {insight_text[:100]}...")

    async def process(self, *args):
        pass


if __name__ == "__main__":

    async def main():
        dreamer = DreamerAgent()
        await dreamer.dream()  # One-shot for testing/cli

    asyncio.run(main())
