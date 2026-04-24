"""Metrics persistence -- snapshot/restore CompoundMetricsCollector state."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

_METRICS_DIR = Path("data/compound/metrics")


class MetricsPersistence:
    """Snapshot and restore CompoundMetricsCollector state across sessions.

    Parameters
    ----------
    metrics_dir : Path | None
        Override directory for metric files.
    """

    def __init__(self, metrics_dir: Path | None = None) -> None:
        self._metrics_dir = metrics_dir or _METRICS_DIR

    def save_snapshot(self, collector: Any) -> str:
        """Serialize collector state to a timestamped JSON file.

        Parameters
        ----------
        collector : CompoundMetricsCollector
            The collector whose state to persist.

        Returns
        -------
        str
            Path to the written snapshot file.
        """
        self._metrics_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        path = self._metrics_dir / f"metrics_snapshot_{ts}.json"

        snapshot = collector.to_snapshot()
        snapshot["saved_at"] = time.time()

        try:
            path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
            logger.info("Saved metrics snapshot to %s", path)
        except Exception:
            logger.exception("Failed to save metrics snapshot")
            return ""

        return str(path)

    def load_latest_snapshot(self) -> dict[str, Any] | None:
        """Load the most recent metrics snapshot.

        Returns
        -------
        dict[str, Any] | None
            Snapshot data, or None if no snapshots exist.
        """
        if not self._metrics_dir.exists():
            return None

        snapshots = sorted(
            self._metrics_dir.glob("metrics_snapshot_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not snapshots:
            return None

        try:
            data = json.loads(snapshots[0].read_text(encoding="utf-8"))
            logger.info("Loaded metrics snapshot from %s", snapshots[0])
            return dict(data) if isinstance(data, dict) else None
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to load metrics snapshot")
            return None

    def save_compound_scores(self, scores: list[dict[str, Any]]) -> int:
        """Append compound score entries to the score history JSONL.

        Parameters
        ----------
        scores : list[dict[str, Any]]
            Score entries with skill_name, compound_score_delta, timestamp.

        Returns
        -------
        int
            Number of entries written.
        """
        self._metrics_dir.mkdir(parents=True, exist_ok=True)
        path = self._metrics_dir / "compound_scores.jsonl"

        count = 0
        try:
            with path.open("a", encoding="utf-8") as f:
                for score in scores:
                    f.write(json.dumps(score) + "\n")
                    count += 1
        except Exception:
            logger.exception("Failed to save compound scores")

        return count

    def load_compound_score_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Load compound score history from JSONL.

        Parameters
        ----------
        limit : int
            Maximum entries to return.

        Returns
        -------
        list[dict[str, Any]]
            Score entries, most recent first.
        """
        path = self._metrics_dir / "compound_scores.jsonl"
        if not path.exists():
            return []

        entries: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").strip().splitlines():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        # Most recent first
        entries.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
        return entries[:limit]
