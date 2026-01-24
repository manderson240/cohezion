import asyncio
import numpy as np
from cohezion.db.surreal_client import SurrealClient, UniverseNode, PhysicsState

async def test_compression_roundtrip():
    client = SurrealClient()
    # Using InMemoryStore for testing
    await client.connect()

    long_content = "This is a very long string that should be compressed by zlib for efficient storage in SurrealDB. " * 10
    physics = PhysicsState(x=1.0, y=2.0, z=3.0, novelty=0.8)

    node = UniverseNode(
        id="test_compressed",
        content=long_content,
        physics_state=physics,
        node_type="test"
    )

    # Store with compression
    await client.store_node(node, compress=True)

    # Retrieve
    retrieved = await client.get_node("test_compressed")

    assert retrieved is not None
    assert retrieved.content == long_content
    assert retrieved.compressed is True
    assert np.isclose(retrieved.physics_state.x, 1.0)
    assert np.isclose(retrieved.physics_state.novelty, 0.8)
    print("✅ Compression roundtrip successful!")

if __name__ == "__main__":
    asyncio.run(test_compression_roundtrip())
