"""
VisionAgent - Multi-modal sensory processing for the swarm.

Interprets diagrams, UI mockups, and visual code representations
using local VLMs (e.g., Qwen3-VL, Moondream).
"""

import logging
from pathlib import Path

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class VisionAgent(BaseAgent):
    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="moondream:latest",  # Lightweight, reliable local vision
            config=config or SwarmConfig(),
        )

    async def process(
        self,
        image_path: str,
        prompt: str = "Describe this diagram in technical detail.",
    ) -> str:
        """
        Analyze an image and return a textual or code-based interpretation.

        Args:
            image_path: Path to the image file to analyze.
            prompt: Text instruction for the vision model.
        """
        logger.info(f"👁️ VisionAgent analyzing image: {image_path}")

        img_b64 = self._load_image_b64(image_path)
        if not img_b64:
            return f"Error: Image path {image_path} does not exist."

        try:
            return await self._call_vision_model(prompt, img_b64)
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return f"Failed to analyze image: {e}"

    def _load_image_b64(self, image_path: str) -> str | None:
        """Load and encode image."""
        path = Path(image_path)
        if not path.exists():
            return None

        import base64

        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    async def _call_vision_model(self, prompt: str, img_b64: str) -> str:
        """Execute the API call."""
        response = await self.client.post(
            "/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "images": [img_b64],
                "stream": False,
            },
            timeout=60.0,  # Vision tasks can be heavy
        )
        response.raise_for_status()
        return response.json().get("response", "")

    async def diagram_to_mermaid(self, image_path: str) -> str:
        """Specialize in converting architectural sketches to Mermaid code."""
        prompt = """Analyze this architectural sketch/diagram.
Convert it into valid Mermaid.js graph code.
Provide ONLY the mermaid code block.
"""
        return await self.process(image_path, prompt)

    async def ui_to_code(self, image_path: str) -> str:
        """Specialize in converting UI mockups to React/Vanilla CSS."""
        prompt = """Analyze this UI mockup.
Generate a basic HTML/CSS implementation that matches the layout and colors.
Use vibrant, professional aesthetics.
"""
        return await self.process(image_path, prompt)
