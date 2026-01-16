"""
SurrealDB Client - Multi-model database for the Universe Simulation.

Supports:
- Document storage with embeddings
- 12D physics_state vectors for visualization
- Graph relationships between nodes
- Vector similarity search
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PhysicsState:
    """
    The 12-dimensional physics state vector for visualization.
    
    Each dimension represents a semantic/analytical attribute
    extracted from the content.
    """
    # Spatial dimensions (for 3D positioning)
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    # Temporal dimension
    time: float = 0.0
    
    # Semantic dimensions
    mass: float = 0.0         # Importance/weight
    sentiment: float = 0.0     # -1 to 1 
    complexity: float = 0.0    # 0 to 1
    factuality: float = 0.0    # 0 to 1
    
    # Relational dimensions
    connectivity: float = 0.0  # How connected to other nodes
    stability: float = 0.0     # How stable/consistent
    
    # Abstract dimensions
    novelty: float = 0.0       # How novel/unique
    coherence: float = 0.0     # Internal coherence
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array for calculations."""
        return np.array([
            self.x, self.y, self.z, self.time,
            self.mass, self.sentiment, self.complexity, self.factuality,
            self.connectivity, self.stability, self.novelty, self.coherence,
        ], dtype=np.float32)
    
    @classmethod
    def from_array(cls, arr: np.ndarray) -> "PhysicsState":
        """Create from numpy array."""
        if len(arr) != 12:
            raise ValueError(f"Expected 12 dimensions, got {len(arr)}")
        return cls(
            x=float(arr[0]), y=float(arr[1]), z=float(arr[2]), time=float(arr[3]),
            mass=float(arr[4]), sentiment=float(arr[5]), 
            complexity=float(arr[6]), factuality=float(arr[7]),
            connectivity=float(arr[8]), stability=float(arr[9]),
            novelty=float(arr[10]), coherence=float(arr[11]),
        )
    
    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for storage."""
        return {
            "dim_1_x": self.x,
            "dim_2_y": self.y,
            "dim_3_z": self.z,
            "dim_4_time": self.time,
            "dim_5_mass": self.mass,
            "dim_6_sentiment": self.sentiment,
            "dim_7_complexity": self.complexity,
            "dim_8_factuality": self.factuality,
            "dim_9_connectivity": self.connectivity,
            "dim_10_stability": self.stability,
            "dim_11_novelty": self.novelty,
            "dim_12_coherence": self.coherence,
        }


@dataclass
class UniverseNode:
    """A node in the Universe Simulation."""
    id: str
    content: str
    embedding: list[float] | None = None  # 768-dim for search
    physics_state: PhysicsState = field(default_factory=PhysicsState)
    node_type: str = "document"
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding,
            "physics_state": self.physics_state.to_dict(),
            "node_type": self.node_type,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class SurrealClient:
    """
    Async client for SurrealDB.
    
    Manages the universe_nodes table and provides
    vector similarity search capabilities.
    """
    
    # SurrealDB schema for setup
    SCHEMA = """
DEFINE TABLE universe_nodes SCHEMAFULL;

DEFINE FIELD id ON TABLE universe_nodes TYPE string;
DEFINE FIELD content ON TABLE universe_nodes TYPE string;
DEFINE FIELD embedding ON TABLE universe_nodes TYPE array;
DEFINE FIELD physics_state ON TABLE universe_nodes TYPE object;
DEFINE FIELD node_type ON TABLE universe_nodes TYPE string DEFAULT 'document';
DEFINE FIELD created_at ON TABLE universe_nodes TYPE datetime DEFAULT time::now();
DEFINE FIELD metadata ON TABLE universe_nodes TYPE object DEFAULT {};

-- Index for vector similarity search (SurrealDB 2.0+)
-- DEFINE INDEX embedding_idx ON universe_nodes FIELDS embedding MTREE DIMENSION 768 DIST COSINE;
"""
    
    def __init__(
        self,
        url: str = "ws://localhost:8000/rpc",
        namespace: str = "cohezion",
        database: str = "universe",
    ):
        self.url = url
        self.namespace = namespace
        self.database = database
        self._connected = False
        self._client: Any = None  # Will be surrealdb client when connected
    
    async def connect(self) -> bool:
        """
        Connect to SurrealDB.
        
        Returns True if connected successfully.
        """
        try:
            # Try to import surrealdb
            try:
                from surrealdb import Surreal
            except ImportError:
                logger.warning(
                    "surrealdb package not installed. "
                    "Using in-memory fallback. "
                    "Install with: uv add surrealdb"
                )
                self._connected = True
                self._client = InMemoryStore()
                return True
            
            self._client = Surreal(self.url)
            await self._client.connect()
            await self._client.use(self.namespace, self.database)
            self._connected = True
            logger.info(f"Connected to SurrealDB at {self.url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to SurrealDB: {e}")
            # Fall back to in-memory store
            self._client = InMemoryStore()
            self._connected = True
            return True
    
    async def setup_schema(self) -> bool:
        """
        Set up the database schema.
        
        Should be run once on initial setup.
        """
        if not self._connected:
            await self.connect()
        
        try:
            if isinstance(self._client, InMemoryStore):
                return True
            await self._client.query(self.SCHEMA)
            logger.info("Schema created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            return False
    
    async def store_node(self, node: UniverseNode) -> str:
        """
        Store a universe node.
        
        Returns the node ID.
        """
        if not self._connected:
            await self.connect()
        
        try:
            data = node.to_dict()
            
            if isinstance(self._client, InMemoryStore):
                self._client.store(node.id, data)
            else:
                await self._client.create(f"universe_nodes:{node.id}", data)
            
            logger.debug(f"Stored node {node.id}")
            return node.id
            
        except Exception as e:
            logger.error(f"Failed to store node: {e}")
            raise
    
    async def get_node(self, node_id: str) -> UniverseNode | None:
        """Retrieve a node by ID."""
        if not self._connected:
            await self.connect()
        
        try:
            if isinstance(self._client, InMemoryStore):
                data = self._client.get(node_id)
            else:
                result = await self._client.select(f"universe_nodes:{node_id}")
                data = result[0] if result else None
            
            if not data:
                return None
            
            return self._dict_to_node(data)
            
        except Exception as e:
            logger.error(f"Failed to get node: {e}")
            return None
    
    async def query_similar(
        self,
        vector: np.ndarray | list[float],
        limit: int = 10,
    ) -> list[UniverseNode]:
        """
        Find nodes with similar embeddings.
        
        Uses cosine similarity.
        """
        if not self._connected:
            await self.connect()
        
        if isinstance(vector, np.ndarray):
            vector = vector.tolist()
        
        try:
            if isinstance(self._client, InMemoryStore):
                results = self._client.search_similar(vector, limit)
            else:
                # SurrealDB vector search query
                query = f"""
                SELECT *, vector::similarity::cosine(embedding, $vector) AS score
                FROM universe_nodes
                ORDER BY score DESC
                LIMIT {limit}
                """
                results = await self._client.query(query, {"vector": vector})
                results = results[0].get("result", []) if results else []
            
            return [self._dict_to_node(r) for r in results]
            
        except Exception as e:
            logger.error(f"Failed to query similar nodes: {e}")
            return []
    
    async def get_all_nodes(self, limit: int = 100) -> list[UniverseNode]:
        """Get all nodes (for visualization)."""
        if not self._connected:
            await self.connect()
        
        try:
            if isinstance(self._client, InMemoryStore):
                results = self._client.get_all(limit)
            else:
                results = await self._client.query(
                    f"SELECT * FROM universe_nodes LIMIT {limit}"
                )
                results = results[0].get("result", []) if results else []
            
            return [self._dict_to_node(r) for r in results]
            
        except Exception as e:
            logger.error(f"Failed to get all nodes: {e}")
            return []
    
    def _dict_to_node(self, data: dict[str, Any]) -> UniverseNode:
        """Convert a dictionary to UniverseNode."""
        physics_data = data.get("physics_state", {})
        physics_state = PhysicsState(
            x=physics_data.get("dim_1_x", 0),
            y=physics_data.get("dim_2_y", 0),
            z=physics_data.get("dim_3_z", 0),
            time=physics_data.get("dim_4_time", 0),
            mass=physics_data.get("dim_5_mass", 0),
            sentiment=physics_data.get("dim_6_sentiment", 0),
            complexity=physics_data.get("dim_7_complexity", 0),
            factuality=physics_data.get("dim_8_factuality", 0),
            connectivity=physics_data.get("dim_9_connectivity", 0),
            stability=physics_data.get("dim_10_stability", 0),
            novelty=physics_data.get("dim_11_novelty", 0),
            coherence=physics_data.get("dim_12_coherence", 0),
        )
        
        return UniverseNode(
            id=data.get("id", ""),
            content=data.get("content", ""),
            embedding=data.get("embedding"),
            physics_state=physics_state,
            node_type=data.get("node_type", "document"),
            created_at=datetime.fromisoformat(data["created_at"]) 
                       if "created_at" in data else datetime.now(),
            metadata=data.get("metadata", {}),
        )
    
    async def close(self) -> None:
        """Close the connection."""
        if self._client and not isinstance(self._client, InMemoryStore):
            await self._client.close()
        self._connected = False


class InMemoryStore:
    """
    In-memory fallback when SurrealDB is not available.
    
    Useful for development and testing.
    """
    
    def __init__(self):
        self._data: dict[str, dict[str, Any]] = {}
    
    def store(self, key: str, value: dict[str, Any]) -> None:
        self._data[key] = value
    
    def get(self, key: str) -> dict[str, Any] | None:
        return self._data.get(key)
    
    def get_all(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(self._data.values())[:limit]
    
    def search_similar(
        self, 
        vector: list[float], 
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Simple cosine similarity search."""
        if not self._data:
            return []
        
        query_vec = np.array(vector)
        scores = []
        
        for key, data in self._data.items():
            embedding = data.get("embedding")
            if embedding:
                doc_vec = np.array(embedding)
                # Cosine similarity
                similarity = np.dot(query_vec, doc_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(doc_vec) + 1e-8
                )
                scores.append((similarity, data))
        
        scores.sort(reverse=True, key=lambda x: x[0])
        return [s[1] for s in scores[:limit]]


async def main() -> None:
    """Test the SurrealDB client."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test SurrealDB Client")
    parser.add_argument("--verify-schema", action="store_true")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    client = SurrealClient()
    await client.connect()
    
    if args.verify_schema:
        success = await client.setup_schema()
        print(f"Schema setup: {'SUCCESS' if success else 'FAILED'}")
        
        # Test store and retrieve
        test_node = UniverseNode(
            id="test_001",
            content="This is a test node for the universe simulation.",
            embedding=[0.1] * 768,  # Fake embedding
            physics_state=PhysicsState(
                x=0.5, y=0.5, z=0.5, time=1.0,
                mass=0.8, sentiment=0.2, complexity=0.6, factuality=0.9,
            ),
        )
        
        await client.store_node(test_node)
        retrieved = await client.get_node("test_001")
        
        if retrieved:
            print(f"Retrieved node: {retrieved.id}")
            print(f"Content: {retrieved.content[:50]}...")
            print(f"Physics: x={retrieved.physics_state.x}, mass={retrieved.physics_state.mass}")
        
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
