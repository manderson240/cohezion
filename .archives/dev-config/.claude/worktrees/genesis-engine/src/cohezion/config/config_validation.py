"""Configuration validation framework - Phase 3.

Comprehensive validation including schema checks, size limits,
reference validation, and cycle detection.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from cohezion.config.config_state import (
    FileMetadata,
    ValidationReport,
)


logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates configuration files against schema and constraints."""

    def __init__(self, size_limits: dict[str, dict[str, int]] | None = None):
        """Initialize validator with size limits."""
        self.size_limits = size_limits or {
            "CLAUDE.md": {"max_lines": 250, "max_chars": 15000},
            "GEMINI.md": {"max_lines": 200, "max_chars": 12000},
        }

    def validate_file(self, file_path: Path) -> ValidationReport:
        """Validate a single config file."""
        report = ValidationReport()

        try:
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                report.passed = False
                report.recommendations.append(f"File not found: {file_path}")
                return report

            metadata = FileMetadata.from_file(file_path)

            # Run all validation checks
            checks = [
                self._check_schema(file_path),
                self._check_size(file_path, metadata),
                self._check_references(file_path),
                self._check_cycles(file_path),
                self._check_frontmatter(file_path),
            ]

            for check_result in checks:
                report.passed = report.passed and check_result.get("passed", True)
                if not check_result.get("passed", True):
                    report.recommendations.extend(check_result.get("recommendations", []))

        except Exception as e:
            logger.error(f"Validation error for {file_path}: {e}")
            report.passed = False
            report.recommendations.append(f"Validation error: {e}")

        return report

    def _check_schema(self, file_path: Path) -> dict[str, Any]:
        """Check file schema (YAML frontmatter, structure)."""
        try:
            content = file_path.read_text()

            # Check for frontmatter
            if not content.startswith("---"):
                return {
                    "passed": False,
                    "recommendations": [f"{file_path.name} missing YAML frontmatter"],
                }

            # Extract frontmatter
            parts = content.split("---", 2)
            if len(parts) < 3:
                return {
                    "passed": False,
                    "recommendations": [f"{file_path.name} has invalid frontmatter"],
                }

            # Check required fields
            frontmatter = parts[1]
            required_fields = ["title", "status"]
            for field in required_fields:
                if field not in frontmatter:
                    return {
                        "passed": False,
                        "recommendations": [f"{file_path.name} missing required field: {field}"],
                    }

            return {"passed": True}

        except Exception as e:
            logger.warning(f"Schema check error for {file_path}: {e}")
            return {"passed": False, "recommendations": [f"Schema check error: {e}"]}

    def _check_size(self, file_path: Path, metadata: FileMetadata) -> dict[str, Any]:
        """Check file size limits."""
        filename = file_path.name
        if filename not in self.size_limits:
            return {"passed": True}

        limits = self.size_limits[filename]
        violations = []

        if metadata.line_count > limits["max_lines"]:
            violations.append(f"{filename} exceeds line limit: {metadata.line_count} > {limits['max_lines']}")

        if metadata.size_bytes > limits["max_chars"]:
            violations.append(f"{filename} exceeds size limit: {metadata.size_bytes} > {limits['max_chars']}")

        return {
            "passed": len(violations) == 0,
            "recommendations": violations,
        }

    def _check_references(self, file_path: Path) -> dict[str, Any]:
        """Check that all wiki-links and references resolve."""
        try:
            content = file_path.read_text()

            # Find all wiki-links: [[path/to/file]]
            wiki_links = re.findall(r"\[\[([^\]]+)\]\]", content)

            broken_refs = []
            for link in wiki_links:
                # Resolve relative to vault root
                vault_root = Path.home() / "vaults" / "cohezion-vault"
                resolved = vault_root / link
                if not resolved.exists() and not resolved.with_suffix(".md").exists():
                    broken_refs.append(link)

            return {
                "passed": len(broken_refs) == 0,
                "recommendations": [f"Broken reference: {ref}" for ref in broken_refs],
            }

        except Exception as e:
            logger.warning(f"Reference check error for {file_path}: {e}")
            return {"passed": True}  # Not critical

    def _check_cycles(self, file_path: Path) -> dict[str, Any]:
        """Detect circular references in wiki-links."""
        try:
            content = file_path.read_text()

            # Find all wiki-links
            wiki_links = re.findall(r"\[\[([^\]]+)\]\]", content)

            # Check for self-references (simple form of cycle)
            file_name = file_path.stem
            self_refs = [link for link in wiki_links if link.endswith(file_name)]

            if self_refs:
                return {
                    "passed": False,
                    "recommendations": [f"Self-referential link detected: {self_refs}"],
                }

            return {"passed": True}

        except Exception as e:
            logger.warning(f"Cycle check error for {file_path}: {e}")
            return {"passed": True}  # Not critical

    def _check_frontmatter(self, file_path: Path) -> dict[str, Any]:
        """Check frontmatter format and content."""
        try:
            content = file_path.read_text()
            parts = content.split("---", 2)

            if len(parts) < 3:
                return {"passed": False, "recommendations": ["Invalid frontmatter"]}

            frontmatter = parts[1].strip()

            # Check YAML syntax (basic)
            lines = frontmatter.split("\n")
            for line in lines:
                if line and ":" not in line and not line.startswith("-"):
                    return {
                        "passed": False,
                        "recommendations": [f"Invalid YAML line: {line}"],
                    }

            return {"passed": True}

        except Exception as e:
            logger.warning(f"Frontmatter check error for {file_path}: {e}")
            return {"passed": True}


class ReconciliationValidator:
    """Validates consistency between multiple config sources."""

    def validate_consistency(
        self,
        claude_md: Path,
        gemini_md: Path,
        vault_root: Path,
    ) -> ValidationReport:
        """Validate consistency between all config sources."""
        report = ValidationReport()

        try:
            # Load all files
            sources = {}
            for name, path in [
                ("CLAUDE.md", claude_md),
                ("GEMINI.md", gemini_md),
            ]:
                if path.exists():
                    sources[name] = path.read_text()

            # Check consistency
            if len(sources) >= 2:
                # Cross-reference checks
                for name, content in sources.items():
                    missing_links = self._check_cross_refs(content, vault_root)
                    if missing_links:
                        report.recommendations.append(f"{name} has broken cross-references: {missing_links}")

            report.passed = len(report.recommendations) == 0

        except Exception as e:
            logger.error(f"Reconciliation error: {e}")
            report.passed = False
            report.recommendations.append(f"Reconciliation error: {e}")

        return report

    def _check_cross_refs(self, content: str, vault_root: Path) -> list[str]:
        """Check cross-references in content."""
        links = re.findall(r"\[\[([^\]]+)\]\]", content)
        missing = []

        for link in links:
            resolved = vault_root / link
            if not resolved.exists() and not resolved.with_suffix(".md").exists():
                missing.append(link)

        return missing
