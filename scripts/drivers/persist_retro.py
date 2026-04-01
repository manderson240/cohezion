#!/usr/bin/env python3
"""
Persist Retrospective to SurrealDB.
Handles async loop management properly.
"""

import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__file__).parents[2] / "src"))

from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    SurrealClient,
    UniverseNode,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PersistRetro")


async def persist():
    logger.info("Connecting to SurrealDB...")
    db = SurrealClient()
    await db.connect()

    retro_content = Path("src/cohezion/knowledge_graph/retrospectives/RETRO_MISSION_50.md").read_text()

    node = UniverseNode(
        id=f"retro_mission_50_{int(asyncio.get_event_loop().time())}",
        content=retro_content,
        node_type="retrospective",
        physics_state=PhysicsState(complexity=0.8, stability=0.9, coherence=0.95),
        metadata={
            "mission": "50_gateways",
            "drivers": ["evolutionary_driver", "code_simplifier"],
        },
    )

    await db.store_node(node)
    logger.info(f"✅ Stored Retrospective: {node.id}")
    await db.close()


if __name__ == "__main__":
    asyncio.run(persist())
