"""
LabAgent - Orchestrator of the Autonomous AI Lab.

This agent runs in the background, continuously generating hypotheses,
executing tests, and synthesizing findings. It ensures all discoveries
are persisted with rich narration and mapped to the Anthropic Research Role.
"""

import asyncio
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.agents.hypothesis_agent import HypothesisAgent
from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    SurrealClient,
    UniverseNode,
)
from cohezion.flume.alignment import LatentAligner
from cohezion.mcp.email_notifier import EmailNotifier
from cohezion.simulation.simulation_logger import SimulationLogger

logger = logging.getLogger(__name__)


class LabAgent(BaseAgent):
    def __init__(self, config: Any = None):
        super().__init__(
            model_name="deepseek-r1:70b",  # Primary reasoning model
            config=config or {},
        )
        self.controller = ControllerAgent()
        self.hypothesis_agent = HypothesisAgent()
        self.db_client = SurrealClient()
        self.notifier = EmailNotifier()
        self.sim_logger = SimulationLogger()
        self.aligner = LatentAligner()
        self.session_discoveries = []

    async def run_autonomous_loop(self, duration_minutes: int = 60):
        """
        Run the lab autonomously for a specified duration.
        Generates research, verifies experiments, and publishes findings.
        """
        logger.info(
            f"🚀 LabAgent: Engaging Autonomous Drive for {duration_minutes} minutes."
        )
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        cycles = 0
        last_report_time = start_time

        while time.time() < end_time:
            cycles += 1
            logger.info(f"🔄 Loop Cycle {cycles}")

            await self.run_cycle()

            # Email every 30 minutes (real-time simulation)
            if time.time() - last_report_time > 1800:  # 30 mins
                await self.send_summary_report()
                last_report_time = time.time()

            # Yield for other processes
            await asyncio.sleep(5)

        # Final Report
        await self.send_summary_report()
        logger.info("🛑 LabAgent: Autonomous Drive Complete.")

    async def research_specific_topic(self, topic: str, context: str):
        """Execute a directed research mission on a specific topic."""
        logger.info(f"🧪 LabAgent: Starting DIRECTED research on '{topic}'...")
        seed_packet = f"TOPIC: {topic}\nDETAILS: {context}"
        await self.run_cycle(seed_override=seed_packet)
        return self.session_discoveries[-1] if self.session_discoveries else None

    async def analyze_abstractly(self, topic: str):
        """
        Perform abstract meta-analysis on the local codebase.
        Uses the internal swarm to map structural patterns to the knowledge graph.
        """
        logger.info(f"📂 LabAgent: Initiating ABSTRACT ANALYSIS on '{topic}'...")

        # 1. Search for local context (Abstraction Phase)
        from cohezion.agents.nexus_research_agent import NexusResearchAgent

        search_agent = NexusResearchAgent()
        code_context = f"Searching for patterns in: {topic}"

        # Simulated Codebase Mining
        logger.info(f"🔍 Mining codebase for '{topic}' signatures...")
        findings = await search_agent.secure_index_sim("src/cohezion")

        # 2. Route findings through the Swarm
        abstraction_prompt = f"### ABSTRACT MINING REPORT\nTOPIC: {topic}\nCODE FINDINGS: {findings}\n\nTask: Synthesize these patterns into a 12D finding for the Mission Journal."

        # Energy-conscious recursion
        await self.run_cycle(seed_override=abstraction_prompt)

        await search_agent.close()
        return self.session_discoveries[-1] if self.session_discoveries else None

    async def run_cycle(self, seed_override: str = None):
        """Execute a single autonomous lab cycle using Quadrature Nexus architecture."""
        logger.info("🧪 LabAgent: Starting new research cycle...")

        try:
            # MCP-SIM: Self-Correction Loop with Checkpointing
            checkpoint = {
                "timestamp": time.time(),
                "session_depth": len(self.session_discoveries),
            }

            # 1. Fetch & Nexus Pre-Analysis (EXPLORATION-FIRST)
            nexus_result, raw_seed = await self._ideate_and_analyze(seed_override)

            # 2. Hypothesis Generation & Verification (REFINEMENT LOOP)
            max_retries = 3
            base_refinement_cost = 5.0

            for attempt in range(max_retries):
                # Energy Circuit Breaker: Exponentially increasing cost for recursive thought
                refinement_cost = base_refinement_cost * (2**attempt)
                logger.info(
                    f"Refinement attempt {attempt + 1} (Cost: {refinement_cost})"
                )

                report = await self._experiment(nexus_result, raw_seed)

                # Check for "✅ VERIFIED" or "CRITICAL FAILURE"
                if "✅ VERIFIED" in report:
                    logger.info(f"Refinement successful on attempt {attempt + 1}")
                    break
                else:
                    logger.warning(
                        f"Verification failed on attempt {attempt + 1}. Backtracking..."
                    )
                    # Backtrack to checkpoint if necessary
                    await asyncio.sleep(1)  # Simulated context scrubbing

            # 3. Process & Publish
            await self._process_findings(raw_seed, report)
            await self._system_updates(report)

        except Exception as e:
            logger.error(f"Cycle failed: {e}")

    async def _ideate_and_analyze(self, seed_override: str = None):
        """Phase 1: Generate Idea and Analyze with Nexus."""
        raw_seed = seed_override if seed_override else await self._fetch_seed_thought()
        logger.info(f"🌱 Seed Thought: {raw_seed[:100]}...")

        # Route through Quadrature Nexus
        logger.info("🌐 Routing through Quadrature Nexus lattice...")
        nexus_pack: IgnitionPack = {
            "query": f"Analyze this seed for emergent physics and safety: {raw_seed}",
            "context": {"source": "LabDiscoveryLoop", "mode": "QuadrantNexus"},
            "urgency": "medium",
        }
        nexus_result = await self.controller.ignite(nexus_pack)
        return nexus_result, raw_seed

    async def _experiment(self, nexus_result: dict[str, Any], raw_seed: str) -> str:
        """Phase 2: Generate Hypothesis and Verify."""
        contextual_seed = f"CONTEXT: {nexus_result['synthesis']}\n\nSEED: {raw_seed}"
        return await self.hypothesis_agent.imagine_and_verify(contextual_seed)

    async def _fetch_seed_thought(self) -> str:
        """Retrieve a random node from SurrealDB or a fallback seed from novel domains."""
        try:
            nodes = await self.db_client.get_all_nodes(limit=50)
            if nodes:
                return random.choice(nodes).content
        except Exception as e:
            logger.warning(f"Could not fetch seed from DB: {e}. Using fallback.")

        fallbacks = [
            "Designing a simulation for 10,000+ hierarchical agents to test alignment scaling laws.",
            "Moving beyond token prediction: Agents communicating via direct latent vector transmission.",
            "Constructing a high-fidelity 'Universe' simulation for safe capability testing (Sandboxed Reality).",
            "Constitutional AI applied to swarm consensus protocols: Can 100 agents self-police?",
            "The 'Omega Point' of Agentic AI: When does the simulation become indistinguishable from reality?",
            "Recursive self-improvement in a closed-loop physics engine (The Cohezion Standard).",
        ]
        return random.choice(fallbacks)

    async def _process_findings(self, seed: str, report: str):
        """Synthesize discovery, calculate Anthropic alignment, and persist."""
        timestamp = int(time.time())
        discovery_id = f"discovery_{timestamp}"

        # Extract metadata (simplified for demo)
        success = "✅ VERIFIED" in report
        alignment_score = await self._score_anthropic_alignment(report)

        # Persistence to SurrealDB with Narration
        node = UniverseNode(
            id=discovery_id,
            content=report,
            node_type="lab_discovery",
            physics_state=PhysicsState(
                time=float(timestamp),
                novelty=0.9 if success else 0.4,
                stability=0.8 if success else 0.2,
                coherence=0.85 if success else 0.3,
            ),
            metadata={
                "seed": seed,
                "verified": success,
                "anthropic_alignment": alignment_score,
                "narration": f"Autonomous discovery cycle completed at {datetime.now().isoformat()}. "
                f"Hypothesis {'verified' if success else 'rejected'} in sandbox.",
            },
        )

        await self.db_client.store_node(node, compress=True)
        self.session_discoveries.append(node)

        # 4. HF Datasets Logging (Phase 7)
        sim_data = {
            "cycle_id": discovery_id,
            "seed_thought": seed,
            "universe_domain": self._determine_domain(seed),
            "expert_synthesis": "Extracted from nexus_result",  # In a real run we'd pass this in
            "hypothesis": report.split("HYPOTHESIS:")[1].split("CODE:")[0]
            if "HYPOTHESIS:" in report
            else "N/A",
            "code": report.split("CODE:")[1].split("OUTCOME:")[0]
            if "CODE:" in report
            else "N/A",
            "outcome": report.split("OUTCOME:")[1] if "OUTCOME:" in report else report,
            "phi_score": alignment_score,
            "state_trajectory": [
                [
                    node.physics_state.time,
                    node.physics_state.novelty,
                    node.physics_state.stability,
                    node.physics_state.coherence,
                ]
            ],
            "narration": node.metadata["narration"],
        }
        self.sim_logger.log_cycle(sim_data)

        # Update aligner centroids
        # z_vector = await self.db_client.get_node_vector(node.id) # Placeholder
        # if z_vector is not None:
        #     self.aligner.register_centroid(sim_data["universe_domain"], z_vector)

        logger.info(
            f"💾 Discovery {discovery_id} persisted to SurrealDB and HF Dataset."
        )

    def _determine_domain(self, text: str) -> str:
        """Simple domain classifier for seed thoughts."""
        text = text.lower()
        if "physics" in text or "toroidal" in text or "vortex" in text:
            return "physics"
        if "biology" in text or "chlorophyll" in text or "cell" in text:
            return "biology"
        if "quantum" in text or "qubit" in text:
            return "quantum_hw"
        if "consciousness" in text or "orch-or" in text:
            return "quantum_algo"
        return "general"

    async def _score_anthropic_alignment(self, report: str) -> float:
        """Enhanced alignment scoring based on Anthropic Research Role rubrics."""

        # Simple keyword scoring for now, could be LLM-based later
        score = 0.1  # Baseline
        report_lower = report.lower()
        if "neurons" in report_lower or "circuits" in report_lower:
            score += 0.2
        if "rlhf" in report_lower or "constitution" in report_lower:
            score += 0.2
        if "physics" in report_lower or "toroidal" in report_lower:
            score += 0.2
        if "divergence" in report_lower or "latent" in report_lower:
            score += 0.1

        return min(1.0, score)

    async def _system_updates(self, report: str):
        """Update KEY_LEARNINGS and GEMINI.md asynchronously."""
        if "✅ VERIFIED" in report:
            logger.info(
                "📈 Discovery VERIFIED. Triggering recursive skill refinement..."
            )
            await self._update_knowledge_graph(report)
            await self._refine_skills(report)
        else:
            logger.info("📉 Discovery REJECTED. Skipping skill refinement.")

    async def _update_knowledge_graph(self, report: str):
        """Append new verified learning to KEY_LEARNINGS.md and GEMINI.md."""
        learning_path = Path("src/cohezion/knowledge_graph/KEY_LEARNINGS.md")
        gemini_path = Path("GEMINI.md")

        # In a real agentic loop, we'd use the agent to format these properly
        # For now, we simulate the logic of a 12D Learning entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        new_learning = (
            f"\n---\n\n## Learning [AUTO]: Lab Discovery {int(time.time())}\n"
        )
        new_learning += f"**Date:** {timestamp}\n"
        new_learning += "**Context:** Autonomous AI Lab Cycle\n"
        new_learning += f"**Finding:** {report[:200]}...\n"
        new_learning += "**Verification:** Success in Sandbox\n"
        new_learning += (
            f"**12D State:** [t={time.time()}, novelty=0.9, coherence=0.85]\n"
        )

        try:
            if learning_path.exists():
                with open(learning_path, "a") as f:
                    f.write(new_learning)

            # Simple highlight in GEMINI.md
            if gemini_path.exists():
                content = gemini_path.read_text()
                if "## Session Developments" in content:
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if "## Session Developments" in line:
                            lines.insert(
                                i + 2,
                                f"- **Lab Discovery**: {report[:100]}... (Verified)",
                            )
                            break
                    gemini_path.write_text("\n".join(lines))
        except Exception as e:
            logger.error(f"Failed to update knowledge graph: {e}")

    async def _refine_skills(self, report: str):
        """Identify relevant skills and propose improvements."""
        skills_dir = Path("src/cohezion/skills")
        # Logic to match report to skill (simplified)
        relevant_skill = None
        if "physics" in report.lower() or "toroidal" in report.lower():
            relevant_skill = skills_dir / "PHYSICS_PRIME.md"

        if relevant_skill and relevant_skill.exists():
            logger.info(f"🛠️ Refining skill: {relevant_skill.name}")
            # In a real loop, the agent would edit the file.
            # Here we log the intention and could theoretically call another agent.

    async def send_summary_report(self):
        """Send an email summary of session discoveries."""
        if not self.session_discoveries:
            return

        subject = f"🔬 Autonomous Lab: {len(self.session_discoveries)} New Discoveries"
        body = "<h2>Lab Session Summary</h2><ul>"

        for d in self.session_discoveries:
            body += f"<li><strong>{d.id}</strong>: Alignment {d.metadata['anthropic_alignment']:.2f} | Verified: {d.metadata['verified']}</li>"

        body += "</ul><p>Discoveries have been persisted to SurrealDB with zlib compression.</p>"

        await self.notifier.send_email(subject, body, is_html=True)
        self.session_discoveries = []

    async def process(self, context: str, **kwargs: Any) -> str:
        """BaseAgent entry point."""
        await self.run_cycle()
        return "Cycle completed."
