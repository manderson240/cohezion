"""Redis-based session management for MCP servers."""

from __future__ import annotations

import json
import logging

import redis.asyncio as redis

from cohezion.security.credentials import get_credentials


logger = logging.getLogger(__name__)

# Primary: Vault Warden, Fallback: Environment
REDIS_URL = get_credentials().get_secret("COHEZION_REDIS_URL", env_var="REDIS_URL") or "redis://localhost:6379"
DEFAULT_TTL = 3600  # 1 hour


class SessionManager:
    """Manages sessions across all MCP servers using Redis."""

    def __init__(self, redis_url: str = REDIS_URL, prefix: str = "mcp:"):
        self.redis_url = redis_url
        self.prefix = prefix
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    def _key(self, session_id: str) -> str:
        """Generate Redis key with prefix."""
        return f"{self.prefix}session:{session_id}"

    async def create_session(self, session_id: str | None = None, data: dict | None = None) -> str:
        """Create a new session.

        Args:
            session_id: Optional session ID, generates UUID if not provided
            data: Initial session data

        Returns:
            Session ID
        """
        import uuid

        if session_id is None:
            session_id = str(uuid.uuid4())

        redis_client = await self._get_redis()
        key = self._key(session_id)

        session_data = {
            "id": session_id,
            "created_at": json.dumps(None),  # Will be set by Redis
            "data": data or {},
        }

        await redis_client.setex(key, DEFAULT_TTL, json.dumps(session_data))
        logger.info(f"Created session: {session_id}")
        return session_id

    async def get_session(self, session_id: str) -> dict | None:
        """Get session data.

        Args:
            session_id: Session ID

        Returns:
            Session data or None if not found
        """
        if not session_id:
            return None

        redis_client = await self._get_redis()
        key = self._key(session_id)

        data = await redis_client.get(key)
        if data:
            # Refresh TTL
            await redis_client.expire(key, DEFAULT_TTL)
            return json.loads(data)
        return None

    async def update_session(self, session_id: str, data: dict) -> bool:
        """Update session data.

        Args:
            session_id: Session ID
            data: Data to merge/update

        Returns:
            True if successful
        """
        if not session_id:
            return False

        redis_client = await self._get_redis()
        key = self._key(session_id)

        existing = await redis_client.get(key)
        if existing:
            session = json.loads(existing)
            session["data"].update(data)
            await redis_client.setex(key, DEFAULT_TTL, json.dumps(session))
            return True
        return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session ID

        Returns:
            True if deleted
        """
        if not session_id:
            return False

        redis_client = await self._get_redis()
        key = self._key(session_id)

        result = await redis_client.delete(key)
        return result > 0

    async def list_sessions(self, pattern: str = "*") -> list[str]:
        """List session IDs matching pattern.

        Args:
            pattern: Key pattern to match

        Returns:
            List of session IDs
        """
        redis_client = await self._get_redis()
        key_pattern = f"{self.prefix}session:{pattern}"

        keys = await redis_client.keys(key_pattern)
        # Extract session IDs from keys
        prefix_len = len(f"{self.prefix}session:")
        return [k[prefix_len:] for k in keys]

    async def clear_all_sessions(self) -> int:
        """Clear all active sessions from Redis.

        Returns:
            Number of sessions deleted
        """
        redis_client = await self._get_redis()
        key_pattern = f"{self.prefix}session:*"
        keys = await redis_client.keys(key_pattern)
        if keys:
            return await redis_client.delete(*keys)
        return 0

    async def is_connected(self) -> bool:
        """Check Redis connectivity."""
        try:
            redis_client = await self._get_redis()
            await redis_client.ping()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# Global instance
_session_manager: SessionManager | None = None


def get_session_manager(prefix: str = "mcp:") -> SessionManager:
    """Get or create global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(prefix=prefix)
    return _session_manager
