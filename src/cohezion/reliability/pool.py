"""
Connection Pool - Reusable HTTP connections.

Provides:
- Connection pooling for httpx
- Configurable pool size
- Automatic cleanup
"""

import logging

import httpx


logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    HTTP connection pool manager.

    Maintains persistent connections to reduce latency.
    """

    def __init__(
        self,
        base_url: str,
        max_connections: int = 20,
        max_keepalive: int = 10,
        timeout: float = 30.0,
    ):
        self.base_url = base_url
        self.max_connections = max_connections
        self.timeout = timeout

        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive,
        )

        self._client = httpx.AsyncClient(
            base_url=base_url,
            limits=limits,
            timeout=httpx.Timeout(timeout),
        )
        self._stats = {"requests": 0, "errors": 0}

    async def get(self, path: str, **kwargs) -> httpx.Response:
        """Make GET request using pooled connection."""
        self._stats["requests"] += 1
        try:
            return await self._client.get(path, **kwargs)
        except Exception:
            self._stats["errors"] += 1
            raise

    async def post(self, path: str, **kwargs) -> httpx.Response:
        """Make POST request using pooled connection."""
        self._stats["requests"] += 1
        try:
            return await self._client.post(path, **kwargs)
        except Exception:
            self._stats["errors"] += 1
            raise

    async def close(self) -> None:
        """Close all connections."""
        await self._client.aclose()

    def get_stats(self) -> dict:
        """Get pool statistics."""
        return {
            "base_url": self.base_url,
            "max_connections": self.max_connections,
            **self._stats,
        }


# Pool registry
_pools: dict[str, ConnectionPool] = {}


def get_pool(
    name: str,
    base_url: str,
    max_connections: int = 20,
    timeout: float = 300.0,
) -> ConnectionPool:
    """Get or create a connection pool."""
    if name not in _pools:
        _pools[name] = ConnectionPool(
            base_url=base_url,
            max_connections=max_connections,
            timeout=timeout,
        )
    return _pools[name]


async def close_all_pools() -> None:
    """Close all connection pools."""
    for pool in _pools.values():
        await pool.close()
    _pools.clear()
