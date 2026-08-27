"""Skill health tracking for the Cohezion compound engineering loop.

Tracks usage metrics per skill: invocation count, success rate, token usage,
quality scores, and computed health scores. Enables identification of stale
or unhealthy skills for pruning.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class SkillHealthRecord:
    """Health metrics for a single PRIME skill."""

    skill_name: str
    total_invocations: int = 0
    successful_invocations: int = 0
    failed_invocations: int = 0
    last_used: str = ""
    total_tokens_used: int = 0
    total_quality_score: float = 0.0
    created_date: str = ""

    @property
    def success_rate(self) -> float:
        if self.total_invocations == 0:
            return 0.0
        return self.successful_invocations / self.total_invocations

    @property
    def avg_tokens_per_use(self) -> float:
        if self.total_invocations == 0:
            return 0.0
        return self.total_tokens_used / self.total_invocations

    @property
    def avg_quality_score(self) -> float:
        if self.successful_invocations == 0:
            return 0.0
        return self.total_quality_score / self.successful_invocations

    @property
    def health_score(self) -> float:
        """Computed health: success_rate * recency_weight (0.0-1.0).

        Uses a 90-day half-life exponential decay for recency weighting.
        Skills unused for 90 days have their health score halved.
        """
        if self.total_invocations == 0:
            return 0.0
        recency = 1.0
        if self.last_used:
            days_ago = (datetime.now(UTC) - datetime.fromisoformat(self.last_used)).days
            recency = math.exp(-0.693 * days_ago / 90.0)  # 90-day half-life
        return self.success_rate * recency


class SkillHealthTracker:
    """Tracks and persists skill health metrics."""

    @staticmethod
    def default_storage_path() -> Path:
        """Absolute, process-independent default location for health records.

        The previous cwd-relative ``data/skill_health.json`` meant a daemon
        writing health from one directory and a ``CapabilityMatrix`` constructed
        in another used DIFFERENT files, and any process without that path in
        its cwd loaded zero records silently -- which is why the matrix's skill
        axis read 0 against a 275-skill library.

        Resolved per call rather than at import: a module-level ``Path.home()``
        freezes ``$HOME`` at first import, so anything that sets it afterwards
        (test harnesses, service managers) would be silently ignored.
        """
        return Path.home() / ".cohezion" / "skill_health.json"

    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path or self.default_storage_path()
        self._records: dict[str, SkillHealthRecord] = {}
        self._load()

    def _load(self) -> None:
        if self._storage_path.exists():
            data = json.loads(self._storage_path.read_text())
            for name, record_data in data.items():
                self._records[name] = SkillHealthRecord(**record_data)

    def _save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {name: asdict(record) for name, record in self._records.items()}
        self._storage_path.write_text(json.dumps(data, indent=2))

    def record_usage(
        self,
        skill_name: str,
        success: bool,
        tokens_used: int = 0,
        quality_score: float = 0.0,
    ) -> None:
        """Record a skill invocation with its outcome.

        Args:
            skill_name: Name of the PRIME skill that was used
            success: Whether the execution succeeded
            tokens_used: Number of tokens consumed (0 if unknown)
            quality_score: Quality score for successful runs (0.0 if unknown)
        """
        if skill_name not in self._records:
            self._records[skill_name] = SkillHealthRecord(
                skill_name=skill_name,
                created_date=datetime.now(UTC).isoformat(),
            )
        record = self._records[skill_name]
        record.total_invocations += 1
        if success:
            record.successful_invocations += 1
            record.total_quality_score += quality_score
        else:
            record.failed_invocations += 1
        record.total_tokens_used += tokens_used
        record.last_used = datetime.now(UTC).isoformat()
        self._save()

    def get_health(self, skill_name: str) -> SkillHealthRecord | None:
        """Return health record for a specific skill, or None if not tracked."""
        return self._records.get(skill_name)

    def get_all_health(self) -> list[SkillHealthRecord]:
        """Return all records sorted by health_score descending."""
        return sorted(self._records.values(), key=lambda r: r.health_score, reverse=True)

    def get_stale_skills(self, days: int = 30) -> list[str]:
        """Return skill names not used within the given number of days."""
        cutoff = datetime.now(UTC)
        stale = []
        for name, record in self._records.items():
            if not record.last_used:
                stale.append(name)
                continue
            last = datetime.fromisoformat(record.last_used)
            if (cutoff - last).days > days:
                stale.append(name)
        return stale

    def get_unhealthy_skills(self, threshold: float = 0.3) -> list[str]:
        """Return skill names whose health_score is below the given threshold."""
        return [
            name
            for name, record in self._records.items()
            if record.total_invocations > 0 and record.health_score < threshold
        ]
