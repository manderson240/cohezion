# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""Configuration archival and size management - Phase 3.

Handles archiving old content to vault when size limits exceeded.
Implements retention policies and cleanup strategies.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class ConfigArchiver:
    """Manages configuration file archival and size enforcement."""

    def __init__(
        self,
        vault_root: Path | None = None,
        archive_dir: str = "archived/config-sync",
        age_threshold_days: int = 30,
    ):
        """Initialize archiver with vault paths."""
        if vault_root is None:
            vault_root = Path.home() / "vaults" / "cohezion-vault"
        self.vault_root = vault_root
        self.archive_dir = vault_root / archive_dir
        self.age_threshold_days = age_threshold_days

        # Ensure archive directory exists
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    async def archive_old_sections(
        self,
        file_path: Path,
        age_threshold_days: int | None = None,
    ) -> dict[str, Any]:
        """Archive sections older than threshold.

        Returns dict with archive metadata.
        """
        if age_threshold_days is None:
            age_threshold_days = self.age_threshold_days

        result = {
            "archived": False,
            "sections_archived": 0,
            "archive_path": None,
            "details": [],
        }

        try:
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return result

            content = file_path.read_text()
            lines = content.splitlines()

            # Parse sections with timestamps
            sections = self._parse_sections(lines)

            # Identify old sections
            now = datetime.now()
            old_sections = []

            for section in sections:
                # Estimate section age from content (simple heuristic)
                # In production, would use git history
                section_age = self._estimate_section_age(section)
                if section_age and section_age > age_threshold_days:
                    old_sections.append(section)

            if not old_sections:
                logger.debug(f"No old sections to archive in {file_path.name}")
                return result

            # Archive old sections
            archive_data = {
                "archived_at": now.isoformat(),
                "source_file": file_path.name,
                "sections": old_sections,
                "age_threshold_days": age_threshold_days,
            }

            # Create archive file
            archive_path = self._create_archive_file(archive_data)

            result["archived"] = True
            result["sections_archived"] = len(old_sections)
            result["archive_path"] = str(archive_path)
            result["details"] = [s.get("title", "Untitled") for s in old_sections]

            logger.info(f"Archived {len(old_sections)} sections to {archive_path}")

            return result

        except Exception as e:
            logger.error(f"Archival error for {file_path}: {e}")
            result["error"] = str(e)
            return result

    def _parse_sections(self, lines: list[str]) -> list[dict[str, Any]]:
        """Parse markdown sections from lines."""
        sections = []
        current_section: dict[str, Any] = {}

        for i, line in enumerate(lines):
            if line.startswith("#"):
                # Start new section
                if current_section:
                    sections.append(current_section)

                level = len(line) - len(line.lstrip("#"))
                title = line.lstrip("#").strip()

                current_section = {
                    "title": title,
                    "level": level,
                    "start_line": i,
                    "content": [],
                }
            elif current_section:
                current_section["content"].append(line)

        if current_section:
            sections.append(current_section)

        return sections

    def _estimate_section_age(self, section: dict[str, Any]) -> int | None:
        """Estimate section age in days (heuristic).

        In production, would use git blame or commit history.
        """
        # Simple heuristic: sections with "deprecated", "old", "archive" in title
        title = section.get("title", "").lower()
        if any(word in title for word in ["deprecated", "old", "archive", "legacy"]):
            return 999  # Mark as very old

        # Sections with dates in title
        import re

        dates = re.findall(r"\d{4}-\d{2}-\d{2}", section.get("title", ""))
        if dates:
            try:
                date = datetime.strptime(dates[0], "%Y-%m-%d")
                age = (datetime.now() - date).days
                return age
            except (ValueError, TypeError) as e:
                logger.debug("Failed to parse date from section title: %s", e)

        return None

    def _create_archive_file(self, archive_data: dict[str, Any]) -> Path:
        """Create archive file in vault."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"archived_{timestamp}.json"
        archive_path = self.archive_dir / filename

        with open(archive_path, "w") as f:
            json.dump(archive_data, f, indent=2)

        return archive_path

    async def cleanup_archived(self, retention_days: int = 90) -> dict[str, Any]:
        """Clean up archived files older than retention period.

        Note: Phase 3 implements "keep full history", so this is disabled.
        Included for future enhancement.
        """
        result = {
            "cleaned": False,
            "files_deleted": 0,
            "details": [],
        }

        # In Phase 3 design: "keep full history indefinitely"
        # So we don't delete anything
        logger.debug("Archive cleanup disabled (keeping full history)")

        return result

    def get_archive_status(self) -> dict[str, Any]:
        """Get status of archived content."""
        try:
            archives = list(self.archive_dir.glob("archived_*.json"))

            total_size = sum(f.stat().st_size for f in archives)
            total_sections = 0

            for archive_file in archives:
                try:
                    with open(archive_file) as f:
                        data = json.load(f)
                        total_sections += len(data.get("sections", []))
                except (json.JSONDecodeError, OSError) as e:
                    logger.debug("Failed to read archive %s: %s", archive_file, e)

            return {
                "archive_dir": str(self.archive_dir),
                "archive_count": len(archives),
                "total_size_bytes": total_size,
                "total_archived_sections": total_sections,
                "retention_policy": "full_history",
            }

        except Exception as e:
            logger.error(f"Error getting archive status: {e}")
            return {
                "error": str(e),
                "retention_policy": "full_history",
            }


class SizeEnforcer:
    """Enforces size limits on config files."""

    def __init__(self, size_limits: dict[str, dict[str, int]] | None = None):
        """Initialize with size limits."""
        self.size_limits = size_limits or {
            "CLAUDE.md": {"max_lines": 250, "max_chars": 15000},
            "GEMINI.md": {"max_lines": 200, "max_chars": 12000},
        }

    def check_violations(self, file_path: Path) -> dict[str, Any]:
        """Check if file violates size limits."""
        result: dict[str, Any] = {
            "violates": False,
            "violations": [],
            "metadata": {},
        }

        try:
            if not file_path.exists():
                return result

            content = file_path.read_text()
            filename = file_path.name

            if filename not in self.size_limits:
                return result

            limits = self.size_limits[filename]
            line_count = len(content.splitlines())
            char_count = len(content)

            result["metadata"] = {
                "lines": line_count,
                "chars": char_count,
                "max_lines": limits["max_lines"],
                "max_chars": limits["max_chars"],
            }

            if line_count > limits["max_lines"]:
                result["violations"].append(
                    f"Lines: {line_count} > {limits['max_lines']} (excess: {line_count - limits['max_lines']} lines)"
                )

            if char_count > limits["max_chars"]:
                result["violations"].append(
                    f"Size: {char_count} > {limits['max_chars']} bytes "
                    f"(excess: {char_count - limits['max_chars']} bytes)"
                )

            result["violates"] = len(result["violations"]) > 0

        except Exception as e:
            logger.error(f"Size check error for {file_path}: {e}")
            result["error"] = str(e)

        return result

    def get_remediation_actions(self, file_path: Path) -> list[str]:
        """Suggest remediation actions for size violations."""
        actions = []

        violations = self.check_violations(file_path)

        if violations["violates"]:
            actions.append(f"Archive old sections to {file_path.parent}/archived/")
            actions.append("Remove outdated documentation or move to wiki-links")
            actions.append("Regenerate from vault templates to remove manual edits")

        return actions
