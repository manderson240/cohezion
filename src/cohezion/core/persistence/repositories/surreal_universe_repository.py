"""SurrealDB Universe Repository - Persistence layer for universe nodes."""

import logging
from typing import Any, Dict, List, Optional

from cohezion.core.persistence.repositories.universe_repository import (
    UniverseRepository,
    UniverseRepositoryFilter,
)
from cohezion.core.persistence.surreal_client import SurrealClient, UniverseNode


logger = logging.getLogger(__name__)


class SurrealUniverseRepository(UniverseRepository):
    """SurrealDB-backed repository for universe nodes."""

    def __init__(self, client: SurrealClient):
        self._client = client
        self._table = "universe_nodes"
        logger.info("SurrealUniverseRepository initialized")

    async def create(self, node: UniverseNode) -> str:
        """Create a universe node record in SurrealDB.

        Returns:
            The ID of the created universe node.
        """
        try:
            # Convert UniverseNode to dict for SurrealDB
            data = node.to_dict()

            # Ensure we have an ID
            if not data.get("id"):
                from datetime import datetime

                data["id"] = f"node_{int(datetime.now().timestamp() * 1000)}"

            query = f"CREATE {self._table} CONTENT $data"
            logger.debug(f"💾 Repository: Executing {query}")
            result = await self._client.query(query, {"data": data})

            # Extract ID from SurrealDB response
            if result and result[0].get("result"):
                created_data = result[0]["result"][0]
                return created_data.get("id", data["id"])

            return data["id"]

        except Exception as e:
            logger.error(f"Failed to create universe node in SurrealDB: {e}")
            raise

    async def get(self, node_id: str) -> Optional[UniverseNode]:
        """Retrieve a universe node by ID from SurrealDB.

        Args:
            node_id: The universe node ID.

        Returns:
            The UniverseNode if found, None otherwise.
        """
        try:
            # Proper SurrealDB ID selection
            query = f"SELECT * FROM `{self._table}:{node_id}`"
            result = await self._client.query(query)

            if not result or not result[0].get("result"):
                return None

            data = result[0]["result"][0]
            return self._dict_to_universe_node(data)

        except Exception as e:
            logger.error(f"Failed to get universe node from SurrealDB: {e}")
            return None

    async def get_all(
        self,
        limit: int = 100,
        node_type: Optional[str] = None,
    ) -> List[UniverseNode]:
        """Retrieve universe nodes from SurrealDB with optional filtering.

        Args:
            limit: Maximum number of nodes to return.
            node_type: Optional filter by node type.

        Returns:
            List of UniverseNode objects.
        """
        try:
            # Build query with optional filtering
            if node_type:
                query = f"SELECT * FROM {self._table} WHERE node_type = $node_type LIMIT $limit"
                vars = {"limit": limit, "node_type": node_type}
            else:
                query = f"SELECT * FROM {self._table} LIMIT $limit"
                vars = {"limit": limit}

            result = await self._client.query(query, vars)

            if not result or not result[0].get("result"):
                return []

            nodes = []
            for data in result[0]["result"]:
                node = self._dict_to_universe_node(data)
                if node:
                    nodes.append(node)
            return nodes

        except Exception as e:
            logger.error(f"Failed to get all universe nodes from SurrealDB: {e}")
            return []

    async def update(self, node: UniverseNode) -> bool:
        """Update an existing universe node record in SurrealDB.

        Args:
            node: The UniverseNode object with updated values.

        Returns:
            True if the node was updated, False otherwise.
        """
        try:
            # Convert UniverseNode to dict for SurrealDB
            data = node.to_dict()

            # Remove ID from update data as we use it in the WHERE clause
            node_id = data.pop("id", None)
            if not node_id:
                logger.error("Cannot update universe node without ID")
                return False

            data["updated_at"] = self._get_timestamp()

            query = f"UPDATE {self._table}:{node_id} MERGE $data"
            logger.debug(f"💾 Repository: Executing {query}")
            await self._client.query(query, {"data": data})
            return True

        except Exception as e:
            logger.error(f"Failed to update universe node in SurrealDB: {e}")
            return False

    async def delete(self, node_id: str) -> bool:
        """Delete a universe node record from SurrealDB.

        Args:
            node_id: The ID of the universe node to delete.

        Returns:
            True if the node was deleted, False otherwise.
        """
        try:
            query = f"DELETE {self._table}:{node_id}"
            logger.debug(f"💾 Repository: Executing {query}")
            await self._client.query(query)
            return True

        except Exception as e:
            logger.error(f"Failed to delete universe node from SurrealDB: {e}")
            return False

    async def search_by_embedding(
        self, embedding: List[float], limit: int = 10
    ) -> List[UniverseNode]:
        """Search for nodes by vector similarity in SurrealDB.

        Args:
            embedding: The query embedding vector.
            limit: Maximum number of results to return.

        Returns:
            List of UniverseNode objects ordered by similarity.
        """
        try:
            # Use SurrealDB's vector similarity search
            query = """
                SELECT *, vector::similarity::cosine(embedding, $embedding) AS score
                FROM $table
                ORDER BY score DESC
                LIMIT $limit
            """
            vars = {"table": self._table, "embedding": embedding, "limit": limit}
            result = await self._client.query(query, vars)

            if not result or not result[0].get("result"):
                return []

            nodes = []
            for data in result[0]["result"]:
                node = self._dict_to_universe_node(data)
                if node:
                    nodes.append(node)
            return nodes

        except Exception as e:
            logger.error(f"Failed to search universe nodes by embedding in SurrealDB: {e}")
            return []

    def _dict_to_universe_node(self, data: Dict[str, Any]) -> Optional[UniverseNode]:
        """Helper to convert SurrealDB dict to UniverseNode."""
        try:
            # Handle compressed content if present
            content = data.get("content", "")
            if data.get("compressed", False):
                import base64
                import zlib

                try:
                    compressed_data = base64.b64decode(content.encode("ascii"))
                    content = zlib.decompress(compressed_data).decode("utf-8")
                except Exception as e:
                    logger.warning(f"Failed to decompress content: {e}")
                    content = ""  # Fallback to empty content

            # Handle packed physics state
            physics_state = None
            packed_physics = data.get("packed_physics")
            if packed_physics:
                try:
                    from cohezion.core.persistence.surreal_client import PhysicsState

                    physics_state = PhysicsState.unpack(packed_physics)
                except Exception as e:
                    logger.warning(f"Failed to unpack physics state: {e}")
                    # Fallback to regular physics_state if available
                    physics_state_dict = data.get("physics_state")
                    if physics_state_dict:
                        physics_state = PhysicsState(
                            x=physics_state_dict.get("dim_1_x", 0.0),
                            y=physics_state_dict.get("dim_2_y", 0.0),
                            z=physics_state_dict.get("dim_3_z", 0.0),
                            time=physics_state_dict.get("dim_4_time", 0.0),
                            physics=physics_state_dict.get("dim_5_physics", 0.0),
                            biology=physics_state_dict.get("dim_6_biology", 0.0),
                            logic=physics_state_dict.get("dim_7_logic", 0.0),
                            quantum=physics_state_dict.get("dim_8_quantum", 0.0),
                            field=physics_state_dict.get("dim_9_field", 0.0),
                            control=physics_state_dict.get("dim_10_control", 0.0),
                            novelty=physics_state_dict.get("dim_11_novelty", 0.0),
                            precipitation=physics_state_dict.get("dim_12_precipitation", 0.0),
                        )
            else:
                # Use regular physics_state if packed_physics not available
                physics_state_dict = data.get("physics_state")
                if physics_state_dict:
                    physics_state = PhysicsState(
                        x=physics_state_dict.get("dim_1_x", 0.0),
                        y=physics_state_dict.get("dim_2_y", 0.0),
                        z=physics_state_dict.get("dim_3_z", 0.0),
                        time=physics_state_dict.get("dim_4_time", 0.0),
                        physics=physics_state_dict.get("dim_5_physics", 0.0),
                        biology=physics_state_dict.get("dim_6_biology", 0.0),
                        logic=physics_state_dict.get("dim_7_logic", 0.0),
                        quantum=physics_state_dict.get("dim_8_quantum", 0.0),
                        field=physics_state_dict.get("dim_9_field", 0.0),
                        control=physics_state_dict.get("dim_10_control", 0.0),
                        novelty=physics_state_dict.get("dim_11_novelty", 0.0),
                        precipitation=physics_state_dict.get("dim_12_precipitation", 0.0),
                    )
                else:
                    physics_state = PhysicsState()  # Default

            return UniverseNode(
                id=data.get("id", ""),
                content=content,
                embedding=data.get("embedding"),
                physics_state=physics_state or PhysicsState(),
                node_type=data.get("node_type", "document"),
                created_at=data.get("created_at"),
                metadata=data.get("metadata", {}),
                compressed=data.get("compressed", False),
            )
        except Exception as e:
            logger.error(f"Failed to convert dict to UniverseNode: {e}")
            return None

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime

        return datetime.now().isoformat()
