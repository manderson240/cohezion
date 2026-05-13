"""Universe Repository - Abstract definitions for universe persistence."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from cohezion.core.persistence.surreal_client import UniverseNode


@dataclass
class UniverseRepositoryFilter:
    """Filter options for universe repository queries."""

    node_type: str | None = None
    limit: int = 100
    offset: int = 0


class UniverseRepository(ABC):
    """Abstract base class for universe persistence."""

    @abstractmethod
    async def create(self, node: UniverseNode) -> str:
        """Create a universe node record.

        Returns:
            The ID of the created universe node.
        """

    @abstractmethod
    async def get(self, node_id: str) -> UniverseNode | None:
        """Retrieve a universe node by ID.

        Returns:
            The UniverseNode if found, None otherwise.
        """

    @abstractmethod
    async def get_all(self, filter_params: UniverseRepositoryFilter = None) -> list[UniverseNode]:
        """Retrieve universe nodes with optional filtering.

        Args:
            filter_params: Optional filter parameters for querying.

        Returns:
            List of UniverseNode objects.
        """

    @abstractmethod
    async def update(self, node: UniverseNode) -> bool:
        """Update an existing universe node record.

        Args:
            node: The UniverseNode object with updated values.

        Returns:
            True if the node was updated, False otherwise.
        """

    @abstractmethod
    async def delete(self, node_id: str) -> bool:
        """Delete a universe node record.

        Args:
            node_id: The ID of the universe node to delete.

        Returns:
            True if the node was deleted, False otherwise.
        """

    @abstractmethod
    async def search_by_embedding(self, embedding: list[float], limit: int = 10) -> list[UniverseNode]:
        """Search for nodes by vector similarity.

        Args:
            embedding: The query embedding vector.
            limit: Maximum number of results to return.

        Returns:
            List of UniverseNode objects ordered by similarity.
        """
