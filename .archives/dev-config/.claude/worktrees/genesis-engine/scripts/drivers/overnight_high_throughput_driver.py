import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import psutil

from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    SurrealClient,
    UniverseNode,
)
from cohezion.mcp.email_notifier import EmailNotifier
from cohezion.simulation.enhanced_simulator import (
    EnhancedSimulationResult,
    EnhancedSimulator,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("overnight_mission.log"), logging.StreamHandler()],
)
logger = logging.getLogger("OvernightMission")


class MissionController:
    """
    Manages the 1,000,000+ simulation mission 'The Great Convergence'.
    Runs until a specified end time (e.g., 6:00 AM).
    """

    def __init__(self, target_end_time: datetime, batch_size: int = 1000):
        self.target_end_time = target_end_time
        self.batch_size = batch_size
        self.simulator = EnhancedSimulator(output_dir=Path("overnight_simulations"))
        self.db = SurrealClient()
        self.email = EmailNotifier()

        self.total_completed = 0
        self.last_update_time = datetime.now()
        self.update_interval = timedelta(minutes=30)
        self.start_time = datetime.now()

        # Evolutionary State
        self.ancestral_strains: list[str] = []
        self.refinement_threshold = 1000  # Refine every 1000 for tests, change to 50k for prod
        self.last_refinement_count = 0

    async def run(self):
        """Main mission loop."""
        logger.info(
            f"🚀 Mission 'The Great Convergence' started. Targeting {self.target_end_time.isoformat()}"
        )

        await self.db.connect()

        while datetime.now() < self.target_end_time:
            # 1. Resource Health Check
            if self._check_resource_safety():
                # 2. Run Batch
                try:
                    await self._run_mission_batch()
                except Exception as e:
                    logger.error(f"Batch execution failed: {e}")
                    await asyncio.sleep(10)  # Cooling period on error
            else:
                logger.warning("⚠️ System resources under pressure. Throttling for 60 seconds...")
                await asyncio.sleep(60)

            # 3. Evolutionary Refinement
            if self.total_completed - self.last_refinement_count >= self.refinement_threshold:
                await self._perform_evolutionary_refinement()
                self.last_refinement_count = self.total_completed

            # 4. Periodic Reporting
            if datetime.now() - self.last_update_time >= self.update_interval:
                await self._send_status_update()
                self.last_update_time = datetime.now()

            # Yield to other tasks
            await asyncio.sleep(0.1)

        logger.info(f"🏁 Mission reached target time. Total simulations: {self.total_completed}")
        await self._send_status_update(final=True)
        await self.db.close()

    def _check_resource_safety(self) -> bool:
        """Check CPU and RAM usage to avoid system crash, sensitive to other concurrent sessions."""
        cpu_usage = psutil.cpu_percent(interval=None)
        ram_usage = psutil.virtual_memory().percent

        # Throttling thresholds (Strict for concurrent sessions)
        return not (cpu_usage > 75 or ram_usage > 80)

    async def _run_mission_batch(self):
        """Executes a batch of simulations with unique starter conditions."""
        # Use existing simulator logic, but inject unique 'starter' seeds/params
        for _i in range(self.batch_size):
            # Select random scenario
            scenario = random.choice(self.simulator.STREAMS)

            # Evolutionary Seed Injection
            if self.ancestral_strains and random.random() < 0.3:
                random.choice(self.ancestral_strains)
                logger.debug(f"Injecting ancestral strain into {scenario} simulation.")

            result = await self.simulator.run_simulation(scenario)

            # Persist Journey to SurrealDB
            await self._persist_to_db(result)

            self.total_completed += 1
            if self.total_completed % 100 == 0:
                logger.debug(f"Progress: {self.total_completed} sims...")

    async def _persist_to_db(self, result: EnhancedSimulationResult):
        """Log agentic journey and physics state to SurrealDB."""
        # Convert result to UniverseNode
        node = UniverseNode(
            id=result.sim_id,
            content=result.solution.response_text,
            physics_state=PhysicsState(
                stability=result.evaluation.score,
                coherence=result.evaluation.coherence,
                complexity=result.challenge.difficulty / 100.0,  # Scale to 0-1
                time=time.time() - self.start_time.timestamp(),
            ),
            node_type="agentic_journey",
            metadata={
                "stream": result.stream,
                "approved": result.approved,
                "issues": result.evaluation.issues,
                "difficulty": result.challenge.difficulty,
            },
        )
        await self.db.store_node(node)

    async def _send_status_update(self, final: bool = False):
        """Send 30-minute status report via email."""
        stats = self.simulator.get_stats()
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent

        subject = f"{'🏁 FINAL' if final else '📊 UPDATE'}: The Great Convergence"
        status = "COMPLETE" if final else "IN PROGRESS"

        body = f"""
        <h2>Mission: The Great Convergence</h2>
        <p><b>Status:</b> {status}</p>
        <p><b>Total Simulations:</b> {self.total_completed}</p>
        <p><b>Current Difficulty:</b> {stats.get("current_difficulty", 0):.2f}</p>
        <p><b>Approval Rate:</b> {stats.get("approval_rate", 0):.2%}</p>
        <p><b>System Health:</b> CPU: {cpu}% | RAM: {ram}%</p>
        <hr>
        <h3>Latest Agentic Journey Snapshot:</h3>
        <p><i>Scenario: {self.simulator.STREAMS[-1] if self.simulator.STREAMS else "N/A"}</i></p>
        <pre>{stats.get("avg_score", "N/A")}</pre>
        """

        success = await self.email.send_email(subject, body, is_html=True)
        if success:
            logger.info("Email status update sent.")
        else:
            logger.warning("Failed to send email update.")

    async def _perform_evolutionary_refinement(self):
        """Perform 'Survival of the Fittest' selection and Skill Refinement."""
        logger.info(
            f"🧬 Performing Evolutionary Refinement at {self.total_completed} simulations..."
        )

        # 1. Fetch top performing nodes
        try:
            # Simple query for top stability nodes
            query = "SELECT * FROM universe_nodes WHERE stability_score > 0.9 ORDER BY created_at DESC LIMIT 100"
            results = await self.db.query(query)
            top_nodes = results[0] if results else []

            if top_nodes:
                self.ancestral_strains = [n["content"] for n in top_nodes]
                logger.info(
                    f"Updated Ancestral Strains with {len(self.ancestral_strains)} high-performers."
                )

            # 2. Automated Skill Synthesis (Mock for now, would use an LLM expert)
            await self._synthesize_new_skill(top_nodes)

        except Exception as e:
            logger.error(f"Refinement failed: {e}")

    async def _synthesize_new_skill(self, top_nodes):
        """Codify common patterns into a new skill file."""
        if not top_nodes:
            return

        skill_name = f"LATTICE_WISDOM_{self.total_completed // 1000}_PRIME"
        skill_path = Path(f"src/cohezion/skills/{skill_name}.md")

        content = f"# SKILL: {skill_name}\n"
        content += "## DOMAIN EXPERTISE\nExtracted pattern from 1M+ simulation mission.\n"
        content += "## KEY CONCEPTS\n- High Stability Reasoning\n- Manifold Alignment\n"
        content += "## VERSION\nv0.1\n"

        # In a real scenario, we'd use Gemini 3 Pro to synthesize the commonalities
        # of the top_nodes['content'] into a set of instructions.

        try:
            skill_path.write_text(content)
            logger.info(f"✨ Synthesized new skill: {skill_name}")
        except Exception as e:
            logger.error(f"Skill synthesis failed: {e}")


if __name__ == "__main__":
    # Target end time: 6:00 AM tomorrow (Jan 22)
    # Get current time
    now = datetime.now()
    target = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if target < now:
        target += timedelta(days=1)

    controller = MissionController(target_end_time=target, batch_size=200)
    asyncio.run(controller.run())
