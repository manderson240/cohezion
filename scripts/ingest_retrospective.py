import asyncio
import logging
from pathlib import Path

from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    SurrealClient,
    UniverseNode,
)


logger = logging.getLogger(__name__)


async def ingest_retrospective():
    client = SurrealClient(
        url="ws://localhost:8000/rpc",
        namespace="cohezion",
        database="universe",
    )

    retro_path = Path(
        "/home/mike-anderson/.gemini/antigravity/brain/9120da96-0239-4ee7-abdd-df4e26ac2e3c/mission_retrospective.md"
    )
    if not retro_path.exists():
        print(f"Error: Retrospective not found at {retro_path}")
        return

    content = retro_path.read_text()

    try:
        await client.connect()
        node = UniverseNode(
            id="retro_resource_guardrails_20260120",
            content=content,
            node_type="retrospective",
            physics_state=PhysicsState(coherence=0.98, stability=1.0, complexity=0.85),
            metadata={
                "mission": "Resource Guardrails",
                "date": "2026-01-20",
                "author": "Antigravity",
            },
        )
        await client.store_node(node)
        print("✅ Mission Retrospective ingested into SurrealDB.")
        await client.close()
    except Exception as e:
        print(f"❌ Failed to ingest retrospective: {e}")


if __name__ == "__main__":
    asyncio.run(ingest_retrospective())
