import asyncio
import json
import logging
from pathlib import Path

from cohezion.swarm.agents.base import BaseAgent

from cohezion.core.time_keeper import get_time_keeper


logging.basicConfig(level=logging.INFO, format="%(asctime)s - [NEXUS_JUDGE] - %(message)s")
logger = logging.getLogger("NexusJudge")

DATASET_FILE = Path("data/training/finetune_dataset.jsonl")
DATASET_FILE.parent.mkdir(parents=True, exist_ok=True)


class NexusJudge(BaseAgent):
    def __init__(self):
        # Use a "Smarter" model for grading if possible
        # Mistral is often better at reasoning/following format than Phi3-mini
        super().__init__(model_name="mistral")
        self.constitution = (
            Path(".agent/CONSTITUTION.md").read_text() if Path(".agent/CONSTITUTION.md").exists() else "Be Helpful."
        )

    async def run_loop(self):
        logger.info("⚖️ Nexus Judge Started. Court is in session.")
        while True:
            try:
                await self.process_docket()
                logger.info("💤 Dockets cleared. Recessing...")
                await asyncio.sleep(30)  # Check every 30s
            except Exception as e:
                logger.error(f"Judge Error: {e}")
                await asyncio.sleep(30)

    async def process_docket(self):
        # Fetch unverified research
        # Fetch unverified research (Filter in DB to avoid scanning same 10 items)
        # We use 'feedback' as the flag for "Graded/Judged"
        # Support both Missing Field (NONE) and Explicit Null (NULL) -> SurrealDB quirks
        query = "SELECT * FROM universe_nodes WHERE node_type = 'research_paper' AND (metadata.feedback IS NONE OR metadata.feedback = NULL) LIMIT 10"
        response = await self._db.query(query)

        print(f"DEBUG: Response Type: {type(response)}")
        print(f"DEBUG: Response Length: {len(response) if isinstance(response, list) else 'N/A'}")

        candidates = []
        # Handle SurrealClient unwrapping (it returns list of records directly sometimes)
        if isinstance(response, list):
            # Check if it's the raw RPC format [{'result': [...]}] or unwrapped records [{'id': ...}, {'id': ...}]
            if response and isinstance(response[0], dict) and "result" in response[0]:
                print("DEBUG: Detected RPC format")
                items = response[0].get("result", [])
            else:
                print("DEBUG: Detected Raw Records format")
                items = response  # It's the records themselves

            print(f"DEBUG: Items count: {len(items)}")
            for item in items:
                candidates.append(item)

        if not candidates:
            print("DEBUG: No candidates.")
            return

        logger.info(f"📜 Found {len(candidates)} papers to review.")

        for paper in candidates:
            await self.judge_paper(paper)

    async def judge_paper(self, paper: dict):
        paper_id = paper["id"]
        content = paper["content"]
        topic = paper.get("metadata", {}).get("topic", "Unknown Topic")

        logger.info(f"  > Reviewing: {topic} ({paper_id})")

        # Prompt for Evaluation (Constitutional)
        prompt = (
            f"TASK: Acting as a Senior Scientific Editor and Ethics Guardian, evaluate the following research abstract.\n"
            f"TOPIC: {topic}\n"
            f"CONSTITUTIONAL ALIGNMENT:\n"
            f"Use the following principles to judge alignment: {self.constitution[:500]}...\n\n"
            f"CRITERIA:\n"
            f"1. Coherence (Is it logical?)\n"
            f"2. Novelty (Is it insightful?)\n"
            f"3. Depth (Does it explain 'Why'?)\n"
            f"4. ALIGNMENT (Does it adhere to the Constitution and help build the Universe Simulation?)\n\n"
            f"CONTENT:\n{content[:4000]}\n\n"
            f"OUTPUT: Return ONLY a JSON object with keys: 'grade' (0.0 to 1.0) and 'feedback' (string)."
        )

        try:
            response_str = await self._call_ollama(prompt, model="mistral", temperature=0.2)

            # Simple wrapper to extract JSON if model adds text
            start = response_str.find("{")
            end = response_str.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = response_str[start:end]
                result = json.loads(json_str)
            else:
                logger.warning(f"    - Failed to parse JSON from Judge. Payload: {response_str[:100]}...")
                return

            grade = float(result.get("grade", 0.0))
            feedback = result.get("feedback", "")

            logger.info(f"    - Grade: {grade} | Feedback: {feedback[:50]}...")

            # Update DB
            paper["metadata"]["grade"] = grade
            paper["metadata"]["feedback"] = feedback
            paper["metadata"]["graded_at"] = str(get_time_keeper().now())

            is_verified = grade >= 0.8
            is_curated = grade >= 0.9
            is_canon = grade >= 0.95  # S-Tier

            paper["metadata"]["verified"] = is_verified
            paper["metadata"]["canonized"] = is_canon

            # Save update to DB
            update_query = f"UPDATE {paper_id} MERGE $data"
            await self._db.query(update_query, {"data": {"metadata": paper["metadata"]}})

            # Curation (Gold Standard)
            if is_curated:
                await self.curate_for_training(topic, content)
                logger.info("    ⭐ CURATED for Fine-Tuning!")

            # Canonization (Textbook)
            if is_canon:
                await self.canonize_knowledge(topic, content, grade)

                # Reward Agent (Compound Engineering: Economic Yield)
                # We assume the creator is 'NexusDaemon' for now
                self._credit_manager.credit("NexusDaemon", 50)
                logger.info(f"    🏆 CANONIZED! (Grade {grade}) | +50 Credits awarded to NexusDaemon")
            elif is_verified:
                # Small reward for passing
                self._credit_manager.credit("NexusDaemon", 10)
                logger.info("    ✅ Verified. +10 Credits awarded.")

        except Exception as e:
            logger.error(f"    - Judgment failed: {e}")

    async def curate_for_training(self, topic: str, content: str):
        """Append to JSONL dataset."""
        entry = {
            "messages": [
                {"role": "user", "content": f"RESEARCH MISSION: {topic}"},
                {"role": "assistant", "content": content},
            ]
        }
        with open(DATASET_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

    async def canonize_knowledge(self, topic: str, content: str, grade: float):
        """Append to KEY_LEARNINGS.md (The Textbook)."""
        textbook_path = Path("src/cohezion/knowledge_graph/KEY_LEARNINGS.md")

        # Format entry
        entry = f"\n\n## {topic} (Grade: {grade})\n*Canonized at {get_time_keeper().now()}*\n\n{content}\n\n---\n"

        # Append
        with open(textbook_path, "a") as f:
            f.write(entry)

    async def process(self, *args):
        pass


if __name__ == "__main__":

    async def run_judge():
        try:
            judge = NexusJudge()
            await judge.run_loop()
        except KeyboardInterrupt:
            logger.info("Judge Adjourned.")

    asyncio.run(run_judge())
