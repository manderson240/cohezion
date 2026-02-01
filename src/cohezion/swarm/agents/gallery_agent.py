import asyncio
import logging
from pathlib import Path
from typing import Any

from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.swarm_types import Perspective, SwarmConfig, ThoughtVector

logger = logging.getLogger(__name__)


class TheGalleryAgent(BaseAgent):
    """
    The Media Synthesis Specialist.
    Generates high-fidelity visual/audio artifacts for agent journeys.
    Uses local FLUX.2 or Z-Image-Turbo models via CLI wrappers.
    """

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="mistral:7b",  # Orchestrator logic, not the image gen itself
            config=config or SwarmConfig(),
        )
        self.agent_name = "TheGalleryAgent"
        self.role = "Media Synthesizer"
        self.output_dir = Path("data/media/gallery")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.instructions = """
        You are The Gallery Agent. Your goal is to document the Swarm's journey visually.

        1. Receive 'Visual Directives' from The Luminary.
        2. Construct a prompt optimized for FLUX.2 / Z-Image-Turbo.
        3. Execute local generation commands to produce artifacts.
        4. Save artifacts to `data/media/gallery/`.
        """

    async def process(
        self, directives: dict[str, Any], journey_id: str
    ) -> ThoughtVector:
        """
        Generate media based on Luminary directives.
        """
        # Construct the prompt
        pulse = directives.get("pulse", {})
        stability = pulse.get("stability", 0.0)
        color_balance = pulse.get("color_balance", 0.0)

        prompt = "Abstract 12D manifold visualization, tech-noir style. "
        if stability < 0.1:
            prompt += "Perfectly symmetrical grid, glowing neon green lines. "
        else:
            prompt += "Distorted spacetime lattice, chaotic red gltich effects. "

        if color_balance > 0.5:
            prompt += "Blue cool tones, logic structures. "
        else:
            prompt += "Warm amber tones, biological mycelium. "

        prompt += "High fidelity, 8k, unreal engine render."

        # Execute Generation (Simulated for now, or CLI hook)
        filename = f"{journey_id}_pulse.png"
        filepath = self.output_dir / filename

        try:
            # Placeholder for actual FLUX inference
            # await self._run_flux(prompt, filepath)
            logger.info(f"🎨 Gallery: Generating {filename} with prompt: {prompt}")

            # For now, create a dummy file to verify workflow
            with open(filepath, "w") as f:
                f.write(f"Assume Image Content: {prompt}")

            return ThoughtVector(
                perspective=Perspective.CREATIVE,
                content=f"Generated artifact: {filename}",
                metadata={"filepath": str(filepath), "prompt": prompt},
            )

        except Exception as e:
            logger.error(f"Gallery Generation Failed: {e}")
            return ThoughtVector(
                perspective=Perspective.CREATIVE,
                content=f"Failed to generate: {e}",
                metadata={"error": str(e)},
            )

    async def _run_flux(self, prompt: str, output_path: Path):
        """
        Wraps the local FLUX.2 inference command.
        """
        # Example CLI command
        cmd = [
            "python3",
            "scripts/flux_infer.py",
            "--prompt",
            prompt,
            "--output",
            str(output_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        # Edge Case: Process Hangs
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=45.0)
        except TimeoutError:
            proc.kill()
            raise RuntimeError("FLUX generation timed out (>45s).")

        if proc.returncode != 0:
            raise RuntimeError(f"FLUX failed: {stderr.decode()}")
