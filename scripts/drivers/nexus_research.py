import asyncio
import json
import logging
import time
from pathlib import Path

import psutil

from cohezion.core.time_keeper import get_time_keeper
from cohezion.swarm.agents.base import BaseAgent


logging.basicConfig(level=logging.INFO, format="%(asctime)s - [NEXUS_DAEMON] - %(message)s")
logger = logging.getLogger("NexusResearchDaemon")

QUEUE_FILE = Path("data/research_queue.json")
DONE_FILE = Path("data/research_done.json")

# Default Batch 3 if Queue is empty
DEFAULT_QUEUE = [
    {
        "row": 31,
        "topic": "Time Crystals in 12D Manifolds",
        "prompt": "Analyze Time Crystals using FLUME 12D vectors. How is 'Time' a crystal?",
    },
    {
        "row": 32,
        "topic": "Zero Point Energy (Simulated)",
        "prompt": "Logic for extracting ZPE/EVOs from the Void (Vacuum State). Connect to Casimir.",
    },
    {
        "row": 33,
        "topic": "Societal Collapse (The Great Filter)",
        "prompt": "Mathematical threshold for 'Complexity vs Coherence' collapse in agent swarms.",
    },
]


class NexusResearchDaemon(BaseAgent):
    def __init__(self):
        super().__init__(model_name="phi3:mini")
        self.queue: list[dict] = []
        self.done: list[str] = []
        self.load_state()

    def load_state(self):
        """Load Queue and Done history."""
        if QUEUE_FILE.exists():
            try:
                self.queue = json.loads(QUEUE_FILE.read_text())
            except Exception:
                self.queue = []

        if not self.queue:
            self.queue = DEFAULT_QUEUE

        if DONE_FILE.exists():
            try:
                self.done = json.loads(DONE_FILE.read_text())
            except Exception:
                self.done = []

    def save_state(self):
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        QUEUE_FILE.write_text(json.dumps(self.queue, indent=2))
        DONE_FILE.write_text(json.dumps(self.done, indent=2))

    async def wait_for_resources(self):
        """
        Pause if System is Stressed (VRAM/RAM > 90%).
        This prevents the 'Emergency Shutdown' loops.
        """
        while True:
            mem = psutil.virtual_memory()
            # Simple heuristic: If RAM > 92%, Sleep
            if mem.percent > 92.0:
                logger.warning(f"🛑 Resource Pressure (RAM {mem.percent}%). Nexus Sleeping...")
                await asyncio.sleep(60)  # Deep sleep
            else:
                return  # Go

    async def run_loop(self):
        logger.info("🧬 Nexus Research Daemon Started. Standing by.")

        # Visual Cortex is now standalone (Phase 53)

        while True:
            await self.wait_for_resources()

            # 0. Emergency Missions (highest priority)
            if await self.check_emergency_missions():
                continue

            # 1. Priority: Retry Rejected Papers (Recursion)
            if await self.retry_rejected_papers():
                continue

            # 2. Normal Queue
            self.load_state()
            next_task = None
            for item in self.queue:
                if item["topic"] not in self.done:
                    next_task = item
                    break

            if next_task:
                await self.process(next_task)
            else:
                logger.info("💤 No new tasks. Sleeping...")
                await asyncio.sleep(60)

    async def check_emergency_missions(self) -> bool:
        """Check for high-priority missions triggered by the Universe Sim."""
        try:
            query = "SELECT * FROM universe_nodes WHERE node_type = 'mission' AND metadata.status = 'PENDING' LIMIT 1"
            response = await self._db.query(query)

            candidates = []
            if isinstance(response, list) and response and isinstance(response[0], dict):
                candidates = response[0].get("result", [])

            if not candidates:
                return False

            mission = candidates[0]
            topic = mission["metadata"].get("topic")
            logger.info(f"🚨 EMERGENCY MISSION DETECTED: {topic}")

            # Convert to task format
            task = {
                "topic": topic,
                "prompt": f"EMERGENCY STABILIZATION REQUEST.\nSOURCE: Universe Simulation\nISSUE: {mission['metadata'].get('reason')}\n\nPROVIDE STABILIZATION PROTOCOLS.",
                "row": 0,
                "mission_id": mission["id"],  # Track origin
            }

            await self.process(task)

            # Update Mission Status
            await self._db.query(f"UPDATE {mission['id']} SET metadata.status = 'COMPLETED'")
            return True

        except Exception as e:
            logger.error(f"Mission check failed: {e}")
            return False

    async def retry_rejected_papers(self) -> bool:
        """
        Check DB for papers that failed the Judge's review.
        Retry them with feedback.
        """
        try:
            # Fetch recently rejected (Grade < 0.7, Not Verified, Has Feedback)
            # Limit 1 to avoid flooding
            # Using raw query to find candidates
            # Fix: Use 'IS NOT NONE' or just '!= NONE' instead of 'field::none' depending on version
            # Safest generic check: metadata.feedback != NONE
            query = "SELECT * FROM universe_nodes WHERE node_type = 'research_paper' AND metadata.verified = false AND metadata.grade < 0.7 AND metadata.feedback != NONE LIMIT 1"
            response = await self._db.query(query)

            candidates = []
            if isinstance(response, list) and response and isinstance(response[0], dict):
                candidates = response[0].get("result", [])

            if not candidates:
                return False

            paper = candidates[0]
            meta = paper.get("metadata", {})
            topic = meta.get("topic")
            feedback = meta.get("feedback")
            row = meta.get("row")

            # Check retry count to avoid infinite loops
            retries = meta.get("retry_count", 0)
            if retries >= 3:
                logger.warning(f"⚠️ Giving up on {topic} after 3 retries.")
                # Mark as 'failed_permanently' to stop fetching
                # We can't update easily without ID, assuming paper['id'] works
                await self._db.query(f"UPDATE {paper['id']} SET metadata.failed_permanently = true")
                return False

            logger.info(f"♻️ Retrying Rejected Paper: {topic} (Attempt {retries + 1})")

            # Construct Retry Task
            retry_task = {
                "topic": topic,
                "prompt": f"PREVIOUS ATTEMPT REJECTED.\nJUDGE FEEDBACK: {feedback}\n\nIMPROVE AND REWRITE.",
                "row": row,
                "retry_id": paper["id"],  # Track origin
                "retry_count": retries + 1,
            }

            await self.process(retry_task)
            return True

        except Exception as e:
            logger.error(f"Retry check failed: {e}")
            return False

    async def process(self, task: dict) -> str:
        """
        Main worker method (Satisfies BaseAgent abstract method).
        """
        topic = task["topic"]
        prompt = task["prompt"]

        logger.info(f"🔬 Starting Research: {topic}")

        try:
            # 1. Oracle Context
            oracle_context = ""
            try:
                from cohezion.cosmic.oracle import JourneyOracle

                if not hasattr(self, "oracle"):
                    self.oracle = JourneyOracle()

                # Ask Oracle for 'Semantic Seeds'
                insights = await self.oracle.consult(topic)
                if insights:
                    texts = [i.get("content", "")[:150] for i in insights]
                    oracle_context = "\nPREVIOUS SWARM WISDOM:\n- " + "\n- ".join(texts)
            except Exception as e:
                logger.warning(f"Oracle offline: {e}")

            # 2. Research (Tokens Aware: Keep it focused)
            full_prompt = (
                f"RESEARCH MISSION: {topic}\n"
                f"CONTEXT: 12D Universe Simulation.{oracle_context}\n"
                f"QUERY: {prompt}\n"
                f"OUTPUT: Concise Markdown definition and logic."
            )

            response = await self._call_ollama(prompt=full_prompt, model="phi3:mini", temperature=0.7)

            # 3. Crystallize & Compress
            filename = f"LEARNING_{task.get('row', 0)}_{int(time.time())}.md"
            path = Path(f"/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/{filename}")

            content = f"# {topic}\n\n{response}\n"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

            # 4. DB Persistence (Active Memory)
            # Store as a node so Oracle can find it
            from cohezion.core.persistence.surreal_client import UniverseNode

            old_id = task.get("retry_id")
            retry_count = task.get("retry_count", 0)

            # If retrying, we might want to update the OLD node or create a NEW version.
            # Creating a NEW version (v2) preserves history for the Judge to see improvement.
            new_id = f"research_{int(time.time())}"

            meta = {"topic": topic, "row": task.get("row"), "retry_count": retry_count}
            if old_id:
                meta["previous_version"] = old_id

            node = UniverseNode(id=new_id, content=content, node_type="research_paper", metadata=meta)
            # Use BaseAgent's db client
            await self._db.store_node(node)

            # If this was a retry, mark the OLD node as obsolete/retried so we don't pick it up again?
            # Actually, `retry_rejected_papers` looks for `verified=false`.
            # The OLD node remains false. The NEW node is a fresh candidate.
            # We should probably update the OLD node to point to the NEW one to stop retrying the OLD one.
            if old_id:
                await self._db.query(
                    f"UPDATE {old_id} SET metadata.verified = true, metadata.superseded_by = '{new_id}'"
                )

            # 5. Log Event
            tk = get_time_keeper()
            await tk.log_event(
                "NexusDaemon",
                "RESEARCH_COMPLETE",
                {"topic": topic, "file": str(path), "node_id": node.id},
            )

            # Mark Done
            self.done.append(topic)
            self.save_state()

            # 6. Visualization Export (Compound Engineering)
            # Push latest state to WebApp for HUD
            await self.export_lattice()

            logger.info(f"✅ Finished & Indexed: {topic} ({node.id})")

            # Cool down
            await asyncio.sleep(5)
            return f"Completed: {topic}"

        except Exception as e:
            logger.error(f"Task Failed {topic}: {e}")
            await asyncio.sleep(10)
            return f"Failed: {topic}"

    async def export_lattice(self):
        """
        Export recent research nodes to a lightweight JSON for the HUD.
        Token Optimized: Only ID, Topic, Grade, and Coords (Visuals).
        """
        try:
            # Fetch all research papers (No Order By to avoid DB hang)
            query = "SELECT id, created_at, metadata.topic, metadata.grade, metadata.verified FROM universe_nodes WHERE node_type = 'research_paper' LIMIT 100"
            response = await self._db.query(query)

            nodes = []
            # Handle SurrealClient unwrapping (it returns list of records directly sometimes)
            if isinstance(response, list):
                # Check if it's the raw RPC format [{'result': [...]}] or unwrapped records [{'id': ...}, {'id': ...}]
                if response and isinstance(response[0], dict) and "result" in response[0]:
                    items = response[0].get("result", [])
                else:
                    items = response  # It's the records themselves

                # Sort in Python (Token Optimized - Offload DB)
                # Assuming created_at is string ISO
                items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                items = items[:50]

                for i, item in enumerate(items):
                    # Mock coordinates for 3D visualization
                    import math

                    idx = i
                    phi = math.acos(-1 + (2 * idx) / 50)
                    theta = math.sqrt(50 * math.pi) * phi

                    x = 2.5 * math.cos(theta) * math.sin(phi)
                    y = 2.5 * math.sin(theta) * math.sin(phi)
                    z = 2.5 * math.cos(phi)

                    nodes.append(
                        {
                            "id": str(item["id"]),
                            "topic": item["metadata"].get("topic", "Unknown"),
                            "grade": item["metadata"].get("grade", 0.0),
                            "verified": item["metadata"].get("verified", False),
                            "position": [x, y, z],
                        }
                    )

            # Write key file
            Path("apps/webapp/public/data/lattice.json").write_text(json.dumps({"nodes": nodes}))
            logger.info(f"🕸️ Lattice Exported ({len(nodes)} nodes)")
        except Exception as e:
            logger.warning(f"Lattice export failed: {e}")


if __name__ == "__main__":

    async def run_daemon():
        try:
            # Initialize INSIDE the loop so BaseAgent can find it
            daemon = NexusResearchDaemon()
            await daemon.run_loop()
        except KeyboardInterrupt:
            logger.info("Nexus Daemon Stopping.")

    asyncio.run(run_daemon())
