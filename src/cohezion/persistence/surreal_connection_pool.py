"""SurrealDB connection pooling and resource management.

Provides connection reuse, health checking, predictive load scaling,
and automatic reconnection for SurrealDB client connections.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Protocol


logger = logging.getLogger(__name__)


class SurrealClientProtocol(Protocol):
    """Protocol for SurrealDB client interface."""

    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def query(self, sql: str, params: dict[str, Any] | None = None) -> Any: ...
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

    # Auto-scaling parameters
    scale_up_threshold: float = 0.8  # Scale up when usage >= 80%
    scale_down_threshold: float = 0.3  # Scale down when usage <= 30%
    scale_up_factor: int = 2  # Double size when scaling up
    scale_down_factor: int = 2  # Halve size when scaling down
    max_scale_rate: int = 5  # Max connections to add/remove per scaling event

    # Predictive loading parameters
    prediction_window: float = 60.0  # Look ahead 1 minute
    load_factor: float = 1.5  # Scale based on predicted load

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_size < self.min_size:
            raise ValueError("max_size must be >= min_size")
        if self.scale_up_factor < 1 or self.scale_down_factor < 1:
            raise ValueError("Scale factors must be >= 1")


class PooledConnection:
    """Wrapper for pooled connections with health tracking."""

    def __init__(self, client: SurrealClientProtocol, pool: SurrealConnectionPool) -> None:
        self.client = client
        self._pool = pool
        self._last_used: float = time.time()
        self._healthy: bool = True

    async def __aenter__(self) -> PooledConnection:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._pool.release(self)


class SurrealConnectionPool:
    """SurrealDB connection pool with health monitoring and auto-scaling."""

    def __init__(self, client_class: type[SurrealClientProtocol], config: PoolConfig | None = None) -> None:
        self.client_class = client_class
        self.config = config or PoolConfig()
        self._connections: asyncio.Queue[PooledConnection] = asyncio.Queue()
        self._active_connections: set[PooledConnection] = set()
        self._metrics: dict[str, Any] = {
            "created": 0,
            "destroyed": 0,
            "acquired": 0,
            "released": 0,
            "health_failures": 0,
            "scaling_events": 0,
            "current_size": 0,
            "usage_percent": 0.0,
        }
        self._lock = asyncio.Lock()
        self._health_task: asyncio.Task[None] | None = None
        self._scaling_task: asyncio.Task[None] | None = None
        self._usage_history: deque[tuple[float, float]] = deque(maxlen=100)  # (timestamp, usage)

        # Initialize with min_size connections
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Initialize connection pool with minimum size."""
        for _ in range(self.config.min_size):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._create_connection())
            except RuntimeError:
                pass

    async def _create_connection(self) -> PooledConnection | None:
        """Create a new connection with health checking."""
        try:
            client = self.client_class()
            await asyncio.wait_for(client.connect(), self.config.connection_timeout)

            connection = PooledConnection(client, self)
            connection._healthy = await self._check_health(connection)

            async with self._lock:
                self._connections.put_nowait(connection)
                self._metrics["created"] += 1
                self._metrics["current_size"] += 1

            logger.info("Created pooled connection - healthy: %s", connection._healthy)
            return connection

        except Exception as e:
            logger.error("Failed to create connection: %s", e)
            return None

    async def _check_health(self, connection: PooledConnection) -> bool:
        """Check connection health with a lightweight query."""
        try:
            await asyncio.wait_for(connection.client.query("SELECT 1"), 5.0)
            return True
        except Exception as e:
            logger.warning("Health check failed: %s", e)
            return False

    async def _scale_pool(self) -> None:
        """Auto-scale pool based on usage patterns."""
        async with self._lock:
            current_usage = len(self._active_connections) / max(1, self._metrics["current_size"])
            self._metrics["usage_percent"] = current_usage

            # Record usage for predictive scaling
            self._usage_history.append((time.time(), current_usage))

            # Check if we need to scale
            if current_usage >= self.config.scale_up_threshold:
                await self._scale_up()
            elif current_usage <= self.config.scale_down_threshold:
                await self._scale_down()

    async def _scale_up(self) -> None:
        """Scale up pool size based on current and predicted load."""
        predicted_load = self._predict_load()
        needed_connections = int(predicted_load * self.config.load_factor)
        current_size = self._metrics["current_size"]

        max_add = min(
            self.config.max_scale_rate,
            self.config.max_size - current_size,
            needed_connections,
        )

        if max_add > 0:
            logger.info("Scaling up by %d connections (predicted load: %.2f)", max_add, predicted_load)
            tasks = [self._create_connection() for _ in range(max_add)]
            connections = await asyncio.gather(*tasks, return_exceptions=True)

            successful = sum(1 for c in connections if isinstance(c, PooledConnection))
            self._metrics["scaling_events"] += 1
            logger.info("Successfully scaled up by %d connections", successful)

    async def _scale_down(self) -> None:
        """Scale down pool size by closing idle connections."""
        idle_connections: list[PooledConnection] = []
        now = time.time()

        while self._connections.qsize() > self.config.min_size:
            try:
                connection = self._connections.get_nowait()
            except asyncio.QueueEmpty:
                break
            idle_time = now - connection._last_used

            if idle_time >= self.config.max_idle_time:
                idle_connections.append(connection)
            else:
                self._connections.put_nowait(connection)
                break

        for connection in idle_connections:
            await self._close_connection(connection)

        if idle_connections:
            logger.info("Scaled down by %d idle connections", len(idle_connections))
            self._metrics["scaling_events"] += 1

    def _predict_load(self) -> float:
        """Predict future load based on usage history."""
        if len(self._usage_history) < 2:
            return float(len(self._active_connections) / max(1, self._metrics["current_size"]))

        timestamps, usages = zip(*self._usage_history, strict=True)
        n = len(usages)
        if n > 1:
            x_mean = sum(timestamps) / n
            y_mean = sum(usages) / n

            num = sum((t - x_mean) * (u - y_mean) for t, u in self._usage_history)
            den = sum((t - x_mean) ** 2 for t, _ in self._usage_history)

            if den != 0:
                trend = num / den
                future_time = timestamps[-1] + self.config.prediction_window
                predicted_usage = y_mean + trend * (future_time - x_mean)
                return float(max(0.1, min(1.0, predicted_usage)))

        return float(len(self._active_connections) / max(1, self._metrics["current_size"]))

    async def acquire(self) -> PooledConnection:
        """Acquire a connection from the pool."""
        try:
            try:
                connection = self._connections.get_nowait()
            except asyncio.QueueEmpty:
                if self._metrics["current_size"] < self.config.max_size:
                    created = await self._create_connection()
                    if created is None:
                        raise RuntimeError("Failed to create new connection for pool") from None
                    connection = created
                else:
                    connection = await self._connections.get()

            async with self._lock:
                self._active_connections.add(connection)
                self._metrics["acquired"] += 1

            connection._last_used = time.time()

            idle_time = time.time() - connection._last_used
            if idle_time > self.config.health_check_interval:
                connection._healthy = await self._check_health(connection)
                if not connection._healthy:
                    await self._close_connection(connection)
                    return await self.acquire()

            if self._metrics["acquired"] % 10 == 0:
                asyncio.create_task(self._scale_pool())

            return connection

        except Exception as e:
            logger.error("Failed to acquire connection: %s", e)
            raise

    async def release(self, connection: PooledConnection) -> None:
        """Release a connection back to the pool."""
        should_close = False
        async with self._lock:
            self._active_connections.discard(connection)
            self._metrics["released"] += 1

            if connection._healthy and self._metrics["current_size"] <= self.config.max_size:
                self._connections.put_nowait(connection)
            else:
                should_close = True

        if should_close:
            await self._close_connection(connection)

    async def _close_connection(self, connection: PooledConnection) -> None:
        """Close and remove a connection from the pool."""
        try:
            await connection.client.close()
        except Exception as e:
            logger.debug("Error closing pooled connection: %s", e)

        async with self._lock:
            self._metrics["destroyed"] += 1
            self._metrics["current_size"] -= 1

    async def close(self) -> None:
        """Close all connections in the pool."""
        if self._health_task:
            self._health_task.cancel()
        if self._scaling_task:
            self._scaling_task.cancel()

        to_close: list[PooledConnection] = []
        async with self._lock:
            to_close.extend(self._active_connections)
            self._active_connections.clear()
            while not self._connections.empty():
                try:
                    to_close.append(self._connections.get_nowait())
                except asyncio.QueueEmpty:
                    break

        for connection in to_close:
            await self._close_connection(connection)

    async def get_metrics(self) -> dict[str, Any]:
        """Get pool metrics."""
        current_usage = len(self._active_connections) / max(1, self._metrics["current_size"])
        return {
            **self._metrics,
            "usage_percent": current_usage,
            "queue_size": self._connections.qsize(),
            "active_connections": len(self._active_connections),
            "predicted_load": self._predict_load(),
        }


# Global connection pool instance
_global_connection_pool: SurrealConnectionPool | None = None


def get_surreal_connection_pool(
    client_class: type[SurrealClientProtocol], config: PoolConfig | None = None
) -> SurrealConnectionPool:
    """Get global SurrealDB connection pool instance."""
    global _global_connection_pool
    if _global_connection_pool is None:
        _global_connection_pool = SurrealConnectionPool(client_class, config or PoolConfig())
    return _global_connection_pool


def reset_surreal_connection_pool() -> None:
    """Reset global SurrealDB connection pool instance."""
    global _global_connection_pool
    _global_connection_pool = None
