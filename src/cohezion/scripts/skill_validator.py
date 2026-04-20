"""Skill validator - Automated discovery and validation of Cohezion skills.

Validates:
- YAML frontmatter presence and required fields
- Skill ID and version format
- Description completeness
- FLUME 256D compatibility markers
- Cross-skill dependency resolution
- Broken internal links/references

Exit codes:
- 0: All skills valid
- 1: Validation errors found
- 2: System error
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SKILLS_DIR = Path("src/cohezion/skills")
REQUIRED_FIELDS = {"id", "domain", "version"}
OPTIONAL_FIELDS = {"flume_dimension", "coherence_threshold", "tier", "see_also"}
VALID_TIERS = {"L1", "L2", "L3", "PRIME"}


@dataclass
class ValidationResult:
    skill_id: str
    path: Path
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillValidator:
    """Validator for Cohezion skill files."""

    def __init__(self, skills_dir: Path = SKILLS_DIR):
        self.skills_dir = skills_dir
        self.results: list[ValidationResult] = []
        self._discovered_ids: set[str] = set()

    def discover_skills(self) -> list[Path]:
        """Discover all skill files in the skills directory."""
        return sorted(self.skills_dir.glob("*.md"))

    def parse_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        """Parse metadata from skill content.

        Supports two formats:
        1. YAML frontmatter: ---\nyaml\n--- (newer skills)
        2. PRIME format: # SKILL: NAME\n\n## DOMAIN EXPERTISE (older skills)

        Returns (metadata, body) or raises ValueError if invalid.
        """
        # Try YAML frontmatter first
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1])
                    body = parts[2].strip()
                    return metadata or {}, body
                except yaml.YAMLError as e:
                    raise ValueError(f"Invalid YAML: {e}")

        # Try PRIME format: # SKILL: NAME
        lines = content.split("\n")
        metadata = {}
        body_start = 0

        for i, line in enumerate(lines):
            if line.startswith("# SKILL:"):
                skill_name = line.replace("# SKILL:", "").strip()
                metadata["id"] = skill_name
                body_start = i + 1
            elif line.startswith("## DOMAIN EXPERTISE"):
                metadata["domain"] = "PRIME skill"
                body_start = i
                break

        # Look for version in ## VERSION section (PRIME format)
        for i, line in enumerate(lines):
            if line.strip() == "## VERSION":
                # Version is on next line
                if i + 1 < len(lines):
                    version = lines[i + 1].strip()
                    if version.startswith("v"):
                        metadata["version"] = version
                break
            elif line.startswith("## VERSION") and i + 1 < len(lines):
                # Handle "## VERSION\nv1.0" format
                version = lines[i + 1].strip()
                if version.startswith("v"):
                    metadata["version"] = version

        if not metadata:
            raise ValueError("No recognizable skill format found")

        body = "\n".join(lines[body_start:]).strip()
        return metadata, body

    def validate_skill(self, path: Path) -> ValidationResult:
        """Validate a single skill file."""
        # Extract skill ID from filename
        skill_id = path.stem.upper().replace("_", "_")

        result = ValidationResult(skill_id=skill_id, path=path, valid=True)

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            result.valid = False
            result.errors.append(f"Cannot read file: {e}")
            return result

        # Parse frontmatter
        try:
            metadata, body = self.parse_frontmatter(content)
            result.metadata = metadata
        except ValueError as e:
            result.valid = False
            result.errors.append(f"Frontmatter error: {e}")
            return result

        # Validate required fields (but be lenient for legacy PRIME skills)
        for field in REQUIRED_FIELDS:
            if field not in metadata:
                # For PRIME skills, add default values for missing fields
                if field == "version" and metadata.get("domain") == "PRIME skill":
                    metadata["version"] = "v1.0"  # Default version for PRIME skills
                elif field == "tier" and metadata.get("domain") == "PRIME skill":
                    metadata["tier"] = "PRIME"  # PRIME skills get PRIME tier
                else:
                    result.valid = False
                    result.errors.append(f"Missing required field: {field}")

        # Validate tier if present
        tier = metadata.get("tier")
        if tier and tier not in VALID_TIERS:
            result.warnings.append(f"Unknown tier: {tier}")

        # Check for description
        if not body.strip():
            result.valid = False
            result.errors.append("Empty skill body")
        elif len(body) < 50:
            result.warnings.append("Skill body is unusually short")

        # Check for FLUME compatibility marker
        if "flume_dimension" in metadata:
            dim = metadata["flume_dimension"]
            if dim != 256:
                result.warnings.append(f"Non-standard FLUME dimension: {dim}")
        else:
            result.warnings.append("No FLUME dimension specified (defaults to 256D)")

        # Check for coherence threshold (HIHO)
        if "coherence_threshold" in metadata:
            threshold = metadata["coherence_threshold"]
            if not (0.0 <= threshold <= 1.0):
                result.errors.append(f"Coherence threshold out of range: {threshold}")

        # Check "see_also" references
        if "see_also" in metadata:
            see_also = metadata["see_also"]
            if isinstance(see_also, list):
                for ref in see_also:
                    ref_path = self.skills_dir / f"{ref.lower()}.md"
                    if not ref_path.exists():
                        result.warnings.append(f"Broken reference: {ref}")

        self._discovered_ids.add(skill_id)
        return result

    def validate_all(self) -> tuple[bool, list[ValidationResult]]:
        """Validate all discovered skills.

        Returns (all_valid, results).
        """
        paths = self.discover_skills()
        if not paths:
            print("⚠ No skill files found in", self.skills_dir)
            return False, []

        print(f"Discovered {len(paths)} skill files")

        all_valid = True
        for path in paths:
            result = self.validate_skill(path)
            self.results.append(result)
            if not result.valid:
                all_valid = False

        return all_valid, self.results

    def print_report(self) -> None:
        """Print a formatted validation report."""
        if not self.results:
            print("No skills to report")
            return

        valid_count = sum(1 for r in self.results if r.valid)
        error_count = sum(len(r.errors) for r in self.results)
        warning_count = sum(len(r.warnings) for r in self.results)

        print(f"\n{'='*60}")
        print(f"SKILL VALIDATION REPORT")
        print(f"{'='*60}")
        print(f"Total skills: {len(self.results)}")
        print(f"Valid: {valid_count} ({100*valid_count//len(self.results)}%)")
        print(f"Errors: {error_count}")
        print(f"Warnings: {warning_count}")
        print(f"{'='*60}")

        # Show invalid skills
        invalid = [r for r in self.results if not r.valid]
        if invalid:
            print("\n❌ INVALID SKILLS:")
            for r in invalid:
                print(f"\n  {r.skill_id}")
                print(f"    Path: {r.path}")
                for err in r.errors:
                    print(f"    ERROR: {err}")

        # Show warnings
        with_warnings = [r for r in self.results if r.warnings]
        if with_warnings:
            print("\n⚠ SKILLS WITH WARNINGS:")
            for r in with_warnings:
                print(f"\n  {r.skill_id}")
                for warn in r.warnings:
                    print(f"    WARNING: {warn}")

        print(f"\n{'='*60}")

    def export_results(self, output_path: Path) -> None:
        """Export validation results to JSON."""
        def clean_value(v):
            """Make value JSON serializable."""
            if hasattr(v, 'isoformat'):  # datetime/date
                return v.isoformat()
            if isinstance(v, Path):
                return str(v)
            if isinstance(v, dict):
                return {k: clean_value(val) for k, val in v.items()}
            if isinstance(v, list):
                return [clean_value(item) for item in v]
            return v

        data = {
            "valid_count": sum(1 for r in self.results if r.valid),
            "total_count": len(self.results),
            "skills": [
                {
                    "id": r.skill_id,
                    "path": str(r.path),
                    "valid": r.valid,
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "metadata": clean_value(r.metadata),
                }
                for r in self.results
            ],
        }
        output_path.write_text(json.dumps(data, indent=2))
        print(f"Exported results to {output_path}")


def main() -> int:
    """Main entry point."""
    validator = SkillValidator()
    all_valid, results = validator.validate_all()
    validator.print_report()

    # Export for CI
    validator.export_results(Path(".skill_validation.json"))

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
