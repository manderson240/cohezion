"""Token cache persistence -- save/load SHA-256 prompt-response cache to JSONL."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

_CACHE_DIR = Path("data/compound/cache")


class CachePersistence:
    """Save and load the token cache to/from JSONL files.

    Parameters
    ----------
    cache_dir : Path | None
        Override directory for cache files.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir or _CACHE_DIR

    def save_cache(
        self,
        cache_dict: dict[str, str],
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Persist cache entries to JSONL. Returns number of entries written."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._cache_dir / "token_cache.jsonl"

        count = 0
        try:
            with path.open("w", encoding="utf-8") as f:
                for key, value in cache_dict.items():
                    entry = {
                        "key": key,
                        "value": value,
                        "timestamp": time.time(),
                        **(metadata or {}),
                    }
                    f.write(json.dumps(entry) + "\n")
                    count += 1
        except Exception:
            logger.exception("Failed to save cache")

        logger.info("Saved %d cache entries to %s", count, path)
        return count

    def load_cache(self, max_entries: int = 256) -> dict[str, str]:
        """Load most recent N entries from JSONL. Returns {key: value} dict."""
        path = self._cache_dir / "token_cache.jsonl"
        if not path.exists():
            return {}

        entries: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").strip().splitlines():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        # Sort by timestamp desc, take most recent
        entries.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
        entries = entries[:max_entries]

        return {e["key"]: e["value"] for e in entries if "key" in e and "value" in e}

    def get_cache_stats(self) -> dict[str, Any]:
        """Return cache file stats."""
        path = self._cache_dir / "token_cache.jsonl"
        if not path.exists():
            return {"entries": 0, "file_size_bytes": 0, "exists": False}

        lines = path.read_text(encoding="utf-8").strip().splitlines()
        stat = path.stat()
        return {
            "entries": len(lines),
            "file_size_bytes": stat.st_size,
            "last_modified": stat.st_mtime,
            "exists": True,
        }


class WarmCacheLoader:
    """Hydrate a TokenEfficientClient from persisted cache.

    Parameters
    ----------
    persistence : CachePersistence | None
        Override persistence backend.
    """

    def __init__(self, persistence: CachePersistence | None = None) -> None:
        self._persistence = persistence or CachePersistence()

    def warm_client(self, client: Any, max_entries: int = 256) -> int:
        """Load cache from disk into client._cache. Returns entries loaded."""
        cache = self._persistence.load_cache(max_entries)
        loaded = 0
        for key, value in cache.items():
            if len(client._cache) < client._cache_max_size:
                client._cache[key] = value
                loaded += 1
        logger.info("Warmed client cache with %d entries", loaded)
        return loaded
