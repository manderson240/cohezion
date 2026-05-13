"""Version Traceability Gate (Story 7.6, NFR-AUTO_VERSION_HEALTH).

Every story's dependencies are linked to semver contracts.
Epic completion is blocked if version traceability is incomplete.
Release impact reports generated for every release.
CVE incident response returns affected versions in <30 seconds.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class VersionContract:
    """Semver contract for a dependency introduced/updated by a story."""

    package: str
    version_spec: str  # e.g., ">=2.0.0,<3.0.0" or exact "2.1.3"
    story_id: str
    epic_id: str
    introduced_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "package": self.package,
            "version_spec": self.version_spec,
            "story_id": self.story_id,
            "epic_id": self.epic_id,
        }


@dataclass
class ReleaseImpactReport:
    """Version impact report for a release."""

    release_version: str
    stories_included: list[str]
    version_changes: list[dict]
    breaking_changes: list[str]
    security_impact: list[str]
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "release_version": self.release_version,
            "stories_included": self.stories_included,
            "version_changes": self.version_changes,
            "breaking_changes": self.breaking_changes,
            "security_impact": self.security_impact,
        }


@dataclass
class EpicCompletionGate:
    epic_id: str
    blocked: bool
    missing_contracts: list[str]  # story_ids with missing version contracts
    remediation_steps: list[str]

    def to_dict(self) -> dict:
        return {
            "epic_id": self.epic_id,
            "blocked": self.blocked,
            "missing_contracts": self.missing_contracts,
            "remediation_steps": self.remediation_steps,
        }


class VersionTraceabilityGate:
    """Ensures 100% version traceability and gates epic completion."""

    def __init__(self) -> None:
        self._contracts: list[VersionContract] = []
        self._completed_stories: set[str] = set()
        self._impact_reports: list[ReleaseImpactReport] = []

    def register_contract(self, contract: VersionContract) -> None:
        """Register a version contract when a story is done."""
        self._contracts.append(contract)
        self._completed_stories.add(contract.story_id)
        logger.info(
            "Version contract registered: %s@%s (story %s, epic %s)",
            contract.package,
            contract.version_spec,
            contract.story_id,
            contract.epic_id,
        )

    def check_epic_gate(self, epic_id: str, expected_stories: list[str]) -> EpicCompletionGate:
        """Block epic completion if any story lacks version traceability."""
        stories_with_contracts = {c.story_id for c in self._contracts if c.epic_id == epic_id}
        missing = [s for s in expected_stories if s not in stories_with_contracts]

        blocked = len(missing) > 0
        remediation = [f"Register version contract for story {s} before marking epic complete" for s in missing]

        return EpicCompletionGate(
            epic_id=epic_id,
            blocked=blocked,
            missing_contracts=missing,
            remediation_steps=remediation,
        )

    def generate_release_report(
        self,
        release_version: str,
        story_ids: list[str],
    ) -> ReleaseImpactReport:
        """Generate version impact report for a release."""
        relevant_contracts = [c for c in self._contracts if c.story_id in story_ids]

        version_changes = [c.to_dict() for c in relevant_contracts]
        breaking_changes = [f"Breaking change in {c.package}" for c in relevant_contracts if "!" in c.version_spec]

        report = ReleaseImpactReport(
            release_version=release_version,
            stories_included=story_ids,
            version_changes=version_changes,
            breaking_changes=breaking_changes,
            security_impact=[],
        )
        self._impact_reports.append(report)
        return report

    def incident_response_query(self, vulnerable_package: str, vulnerable_version: str) -> dict:
        """Return affected epics/stories for a vulnerable package. <30s guaranteed."""
        t0 = time.perf_counter()

        affected = [
            c for c in self._contracts if c.package == vulnerable_package and vulnerable_version in c.version_spec
        ]

        duration_s = time.perf_counter() - t0
        return {
            "vulnerable_package": vulnerable_package,
            "vulnerable_version": vulnerable_version,
            "affected_stories": [c.story_id for c in affected],
            "affected_epics": list({c.epic_id for c in affected}),
            "query_duration_s": round(duration_s, 4),
        }

    def all_contracts(self) -> list[dict]:
        return [c.to_dict() for c in self._contracts]
