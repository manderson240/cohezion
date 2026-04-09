"""Karpathy ulogme integration - Time tracking to SurrealDB bridge.

Connects ulogme activity logs to the Cohezion unified memory system.
Source: https://github.com/karpathy/ulogme
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from cohezion.core.persistence.surreal_client import PhysicsState, SurrealClient, UniverseNode


logger = logging.getLogger(__name__)


@dataclass
class ActivityEntry:
    """Single ulogme activity record."""

    timestamp: datetime
    window_title: str
    keystrokes: int
    duration_sec: int
    app_name: str | None = None
    app_category: str | None = None


@dataclass
class FocusSession:
    """Aggregated focus session from ulogme data."""

    start_time: datetime
    end_time: datetime
    total_keystrokes: int
    primary_window: str
    app_category: str
    coherence: float  # Focus score derived from keystroke velocity


class UlogmeBridge:
    """Bridge ulogme time tracking to SurrealDB universe graph.

    Reads ulogme JSON logs and stores as activity:ulogme nodes in SurrealDB
    with 12D physics coordinates for temporal analysis.

    Attributes:
        surreal: SurrealDB client instance
        log_dir: Directory containing ulogme logs

    Example:
        >>> bridge = UlogmeBridge()
        >>> await bridge.sync_day("2024-01-15")
        Synced 45 activity entries from 2024-01-15
    """

    def __init__(
        self,
        surreal: SurrealClient | None = None,
        log_dir: str = "~/.local/share/ulogme/logs",
    ):
        self.surreal = surreal or SurrealClient()
        self.log_dir = Path(log_dir).expanduser()
        self._connected = False

    async def _ensure_connection(self) -> None:
        """Lazy connection to SurrealDB."""
        if not self._connected:
            await self.surreal.connect()
            self._connected = True

    def parse_log_file(self, log_path: Path) -> list[ActivityEntry]:
        """Parse ulogme log file to activity entries.

        ulogme logs are JSON lines with: [timestamp, window_title, keystrokes]
        """
        entries = []

        if not log_path.exists():
            logger.warning(f"Log file not found: {log_path}")
            return entries

        try:
            with open(log_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        # ulogme format: [unix_timestamp, window_title, keystrokes]
                        if len(data) >= 3:
                            timestamp = datetime.fromtimestamp(data[0])
                            entry = ActivityEntry(
                                timestamp=timestamp,
                                window_title=data[1],
                                keystrokes=data[2] if len(data) > 2 else 0,
                                duration_sec=2,  # ulogme samples every 2s
                                app_name=self._extract_app_name(data[1]),
                                app_category=self._categorize_window(data[1]),
                            )
                            entries.append(entry)
                    except (json.JSONDecodeError, IndexError, ValueError) as e:
                        logger.debug(f"Skipping malformed line: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error reading log file {log_path}: {e}")

        return entries

    def _extract_app_name(self, window_title: str) -> str | None:
        """Extract application name from window title (heuristic)."""
        # Common patterns: "filename.py - app", "app - document", etc.
        if " - " in window_title:
            parts = window_title.split(" - ")
            return parts[-1].strip()  # Usually app name is last
        return None

    def _categorize_window(self, window_title: str) -> str:
        """Categorize window title into activity type."""
        window_lower = window_title.lower()

        # Coding
        if any(
            kw in window_lower
            for kw in [
                ".py",
                ".js",
                ".rs",
                ".go",
                ".cpp",
                ".c",
                ".h",
                "code",
                "github",
                "git",
                "terminal",
                "vim",
                "nvim",
                "vscode",
                "pycharm",
                "intellij",
                "sublime",
            ]
        ):
            return "coding"

        # Communication
        if any(
            kw in window_lower
            for kw in [
                "slack",
                "discord",
                "teams",
                "zoom",
                "meet",
                "telegram",
                "whatsapp",
                "signal",
                "message",
            ]
        ):
            return "communication"

        # Documentation/Writing
        if any(
            kw in window_lower
            for kw in [
                ".md",
                ".txt",
                ".doc",
                ".pdf",
                "obsidian",
                "notion",
                "docs",
                "readme",
                "documentation",
            ]
        ):
            return "documentation"

        # Browsing/Research
        if any(
            kw in window_lower
            for kw in [
                "chrome",
                "firefox",
                "safari",
                "browser",
                "stackoverflow",
                "github.com",
                "reddit",
                "search",
                "google",
            ]
        ):
            return "research"

        # Default
        return "other"

    def aggregate_sessions(
        self, entries: list[ActivityEntry], session_gap_minutes: int = 5
    ) -> list[FocusSession]:
        """Aggregate raw entries into focus sessions.

        A new session starts after 5 minutes of inactivity (configurable).
        Coherence is calculated from keystroke velocity.
        """
        if not entries:
            return []

        sessions = []
        current_session: list[ActivityEntry] = [entries[0]]

        for entry in entries[1:]:
            last_entry = current_session[-1]
            gap = (entry.timestamp - last_entry.timestamp).total_seconds() / 60

            if gap > session_gap_minutes:
                # New session
                sessions.append(self._create_session(current_session))
                current_session = [entry]
            else:
                current_session.append(entry)

        # Don't forget last session
        if current_session:
            sessions.append(self._create_session(current_session))

        return sessions

    def _create_session(self, entries: list[ActivityEntry]) -> FocusSession:
        """Create a FocusSession from aggregated entries."""
        start_time = entries[0].timestamp
        end_time = entries[-1].timestamp
        total_keystrokes = sum(e.keystrokes for e in entries)

        # Find primary window (by time spent)
        window_times: dict[str, float] = {}
        for e in entries:
            window_times[e.window_title] = window_times.get(e.window_title, 0) + e.duration_sec
        primary_window = max(window_times.items(), key=lambda x: x[1])[0]

        # Calculate coherence (focus score)
        duration_minutes = (end_time - start_time).total_seconds() / 60
        if duration_minutes > 0:
            keystroke_rate = total_keystrokes / duration_minutes
            # Normalize: 0-300 kpm = 0.0-1.0
            coherence = min(1.0, keystroke_rate / 300.0)
        else:
            coherence = 0.5

        return FocusSession(
            start_time=start_time,
            end_time=end_time,
            total_keystrokes=total_keystrokes,
            primary_window=primary_window,
            app_category=entries[0].app_category or "other",
            coherence=coherence,
        )

    async def store_session(self, session: FocusSession, tags: list[str] | None = None) -> str:
        """Store a focus session in SurrealDB.

        Creates activity:ulogme node with 12D physics coordinates.
        """
        await self._ensure_connection()

        # Build physics state
        physics = PhysicsState(
            coherence=session.coherence,
            energy=session.total_keystrokes / 1000.0,  # Normalize
            time=session.start_time.timestamp(),
        )

        # Create universe node
        content = f"""Focus Session: {session.app_category}
Window: {session.primary_window}
Duration: {(session.end_time - session.start_time).total_seconds() / 60:.1f} min
Keystrokes: {session.total_keystrokes}
Coherence: {session.coherence:.2f}"""

        node = UniverseNode(
            content=content,
            physics_state=physics,
            metadata={
                "type": "focus_session",
                "source": "ulogme",
                "category": session.app_category,
                "window_title": session.primary_window,
                "keystrokes": session.total_keystrokes,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat(),
                "tags": tags or [],
            },
        )

        node_id = await self.surreal.store_node(node)
        logger.debug(f"Stored activity: {node_id}")
        return node_id

    async def sync_day(self, date: str | datetime) -> dict[str, Any]:
        """Sync all ulogme data for a specific date.

        Args:
            date: Date string "YYYY-MM-DD" or datetime

        Returns:
            Summary dict with counts and metrics
        """
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d")

        log_file = self.log_dir / f"{date.strftime('%Y-%m-%d')}.log"

        logger.info(f"Syncing ulogme data from {log_file}")

        entries = self.parse_log_file(log_file)
        if not entries:
            return {"entries": 0, "sessions": 0, "stored": []}

        sessions = self.aggregate_sessions(entries)

        stored_ids = []
        for session in sessions:
            node_id = await self.store_session(session, tags=["ulogme", date.strftime("%Y-%m-%d")])
            stored_ids.append(node_id)

        # Calculate daily stats
        total_time = sum((s.end_time - s.start_time).total_seconds() / 3600 for s in sessions)
        total_keystrokes = sum(s.total_keystrokes for s in sessions)
        avg_coherence = sum(s.coherence for s in sessions) / len(sessions) if sessions else 0

        summary = {
            "date": date.strftime("%Y-%m-%d"),
            "entries": len(entries),
            "sessions": len(sessions),
            "total_hours": round(total_time, 2),
            "total_keystrokes": total_keystrokes,
            "avg_coherence": round(avg_coherence, 3),
            "category_breakdown": self._category_breakdown(sessions),
            "stored": stored_ids,
        }

        logger.info(f"Synced {len(sessions)} sessions from {date.strftime('%Y-%m-%d')}")
        return summary

    def _category_breakdown(self, sessions: list[FocusSession]) -> dict[str, float]:
        """Calculate time spent per category."""
        by_category: dict[str, float] = {}
        for s in sessions:
            duration = (s.end_time - s.start_time).total_seconds() / 3600
            by_category[s.app_category] = by_category.get(s.app_category, 0) + duration
        return {k: round(v, 2) for k, v in by_category.items()}

    async def sync_range(self, start_date: datetime, end_date: datetime) -> list[dict[str, Any]]:
        """Sync ulogme data for a date range."""
        results = []
        current = start_date

        while current <= end_date:
            result = await self.sync_day(current)
            results.append(result)
            current += timedelta(days=1)

        return results

    async def query_focus_time(self, category: str | None = None, days: int = 7) -> dict[str, Any]:
        """Query aggregated focus time from SurrealDB.

        Args:
            category: Filter by app category (e.g., "coding")
            days: Number of days to look back

        Returns:
            Aggregated metrics
        """
        await self._ensure_connection()

        # Build SurrealQL query
        query = """
        SELECT 
            metadata.category as category,
            math::sum(metadata.keystrokes) as total_keystrokes,
            count() as session_count,
            math::mean(physics.coherence) as avg_coherence
        FROM activity
        WHERE metadata.source = 'ulogme'
        AND created > $since
        """

        if category:
            query += " AND metadata.category = $category"

        query += " GROUP BY metadata.category"

        since = (datetime.now() - timedelta(days=days)).isoformat()

        result = await self.surreal.query(query, {"since": since, "category": category})
        return result[0]["result"] if result else {}
