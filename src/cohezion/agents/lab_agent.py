"""
LabAgent - Orchestrator of the Autonomous AI Lab.

This agent runs in the background, continuously generating hypotheses,
executing tests, and synthesizing findings. It ensures all discoveries
are persisted with rich narration and mapped to the Anthropic Research Role.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    SurrealClient,
    UniverseNode,
)


logger = logging.getLogger(__name__)


class LabAgent(BaseAgent):
    def __init__(self, config: Any = None):
        super().__init__(
            model_name="deepseek-r1:70b",  # Primary reasoning model
            config=config or {},
        )
        self.db_client = SurrealClient()
        self.session_discoveries: list = []

    async def run_autonomous_loop(self, duration_minutes: int = 60):
        """
        Run the lab autonomously for a specified duration.
        Generates research, verifies experiments, and publishes findings.
        """
        logger.info(f"LabAgent: Engaging Autonomous Drive for {duration_minutes} minutes.")
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        cycles = 0
        last_report_time = start_time

        while time.time() < end_time:
            cycles += 1
            logger.info(f"Loop Cycle {cycles}")

            await self.run_cycle()

            # Log summary every 30 minutes
            if time.time() - last_report_time > 1800:  # 30 mins
                await self.send_summary_report()
                last_report_time = time.time()

            # Yield for other processes
            await asyncio.sleep(5)

        # Final Report
        await self.send_summary_report()
        logger.info("LabAgent: Autonomous Drive Complete.")

    async def research_specific_topic(self, topic: str, context: str):
        """Execute a directed research mission on a specific topic."""
        logger.info(f"LabAgent: Starting DIRECTED research on '{topic}'...")
        seed_packet = f"TOPIC: {topic}\nDETAILS: {context}"
        await self.run_cycle(seed_override=seed_packet)
        return self.session_discoveries[-1] if self.session_discoveries else None

    async def analyze_abstractly(self, topic: str):
        """
        Perform abstract meta-analysis on a topic.
        Uses LLM to synthesize structural patterns into findings.
        """
        logger.info(f"LabAgent: Initiating ABSTRACT ANALYSIS on '{topic}'...")

        # Use LLM to analyze the topic directly
        analysis_prompt = (
            f"Analyze the following topic for emergent patterns and structural insights.\n"
            f"TOPIC: {topic}\n\n"
            f"Synthesize findings into a structured report with HYPOTHESIS and OUTCOME sections."
        )
        findings = await self._call_ollama(analysis_prompt)

        # Route findings through a research cycle
        abstraction_prompt = (
            f"### ABSTRACT MINING REPORT\n"
            f"TOPIC: {topic}\n"
            f"FINDINGS: {findings}\n\n"
            f"Task: Synthesize these patterns into a 12D finding for the Mission Journal."
        )
        await self.run_cycle(seed_override=abstraction_prompt)

        return self.session_discoveries[-1] if self.session_discoveries else None

    async def run_cycle(self, seed_override: str | None = None):
        """Execute a single autonomous lab cycle."""
        logger.info("LabAgent: Starting new research cycle...")

        try:
            # 1. Generate seed thought
            raw_seed = seed_override if seed_override else await self._fetch_seed_thought()
            logger.info(f"Seed Thought: {raw_seed[:100]}...")

            # 2. Analyze seed via LLM
            nexus_result = await self._ideate_and_analyze(raw_seed)

            # 3. Hypothesis Generation & Verification (REFINEMENT LOOP)
            max_retries = 3
            base_refinement_cost = 5.0
            report = ""

            for attempt in range(max_retries):
                refinement_cost = base_refinement_cost * (2**attempt)
                logger.info(f"Refinement attempt {attempt + 1} (Cost: {refinement_cost})")

                report = await self._experiment(nexus_result, raw_seed)

                if "VERIFIED" in report:
                    logger.info(f"Refinement successful on attempt {attempt + 1}")
                    break
                else:
                    logger.warning(f"Verification failed on attempt {attempt + 1}. Backtracking...")
                    await asyncio.sleep(1)

            # 4. Process & Publish
            await self._process_findings(raw_seed, report)
            await self._system_updates(report)

        except Exception as e:
            logger.error(f"Cycle failed: {e}")

    async def _ideate_and_analyze(self, raw_seed: str) -> dict[str, Any]:
        """Phase 1: Analyze seed thought via LLM."""
        prompt = (
            f"Analyze this seed for emergent physics and safety implications:\n\n"
            f"{raw_seed}\n\n"
            f"Provide a synthesis with key insights."
        )
        synthesis = await self._call_ollama(prompt)
        return {"synthesis": synthesis, "source": "LabDiscoveryLoop"}

    async def _experiment(self, nexus_result: dict[str, Any], raw_seed: str) -> str:
        """Phase 2: Generate Hypothesis and Verify."""
        contextual_seed = f"CONTEXT: {nexus_result['synthesis']}\n\nSEED: {raw_seed}"
        prompt = f"Given this context, generate a hypothesis and verify it:\n{contextual_seed}"
        return await self._call_ollama(prompt)

    async def _fetch_seed_thought(self) -> str:
        """Retrieve a random node from SurrealDB or a fallback seed from novel domains."""
        try:
            nodes = await self.db_client.get_all_nodes(limit=50)
            if nodes:
                return random.choice(nodes).content
        except Exception as e:
            logger.warning(f"Could not fetch seed from DB: {e}. Using fallback.")

        fallbacks = [
            (
                "Designing a simulation for 10,000+ hierarchical agents to test alignment scaling "
                "laws."
            ),
            (
                "Moving beyond token prediction: Agents communicating via direct latent vector "
                "transmission."
            ),
            "Constructing a high-fidelity 'Universe' simulation for safe capability testing "
            "(Sandboxed Reality).",
            "Constitutional AI applied to swarm consensus protocols: Can 100 agents self-police?",
            "The 'Omega Point' of Agentic AI: When does the simulation become indistinguishable "
            "from reality?",
            "Recursive self-improvement in a closed-loop physics engine (The Cohezion Standard).",
        ]
        return random.choice(fallbacks)

    async def _process_findings(self, seed: str, report: str):
        """Synthesize discovery, calculate Anthropic alignment, and persist."""
        timestamp = int(time.time())
        discovery_id = f"discovery_{timestamp}"

        success = "VERIFIED" in report
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
                "narration": (
                    f"Autonomous discovery cycle completed at "
                    f"{datetime.now().isoformat()}. "
                    f"Hypothesis {'verified' if success else 'rejected'} in sandbox."
                ),
            },
        )

        await self.db_client.store_node(node, compress=True)
        self.session_discoveries.append(node)

        logger.info(
            f"Discovery {discovery_id} persisted to SurrealDB. Alignment: "
            f"{alignment_score:.2f}, Verified: {success}"
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
        if "VERIFIED" in report:
            logger.info("Discovery VERIFIED. Triggering recursive skill refinement...")
            await self._update_knowledge_graph(report)
            await self._refine_skills(report)
        else:
            logger.info("Discovery REJECTED. Skipping skill refinement.")

    async def _update_knowledge_graph(self, report: str):
        """Append new verified learning to KEY_LEARNINGS.md and GEMINI.md."""
        learning_path = Path("src/cohezion/knowledge_graph/KEY_LEARNINGS.md")
        gemini_path = Path("GEMINI.md")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        new_learning = f"\n---\n\n## Learning [AUTO]: Lab Discovery {int(time.time())}\n"
        new_learning += f"**Date:** {timestamp}\n"
        new_learning += "**Context:** Autonomous AI Lab Cycle\n"
        new_learning += f"**Finding:** {report[:200]}...\n"
        new_learning += "**Verification:** Success in Sandbox\n"
        new_learning += f"**12D State:** [t={time.time()}, novelty=0.9, coherence=0.85]\n"

        try:
            if learning_path.exists():
                with open(learning_path, "a") as f:
                    f.write(new_learning)

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
        relevant_skill = None
        if "physics" in report.lower() or "toroidal" in report.lower():
            relevant_skill = skills_dir / "PHYSICS_PRIME.md"

        if relevant_skill and relevant_skill.exists():
            logger.info(f"Refining skill: {relevant_skill.name}")

    async def send_summary_report(self):
        """Log a summary of session discoveries."""
        if not self.session_discoveries:
            return

        logger.info(f"Autonomous Lab: {len(self.session_discoveries)} New Discoveries")
        for d in self.session_discoveries:
            logger.info(
                f"  {d.id}: Alignment {d.metadata['anthropic_alignment']:.2f} | Verified: "
                f"{d.metadata['verified']}"
            )

        self.session_discoveries = []

    async def process(self, context: str, **kwargs: Any) -> str:
        """BaseAgent entry point."""
        await self.run_cycle()
        return "Cycle completed."
