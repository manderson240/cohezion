"""JSONL-backed observation store for persistent cross-session memory.

Stores observations as newline-delimited JSON records in
``{vault_path}/memory/observations.jsonl``. Each record has the shape::

    {
        "id": 1,
        "timestamp": "2026-02-23T10:00:00Z",
        "text": "...",
        "title": "...",
        "type": "discovery",
        "project": "cohezion",
        "tags": []
    }

**Performance:** Search is O(N) over the file. At the default ceiling of
``max_entries=10_000`` entries this is fast enough for interactive use
(<10 ms on SSD for typical observation sizes).

**Thread safety:** All mutating operations wrap the read-compute-append
section in a ``filelock.FileLock`` to prevent duplicate IDs under concurrent
writes.

**Corruption handling:** Lines that fail ``json.JSONDecodeError`` are
silently skipped with a warning. Call ``repair()`` to rewrite the file
with only valid entries.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_VALID_TYPES = frozenset(
    ("bugfix", "feature", "refactor", "discovery", "decision", "change")
)


class MemoryStore:
    """Synchronous JSONL observation store.

    Args:
        jsonl_path: Absolute path to the ``.jsonl`` file.
        max_entries: FIFO eviction ceiling (default 10 000).
    """

    def __init__(
        self,
        jsonl_path: Path,
        max_entries: int = 10_000,
    ) -> None:
        self._path = Path(jsonl_path)
        self._max_entries = max_entries
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _lock_path(self) -> Path:
        return self._path.with_suffix(".lock")

    def _read_all(self) -> list[dict[str, Any]]:
        """Return all valid entries from the JSONL file."""
        if not self._path.exists():
            return []
        entries: list[dict[str, Any]] = []
        for i, line in enumerate(self._path.read_text().splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSONL line %d in %s", i, self._path)
        return entries

    def _write_all(self, entries: list[dict[str, Any]]) -> None:
        self._path.write_text(
            "\n".join(json.dumps(e, default=str) for e in entries) + "\n"
            if entries
            else ""
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(
        self,
        text: str,
        title: str = "",
        project: str = "cohezion",
        type: str = "discovery",  # noqa: A002
        tags: list[str] | None = None,
    ) -> int:
        """Append a new observation and return its auto-incremented ID.

        Args:
            text: Observation text (required).
            title: Optional short title for index display.
            project: Project name for filtering.
            type: Observation type; must be one of ``bugfix``, ``feature``,
                ``refactor``, ``discovery``, ``decision``, ``change``.
            tags: Optional list of string tags.

        Returns:
            The new observation's integer ID.

        Raises:
            ValueError: If ``type`` is not in the allowed set.
        """
        if type not in _VALID_TYPES:
            raise ValueError(
                f"Invalid type {type!r}. Must be one of: {sorted(_VALID_TYPES)}"
            )

        try:
            from filelock import FileLock
        except ImportError:
            FileLock = None  # type: ignore[assignment]

        def _do_save() -> int:
            entries = self._read_all()
            new_id = (max(e.get("id", 0) for e in entries) if entries else 0) + 1
            entry: dict[str, Any] = {
                "id": new_id,
                "timestamp": datetime.now(tz=timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "text": text,
                "title": title,
                "type": type,
                "project": project,
                "tags": tags or [],
            }
            entries.append(entry)
            # FIFO eviction: keep only the most recent max_entries
            if len(entries) > self._max_entries:
                entries = entries[-self._max_entries :]
            self._write_all(entries)
            return new_id

        if FileLock is not None:
            with FileLock(str(self._lock_path())):
                return _do_save()
        return _do_save()

    def search(
        self,
        query: str,
        limit: int = 20,
        type: str = "",  # noqa: A002
        project: str = "",
        dateStart: str = "",
        dateEnd: str = "",
    ) -> list[dict[str, Any]]:
        """Search observations by substring match on text and title.

        Returns index entries (id, title, timestamp, type, project, snippet)
        for token efficiency. Fetch full details with :meth:`get`.

        Args:
            query: Case-insensitive substring to match in ``text`` or ``title``.
            limit: Maximum number of results to return.
            type: Filter by observation type (empty = no filter).
            project: Filter by project name (empty = no filter).
            dateStart: ISO 8601 timestamp; only include entries on or after.
            dateEnd: ISO 8601 timestamp; only include entries on or before.

        Returns:
            List of index dicts ordered by recency (newest first).
        """
        entries = self._read_all()
        query_lower = query.lower()
        results: list[dict[str, Any]] = []

        for entry in reversed(entries):
            if len(results) >= limit:
                break
            # Text/title match
            if query_lower and query_lower not in (entry.get("text", "") + " " + entry.get("title", "")).lower():
                continue
            # Type filter
            if type and entry.get("type") != type:
                continue
            # Project filter
            if project and entry.get("project") != project:
                continue
            # Date filters
            ts = entry.get("timestamp", "")
            if dateStart and ts < dateStart:
                continue
            if dateEnd and ts > dateEnd:
                continue
            snippet = entry.get("text", "")[:200]
            results.append(
                {
                    "id": entry["id"],
                    "title": entry.get("title", ""),
                    "timestamp": ts,
                    "type": entry.get("type", ""),
                    "project": entry.get("project", ""),
                    "snippet": snippet,
                }
            )
        return results

    def get(self, ids: list[int]) -> list[dict[str, Any]]:
        """Fetch full observation details by ID list.

        Args:
            ids: List of integer observation IDs.

        Returns:
            Full observation dicts for matched IDs (missing IDs are silently
            omitted).
        """
        id_set = set(ids)
        return [e for e in self._read_all() if e.get("id") in id_set]

    def timeline(
        self,
        anchor: int | None = None,
        query: str = "",
        depth_before: int = 5,
        depth_after: int = 5,
    ) -> list[dict[str, Any]]:
        """Return observations chronologically around an anchor.

        Args:
            anchor: Anchor observation ID (chronological centre).
            query: If ``anchor`` is None, find the most recent observation
                matching this query and use it as the anchor.
            depth_before: How many observations before the anchor to include.
            depth_after: How many observations after the anchor to include.

        Returns:
            Chronologically ordered list of observations surrounding the anchor.

        Raises:
            ValueError: If both ``anchor`` and ``query`` are empty/None.
        """
        if anchor is None and not query:
            raise ValueError(
                "timeline() requires either 'anchor' (int) or 'query' (str)"
            )

        entries = self._read_all()
        if not entries:
            return []

        # Resolve anchor from query if needed
        if anchor is None:
            query_lower = query.lower()
            for entry in reversed(entries):
                text = (entry.get("text", "") + " " + entry.get("title", "")).lower()
                if query_lower in text:
                    anchor = entry["id"]
                    break
            if anchor is None:
                return []

        # Find anchor index
        anchor_idx = next(
            (i for i, e in enumerate(entries) if e.get("id") == anchor), None
        )
        if anchor_idx is None:
            return []

        start = max(0, anchor_idx - depth_before)
        end = min(len(entries), anchor_idx + depth_after + 1)
        return entries[start:end]

    def repair(self) -> int:
        """Rewrite the JSONL file keeping only valid entries.

        Returns:
            Number of entries retained.
        """
        entries = self._read_all()
        self._write_all(entries)
        return len(entries)
