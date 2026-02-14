"""
Entire.io HTTP client for checkpoint and lineage operations.

Implements bidirectional sync between git commits and entire.io checkpoints.
"""

import httpx
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class Checkpoint(BaseModel):
    """Entire.io checkpoint model."""
    id: str
    commit_hash: str
    message: str
    timestamp: str
    author: str
    files_changed: int
    lines_added: int
    lines_deleted: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LineageNode(BaseModel):
    """Entire.io lineage graph node."""
    checkpoint_id: str
    parent_ids: List[str] = Field(default_factory=list)
    children_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class EntireOpsError(Exception):
    """Base exception for entire.io operations."""
    pass


class EntireOpsClient:
    """
    HTTP client for entire.io API.

    Handles checkpoint creation, retrieval, lineage queries, and bidirectional sync.
    Uses async/await for non-blocking I/O.
    """

    def __init__(
        self,
        api_url: str = "https://api.entire.io/v1",
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize entire.io client.

        Args:
            api_url: Base URL for entire.io API
            api_key: API authentication key
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=self.timeout
            )
        return self._client

    async def close(self):
        """Close HTTP client connection."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def create_checkpoint(
        self,
        commit_hash: str,
        message: str,
        author: str,
        files_changed: int,
        lines_added: int,
        lines_deleted: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Checkpoint:
        """
        Create new checkpoint from git commit.

        Args:
            commit_hash: Git commit SHA
            message: Commit message
            author: Commit author
            files_changed: Number of files modified
            lines_added: Lines added
            lines_deleted: Lines deleted
            metadata: Optional metadata dict

        Returns:
            Created checkpoint object

        Raises:
            EntireOpsError: If API request fails
        """
        client = await self._get_client()

        payload = {
            "commit_hash": commit_hash,
            "message": message,
            "author": author,
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_deleted": lines_deleted,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": metadata or {}
        }

        try:
            response = await client.post("/checkpoints", json=payload)
            response.raise_for_status()
            data = response.json()
            return Checkpoint(**data)
        except httpx.HTTPStatusError as e:
            raise EntireOpsError(f"Failed to create checkpoint: {e}") from e
        except Exception as e:
            raise EntireOpsError(f"Unexpected error creating checkpoint: {e}") from e

    async def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        Retrieve checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            Checkpoint object or None if not found

        Raises:
            EntireOpsError: If API request fails
        """
        client = await self._get_client()

        try:
            response = await client.get(f"/checkpoints/{checkpoint_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return Checkpoint(**data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                raise EntireOpsError(f"Failed to get checkpoint: {e}") from e
            return None
        except Exception as e:
            raise EntireOpsError(f"Unexpected error getting checkpoint: {e}") from e

    async def list_checkpoints(
        self,
        limit: int = 100,
        offset: int = 0,
        since: Optional[str] = None
    ) -> List[Checkpoint]:
        """
        List checkpoints with pagination.

        Args:
            limit: Maximum results to return
            offset: Number of results to skip
            since: ISO timestamp to filter by (optional)

        Returns:
            List of checkpoint objects

        Raises:
            EntireOpsError: If API request fails
        """
        client = await self._get_client()

        params = {"limit": limit, "offset": offset}
        if since:
            params["since"] = since

        try:
            response = await client.get("/checkpoints", params=params)
            response.raise_for_status()
            data = response.json()
            return [Checkpoint(**item) for item in data.get("checkpoints", [])]
        except httpx.HTTPStatusError as e:
            raise EntireOpsError(f"Failed to list checkpoints: {e}") from e
        except Exception as e:
            raise EntireOpsError(f"Unexpected error listing checkpoints: {e}") from e

    async def get_lineage(self, checkpoint_id: str) -> LineageNode:
        """
        Get checkpoint lineage (parents, children).

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            Lineage node with parent/child relationships

        Raises:
            EntireOpsError: If API request fails
        """
        client = await self._get_client()

        try:
            response = await client.get(f"/checkpoints/{checkpoint_id}/lineage")
            response.raise_for_status()
            data = response.json()
            return LineageNode(**data)
        except httpx.HTTPStatusError as e:
            raise EntireOpsError(f"Failed to get lineage: {e}") from e
        except Exception as e:
            raise EntireOpsError(f"Unexpected error getting lineage: {e}") from e

    async def tag_checkpoint(
        self,
        checkpoint_id: str,
        tags: List[str]
    ) -> Checkpoint:
        """
        Add tags to checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier
            tags: List of tag strings to add

        Returns:
            Updated checkpoint object

        Raises:
            EntireOpsError: If API request fails
        """
        client = await self._get_client()

        payload = {"tags": tags}

        try:
            response = await client.post(
                f"/checkpoints/{checkpoint_id}/tags",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return Checkpoint(**data)
        except httpx.HTTPStatusError as e:
            raise EntireOpsError(f"Failed to tag checkpoint: {e}") from e
        except Exception as e:
            raise EntireOpsError(f"Unexpected error tagging checkpoint: {e}") from e

    async def health_check(self) -> Dict[str, Any]:
        """
        Check entire.io API health status.

        Returns:
            Health status dict with status, latency, timestamp

        Raises:
            EntireOpsError: If health check fails
        """
        client = await self._get_client()

        start_time = datetime.utcnow()
        try:
            response = await client.get("/health")
            response.raise_for_status()
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            return {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        except Exception as e:
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return {
                "status": "unhealthy",
                "error": str(e),
                "latency_ms": round(latency_ms, 2),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }


# Singleton instance
_entire_ops_client: Optional[EntireOpsClient] = None


def get_entire_ops(
    api_url: str = "https://api.entire.io/v1",
    api_key: Optional[str] = None,
    timeout: float = 30.0
) -> EntireOpsClient:
    """
    Get or create singleton EntireOpsClient instance.

    Args:
        api_url: Base URL for entire.io API
        api_key: API authentication key
        timeout: Request timeout in seconds

    Returns:
        EntireOpsClient singleton instance
    """
    global _entire_ops_client
    if _entire_ops_client is None:
        _entire_ops_client = EntireOpsClient(
            api_url=api_url,
            api_key=api_key,
            timeout=timeout
        )
    return _entire_ops_client


def reset_entire_ops():
    """Reset singleton (for testing)."""
    global _entire_ops_client
    if _entire_ops_client:
        asyncio.run(_entire_ops_client.close())
    _entire_ops_client = None
