"""Local skills cache using Redis."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from cohezion.mcp.shared.session import get_session_manager


logger = logging.getLogger(__name__)

CACHE_PREFIX = "skills:cache:"
CACHE_TTL = 86400  # 24 hours
MAX_CACHE_SIZE = int(os.getenv("SKILLS_CACHE_SIZE", "1000"))


class SkillsCache:
    """Cache for skills.sh data."""

    def __init__(self, max_size: int = MAX_CACHE_SIZE):
        self.max_size = max_size
        self._session_manager = get_session_manager(prefix="skills:")

    def _key(self, skill_id: str) -> str:
        """Generate cache key."""
        return f"{CACHE_PREFIX}{skill_id.replace('/', ':')}"

    async def get(self, skill_id: str) -> dict[str, Any] | None:
        """Get skill from cache.

        Args:
            skill_id: Skill ID (owner/repo format)

        Returns:
            Cached skill data or None
        """
        try:
            key = self._key(skill_id)
            data = await self._session_manager.get_session(key)

            if data:
                logger.debug("Cache hit: %s", skill_id.replace("\n", " "))
                return data.get("data")

            logger.debug("Cache miss: %s", skill_id.replace("\n", " "))
            return None

        except Exception as _e:
            logger.exception("Error getting from cache")
            return None

    async def set(self, skill_id: str, data: dict[str, Any]) -> bool:
        """Cache skill data.

        Args:
            skill_id: Skill ID
            data: Skill data to cache

        Returns:
            True if cached successfully
        """
        try:
            key = self._key(skill_id)

            cache_entry = {
                "id": skill_id,
                "data": data,
                "cached_at": datetime.utcnow().isoformat(),
            }

            # Store in Redis with TTL
            await self._session_manager.create_session(key, cache_entry)

            # Set TTL
            from redis.asyncio import from_url

            redis_client = from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
            await redis_client.expire(f"skills:session:{key}", CACHE_TTL)
            await redis_client.close()

            logger.debug("Cached: %s", skill_id.replace("\n", " "))
            return True

        except Exception as e:
            logger.exception(f"Error setting cache: {e}")
            return False

    async def get_content(self, skill_id: str) -> str | None:
        """Get cached skill content.

        Args:
            skill_id: Skill ID

        Returns:
            Cached content or None
        """
        try:
            key = f"{CACHE_PREFIX}content:{skill_id.replace('/', ':')}"
            data = await self._session_manager.get_session(key)

            if data:
                return data.get("content")

            return None

        except Exception as e:
            logger.exception(f"Error getting content from cache: {e}")
            return None

    async def set_content(self, skill_id: str, content: str) -> bool:
        """Cache skill content.

        Args:
            skill_id: Skill ID
            content: Skill file content

        Returns:
            True if cached successfully
        """
        try:
            key = f"{CACHE_PREFIX}content:{skill_id.replace('/', ':')}"

            cache_entry = {
                "id": skill_id,
                "content": content,
                "cached_at": datetime.utcnow().isoformat(),
            }

            await self._session_manager.create_session(key, cache_entry)

            # Set TTL
            from redis.asyncio import from_url

            redis_client = from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
            await redis_client.expire(f"skills:session:{key}", CACHE_TTL)
            await redis_client.close()

            return True

        except Exception as e:
            logger.exception(f"Error setting content cache: {e}")
            return False

    async def invalidate(self, skill_id: str) -> bool:
        """Invalidate cached skill.

        Args:
            skill_id: Skill ID

        Returns:
            True if invalidated
        """
        try:
            key = self._key(skill_id)
            content_key = f"{CACHE_PREFIX}content:{skill_id.replace('/', ':')}"

            await self._session_manager.delete_session(key)
            await self._session_manager.delete_session(content_key)

            logger.debug(f"Invalidated cache: {skill_id}")
            return True

        except Exception as e:
            logger.exception(f"Error invalidating cache: {e}")
            return False

    async def list_cached(self) -> list[dict[str, Any]]:
        """List all cached skills.

        Returns:
            List of cached skill summaries
        """
        try:
            sessions = await self._session_manager.list_sessions(f"{CACHE_PREFIX}*")

            cached = []
            for session_id in sessions:
                if not session_id.startswith("content:"):
                    data = await self._session_manager.get_session(session_id)
                    if data:
                        cached.append(
                            {
                                "id": data.get("id"),
                                "cached_at": data.get("cached_at"),
                            }
                        )

            return cached

        except Exception as e:
            logger.exception(f"Error listing cached skills: {e}")
            return []

    async def clear(self) -> bool:
        """Clear all cached skills.

        Returns:
            True if cleared
        """
        try:
            sessions = await self._session_manager.list_sessions(f"{CACHE_PREFIX}*")

            for session_id in sessions:
                await self._session_manager.delete_session(session_id)

            logger.info(f"Cleared {len(sessions)} cached skills")
            return True

        except Exception as e:
            logger.exception(f"Error clearing cache: {e}")
            return False

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        try:
            cached = await self.list_cached()

            return {
                "total_cached": len(cached),
                "max_size": self.max_size,
                "ttl_hours": CACHE_TTL / 3600,
                "cache_full": len(cached) >= self.max_size,
            }

        except Exception as e:
            logger.exception(f"Error getting cache stats: {e}")
            return {
                "total_cached": 0,
                "max_size": self.max_size,
                "ttl_hours": CACHE_TTL / 3600,
                "cache_full": False,
            }
