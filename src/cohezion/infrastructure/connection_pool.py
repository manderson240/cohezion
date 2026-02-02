"""SurrealDB connection pooling and resource management.

Provides connection reuse, health checking, and automatic reconnection.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Protocol

logger = logging.getLogger(__name__)


class SurrealClientProtocol(Protocol):
    """Protocol for SurrealDB client interface."""

    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def query(self, sql: str, vars: dict[str, Any] | None = None) -> Any: ...
    async def create(self, table: str, data: dict[str, Any]) -> Any: ...
    async def update(self, thing: str, data: dict[str, Any]) -> Any: ...


@dataclass(frozen=True, slots=True)
class PoolConfig:
    """Configuration for connection pool."""

    max_size: int = 10
    min_size: int = 2
    max_idle_time: float = 300.0  # 5 minutes
    health_check_interval: float = 30.0
    connection_timeout: float = 10.0
    retry_attempts: int = 3
    retry_delay: float = 1.0


class PooledConnection:
    """Wrapper for pooled connections with health tracking."""

    def __init__(self, client: SurrealClientProtocol, pool: ConnectionPool):
        self.client = client
        self._pool = pool
        self._last_used = asyncio.get_event_loop().time()
        self._healthy = True

    async def __aenter__(self) -> PooledConnection:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._pool.release(self)

    def mark_unhealthy(self) -> None:
        self._healthy = False

    @property
    def is_healthy(self) -> bool:
        return self._healthy

    @property
    def idle_time(self) -> float:
        return asyncio.get_event_loop().time() - self._last_used


class ConnectionPool:
    """Async connection pool for SurrealDB with health monitoring.

    Usage:
        pool = ConnectionPool(SurrealDBClient, PoolConfig(max_size=10))
        await pool.initialize()

        async with pool.acquire() as conn:
            result = await conn.client.query("SELECT * FROM nodes")
    """

    def __init__(
        self,
        client_factory: type[SurrealClientProtocol],
        config: PoolConfig | None = None,
    ):
        self._factory = client_factory
        self._config = config or PoolConfig()
        self._pool: asyncio.Queue[PooledConnection] = asyncio.Queue()
        self._in_use: set[PooledConnection] = set()
        self._semaphore = asyncio.Semaphore(self._config.max_size)
        self._initialized = False
        self._health_check_task: asyncio.Task | None = None
        self._metrics = {
            "created": 0,
            "destroyed": 0,
            "acquired": 0,
            "released": 0,
            "health_failures": 0,
        }

    async def initialize(self) -> None:
        """Initialize pool with minimum connections."""
        if self._initialized:
            return

        logger.info(
            f"Initializing connection pool (min={self._config.min_size}, max={self._config.max_size})"
        )

        # Create minimum connections
        for _ in range(self._config.min_size):
            conn = await self._create_connection()
            if conn:
                await self._pool.put(conn)

        # Start health checker
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._initialized = True

    async def close(self) -> None:
        """Close all connections and cleanup."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        all_conns = list(self._in_use) + list(self._pool._queue)
        await asyncio.gather(
            *[self._close_connection(conn) for conn in all_conns],
            return_exceptions=True,
        )

        self._initialized = False
        logger.info(f"Connection pool closed. Metrics: {self._metrics}")

    async def acquire(self) -> PooledConnection:
        """Acquire connection from pool (blocks if at max)."""
        async with self._semaphore:
            self._metrics["acquired"] += 1

            # Try to get from pool
            if not self._pool.empty():
                conn = await self._pool.get()
                if conn.is_healthy:
                    self._in_use.add(conn)
                    return conn
                else:
                    await self._close_connection(conn)

            # Create new connection
            conn = await self._create_connection()
            if conn:
                self._in_use.add(conn)
                return conn

            raise ConnectionError("Failed to acquire database connection")

    async def release(self, conn: PooledConnection) -> None:
        """Release connection back to pool."""
        self._metrics["released"] += 1

        if conn in self._in_use:
            self._in_use.remove(conn)

        if conn.is_healthy and conn.idle_time < self._config.max_idle_time:
            await self._pool.put(conn)
        else:
            await self._close_connection(conn)

    async def _create_connection(self) -> PooledConnection | None:
        """Create new database connection with retries."""
        for attempt in range(self._config.retry_attempts):
            try:
                client = self._factory()
                await asyncio.wait_for(
                    client.connect(), timeout=self._config.connection_timeout
                )

                self._metrics["created"] += 1
                return PooledConnection(client, self)

            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self._config.retry_attempts - 1:
                    await asyncio.sleep(self._config.retry_delay)

        return None

    async def _close_connection(self, conn: PooledConnection) -> None:
        """Close a connection."""
        try:
            await conn.client.close()
            self._metrics["destroyed"] += 1
        except Exception as e:
            logger.debug(f"Error closing connection: {e}")

    async def _health_check_loop(self) -> None:
        """Periodic health check for idle connections."""
        while True:
            try:
                await asyncio.sleep(self._config.health_check_interval)
                await self._run_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _run_health_checks(self) -> None:
        """Check and cleanup idle connections."""
        now = asyncio.get_event_loop().time()
        to_check = []

        # Get all idle connections
        while not self._pool.empty():
            conn = await self._pool.get()
            if now - conn._last_used > self._config.max_idle_time:
                to_check.append(conn)
            else:
                await self._pool.put(conn)

        # Check and close stale connections
        for conn in to_check:
            try:
                # Simple health check query
                await conn.client.query("SELECT 1")
                await self._pool.put(conn)
            except Exception:
                conn.mark_unhealthy()
                await self._close_connection(conn)
                self._metrics["health_failures"] += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get pool metrics."""
        return {
            **self._metrics,
            "pool_size": self._pool.qsize(),
            "in_use": len(self._in_use),
            "available": self._pool.qsize(),
        }


# Global pool singleton
_pool: ConnectionPool | None = None


async def get_connection_pool(
    client_factory: type[SurrealClientProtocol] | None = None,
    config: PoolConfig | None = None,
) -> ConnectionPool:
    """Get or create global connection pool."""
    global _pool
    if _pool is None and client_factory is not None:
        _pool = ConnectionPool(client_factory, config)
        await _pool.initialize()
    return _pool


async def close_connection_pool() -> None:
    """Close global connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
