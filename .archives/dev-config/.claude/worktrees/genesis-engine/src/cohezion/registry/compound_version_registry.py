"""Compound Version Registry (Story 7.3, NFR-COMPOUND_VERSION_REGISTRY).

Logs all version changes with full diff context and linked epic/story IDs.
Every version bump is traceable to its originating epic and story.
Rollback context retrieved in <1 second.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class VersionEntry:
    """A single version change record with full traceability."""

    version: str
    previous_version: str
    release_date: float
    changelog_diff: str
    epic_ids: list[str]
    story_ids: list[str]
    pr_number: int | None = None
    auto_healed: bool = False

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "previous_version": self.previous_version,
            "release_date": self.release_date,
            "changelog_diff": self.changelog_diff,
            "epic_ids": self.epic_ids,
            "story_ids": self.story_ids,
            "pr_number": self.pr_number,
            "auto_healed": self.auto_healed,
        }


class CompoundVersionRegistry:
    """Version registry with semantic traceability and rollback support."""

    def __init__(self) -> None:
        self._entries: list[VersionEntry] = []

    def record_release(
        self,
        version: str,
        previous_version: str,
        changelog_diff: str,
        epic_ids: list[str],
        story_ids: list[str],
        pr_number: int | None = None,
        auto_healed: bool = False,
    ) -> VersionEntry:
        """Append a new version entry to the registry."""
        entry = VersionEntry(
            version=version,
            previous_version=previous_version,
            release_date=time.time(),
            changelog_diff=changelog_diff,
            epic_ids=epic_ids,
            story_ids=story_ids,
            pr_number=pr_number,
            auto_healed=auto_healed,
        )
        self._entries.append(entry)
        logger.info("Registered version %s (from %s) for epics %s", version, previous_version, epic_ids)
        return entry

    def query_by_epic(self, epic_id: str) -> list[VersionEntry]:
        """Return all version bumps linked to an epic, sorted by release date."""
        return sorted(
            [e for e in self._entries if epic_id in e.epic_ids],
            key=lambda e: e.release_date,
        )

    def get_rollback_context(self, version: str) -> VersionEntry | None:
        """Retrieve full rollback context for a version. <1 second guaranteed."""
        for entry in self._entries:
            if entry.version == version:
                return entry
        return None

    def latest_version(self) -> str | None:
        if not self._entries:
            return None
        return sorted(self._entries, key=lambda e: e.release_date)[-1].version

    def all_entries(self) -> list[dict]:
        return [e.to_dict() for e in self._entries]
