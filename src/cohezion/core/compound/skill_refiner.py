# ruff: noqa: S112  # best-effort skip in cleanup paths
"""Skill refiner: closes the compound loop by applying insights to PRIME skills.

Takes retrospection suggestions and appends a ``## LEARNED REFINEMENTS``
section to the relevant PRIME skill ``.md`` files, then optionally
regenerates the agent code via :class:`ConfigTemplateManager`.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


logger = logging.getLogger(__name__)

_SKILLS_DIR = Path("src/cohezion/skills/")


@dataclass
class RefinementResult:
    """Outcome of refining a single PRIME skill.

    Attributes
    ----------
    skill_name : str
        Name of the refined skill.
    additions : list[str]
        Learning titles that were added.
    version_before : str
        Version string before refinement.
    version_after : str
        Version string after refinement.
    code_regenerated : bool
        Whether agent code was regenerated.
    """

    skill_name: str
    additions: list[str] = field(default_factory=list)
    version_before: str = "unknown"
    version_after: str = "unknown"
    code_regenerated: bool = False


class SkillRefiner:
    """Apply retrospection insights to PRIME skill definitions.

    Parameters
    ----------
    skills_dir : Path | None
        Override path to the skills directory.
    auto_regenerate : bool
        If ``True``, regenerate agent code after refining a skill.
    """

    def __init__(
        self,
        skills_dir: Path | None = None,
        auto_regenerate: bool = False,
    ) -> None:
        self.skills_dir = skills_dir or _SKILLS_DIR
        self.auto_regenerate = auto_regenerate

    def refine_skill(
        self,
        skill_name: str,
        learnings: list[str],
        reason: str = "",
    ) -> RefinementResult:
        """Append learned refinements to a PRIME skill file.

        Parameters
        ----------
        skill_name : str
            Name of the PRIME skill (e.g. ``"COMPOUND_ENGINEERING_PRIME"``).
        learnings : list[str]
            Learning titles to add as refinements.
        reason : str
            Why the refinement is being suggested.

        Returns
        -------
        RefinementResult
            Outcome of the refinement.
        """
        md_path = self._find_skill_file(skill_name)
        if md_path is None:
            logger.warning("Skill file not found for: %s", skill_name)
            return RefinementResult(skill_name=skill_name)

        text = md_path.read_text(encoding="utf-8")
        version_before = self._extract_version(text)

        # Build refinement section
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d")
        refinement_lines = [
            "",
            "## LEARNED REFINEMENTS",
            "",
            f"_Auto-applied on {timestamp} via RetrospectionEngine._",
        ]
        if reason:
            refinement_lines.append(f"\n**Reason**: {reason}")
        refinement_lines.append("")
        for learning in learnings:
            refinement_lines.append(f"- {learning}")
        refinement_lines.append("")

        # Check if LEARNED REFINEMENTS section already exists
        if "## LEARNED REFINEMENTS" in text:
            # Append to existing section
            insert_point = text.index("## LEARNED REFINEMENTS")
            # Find end of existing section (next ## heading or EOF)
            next_heading = text.find("\n## ", insert_point + 5)
            if next_heading == -1:
                next_heading = len(text)
            _existing = text[insert_point:next_heading].rstrip()
            new_entries = "\n".join(f"- {learning}" for learning in learnings)
            text = (
                text[:next_heading].rstrip()
                + f"\n- _{timestamp}_: {new_entries}\n"
                + text[next_heading:]
            )
        else:
            # Append new section at end
            text = text.rstrip() + "\n" + "\n".join(refinement_lines)

        # Bump version
        version_after = self._bump_version(version_before)
        text = self._update_version(text, version_before, version_after)

        md_path.write_text(text, encoding="utf-8")
        logger.info(
            "Refined %s: added %d learnings, version %s -> %s",
            skill_name,
            len(learnings),
            version_before,
            version_after,
        )

        result = RefinementResult(
            skill_name=skill_name,
            additions=learnings,
            version_before=version_before,
            version_after=version_after,
        )

        # Optionally regenerate code
        if self.auto_regenerate:
            try:
                from cohezion.core.config_templates import ConfigTemplateManager

                manager = ConfigTemplateManager()
                manager.generate_and_register(skill_name)
                result.code_regenerated = True
                logger.info("Regenerated code for %s", skill_name)
            except Exception:
                logger.exception("Failed to regenerate code for %s", skill_name)

        return result

    def refine_from_suggestions(self, suggestions: list) -> list[RefinementResult]:
        """Apply a batch of :class:`SkillRefinement` suggestions.

        Parameters
        ----------
        suggestions : list[SkillRefinement]
            From :meth:`RetrospectionEngine.suggest_skill_refinements`.

        Returns
        -------
        list[RefinementResult]
            Results for each refinement applied.
        """
        results = []
        for suggestion in suggestions:
            result = self.refine_skill(
                skill_name=suggestion.skill_name,
                learnings=suggestion.suggested_additions,
                reason=suggestion.reason,
            )
            results.append(result)
        return results

    def _find_skill_file(self, skill_name: str) -> Path | None:
        """Locate the ``.md`` file for a skill name."""
        # Direct filename match
        candidates = [
            self.skills_dir / f"{skill_name}.md",
            self.skills_dir / f"{skill_name.lower()}.md",
            self.skills_dir / f"{skill_name.upper()}.md",
        ]
        for path in candidates:
            if path.exists():
                return path

        # Search by content (# SKILL: header)
        if self.skills_dir.exists():
            for md_file in self.skills_dir.glob("*.md"):
                try:
                    first_lines = md_file.read_text(encoding="utf-8")[:500]
                    if skill_name.upper() in first_lines.upper():
                        return md_file
                except Exception as _e:
                    logger.debug("Skipping: %s", _e)
                    continue
        return None

    @staticmethod
    def _extract_version(text: str) -> str:
        """Extract version from ## VERSION section."""
        m = re.search(r"##\s+VERSION\s*\n+\s*(.+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip().split()[0]
        return "1.0"

    @staticmethod
    def _bump_version(version: str) -> str:
        """Increment the patch component of a version string."""
        parts = version.split(".")
        try:
            parts[-1] = str(int(parts[-1]) + 1)
        except (ValueError, IndexError):
            parts.append("1")
        return ".".join(parts)

    @staticmethod
    def _update_version(text: str, old: str, new: str) -> str:
        """Replace version string in the text."""
        pattern = re.compile(
            rf"(##\s+VERSION\s*\n+\s*){re.escape(old)}",
            re.IGNORECASE,
        )
        return pattern.sub(rf"\g<1>{new}", text, count=1)
