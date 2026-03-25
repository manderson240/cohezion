import asyncio
import logging
import re

from cohezion.cosmic.knowledge_mapper import KnowledgeMapper
from cohezion.system.sheet_sync import SheetSyncAgent

from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    SurrealClient,
    UniverseNode,
)


# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IngestResearch")


async def main():
    # 1. Initialize Components
    sheet_path = "/home/mike-anderson/Downloads/Cohezion_Research - Sheet1.csv"
    agent = SheetSyncAgent(sheet_path)
    mapper = KnowledgeMapper()
    db = SurrealClient()

    # 2. Sync from Sheet
    items = agent.sync()
    logger.info(f"Found {len(items)} items from Sheet.")

    if not items:
        logger.info("No new items (or sheet empty).")
        return

    try:
        await db.connect()

        for item in items:
            logger.info(f"Processing: {item['link']}")

            # 3. Enhanced Physics Mapping (12D)
            # Try to extract explicit 12D tags from Abstractions
            # e.g. "FLUME [nov:0.9, log:0.8]"
            abstractions = item["abstractions"]

            # Default from Mapper based on Category
            category = item["category"]
            base_physics = mapper.map_research_to_physics(category, 0.8)  # Default grade 0.8

            # Create PhysicsState
            # Mapper returns {mass, color, ...} -> We need 12D
            # Map: Mass -> Physics(5)
            #      Color -> Ignored (Visualization)

            p_state = PhysicsState()
            p_state.physics = base_physics.get("mass", 1.0)

            # Parse Regex overrides
            # looking for: dim:val e.g. nov:0.9
            patterns = {
                "nov": "novelty",
                "log": "logic",
                "bio": "biology",
                "phy": "physics",
                "ctl": "control",
                "prec": "precipitation",
                "field": "field",
                "quant": "quantum",
            }

            for key, attr in patterns.items():
                match = re.search(rf"{key}:([\d\.]+)", abstractions, re.IGNORECASE)
                if match:
                    val = float(match.group(1))
                    setattr(p_state, attr, val)
                    logger.info(f"  -> Extracted {attr}={val}")

            # 4. Create Node
            node = UniverseNode(
                id=f"research_{item['id']}",
                node_type="research",
                content=str(item),
                physics_state=p_state,
                metadata={
                    "source": "GoogleSheet",
                    "link": item["link"],
                    "category": category,
                    "integration": item["integration"],
                },
            )

            # 5. Store
            await db.store_node(node)
            logger.info(f"Stored Node: {node.id}")

    except Exception as e:
        logger.error(f"Ingestion Error: {e}")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
