"""Configuration state tracking and validation framework.

Tracks file metadata, validation results, and sync operations
for CLAUDE.md, GEMINI.md, and vault integration.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


@dataclass
class SectionRef:
    """Reference to a section within a config file."""

    title: str
    start_line: int
    end_line: int
    level: int  # Heading level (1-3)
    last_modified: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    age_days: int = 0


@dataclass
class FileMetadata:
    """Tracks state and metadata of a configuration file."""

    path: Path
    size_bytes: int
    line_count: int
    content_hash: str
    last_modified: datetime
    sections: list[SectionRef] = field(default_factory=list)
    manual_edited: bool = False
    last_sync_time: datetime | None = None
    last_git_author: str | None = None

    @classmethod
    def from_file(cls, path: Path) -> FileMetadata:
        """Create metadata by reading file."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        content = path.read_text()
        return cls(
            path=path,
            size_bytes=len(content.encode()),
            line_count=len(content.splitlines()),
            content_hash=cls._compute_hash(content),
            last_modified=datetime.fromtimestamp(path.stat().st_mtime),
            sections=cls._extract_sections(content),
        )

    @staticmethod
    def _compute_hash(content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def _extract_sections(content: str) -> list[SectionRef]:
        """Extract headings and sections from markdown."""
        sections = []
        for i, line in enumerate(content.splitlines(), 1):
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                title = line.lstrip("#").strip()
                sections.append(
                    SectionRef(
                        title=title,
                        start_line=i,
                        end_line=i,  # Will be updated on next section
                        level=level,
                    )
                )
        return sections


@dataclass
class ChangeSet:
    """Represents changes detected between config states."""

    added: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    moved: dict[str, str] = field(default_factory=dict)

    def is_empty(self) -> bool:
        """Check if there are no changes."""
        return not self.added and not self.modified and not self.deleted and not self.moved


@dataclass
class ConfigConflict:
    """Represents a detected conflict between sources."""

    file: str
    conflict_type: str  # "manual_edit", "diverged_content", "size_mismatch"
    vault_version_hash: str
    config_version_hash: str
    vault_modified: datetime
    config_modified: datetime
    diffs: dict[str, Any] = field(default_factory=dict)


class ValidationReport(BaseModel):
    """Results of consistency check between all config sources."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    timestamp: datetime = Field(default_factory=datetime.now)
    passed: bool = True
    checksums_match: bool = True
    schema_valid: bool = True
    size_compliant: bool = True
    references_valid: bool = True
    cycles_detected: list[str] = Field(default_factory=list)
    conflicts_found: list[ConfigConflict] = Field(default_factory=list)
    diffs: dict[str, str] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0


class ConfigSchema(BaseModel):
    """Schema validation for CLAUDE.md and GEMINI.md."""

    title: str = Field(..., max_length=100)
    date: datetime | None = None
    status: str = Field(..., pattern="^(active|archived|draft)$")
    tags: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)

    # Size constraints
    max_lines: int = 250
    max_chars: int = 15000


class ConfigState(BaseModel):
    """Complete configuration system state."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    claude_md: FileMetadata | None = None
    gemini_md: FileMetadata | None = None
    vault_canonical: FileMetadata | None = None
    last_validation: ValidationReport | None = None
    last_sync_time: datetime | None = None

    # Metrics
    total_syncs: int = 0
    total_conflicts: int = 0
    total_validations: int = 0
    sync_failures: int = 0
