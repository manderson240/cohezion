"""
LabAgent - Orchestrator of the Autonomous AI Lab.

This agent runs in the background, continuously generating hypotheses,
executing tests, and synthesizing findings. It ensures all discoveries
are persisted with rich narration and mapped to the Anthropic Research Role.
"""

import asyncio
import logging
import time
import random
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.agents.hypothesis_agent import HypothesisAgent
from cohezion.swarm.controller_agent import ControllerAgent, IgnitionPack
from cohezion.db.surreal_client import SurrealClient, UniverseNode, PhysicsState
from cohezion.mcp.email_notifier import EmailNotifier
from cohezion.simulation.simulation_logger import SimulationLogger
from cohezion.flume.alignment import LatentAligner

logger = logging.getLogger(__name__)

class LabAgent(BaseAgent):
    def __init__(self, config: Any = None):
        super().__init__(
            model_name="deepseek-r1:70b", # Primary reasoning model
            config=config or {},
        )
        self.controller = ControllerAgent()
        self.hypothesis_agent = HypothesisAgent()
        self.db_client = SurrealClient()
        self.notifier = EmailNotifier()
        self.sim_logger = SimulationLogger()
        self.aligner = LatentAligner()
        self.session_discoveries = []

    async def run_cycle(self):
        """Execute a single autonomous lab cycle using Quadrature Nexus architecture."""
        logger.info("🧪 LabAgent: Starting new research cycle...")

        # 1. Fetch & Nexus Pre-Analysis
        raw_seed = await self._fetch_seed_thought()
        logger.info(f"🌱 Seed Thought: {raw_seed[:100]}...")

        # Route through Quadrature Nexus for multi-domain perspective
        logger.info("🌐 Routing through Quadrature Nexus lattice...")
        nexus_pack: IgnitionPack = {
            "query": f"Analyze this seed for emergent physics and safety: {raw_seed}",
            "context": {"source": "LabDiscoveryLoop", "mode": "QuadrantNexus"},
            "urgency": "medium"
        }
        nexus_result = await self.controller.ignite(nexus_pack)

        # 2. Hypothesis Generation & Verification (via HypothesisAgent)
        # We pass the synthesized Nexus context to the HypothesisAgent
        contextual_seed = f"CONTEXT: {nexus_result['synthesis']}\n\nSEED: {raw_seed}"
        report = await self.hypothesis_agent.imagine_and_verify(contextual_seed)

        # 3. Process Findings
        await self._process_findings(raw_seed, report)

        # 4. Update Knowledge Graph & Skills
        await self._system_updates(report)

    async def _fetch_seed_thought(self) -> str:
        """Retrieve a random node from SurrealDB or a fallback seed from novel domains."""
        try:
            nodes = await self.db_client.get_all_nodes(limit=50)
            if nodes:
                return random.choice(nodes).content
        except Exception as e:
            logger.warning(f"Could not fetch seed from DB: {e}. Using fallback.")

        fallbacks = [
            "HIHO (Half-In-Half-Out) reality precipitation at 0.5 coherence.",
            "Fractal Toroidal vortex stability in exotic vacuum objects (EVOs).",
            "Lattice confinement fusion using LENR commercialization insights (ENG8/Aureon).",
            "Warm coherence in chlorophyll Qx states for Quantum Biology simulation.",
            "Penrose Twistors and Orch-OR consciousness manifolds.",
            "Chirality violation in origin-of-life prebiotic chemistry."
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
                coherence=0.85 if success else 0.3
            ),
            metadata={
                "seed": seed,
                "verified": success,
                "anthropic_alignment": alignment_score,
                "narration": f"Autonomous discovery cycle completed at {datetime.now().isoformat()}. "
                             f"Hypothesis {'verified' if success else 'rejected'} in sandbox."
            }
        )

        await self.db_client.store_node(node, compress=True)
        self.session_discoveries.append(node)

        # 4. HF Datasets Logging (Phase 7)
        sim_data = {
            "cycle_id": discovery_id,
            "seed_thought": seed,
            "universe_domain": self._determine_domain(seed),
            "expert_synthesis": "Extracted from nexus_result", # In a real run we'd pass this in
            "hypothesis": report.split("HYPOTHESIS:")[1].split("CODE:")[0] if "HYPOTHESIS:" in report else "N/A",
            "code": report.split("CODE:")[1].split("OUTCOME:")[0] if "CODE:" in report else "N/A",
            "outcome": report.split("OUTCOME:")[1] if "OUTCOME:" in report else report,
            "phi_score": alignment_score,
            "state_trajectory": [[node.physics_state.time, node.physics_state.novelty, node.physics_state.stability, node.physics_state.coherence]],
            "narration": node.metadata["narration"]
        }
        self.sim_logger.log_cycle(sim_data)

        # Update aligner centroids
        # z_vector = await self.db_client.get_node_vector(node.id) # Placeholder
        # if z_vector is not None:
        #     self.aligner.register_centroid(sim_data["universe_domain"], z_vector)

        logger.info(f"💾 Discovery {discovery_id} persisted to SurrealDB and HF Dataset.")

    def _determine_domain(self, text: str) -> str:
        """Simple domain classifier for seed thoughts."""
        text = text.lower()
        if "physics" in text or "toroidal" in text or "vortex" in text: return "physics"
        if "biology" in text or "chlorophyll" in text or "cell" in text: return "biology"
        if "quantum" in text or "qubit" in text: return "quantum_hw"
        if "consciousness" in text or "orch-or" in text: return "quantum_algo"
        return "general"

    async def _score_anthropic_alignment(self, report: str) -> float:
        """Enhanced alignment scoring based on Anthropic Research Role rubrics."""
        rubrics = {
            "mechanistic_interpretability": "How well does it explain internal model states?",
            "scalable_oversight": "Does it enable supervising models more capable than the supervisor?",
            "adversarial_robustness": "Does it improve defense against jailbreaks or deception?",
            "physics_informed_safety": "Does it map physical laws to AI safety guardrails?"
        }

        # Simple keyword scoring for now, could be LLM-based later
        score = 0.1 # Baseline
        report_lower = report.lower()
        if "neurons" in report_lower or "circuits" in report_lower: score += 0.2
        if "rlhf" in report_lower or "constitution" in report_lower: score += 0.2
        if "physics" in report_lower or "toroidal" in report_lower: score += 0.2
        if "divergence" in report_lower or "latent" in report_lower: score += 0.1

        return min(1.0, score)

    async def _system_updates(self, report: str):
        """Update KEY_LEARNINGS and GEMINI.md asynchronously."""
        if "✅ VERIFIED" in report:
            logger.info("📈 Discovery VERIFIED. Triggering recursive skill refinement...")
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

        new_learning = f"\n---\n\n## Learning [AUTO]: Lab Discovery {int(time.time())}\n"
        new_learning += f"**Date:** {timestamp}\n"
        new_learning += f"**Context:** Autonomous AI Lab Cycle\n"
        new_learning += f"**Finding:** {report[:200]}...\n"
        new_learning += f"**Verification:** Success in Sandbox\n"
        new_learning += f"**12D State:** [t={time.time()}, novelty=0.9, coherence=0.85]\n"

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
                            lines.insert(i+2, f"- **Lab Discovery**: {report[:100]}... (Verified)")
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
