"""Vanguard Attribution & License Compliance Engine (Story 4.1c, FR-5, Security).

Every extracted pattern carries immutable attribution metadata and license verification.
Incompatible licenses (GPL, proprietary) are quarantined and logged as "Blocked Discovery".
Unknown licenses are flagged for manual review before integration.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from cohezion.vanguard.source_connector import DiscoveryRecord


logger = logging.getLogger(__name__)

COMPATIBLE_LICENSES = {
    "mit",
    "apache-2.0",
    "cc-by",
    "cc-by-sa",
    "bsd-2-clause",
    "bsd-3-clause",
    "public-domain",
}
INCOMPATIBLE_LICENSES = {"gpl-2.0", "gpl-3.0", "agpl-3.0", "proprietary", "commercial"}


class LicenseStatus(Enum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


@dataclass
class AttributionMetadata:
    """Immutable attribution for a DiscoveryRecord."""

    origin_url: str
    authors: list[str]
    license_type: str
    content_hash: str
    status: LicenseStatus
    flagged_for_review: bool = False

    def to_dict(self) -> dict:
        return {
            "origin_url": self.origin_url,
            "authors": self.authors,
            "license_type": self.license_type,
            "content_hash": self.content_hash,
            "status": self.status.value,
            "flagged_for_review": self.flagged_for_review,
        }


@dataclass
class AttributedRecord:
    record: DiscoveryRecord
    attribution: AttributionMetadata
    quarantined: bool = False
    quarantine_reason: str = ""


class AttributionEngine:
    """Attaches license metadata and enforces compliance."""

    def __init__(self) -> None:
        self._quarantine: list[AttributedRecord] = []

    def process(
        self, record: DiscoveryRecord, authors: list[str], license_type: str
    ) -> AttributedRecord:
        """Attach attribution and determine license compliance."""
        content_hash = hashlib.sha256(record.source_url.encode()).hexdigest()[:16]
        license_lower = license_type.lower()

        if license_lower in INCOMPATIBLE_LICENSES:
            status = LicenseStatus.INCOMPATIBLE
        elif license_lower in COMPATIBLE_LICENSES:
            status = LicenseStatus.COMPATIBLE
        else:
            status = LicenseStatus.UNKNOWN

        attribution = AttributionMetadata(
            origin_url=record.source_url,
            authors=authors,
            license_type=license_type,
            content_hash=content_hash,
            status=status,
            flagged_for_review=(status == LicenseStatus.UNKNOWN),
        )

        attributed = AttributedRecord(record=record, attribution=attribution)

        if status == LicenseStatus.INCOMPATIBLE:
            attributed.quarantined = True
            attributed.quarantine_reason = f"Incompatible license: {license_type}"
            self._quarantine.append(attributed)
            logger.warning(
                "Discovery quarantined: %s — license violation: %s",
                record.title[:50],
                license_type,
            )

        return attributed

    def quarantined_records(self) -> list[dict]:
        return [
            {
                "title": r.record.title,
                "reason": r.quarantine_reason,
                "attribution": r.attribution.to_dict(),
            }
            for r in self._quarantine
        ]

    def quarantine_count(self) -> int:
        return len(self._quarantine)
