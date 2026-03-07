"""Redis-backed distributed semantic cache for multi-instance AI execution.

Implements 4-tier cache hierarchy:
- L0: Redis (distributed, shared across instances)
- L1: Local dict hash-based lookup (fast, in-process)
- L2: Local semantic/cosine similarity (slower, fallback)
- L3: Vault persistence (slowest, fallback to L1/L2 if unavailable)

Gracefully degrades when Redis unavailable, falling back to L1→L2→L3.
"""

import hashlib
import json
import logging
import time
from typing import Any


try:
    import redis
except ImportError:
    redis = None

from cohezion.cache.semantic_cache import SemanticCache


logger = logging.getLogger(__name__)


class RedisSemanticCache(SemanticCache):
    """Distributed semantic cache with Redis L0 tier for multi-instance sharing.

    Wraps SemanticCache to add a Redis-backed distributed layer (L0).
    When Redis is unavailable, gracefully falls back to L1/L2/L3 tiers.

    Example:
        ```python
        cache = RedisSemanticCache(
            redis_host="localhost",
            redis_port=6379,
            redis_ttl_seconds=3600,
        )

        # Get from cache (L0→L1→L2→L3)
        result = await cache.get("prompt text")

        # Put to cache (L0 + L1/L2/L3)
        await cache.put("prompt text", "response text")
        ```
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_ttl_seconds: int = 3600,
        redis_db: int = 0,
        redis_password: str | None = None,
        enable_redis: bool = True,
        connection_timeout: float = 2.0,
        max_retries: int = 3,
        similarity_threshold: float = 0.92,
        max_l1_size: int = 512,
        max_l2_size: int = 1024,
        mcp_client: Any = None,
        **kwargs: Any,
    ):
        """Initialize Redis-backed semantic cache.

        Args:
            redis_host: Redis server hostname
            redis_port: Redis server port
            redis_ttl_seconds: Time-to-live for Redis entries (seconds)
            redis_db: Redis database number (0-15)
            redis_password: Redis authentication password
            enable_redis: Whether to enable Redis tier (for testing)
            connection_timeout: Redis connection timeout (seconds)
            max_retries: Max connection retry attempts
            similarity_threshold: Cosine similarity threshold for L2
            max_l1_size: L1 cache size
            max_l2_size: L2 cache size
            mcp_client: Optional MCPClient for L3 vault operations
            **kwargs: Additional arguments passed to SemanticCache
        """
        super().__init__(
            similarity_threshold=similarity_threshold,
            max_l1_size=max_l1_size,
            max_l2_size=max_l2_size,
            mcp_client=mcp_client,
            **kwargs,
        )

        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_ttl_seconds = redis_ttl_seconds
        self.redis_db = redis_db
        self.enable_redis = enable_redis
        self.connection_timeout = connection_timeout
        self.max_retries = max_retries

        self._redis_client: redis.Redis | None = None
        self._redis_available = False
        self._connection_attempts = 0
        self._last_connection_attempt = 0.0

        # Initialize Redis connection if enabled
        if enable_redis:
            self._init_redis_connection()

        # Track L0 statistics (public for test access)
        self.hits_l0 = 0
        self.misses_l0 = 0
        self.errors_l0 = 0

        # Connection retry tracking
        self._redis_connection_attempts = 0
        self._redis_max_retries = max_retries

    def _init_redis_connection(self) -> None:
        """Initialize Redis connection with retry logic."""
        if not redis:
            logger.warning("redis package not installed, Redis tier disabled")
            self._redis_available = False
            return

        try:
            self._redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=getattr(self, "redis_password", None),
                socket_connect_timeout=self.connection_timeout,
                socket_keepalive=True,
                decode_responses=False,  # Keep as bytes for JSON handling
            )
            # Test connection
            self._redis_client.ping()
            self._redis_available = True
            logger.info(f"Redis connected: {self.redis_host}:{self.redis_port}")
        except Exception as e:
            logger.debug(f"Redis connection failed: {e}, using L1/L2/L3 only")
            self._redis_available = False
            self._redis_client = None

    def _ensure_redis_connection(self) -> bool:
        """Ensure Redis connection is established.

        Returns:
            True if Redis is available, False otherwise
        """
        if self._redis_available:
            return True

        # Attempt to reconnect
        if self._redis_connection_attempts < self._redis_max_retries:
            self._redis_connection_attempts += 1
            self._init_redis_connection()

        return self._redis_available

    def _get_redis_key(self, prompt: str) -> str:
        """Generate deterministic Redis key with namespace."""
        # Use SHA256 hash for consistent keys across instances
        hash_val = hashlib.sha256(prompt.encode()).hexdigest()
        return f"cache:{hash_val[:16]}"

    async def get(
        self, prompt: str, system: str | None = None, model: str | None = None
    ) -> str | None:
        """Get entry from cache with L0→L1→L2→L3 fallback.

        Args:
            prompt: Query prompt
            system: System prompt (included in cache key)
            model: Model name (included in cache key)

        Returns:
            Cached response if found, None otherwise
        """
        # Try L0 (Redis) first
        if self._redis_available:
            try:
                full_prompt = f"{system or ''}\n{prompt}\n{model or ''}"
                redis_key = self._get_redis_key(full_prompt)
                data = self._redis_client.get(redis_key)
                if data:
                    response_dict = json.loads(data.decode() if isinstance(data, bytes) else data)
                    self.hits_l0 += 1
                    logger.debug(f"L0 hit for {prompt[:30]}...")
                    return response_dict.get("response")
                self.misses_l0 += 1
            except Exception as e:
                self.errors_l0 += 1
                logger.debug(f"L0 error: {e}, falling back to L1/L2/L3")
                self._redis_available = False  # Mark as unavailable

        # Fall back to parent L1/L2/L3
        return await super().get(prompt, system, model)

    async def put(
        self,
        prompt: str,
        response: str,
        system: str | None = None,
        model: str | None = None,
    ) -> None:
        """Put entry to cache (L0 + L1/L2/L3).

        Args:
            prompt: Prompt
            response: Response to cache
            system: System prompt
            model: Model name
        """
        # Put to parent (L1/L2/L3)
        await super().put(prompt, response, system, model)

        # Also try L0 (Redis)
        if self._redis_available and self.enable_redis:
            try:
                full_prompt = f"{system or ''}\n{prompt}\n{model or ''}"
                redis_key = self._get_redis_key(full_prompt)
                response_dict = {
                    "prompt": prompt,
                    "response": response,
                    "system": system,
                    "model": model,
                    "timestamp": time.time(),
                }
                self._redis_client.setex(
                    redis_key,
                    self.redis_ttl_seconds,
                    json.dumps(response_dict),
                )
                logger.debug(f"L0 put for {prompt[:30]}...")
            except Exception as e:
                self.errors_l0 += 1
                logger.debug(f"L0 write error: {e}, continuing with L1/L2/L3")
                self._redis_available = False

    async def clear(self) -> None:
        """Clear all cache tiers."""
        # Clear L1/L2/L3
        await super().clear()

        # Clear L0 (Redis)
        if self._redis_available and self.enable_redis:
            try:
                # Delete all cache:* keys
                self._redis_client.eval(
                    "return redis.call('del', unpack(redis.call('keys', 'cache:*')))",
                    0,
                )
                logger.debug("L0 cleared")
            except Exception as e:
                logger.debug(f"L0 clear error: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics including L0 metrics."""
        stats = super().get_stats()

        # Add L0 stats
        stats["l0_hits"] = self.hits_l0
        stats["l0_misses"] = self.misses_l0
        stats["l0_errors"] = self.errors_l0
        if self.hits_l0 + self.misses_l0 > 0:
            stats["l0_hit_rate"] = self.hits_l0 / (self.hits_l0 + self.misses_l0) * 100
        else:
            stats["l0_hit_rate"] = 0.0
        stats["redis_available"] = self._redis_available
        stats["redis_host"] = self.redis_host
        stats["redis_port"] = self.redis_port
        stats["redis_endpoint"] = f"{self.redis_host}:{self.redis_port}"

        # Adjust overall hit rate to include L0 hits
        total_hits = stats["l1_hits"] + stats["l2_hits"] + stats["l3_hits"] + self.hits_l0
        total_requests = stats["total_requests"] + self.hits_l0 + self.misses_l0
        if total_requests > 0:
            stats["overall_hit_rate"] = (total_hits / total_requests) * 100
        else:
            stats["overall_hit_rate"] = 0.0

        return stats

    def health_check(self) -> dict:
        """Check Redis connection health.

        Returns:
            dict with status, memory, clients info
        """
        health = {
            "redis_available": self._redis_available,
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
        }

        if self._redis_available and self._redis_client:
            try:
                info = self._redis_client.info()
                health["memory_used"] = info.get("used_memory_human")
                health["connected_clients"] = info.get("connected_clients", 0)
                health["last_error"] = None
            except Exception as e:
                health["last_error"] = str(e)
                self._redis_available = False

        return health
