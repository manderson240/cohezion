import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__name__).parent / "src"))

from cohezion.swarm.agents.vision_agent import VisionAgent
from cohezion.swarm.swarm_types import SwarmConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("VisionVerification")

    config = SwarmConfig()
    vision = VisionAgent(config=config)

    image_path = "/home/mike-anderson/dev/cohezion/debate_trajectory.png"

    print("\n--- Testing VisionAgent Analysis ---")
    if Path(image_path).exists():
        description = await vision.process(
            image_path, "Describe the visual structure of this diagram."
        )
        print(f"Vision Analysis Result:\n{description[:500]}...")
    else:
        print(f"Error: {image_path} not found. Skipping vision test.")

    await vision.close()


if __name__ == "__main__":
    asyncio.run(main())
