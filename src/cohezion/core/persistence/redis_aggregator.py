"""
Redis Aggregator - Shard-aware caching layer for the Cohezion ecosystem.
=======================================================================
Provides high-performance L1 caching to supplement SurrealDB persistence.
"""

import logging
import json
from typing import Any, Optional
import redis.asyncio as redis
from cohezion.reliability import get_circuit

logger = logging.getLogger(__name__)

class RedisAggregator:
    """
    Asynchronous Redis client wrapper for swarm-wide caching.
    
    Attributes:
        host (str): Redis host.
        port (int): Redis port.
        db (int): Redis database index.
        client (redis.Redis): Async Redis client.
    """

    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 6379, 
        db: int = 0,
        password: Optional[str] = None
    ):
        """Initialize the Redis aggregator."""
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._client: Optional[redis.Redis] = None
        self._circuit = get_circuit("redis", failure_threshold=5)

    async def connect(self) -> bool:
        """
        Connect to the Redis instance.
        
        Returns:
            bool: True if connection successful, False otherwise.
        """
        if self._client is not None:
            return True

        if not self._circuit.allow_request():
            logger.warning("🛑 Redis circuit is OPEN. Connection rejected.")
            return False

        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
            await self._client.ping()
            self._circuit.record_success()
            logger.info(f"✅ Redis connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            self._circuit.record_failure()
            logger.error(f"❌ Failed to connect to Redis: {e}")
            self._client = None
            return False

    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        
        Args:
            key (str): The cache key.
            
        Returns:
            Optional[Any]: The cached value if found, else None.
        """
        if not await self.connect():
            return None

        if not self._circuit.allow_request():
            return None

        try:
            value = await self._client.get(key)
            if value:
                self._circuit.record_success()
                return json.loads(value)
            return None
        except Exception as e:
            self._circuit.record_failure()
            logger.error(f"Redis GET failed for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Store a value in the cache.
        
        Args:
            key (str): The cache key.
            value (Any): The value to cache (must be JSON serializable).
            ttl (int): Time-to-live in seconds.
            
        Returns:
            bool: True if storage successful, False otherwise.
        """
        if not await self.connect():
            return False

        if not self._circuit.allow_request():
            return False

        try:
            json_val = json.dumps(value)
            await self._client.set(key, json_val, ex=ttl)
            self._circuit.record_success()
            return True
        except Exception as e:
            self._circuit.record_failure()
            logger.error(f"Redis SET failed for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Remove a value from the cache.
        
        Args:
            key (str): The cache key.
            
        Returns:
            bool: True if deletion successful, False otherwise.
        """
        if not await self.connect():
            return False

        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE failed for key {key}: {e}")
            return False

    async def close(self):
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

# Global instance registry
_pools: dict[str, RedisAggregator] = {}

def get_redis(name: str = "default", **kwargs) -> RedisAggregator:
    """Get or create a Redis aggregator instance."""
    if name not in _pools:
        _pools[name] = RedisAggregator(**kwargs)
    return _pools[name]
