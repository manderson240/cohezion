"""
SurrealDB Client - Multi-model database for the Universe Simulation.

Supports:
- Document storage with embeddings
- 12D physics_state vectors for visualization
- Graph relationships between nodes
- Vector similarity search
"""

import asyncio
import base64
import logging
import re
import time
import zlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx
import numpy as np

from cohezion.reliability import get_circuit


logger = logging.getLogger(__name__)


# Shared in-memory store for fallback/testing
_SHARED_STORE = None


@dataclass
class PhysicsState:
    """
    The 12-dimensional physics state vector (3 Spatial + 1 Time + 8 Brane).
    Aligns with the FLUME methodology for latent understanding.
    """

    # Spatial dimensions (3)
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    # Temporal dimension (1)
    time: float = 0.0

    # Brane dimensions (8)
    physics: float = 0.0  # Energy/Mass signatures
    biology: float = 0.0  # Organic/Agentic signatures
    logic: float = 0.0  # Semantic structure
    quantum: float = 0.0  # Uncertainty/Probabilistic state
    field: float = 0.0  # Influence/Contextual weight
    control: float = 0.0  # Governance/Stabilization
    novelty: float = 0.0  # Innovation/Entropy
    precipitation: float = 0.0  # COMMERCE/Value Manifestation (UCP)

    def to_array(self) -> Any:
        """Convert to numpy array for calculations."""
        data = [
            self.x,
            self.y,
            self.z,
            self.time,
            self.physics,
            self.biology,
            self.logic,
            self.quantum,
            self.field,
            self.control,
            self.novelty,
            self.precipitation,
        ]
        if hasattr(np, "array"):  # Check if it's a real numpy
            try:
                return np.array(data, dtype=np.float32)
            except (ValueError, TypeError, AttributeError):
                return data
        return data

    @classmethod
    def from_array(cls, arr: np.ndarray) -> "PhysicsState":
        """Create from numpy array."""
        if len(arr) != 12:
            raise ValueError(f"Expected 12 dimensions, got {len(arr)}")
        return cls(
            x=float(arr[0]),
            y=float(arr[1]),
            z=float(arr[2]),
            time=float(arr[3]),
            physics=float(arr[4]),
            biology=float(arr[5]),
            logic=float(arr[6]),
            quantum=float(arr[7]),
            field=float(arr[8]),
            control=float(arr[9]),
            novelty=float(arr[10]),
            precipitation=float(arr[11]),
        )

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for storage."""
        return {
            "dim_1_x": self.x,
            "dim_2_y": self.y,
            "dim_3_z": self.z,
            "dim_4_time": self.time,
            "dim_5_physics": self.physics,
            "dim_6_biology": self.biology,
            "dim_7_logic": self.logic,
            "dim_8_quantum": self.quantum,
            "dim_9_field": self.field,
            "dim_10_control": self.control,
            "dim_11_novelty": self.novelty,
            "dim_12_precipitation": self.precipitation,
        }

    def pack(self) -> str:
        """Pack 12D state into a compact base64 string for storage."""
        arr = self.to_array()
        if hasattr(arr, "tobytes"):
            try:
                return base64.b64encode(arr.tobytes()).decode("ascii")
            except (TypeError, ValueError, AttributeError) as e:
                logger.debug("Binary pack failed, using JSON fallback: %s", e)
        # Fallback to JSON string as 'packed' if numpy is missing
        return base64.b64encode(str(arr).encode()).decode("ascii")

    @classmethod
    def unpack(cls, packed: str) -> "PhysicsState":
        """Unpack 12D state from base64 string."""
        data = base64.b64decode(packed)
        # Ensure numpy is available as np
        import numpy as np

        arr = np.frombuffer(data, dtype=np.float32)
        return cls.from_array(arr)


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
    compressed: bool = False

    def to_dict(self, compress: bool = False) -> dict[str, Any]:
        content_val = self.content
        is_compressed = False

        if compress and len(self.content) > 100:
            compressed_data = zlib.compress(self.content.encode("utf-8"))
            content_val = base64.b64encode(compressed_data).decode("ascii")
            is_compressed = True

        return {
            "id": self.id,
            "content": content_val,
            "embedding": self.embedding,
            "physics_state": self.physics_state.to_dict(),
            "node_type": self.node_type,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "compressed": is_compressed or self.compressed,
            "packed_physics": self.physics_state.pack(),
        }


class SurrealClient:
    """
    Async client for SurrealDB.

    Manages the universe_nodes table and provides
    vector similarity search capabilities.
    """

    _FAILED_ONCE = False  # Track if connection failed to avoid repeated timeouts
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
DEFINE FIELD packed_physics ON TABLE universe_nodes TYPE string;
DEFINE FIELD node_type ON TABLE universe_nodes TYPE string DEFAULT 'document';
DEFINE FIELD created_at ON TABLE universe_nodes TYPE datetime DEFAULT time::now();
DEFINE FIELD metadata ON TABLE universe_nodes TYPE object DEFAULT {};
DEFINE FIELD compressed ON TABLE universe_nodes TYPE bool DEFAULT false;
DEFINE FIELD stability_score ON TABLE universe_nodes VALUE (
    (physics_state.dim_10_control + physics_state.dim_12_precipitation) / 2
) OR 0.0;

-- Index for vector similarity search (SurrealDB 2.0+)
-- DEFINE INDEX embedding_idx ON universe_nodes FIELDS embedding MTREE DIMENSION 768 DIST COSINE;
"""

    async def is_alive(self) -> bool:
        """Check if the SurrealDB server is responsive."""
        try:
            # Try to hit the health endpoint
            # We use the URL to derive the health port (usually same as RPC but HTTP)
            health_url = self.url.replace("ws://", "http://").replace("/rpc", "/health")
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(health_url)
                return response.status_code == 200
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ConnectionError):
            return False

    async def ensure_active(self, timeout: int = 30) -> bool:
        """
        Ensures the database is available. Blocks until active.
        If it's down, logs a critical error.
        """
        if SurrealClient._FAILED_ONCE:
            return False

        start = time.time()
        while time.time() - start < timeout:
            if await self.is_alive():
                logger.info("📡 SurrealDB existence confirmed.")
                return True
            logger.warning("⏳ Waiting for SurrealDB substrate...")
            await asyncio.sleep(2)

        logger.error("❌ SurrealDB substrate FAILURE: Persistence guard timeout.")
        SurrealClient._FAILED_ONCE = True  # One failure is enough
        return False

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
        self._using_fallback = False
        self._client: Any = None  # Will be surrealdb client when connected

    async def connect(self) -> bool:
        """
        Connect to SurrealDB.

        Returns True if connected successfully.
        """
        breaker = get_circuit("surrealdb", failure_threshold=5)
        if not breaker.allow_request():
            logger.warning("🛑 Circuit Open: SurrealDB connection rejected. Using fallback.")
            self._use_fallback()
            return True

        global _SHARED_STORE
        try:
            # Try to import surrealdb
            try:
                from surrealdb import AsyncSurreal
            except ImportError:
                logger.warning("surrealdb package not installed. Using in-memory fallback.")
                self._connected = True
                if _SHARED_STORE is None:
                    _SHARED_STORE = InMemoryStore()
                self._client = _SHARED_STORE
                return True

            # Use AsyncSurreal with the new API (v1.0.8+)
            import os as _os

            self._client = AsyncSurreal(self.url)
            await self._client.connect()
            await self._client.signin(
                {
                    "username": _os.environ.get("SURREAL_USER", "root"),
                    "password": _os.environ.get("SURREAL_PASSWORD", "root"),
                }
            )
            await self._client.use(self.namespace, self.database)
            self._connected = True
            breaker.record_success()
            logger.info(
                (
                    f"✅ REAL CLIENT: Connected to SurrealDB at {self.url} "
                    f"({self.namespace}/{self.database})"
                )
            )
            return True
        except (
            ConnectionError,
            OSError,
            httpx.HTTPError,
            httpx.TimeoutException,
            asyncio.TimeoutError,
            RuntimeError,
            ValueError,
        ) as e:
            breaker.record_failure()
            logger.error(
                "Failed to connect to SurrealDB: %s. Falling back to InMemoryStore.",
                e,
                exc_info=True,
            )
            self._use_fallback()
            return True

    def _use_fallback(self):
        """Enable in-memory fallback."""
        global _SHARED_STORE
        if _SHARED_STORE is None:
            _SHARED_STORE = InMemoryStore()
        self._client = _SHARED_STORE
        self._connected = True
        self._using_fallback = True
        logger.warning("🔸 FALLBACK: Using InMemoryStore for persistence.")

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
        except (
            ConnectionError,
            OSError,
            httpx.HTTPError,
            asyncio.TimeoutError,
            RuntimeError,
            ValueError,
        ) as e:
            logger.error("Failed to create schema: %s", e, exc_info=True)
            return False

    async def store_node(self, node: UniverseNode, compress: bool = False) -> str:
        """
        Store a universe node.

        Returns the node ID.
        """
        if not self._connected:
            await self.connect()

        try:
            data = node.to_dict(compress=compress)

            if isinstance(self._client, InMemoryStore):
                self._client.store(node.id, data)
                logger.debug("Stored node %s. Compressed: %s", node.id, data.get("compressed"))
            else:
                await self._client.create(f"universe_nodes:{node.id}", data)

            logger.debug(f"Stored node {node.id}")
            return node.id

        except (
            ConnectionError,
            OSError,
            httpx.HTTPError,
            asyncio.TimeoutError,
            RuntimeError,
            ValueError,
            KeyError,
        ) as e:
            logger.error("Failed to store node: %s", e, exc_info=True)
            raise

    async def create(self, table: str, data: dict[str, Any]) -> Any:
        """Create a record in a specific table."""
        if not self._connected:
            await self.connect()
        try:
            if isinstance(self._client, InMemoryStore):
                # For InMemoryStore, we need to simulate creation.
                # If 'id' is provided in data, use it. Otherwise, generate one.
                record_id = data.get("id") or f"{table}_{int(time.time() * 1000)}"
                self._client.store(record_id, data)
                return [{"id": f"{table}:{record_id}", "data": data}]  # Simulate SurrealDB response
            else:
                return await self._client.create(table, data)
        except (
            ConnectionError,
            OSError,
            httpx.HTTPError,
            asyncio.TimeoutError,
            RuntimeError,
            ValueError,
            KeyError,
        ) as e:
            logger.error("Create failed in %s: %s", table, e, exc_info=True)
            raise

    async def query(self, sql: str, vars: dict[str, Any] | None = None) -> Any:
        """Execute a raw SQL query against the database."""
        if not self._connected:
            await self.connect()

        breaker = get_circuit("surrealdb")
        try:
            if isinstance(self._client, InMemoryStore):
                # Basic mock for mission/thought queries
                if "CREATE missions" in sql or "CREATE agent_journey" in sql:
                    data = vars.get("data") if vars else vars
                    if data:
                        # Extract the bare ID from table:id if present
                        bare_id = data["id"].split(":")[-1] if ":" in data["id"] else data["id"]
                        self._client.store(bare_id, data)
                    return [data]
                if "CREATE agent_thought" in sql:
                    data = vars.get("data") if vars else vars
                    if data:
                        self._client.store(data["id"], data)
                    return [data]
                if "CREATE velocity_events" in sql:
                    data = vars.get("data") if vars else vars
                    if data:
                        self._client.store(f"event_{int(time.time() * 1000)}", data)
                    return [data]
                if "FROM missions" in sql or "FROM agent_journey" in sql:
                    mission_id = vars.get("id") if vars else None
                    if not mission_id:
                        # Try to extract from SQL table:id
                        match = re.search(r"FROM\s+[\w`]+:([\w-]+)", sql)
                        if match:
                            mission_id = match.group(1)

                    mission = self._client.get(mission_id) if mission_id else None
                    if not mission and not mission_id:
                        # Return all for generic SELECT * FROM table
                        all_items = self._client.get_all(limit=100)
                        return [{"result": all_items, "status": "OK"}]

                    return [{"result": [mission] if mission else [], "status": "OK"}]
                if "FROM agent_thought" in sql:
                    # Handle queries like: SELECT content, metadata.query_hash as qh, metadata.agent
                    # as agent FROM agent_thought ORDER BY timestamp DESC LIMIT 100
                    all_nodes = self._client.get_all(1000)
                    # Filter for agent_thought type
                    matches = [n for n in all_nodes if n.get("node_type") == "agent_thought"]

                    # Handle specific projections if using alias (e.g., metadata.query_hash as qh)
                    if "qh" in sql or "metadata.query_hash" in sql:
                        processed = []
                        for m in matches:
                            meta = m.get("metadata", {})
                            processed.append(
                                {
                                    "content": m.get("content"),
                                    "qh": meta.get("query_hash"),
                                    "agent": meta.get("agent"),
                                }
                            )
                        return [processed]

                    return [matches]

                # Table-based filtering mock (e.g., SELECT * FROM table WHERE field = $value)
                if "SELECT * FROM" in sql and "WHERE" in sql:
                    # Generic mock for "WHERE x > y AND a > b" type queries based on
                    # EvolutionaryDriver
                    # SELECT * FROM universe_nodes WHERE node_type = 'energy_snapshot' AND ...

                    if "node_type = 'energy_snapshot'" in sql:
                        # Return all energy snapshots that meet the criteria
                        all_items = self._client.get_all(1000)
                        results = []
                        for item in all_items:
                            if item.get("node_type") != "energy_snapshot":
                                continue

                            # Physics check (Mocking the SQL logic: physics_state.dim_12_coherence >
                            # 0.9)
                            # We just return them if they are snapshots, assuming the caller filters
                            # or we mock the success
                            # But let's try to be a bit specific if possible
                            ps = item.get("physics_state", {})

                            # Check conditions roughly
                            if "coherence > 0.9" in sql and ps.get("dim_12_coherence", 0) <= 0.9:
                                continue
                            if "stability > 0.9" in sql and ps.get("dim_10_stability", 0) <= 0.9:
                                continue

                            results.append(item)

                        return [{"result": results, "status": "OK"}]

                    # Extract table name (simple regex for "FROM table_name")
                    match_from = re.search(r"FROM\s+(\w+)", sql)
                    if match_from:
                        match_from.group(1)
                        # Extract WHERE clause (simple regex for "WHERE field = $var")
                        match_where = re.search(r"WHERE\s+(\w+)\s*=\s*\$(\w+)", sql)
                        if match_where:
                            field = match_where.group(1)
                            var_name = match_where.group(2)

                            if var_name in vars:
                                target_value = vars[var_name]
                                all_items = self._client.get_all(
                                    1000
                                )  # Assuming all items are nodes for now

                                # Filter based on the field and value
                                filtered_items = [
                                    item for item in all_items if item.get(field) == target_value
                                ]
                                return [
                                    filtered_items
                                ]  # SurrealDB returns a list of results, each a list of records

                logger.warning("Query not supported in InMemoryStore")
                return []

            res = await self._client.query(sql, vars)
            breaker.record_success()
            logger.info(f"SurrealDB Response: {res}")
            return res
        except (
            ConnectionError,
            OSError,
            httpx.HTTPError,
            asyncio.TimeoutError,
            RuntimeError,
            ValueError,
            KeyError,
        ) as e:
            breaker.record_failure()
            logger.error("Query failed: %s", e, exc_info=True)
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

        except (
            ConnectionError,
            OSError,
            httpx.HTTPError,
            asyncio.TimeoutError,
            RuntimeError,
            ValueError,
            KeyError,
            TypeError,
        ) as e:
            logger.error("Failed to get node: %s", e, exc_info=True)
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
                # SurrealDB vector search query — cap limit to prevent abuse
                safe_limit = min(int(limit), 10000)
                query = """
                SELECT *, vector::similarity::cosine(embedding, $vector) AS score
                FROM universe_nodes
                ORDER BY score DESC
                LIMIT $limit
                """
                results = await self._client.query(query, {"vector": vector, "limit": safe_limit})
                results = results[0].get("result", []) if results else []

            return [self._dict_to_node(r) for r in results]

        except (
            ConnectionError,
            OSError,
            httpx.HTTPError,
            asyncio.TimeoutError,
            RuntimeError,
            ValueError,
            KeyError,
            TypeError,
        ) as e:
            logger.error("Failed to query similar nodes: %s", e, exc_info=True)
            return []

    async def get_all_nodes(self, limit: int = 100) -> list[UniverseNode]:
        """Get all nodes (for visualization)."""
        if not self._connected:
            await self.connect()

        try:
            if isinstance(self._client, InMemoryStore):
                results = self._client.get_all(limit)
            else:
                safe_limit = min(int(limit), 10000)
                results = await self._client.query(
                    "SELECT * FROM universe_nodes LIMIT $limit",
                    {"limit": safe_limit},
                )
                results = results[0].get("result", []) if results else []

            return [self._dict_to_node(r) for r in results]

        except (
            ConnectionError,
            OSError,
            httpx.HTTPError,
            asyncio.TimeoutError,
            RuntimeError,
            ValueError,
            KeyError,
            TypeError,
        ) as e:
            logger.error("Failed to get all nodes: %s", e, exc_info=True)
            return []

    async def create_relationship(
        self,
        from_id: str,
        to_id: str,
        relation_type: str,
        weight: float = 1.0,
        metadata: dict | None = None,
    ) -> str | None:
        """
        Create a graph relationship between two nodes.

        Supports cross-domain bridging for Gateway 2 capabilities.

        Args:
            from_id: Source node ID
            to_id: Target node ID
            relation_type: Type of relationship (e.g., 'bridges', 'informs', 'derives')
            weight: Relationship strength (0-1)
            metadata: Additional relationship data

        Returns:
            Relationship ID if successful
        """
        if not self._connected:
            await self.connect()

        try:
            if isinstance(self._client, InMemoryStore):
                rel_id = f"rel:{from_id}->{to_id}"
                self._client.store(
                    rel_id,
                    {
                        "from": from_id,
                        "to": to_id,
                        "type": relation_type,
                        "weight": weight,
                        "metadata": metadata or {},
                        "created_at": datetime.now().isoformat(),
                    },
                )
                return rel_id
            else:
                # Validate relation_type to prevent injection (allow only alphanumeric + underscore)
                if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", relation_type):
                    raise ValueError(f"Invalid relation type: {relation_type}")
                result = await self._client.query(
                    f"RELATE $from_id->{relation_type}->$to_id SET "
                    "weight = $weight, "
                    "metadata = $metadata, "
                    "created_at = time::now()",
                    {
                        "from_id": from_id,
                        "to_id": to_id,
                        "weight": weight,
                        "metadata": metadata or {},
                    },
                )
                if result and result[0].get("result"):
                    return str(result[0]["result"][0].get("id", ""))
                return None

        except (
            ConnectionError,
            OSError,
            httpx.HTTPError,
            asyncio.TimeoutError,
            RuntimeError,
            ValueError,
            KeyError,
            TypeError,
        ) as e:
            logger.error("Failed to create relationship: %s", e, exc_info=True)
            return None

    async def get_relationships(
        self,
        node_id: str,
        direction: str = "both",
    ) -> list[dict]:
        """
        Get relationships for a node.

        Args:
            node_id: Node to query relationships for
            direction: 'in', 'out', or 'both'

        Returns:
            List of relationship dictionaries
        """
        if not self._connected:
            await self.connect()

        try:
            if isinstance(self._client, InMemoryStore):
                # Filter in-memory relationships
                all_data = self._client.get_all(1000)
                rels = []
                for item in all_data:
                    if item.get("from") == node_id or item.get("to") == node_id:
                        rels.append(item)
                return rels
            else:
                result = await self._client.query(
                    "SELECT * FROM universe_nodes WHERE id = $node_id FETCH <->, ->;",
                    {"node_id": node_id},
                )
                if result and result[0].get("result"):
                    return result[0]["result"]
                return []

        except (
            ConnectionError,
            OSError,
            httpx.HTTPError,
            asyncio.TimeoutError,
            RuntimeError,
            ValueError,
            KeyError,
            TypeError,
        ) as e:
            logger.error("Failed to get relationships: %s", e, exc_info=True)
            return []

    async def find_bridges(
        self,
        domain_a: str,
        domain_b: str,
        limit: int = 10,
    ) -> list[dict]:
        """
        Find bridging nodes between two domains.

        Key for Gateway 2: Cross-Domain Lattice.

        Args:
            domain_a: First domain (node_type)
            domain_b: Second domain (node_type)
            limit: Max bridges to return

        Returns:
            List of bridge candidates with connection strength
        """
        if not self._connected:
            await self.connect()

        try:
            if isinstance(self._client, InMemoryStore):
                # Fallback for in-memory
                all_nodes = self._client.get_all(1000)
                a_nodes = [n for n in all_nodes if n.get("node_type") == domain_a]
                return a_nodes[:limit]
            else:
                # Find nodes that have relationships to both domains
                safe_limit = min(int(limit), 10000)
                query = """
                    SELECT *,
                        (
                            SELECT count() FROM ->bridges
                            WHERE out.node_type = $domain_b
                        )[0].count AS b_count
                    FROM universe_nodes
                    WHERE node_type = $domain_a
                    ORDER BY b_count DESC
                    LIMIT $limit
                """
                result = await self._client.query(
                    query,
                    {"domain_a": domain_a, "domain_b": domain_b, "limit": safe_limit},
                )
                if result and result[0].get("result"):
                    return result[0]["result"]
                return []

        except (
            ConnectionError,
            OSError,
            httpx.HTTPError,
            asyncio.TimeoutError,
            RuntimeError,
            ValueError,
            KeyError,
            TypeError,
        ) as e:
            logger.error("Failed to find bridges: %s", e, exc_info=True)
            return []

    def _dict_to_node(self, data: dict[str, Any]) -> UniverseNode:
        """Convert a dictionary to UniverseNode."""
        physics_data = data.get("physics_state", {})

        # Prefer packed physics if available
        if "packed_physics" in data:
            try:
                physics_state = PhysicsState.unpack(data["packed_physics"])
            except (ValueError, TypeError, AttributeError, base64.binascii.Error):
                physics_state = self._parse_physics_dict(physics_data)
        else:
            physics_state = self._parse_physics_dict(physics_data)

        content = data.get("content", "")
        compressed = data.get("compressed", False)

        if compressed:
            try:
                decoded = base64.b64decode(content)
                content = zlib.decompress(decoded).decode("utf-8")
            except (
                zlib.error,
                base64.binascii.Error,
                UnicodeDecodeError,
                ValueError,
                TypeError,
            ) as e:
                logger.error("Failed to decompress node %s: %s", data.get("id"), e, exc_info=True)

        return UniverseNode(
            id=data.get("id", ""),
            content=content,
            embedding=data.get("embedding"),
            physics_state=physics_state,
            node_type=data.get("node_type", "document"),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.now(),
            metadata=data.get("metadata", {}),
            compressed=compressed,
        )

    def _parse_physics_dict(self, physics_data: dict) -> PhysicsState:
        """Internal helper to parse physics dict."""
        return PhysicsState(
            x=physics_data.get("dim_1_x", 0),
            y=physics_data.get("dim_2_y", 0),
            z=physics_data.get("dim_3_z", 0),
            time=physics_data.get("dim_4_time", 0),
            physics=physics_data.get("dim_5_physics", 0),
            biology=physics_data.get("dim_6_biology", 0),
            logic=physics_data.get("dim_7_logic", 0),
            quantum=physics_data.get("dim_8_quantum", 0),
            field=physics_data.get("dim_9_field", 0),
            control=physics_data.get("dim_10_control", 0),
            novelty=physics_data.get("dim_11_novelty", 0),
            precipitation=physics_data.get("dim_12_precipitation", 0),
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

        for _key, data in self._data.items():
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
                x=0.5,
                y=0.5,
                z=0.5,
                time=1.0,
                physics=0.8,
                field=0.2,
                novelty=0.6,
                logic=0.9,
            ),
        )

        await client.store_node(test_node)
        retrieved = await client.get_node("test_001")

        if retrieved:
            print(f"Retrieved node: {retrieved.id}")
            print(f"Content: {retrieved.content[:50]}...")
            print(
                f"Physics: x={retrieved.physics_state.x}, physics={retrieved.physics_state.physics}"
            )

    await client.close()


_surreal_client_instance: SurrealClient | None = None


def get_surreal_client() -> SurrealClient:
    """Get the singleton SurrealClient instance."""
    global _surreal_client_instance
    if _surreal_client_instance is None:
        _surreal_client_instance = SurrealClient()
    return _surreal_client_instance


if __name__ == "__main__":
    asyncio.run(main())
