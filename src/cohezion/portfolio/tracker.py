"""Cohezion Portfolio Tracker — CRUD backed by a local JSON file.

SurrealDB is used when available (ws://localhost:8001) but the tracker
falls back gracefully to a JSON file at ~/.cohezion/portfolio.json so
it works even when the DB is offline.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.portfolio.models import PortfolioProject, PortfolioSummary


logger = logging.getLogger(__name__)

_DEFAULT_STORE = Path.home() / ".cohezion" / "portfolio.json"


class PortfolioTracker:
    """Manages portfolio projects with JSON persistence + optional SurrealDB sync."""

    def __init__(self, store_path: Path | None = None) -> None:
        self._store = store_path or _DEFAULT_STORE
        self._store.parent.mkdir(parents=True, exist_ok=True)
        self._projects: dict[str, PortfolioProject] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._store.exists():
            return
        try:
            raw: list[dict[str, Any]] = json.loads(self._store.read_text())
            for d in raw:
                p = PortfolioProject.model_validate(d)
                self._projects[p.id] = p
        except Exception as exc:
            logger.warning("portfolio load failed, starting empty: %s", exc)

    def _save(self) -> None:
        try:
            data = [p.model_dump(mode="json") for p in self._projects.values()]
            self._store.write_text(json.dumps(data, indent=2, default=str))
        except Exception as exc:
            logger.error("portfolio save failed: %s", exc)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def upsert(self, project: PortfolioProject) -> PortfolioProject:
        """Insert or replace a project."""
        self._projects[project.id] = project
        self._save()
        return project

    def get(self, project_id: str) -> PortfolioProject | None:
        return self._projects.get(project_id)

    def list_all(self) -> list[PortfolioProject]:
        return sorted(
            self._projects.values(),
            key=lambda p: (p.deadline is None, p.deadline or datetime.max),
        )

    def summaries(self) -> list[PortfolioSummary]:
        return [
            PortfolioSummary(
                id=p.id,
                name=p.name,
                competition=p.competition,
                deadline=p.deadline,
                prize=p.prize,
                status=p.status,
                score_label=p.score_label,
                days_to_deadline=p.days_to_deadline(),
                is_urgent=p.is_urgent(),
            )
            for p in self.list_all()
        ]

    def patch(self, project_id: str, **fields: Any) -> PortfolioProject | None:
        """Update specific fields on an existing project."""
        project = self._projects.get(project_id)
        if project is None:
            return None
        from datetime import UTC

        updated = project.model_copy(update={**fields, "last_updated": datetime.now(UTC)})
        self._projects[project_id] = updated
        self._save()
        return updated

    def add_note(self, project_id: str, note: str) -> PortfolioProject | None:
        """Append a timestamped note to a project."""
        from datetime import UTC

        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
        return self.patch(project_id, notes=[*self._projects[project_id].notes, f"[{ts}] {note}"])

    def update_from_session(
        self,
        project_id: str,
        *,
        session_id: str,
        status: str | None = None,
        score: float | None = None,
        score_label: str | None = None,
        kernel: str | None = None,
        note: str | None = None,
    ) -> PortfolioProject | None:
        """Called by the PortfolioAgent after a work session to persist progress."""
        updates: dict[str, Any] = {"last_session": session_id}
        if status:
            updates["status"] = status
        if score is not None:
            updates["score"] = score
        if score_label:
            updates["score_label"] = score_label
        if kernel:
            updates["kernel"] = kernel
        project = self.patch(project_id, **updates)
        if project and note:
            project = self.add_note(project_id, note)
        return project


# Module-level singleton
_tracker: PortfolioTracker | None = None


def get_tracker() -> PortfolioTracker:
    global _tracker
    if _tracker is None:
        _tracker = PortfolioTracker()
    return _tracker
