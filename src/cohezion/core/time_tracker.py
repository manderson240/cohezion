#!/usr/bin/env python3
"""
COHEZION Time & Date Utility
Systematic date/time capture for accurate code velocity tracking and git safe handoffs.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class COHEZIONTimeTracker:
    """Systematic time and date tracking for development velocity metrics"""

    def __init__(self, project_root: str = "/home/mike-anderson/dev/cohezion"):
        self.project_root = Path(project_root)
        self.time_data_file = self.project_root / ".cohezion_time_data.json"
        self.session_start = datetime.now(UTC)

        # Load existing time data
        self.time_data = self._load_time_data()

        logger.info("⏰ COHEZION Time Tracker initialized")

    def _load_time_data(self) -> dict[str, Any]:
        """Load existing time tracking data"""
        if self.time_data_file.exists():
            try:
                with open(self.time_data_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ Could not load time data: {e}")

        return {
            "project_start_date": "2026-01-15",  # Project start date
            "current_session_start": self.session_start.isoformat(),
            "total_sessions": 0,
            "session_history": [],
        }

    def _save_time_data(self):
        """Save time tracking data"""
        try:
            with open(self.time_data_file, "w") as f:
                json.dump(self.time_data, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save time data: {e}")

    def get_current_timestamp(self) -> dict[str, str]:
        """Get structured timestamp for current moment"""
        now = datetime.now(UTC)
        return {
            "iso_utc": now.isoformat(),
            "readable": now.strftime("%B %d, %Y at %I:%M %p UTC"),
            "timestamp": now.timestamp(),
            "session_id": self._generate_session_id(),
            "git_friendly": now.strftime("%Y-%m-%d %H:%M:%S"),
            "velocity_friendly": now.strftime("%Y%m%d_%H%M%S"),
        }

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        import hashlib
        import time

        unique_str = f"{self.session_start.timestamp()}_{time.time()}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:8]

    def update_session_metrics(self, session_data: dict[str, Any]):
        """Update current session metrics"""
        session_end = datetime.now(UTC)
        session_duration = (session_end - self.session_start).total_seconds()

        session_record = {
            "session_id": session_data.get("session_id", self._generate_session_id()),
            "start_time": self.session_start.isoformat(),
            "end_time": session_end.isoformat(),
            "duration_seconds": session_duration,
            "files_modified": session_data.get("files_modified", 0),
            "lines_added": session_data.get("lines_added", 0),
            "lines_removed": session_data.get("lines_removed", 0),
            "commits_made": session_data.get("commits_made", 0),
            "major_features": session_data.get("major_features", []),
            "tasks_completed": session_data.get("tasks_completed", []),
            "performance_improvements": session_data.get(
                "performance_improvements", []
            ),
        }

        # Add to session history
        self.time_data["session_history"].append(session_record)
        self.time_data["total_sessions"] += 1
        self.time_data["last_session"] = session_record

        # Reset for next session
        self.session_start = datetime.now(UTC)

        # Save updated data
        self._save_time_data()

        logger.info(
            f"📊 Session completed: {session_duration:.1f}s, {session_data.get('files_modified', 0)} files modified"
        )

        return session_record

    def get_development_velocity(self, days_back: int = 7) -> dict[str, Any]:
        """Calculate development velocity metrics"""
        if not self.time_data.get("session_history"):
            return {"error": "No session history available"}

        cutoff_date = datetime.now(UTC).timestamp() - (days_back * 24 * 60 * 60)

        # Filter recent sessions
        recent_sessions = [
            session
            for session in self.time_data["session_history"]
            if datetime.fromisoformat(session["start_time"]).timestamp() > cutoff_date
        ]

        if not recent_sessions:
            return {"error": f"No sessions in last {days_back} days"}

        # Calculate velocity metrics
        total_duration = sum(session["duration_seconds"] for session in recent_sessions)
        total_files = sum(session["files_modified"] for session in recent_sessions)
        total_lines = sum(
            session["lines_added"] + session.get("lines_removed", 0)
            for session in recent_sessions
        )
        total_commits = sum(session["commits_made"] for session in recent_sessions)

        avg_session_duration = (
            total_duration / len(recent_sessions) if recent_sessions else 0
        )

        return {
            "period_days": days_back,
            "total_sessions": len(recent_sessions),
            "total_duration_hours": total_duration / 3600,
            "avg_session_duration_minutes": avg_session_duration / 60,
            "files_modified_per_day": round(total_files / days_back, 1),
            "lines_added_per_day": round(total_lines / days_back, 1),
            "commits_per_day": round(total_commits / days_back, 1),
            "velocity_score": self._calculate_velocity_score(
                recent_sessions, days_back
            ),
            "most_productive_day": self._find_most_productive_day(recent_sessions),
        }

    def _calculate_velocity_score(self, sessions: list, days_back: int) -> float:
        """Calculate overall development velocity score"""
        if not sessions:
            return 0.0

        # Factors: consistency (40%), productivity (30%), impact (30%)
        consistency_score = min(len(sessions) / days_back, 1.0) * 40

        total_lines = sum(
            s["lines_added"] + s.get("lines_removed", 0) for s in sessions
        )
        productivity_score = (
            min(total_lines / (days_back * 100), 1.0) * 30
        )  # 100 lines/day baseline

        major_features = sum(len(s.get("major_features", [])) for s in sessions)
        impact_score = (
            min(major_features / (days_back * 2), 1.0) * 30
        )  # 2 major features/week baseline

        return consistency_score + productivity_score + impact_score

    def _find_most_productive_day(self, sessions: list) -> dict[str, Any] | None:
        """Find most productive day from session history"""
        if not sessions:
            return None

        day_productivity = {}
        for session in sessions:
            session_date = datetime.fromisoformat(session["start_time"]).date()
            day_key = session_date.isoformat()

            if day_key not in day_productivity:
                day_productivity[day_key] = {
                    "files_modified": 0,
                    "lines_added": 0,
                    "session_count": 0,
                }

            day_productivity[day_key]["files_modified"] += session["files_modified"]
            day_productivity[day_key]["lines_added"] += session[
                "lines_added"
            ] + session.get("lines_removed", 0)
            day_productivity[day_key]["session_count"] += 1

        # Find most productive day
        most_productive = max(
            day_productivity.items(), key=lambda x: x[1]["lines_added"]
        )

        return {
            "date": most_productive[0],
            "files_modified": most_productive[1]["files_modified"],
            "lines_added": most_productive[1]["lines_added"],
            "session_count": most_productive[1]["session_count"],
        }

    def get_git_safe_handoff_timestamp(self) -> dict[str, str]:
        """Generate timestamp for git safe handoff"""
        now = datetime.now(UTC)
        return {
            "commit_message_prefix": now.strftime("[%Y-%m-%d %H:%M]"),
            "branch_name": now.strftime("work/session-%Y%m%d-%H%M"),
            "tag_format": now.strftime("v%Y.%m.%d-session"),
            "full_context": now.strftime(
                "COHEZION Safe Handoff - %B %d, %Y %I:%M %p UTC\n\nSession Duration: %.1f hours\n\nVelocity: %.1f lines/day\n\nMajor Features: %s"
            ),
            "summary": now.strftime("%Y%m%d_%H%M%S_safe_handoff"),
        }


# Global time tracker instance
_time_tracker = None


def get_time_tracker() -> COHEZIONTimeTracker:
    """Get or create global time tracker instance"""
    global _time_tracker
    if _time_tracker is None:
        _time_tracker = COHEZIONTimeTracker()
    return _time_tracker


def get_current_timestamp() -> dict[str, str]:
    """Get current timestamp for use in templates and configs"""
    tracker = get_time_tracker()
    return tracker.get_current_timestamp()


def format_timestamp_for_config() -> str:
    """Get timestamp formatted for configuration files"""
    tracker = get_time_tracker()
    timestamp_data = tracker.get_current_timestamp()
    return timestamp_data["iso_utc"]


def format_git_safe_handoff() -> dict[str, str]:
    """Get formatted data for git safe handoff"""
    tracker = get_time_tracker()
    return tracker.get_git_safe_handoff_timestamp()
