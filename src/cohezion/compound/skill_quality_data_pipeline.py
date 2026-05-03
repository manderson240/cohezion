"""Skill quality data pipeline — persists quality reports across sessions as JSONL.

Provides:
- SkillQualityDataPipeline: save/load/trend operations for SkillQualityReport objects.
- JSONL storage in data/skill_quality/<skill_name>.jsonl for append-only durability.
- Trend analysis: compute deltas over the last N sessions.

Follows the autoresearch JSON state file pattern (one JSON object per line).
"""

from __future__ import annotations

import json
import logging
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cohezion.compound.skill_quality_scorer import SkillQualityReport

logger = logging.getLogger(__name__)


class SkillQualityDataPipeline:
    """Append-only JSONL pipeline for skill quality reports.

    Each skill gets its own ``<skill_name>.jsonl`` file under the configured
    storage directory.  Records are written atomically (line-by-line) so a
    crash never corrupts prior history.

    Usage:
        pipeline = SkillQualityDataPipeline()
        pipeline.save_report("my-skill", report)
        history = pipeline.load_history("my-skill")
        trend = pipeline.get_trend("my-skill", n_sessions=5)
    """

    def __init__(self, storage_dir: Path | None = None) -> None:
        self._storage_dir = storage_dir or Path("data/skill_quality")
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_report(self, skill_name: str, report: SkillQualityReport) -> Path:
        """Persist a quality report for *skill_name*.

        The record is enriched with a UTC timestamp and the report's
        ``to_dict()`` serialization, then appended as one JSON line.

        Args:
            skill_name: canonical skill identifier (used as filename stem)
            report: the ``SkillQualityReport`` to archive

        Returns:
            Path to the JSONL file that was written.
        """
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "report": report.to_dict(),
        }
        file_path = self._file_for(skill_name)
        with file_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, separators=(",", ":")) + "\n")
        logger.debug("Saved quality report for %s (%s)", skill_name, file_path)
        return file_path

    def load_history(self, skill_name: str) -> list[dict[str, Any]]:
        """Load all archived records for *skill_name* in chronological order.

        Args:
            skill_name: skill identifier

        Returns:
            List of dicts, each with ``timestamp`` and ``report`` keys.
            Returns an empty list if the skill has never been recorded.
        """
        file_path = self._file_for(skill_name)
        if not file_path.exists():
            return []

        records: list[dict[str, Any]] = []
        with file_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed JSONL line in %s", file_path)
                    continue
        return records

    def get_trend(self, skill_name: str, n_sessions: int = 5) -> dict[str, Any]:
        """Compute trend statistics over the last *n_sessions* records.

        Args:
            skill_name: skill identifier
            n_sessions: number of most-recent sessions to include

        Returns:
            Dict with:
            - ``skill_name``
            - ``n_sessions`` (actual count, may be < requested)
            - ``scores`` — list of overall scores (oldest → newest)
            - ``delta`` — change from first to last in the window
            - ``avg_score`` — arithmetic mean
            - ``max_score`` — best score in window
            - ``min_score`` — worst score in window
            - ``trend_direction`` — ``"improving" | "stable" | "declining"``
            - ``timestamps`` — ISO timestamps for the window
        """
        history = self.load_history(skill_name)
        if not history:
            return {
                "skill_name": skill_name,
                "n_sessions": 0,
                "scores": [],
                "delta": 0.0,
                "avg_score": 0.0,
                "max_score": 0.0,
                "min_score": 0.0,
                "trend_direction": "stable",
                "timestamps": [],
            }

        window = deque(history, maxlen=n_sessions)
        scores = [r["report"]["overall_score"] for r in window]
        timestamps = [r["timestamp"] for r in window]

        delta = scores[-1] - scores[0] if len(scores) > 1 else 0.0
        avg_score = sum(scores) / len(scores) if scores else 0.0
        max_score = max(scores) if scores else 0.0
        min_score = min(scores) if scores else 0.0

        if len(scores) < 2:
            trend_direction = "stable"
        elif delta > 0.01:
            trend_direction = "improving"
        elif delta < -0.01:
            trend_direction = "declining"
        else:
            trend_direction = "stable"

        return {
            "skill_name": skill_name,
            "n_sessions": len(scores),
            "scores": scores,
            "delta": round(delta, 4),
            "avg_score": round(avg_score, 4),
            "max_score": round(max_score, 4),
            "min_score": round(min_score, 4),
            "trend_direction": trend_direction,
            "timestamps": timestamps,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _file_for(self, skill_name: str) -> Path:
        """Return the JSONL path for a given skill name."""
        safe_name = skill_name.replace("/", "_").replace("\\", "_")
        return self._storage_dir / f"{safe_name}.jsonl"
