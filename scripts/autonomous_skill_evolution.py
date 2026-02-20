"""Script to trigger autonomous skill evolution."""

import asyncio
import logging

from cohezion.swarm.agents.specialized.skill_architect import get_skill_architect


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("skill_evolution")


async def main():
    logger.info("Starting autonomous skill evolution loop...")
    architect = get_skill_architect()

    updated_skills = await architect.evolve_skills()

    if updated_skills:
        logger.info(f"Successfully evolved {len(updated_skills)} skills:")
        for s in updated_skills:
            logger.info(f" - {s}")
    else:
        logger.info("No new learnings found to evolve skills.")


if __name__ == "__main__":
    asyncio.run(main())
