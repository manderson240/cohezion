import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MultimodalReporter:
    """
    Synthesizes simulation data into multimodal reports (Images, Audio Data, Marimo Carousels).
    """

    ARCHETYPE_IMAGES = {
        "The_Void": "/home/mike-anderson/.gemini/antigravity/brain/50ca8f0d-c9b3-4c86-915c-865a8abbd5e3/the_void_archetype_1769027705303.png",
        "Resonant_Lattice": "/home/mike-anderson/.gemini/antigravity/brain/50ca8f0d-c9b3-4c86-915c-865a8abbd5e3/resonant_lattice_archetype_1769027720759.png",
        "The_Glitch": "/home/mike-anderson/.gemini/antigravity/brain/50ca8f0d-c9b3-4c86-915c-865a8abbd5e3/the_glitch_archetype_1769027737704.png",
        "Fractal_Nexus": "/home/mike-anderson/.gemini/antigravity/brain/50ca8f0d-c9b3-4c86-915c-865a8abbd5e3/fractal_nexus_archetype_1769027752892.png",
    }

    def __init__(
        self, output_dir: str = "src/cohezion/knowledge_graph/universe_nodes/multimodal"
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_universe_summary(self, scenario_results: dict[str, Any]) -> str:
        """
        Creates a markdown summary with embedded assets.
        """
        name = scenario_results["scenario_name"]
        image_path = self.ARCHETYPE_IMAGES.get(name, "")

        # Sonification Data (placeholder logic)
        # Map stability to frequency: 0.5 center = 440Hz (A4)
        stability = scenario_results["mean_stability"]
        frequency = 440 * (1.0 + (stability - 0.5))

        sonification = {
            "base_freq": frequency,
            "timbre": "Complex"
            if "Nexus" in name
            else "Noisy"
            if "Glitch" in name
            else "Pure",
            "duration": 5.0,
        }

        summary = f"""
## 🌌 Archetype: {name.replace("_", " ")}
![{name} Visualization]({image_path})

### 📊 Stability Vitals
- **Mean HIHO Stability:** {stability:.4f}
- **Bright Spots:** {scenario_results["bright_spot_count"]}
- **Precipitation Potential:** {scenario_results["max_reality"]:.4f}

### 🔊 Sonification Pattern
- **Harmonic Center:** {frequency:.2f} Hz
- **Texture:** {sonification["timbre"]}
- **Description:** A {sonification["timbre"].lower()} oscillation representing the {name.lower()} manifold.
"""
        return summary

    def create_multiverse_carousel(self, all_results: list[dict[str, Any]]) -> str:
        """
        Wraps multiple universe summaries into a carousel format.
        """
        carousel = "# 🎡 Multiverse Journey Carousel\n\n"
        carousel += "````carousel\n"

        for i, res in enumerate(all_results):
            carousel += self.generate_universe_summary(res)
            if i < len(all_results) - 1:
                carousel += "\n<!-- slide -->\n"

        carousel += "````"

        output_file = self.output_dir / f"multiverse_carousel_{int(time.time())}.md"
        output_file.write_text(carousel)
        return str(output_file)
