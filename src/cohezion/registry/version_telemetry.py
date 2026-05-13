"""Version Telemetry Dashboard (Story 7.4, NFR-VERSION_TELEMETRY).

Real-time version state visualization analogous to HIHO stability.
Tracks dependency drift, version coherence score (0.0-1.0), and conflict detection.
Version Coherence Collapse (< 0.3) triggers Ouroboros Version Healing (Story 7.5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)

DRIFT_THRESHOLD_MINOR = 2  # 2+ minor versions behind = amber
COHERENCE_COLLAPSE_THRESHOLD = 0.3


class DriftStatus(Enum):
    GREEN = "green"  # Up to date
    AMBER = "amber"  # >= DRIFT_THRESHOLD minor versions behind
    RED = "red"  # Major version behind or conflict


@dataclass
class DependencyDrift:
    package: str
    current_version: str
    latest_version: str
    minor_versions_behind: int
    status: DriftStatus
    recommended_action: str = ""

    def to_dict(self) -> dict:
        return {
            "package": self.package,
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "minor_versions_behind": self.minor_versions_behind,
            "status": self.status.value,
            "recommended_action": self.recommended_action,
        }


@dataclass
class VersionConflict:
    package: str
    constraint_a: str  # e.g., ">=1.0"
    constraint_b: str  # e.g., "<1.0"
    from_packages: list[str]

    def to_dict(self) -> dict:
        return {
            "package": self.package,
            "constraint_a": self.constraint_a,
            "constraint_b": self.constraint_b,
            "from_packages": self.from_packages,
        }


@dataclass
class VersionHealthPanel:
    """The Version Health panel state for the Observatory Dashboard."""

    coherence_score: float  # 0.0-1.0 (1.0 = all deps current, no conflicts)
    drifts: list[DependencyDrift]
    conflicts: list[VersionConflict]
    healing_triggered: bool = False

    def to_dict(self) -> dict:
        return {
            "coherence_score": self.coherence_score,
            "drifts": [d.to_dict() for d in self.drifts],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "healing_triggered": self.healing_triggered,
        }


class VersionTelemetry:
    """Tracks version drift and coherence across all dependencies."""

    def __init__(self) -> None:
        self._panels: list[VersionHealthPanel] = []

    def scan(
        self,
        current_versions: dict[str, str],
        latest_versions: dict[str, str],
        conflicts: list[VersionConflict] | None = None,
    ) -> VersionHealthPanel:
        """Compute Version Health panel state."""
        drifts = []
        for pkg, current in current_versions.items():
            latest = latest_versions.get(pkg, current)
            behind = self._minor_versions_behind(current, latest)

            if behind >= DRIFT_THRESHOLD_MINOR:
                status = DriftStatus.AMBER
            elif self._major_behind(current, latest):
                status = DriftStatus.RED
            else:
                status = DriftStatus.GREEN

            if status != DriftStatus.GREEN:
                drifts.append(
                    DependencyDrift(
                        package=pkg,
                        current_version=current,
                        latest_version=latest,
                        minor_versions_behind=behind,
                        status=status,
                        recommended_action=f"Upgrade {pkg} from {current} to {latest}",
                    )
                )

        conflicts = conflicts or []
        coherence = self._compute_coherence(drifts, conflicts, len(current_versions))
        healing_triggered = coherence < COHERENCE_COLLAPSE_THRESHOLD or len(conflicts) > 0

        if healing_triggered:
            logger.warning(
                "Version Coherence Collapse: score=%.2f, conflicts=%d. Triggering healing.",
                coherence,
                len(conflicts),
            )

        panel = VersionHealthPanel(
            coherence_score=round(coherence, 3),
            drifts=drifts,
            conflicts=conflicts,
            healing_triggered=healing_triggered,
        )
        self._panels.append(panel)
        return panel

    def _compute_coherence(self, drifts: list[DependencyDrift], conflicts: list[VersionConflict], total: int) -> float:
        if total == 0:
            return 1.0
        drift_penalty = sum(0.1 * d.minor_versions_behind for d in drifts)
        conflict_penalty = len(conflicts) * 0.5
        score = 1.0 - (drift_penalty + conflict_penalty) / total
        return max(0.0, min(1.0, score))

    def _minor_versions_behind(self, current: str, latest: str) -> int:
        try:
            c = tuple(int(x) for x in current.split("."))
            lv = tuple(int(x) for x in latest.split("."))
            if c[0] != lv[0]:
                return 0  # Major version diff handled separately
            return max(0, lv[1] - c[1])
        except (ValueError, IndexError):
            return 0

    def _major_behind(self, current: str, latest: str) -> bool:
        try:
            c = int(current.split(".")[0])
            lv = int(latest.split(".")[0])
            return lv > c
        except (ValueError, IndexError):
            return False
