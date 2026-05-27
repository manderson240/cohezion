#!/usr/bin/env python3
"""
Roundtable Driver v2.0: Evolutionary Consensus & Implementation
Orchestrates a Deep Thought session, seeds from history, and synthesizes a blueprint.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__file__).parents[2] / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [ROUNDTABLE] - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/roundtable_deep_thought.log"),
    ],
)
logger = logging.getLogger("RoundtableDriver")

MD_LOG = Path("logs/roundtable_deep_thought.md")
BLUEPRINT_FILE = Path("logs/evolutionary_blueprint.md")


class LocalAgent:
    def __init__(self, name: str, role: str, model: str):
        self.name = name
        self.role = role
        self.model = model

    async def speak(
        self, conversation_history: str, specific_instruction: str | None = None
    ) -> str:
        instruction = (
            specific_instruction
            or f"""
        You are {self.name}, a {self.role} in the Cohezion Swarm.
        Your goal is to propose unique, novel solutions that nobody has ever thought of before.

        Focus on: High-Dimensional Physics (HIHO), Fluid Intelligence (FLUME), and Quantum Computing.
        Build upon previous ideas in the conversation or challenge them with radical alternatives.

        Reply as {self.name}:
        """
        )

        prompt = f"""
        {instruction}

        [CONVERSATION HISTORY START]
        {conversation_history[-8000:]}
        [CONVERSATION HISTORY END]
        """

        cmd = ["ollama", "run", self.model, prompt]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.error(f"Model {self.model} Error: {stderr.decode()}")
                return f"[Error: {self.model} failed]"

            response = stdout.decode().strip()
            return response
        except Exception as e:
            logger.error(f"Inference Failed: {e}")
            return "[Error: Inference Failed]"


class Roundtable:
    def __init__(self, duration_hours: float = 2.0, seed_file: Path | None = None):
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=duration_hours)
        self.agents = [
            LocalAgent("DeepSeek-R1", "Architect & Logic Master", "deepseek-r1:70b"),
            LocalAgent("GPT-OSS", "Lateral Thinker & Visionary", "gpt-oss:120b"),
            LocalAgent("Qwen3-Coder", "Technical Implementation Expert", "qwen3-coder:30b"),
            LocalAgent("Mistral", "Critical Reviewer", "mistral:7b"),
        ]

        # Load Seed if exists
        self.history = "# Cohezion Roundtable: Evolutionary Continuation\n\n"
        if seed_file and seed_file.exists():
            with open(seed_file) as f:
                content = f.read()
                # Clean up existing history to prevent infinite appending of headers
                self.history += "## SEEDED CONTEXT\n" + content + "\n\n---\n"

        # Initialize MD log
        MD_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(MD_LOG, "w") as f:
            f.write(self.history)

    async def run_session(self):
        logger.info(
            f"🚀 Starting Roundtable Session. Duration: {(self.end_time - self.start_time).total_seconds() / 3600:.1f}h"
        )

        topic = "Topic: Formulate a concrete, implementable Python prototype for a 'Quantum-Fluid Information Field (QFIF)' system that enhances Cohezion's autonomous optimization capabilities."
        self.history += f"## {topic}\n\n"

        with open(MD_LOG, "a") as f:
            f.write(f"## {topic}\n\n")

        round_num = 1
        while datetime.now() < self.end_time:
            logger.info(f"--- Round {round_num} ---")

            for agent in self.agents:
                logger.info(f"Thinking: {agent.name}...")
                response = await agent.speak(self.history)

                # Update State
                entry = f"### {agent.name} ({agent.role})\n{response}\n\n"
                self.history += entry

                # Log to file
                with open(MD_LOG, "a") as f:
                    f.write(entry)

                logger.info(f"{agent.name} spoke.")
                # Respect GPU Cooling / Swapping
                await asyncio.sleep(15)

            round_num += 1
            # Breathe between rounds
            await asyncio.sleep(60)

        # FINAL SYNTHESIS PHASE
        logger.info("Session Complete. Finalizing Decision...")
        decider = LocalAgent("Synthesizer", "The Final Decider", "deepseek-r1:70b")
        final_inst = """
        You are the Synthesizer. Review the entire debate.
        Identify the single most innovative and implementable technical solution.
        Output a concrete TECHNICAL BLUEPRINT in a markdown code block.
        The blueprint must include:
        1. Name of the System
        2. Core Mathematical Logic
        3. Python File Structure
        4. Key Algorithm description
        """
        blueprint = await decider.speak(self.history, specific_instruction=final_inst)

        with open(BLUEPRINT_FILE, "w") as f:
            f.write(f"# FINAL EVOLUTIONARY BLUEPRINT\n\n{blueprint}")

        logger.info(f"Blueprint saved to {BLUEPRINT_FILE}")

    def start(self):
        asyncio.run(self.run_session())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=str, default="logs/roundtable_deep_thought.md")
    parser.add_argument("--hours", type=float, default=2.0)
    args = parser.parse_args()

    rt = Roundtable(duration_hours=args.hours, seed_file=Path(args.seed))
    rt.start()
