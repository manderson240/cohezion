"""Vanguard Source Connector Framework (Story 4.1, FR-5, NFR-10).

Pluggable connector framework for scraping and normalizing content from heterogeneous
sources. Reference implementation: ArXiv connector.
Single source failure never blocks the entire scouting cycle.
"""

from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)

ARXIV_CATEGORIES = ["cs.LG", "cs.AI", "cs.RO", "cs.NE"]


class SourceHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"


@dataclass
class DiscoveryRecord:
    """Normalized research artifact from any source."""

    title: str
    abstract: str
    source_url: str
    category: str
    source_name: str
    extraction_timestamp: float = field(default_factory=time.time)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            raw = f"{self.title}:{self.source_url}"
            self.content_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class SourceHealthReport:
    source_name: str
    status: SourceHealth
    error_message: str = ""
    http_status: int = 200
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "source_name": self.source_name,
            "status": self.status.value,
            "error_message": self.error_message,
            "http_status": self.http_status,
            "timestamp": self.timestamp,
        }


class SourceConnector(ABC):
    """Abstract base for all Vanguard source connectors."""

    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @abstractmethod
    def discover(self) -> tuple[list[DiscoveryRecord], SourceHealthReport]:
        """Scrape and normalize records. Returns (records, health_report)."""
        ...

    def extract(self, record: DiscoveryRecord) -> DiscoveryRecord:
        """Optional post-processing (default: passthrough)."""
        return record

    def normalize(self, raw: dict) -> DiscoveryRecord:
        """Normalize raw source data to DiscoveryRecord."""
        return DiscoveryRecord(
            title=raw.get("title", ""),
            abstract=raw.get("abstract", ""),
            source_url=raw.get("url", ""),
            category=raw.get("category", ""),
            source_name=self.source_name,
        )


class ArXivConnector(SourceConnector):
    """ArXiv connector for cs.LG, cs.AI, cs.RO, cs.NE categories."""

    @property
    def source_name(self) -> str:
        return "arxiv"

    def discover(self) -> tuple[list[DiscoveryRecord], SourceHealthReport]:
        """Scrape ArXiv (simulated) across cs.LG, cs.AI, cs.RO, cs.NE."""
        records = []
        for category in ARXIV_CATEGORIES:
            records.append(
                DiscoveryRecord(
                    title=f"Advances in {category} Research",
                    abstract=f"Abstract for {category} paper",
                    source_url=f"https://arxiv.org/abs/2026.{category.replace('.', '')}",
                    category=category,
                    source_name=self.source_name,
                )
            )

        report = SourceHealthReport(source_name=self.source_name, status=SourceHealth.HEALTHY)
        return records, report


class FailingConnector(SourceConnector):
    """Test connector that simulates source failure."""

    def __init__(self, http_status: int = 503) -> None:
        self._http_status = http_status

    @property
    def source_name(self) -> str:
        return "failing_source"

    def discover(self) -> tuple[list[DiscoveryRecord], SourceHealthReport]:
        report = SourceHealthReport(
            source_name=self.source_name,
            status=SourceHealth.UNREACHABLE,
            error_message=f"HTTP {self._http_status} from source",
            http_status=self._http_status,
        )
        return [], report
