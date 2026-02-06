"""Retrospection engine for compound engineering pattern analysis."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Path constants
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
_KG_DIR = _PROJECT_ROOT / "src" / "cohezion" / "knowledge_graph"


@dataclass
class LearningPattern:
    """A pattern extracted from KEY_LEARNINGS.md.

    Attributes
    ----------
    id : int
        Numeric learning identifier.
    title : str
        Human-readable title of the learning.
    date : str
        ISO date string (YYYY-MM-DD) if present.
    tags : list[str]
        Extracted tags (e.g. brane encodings).
    cross_references : list[str]
        References to other learnings or PRIME skills.
    compound_score : float
        Calculated compound impact score (0-1).
    """

    id: int
    title: str
    date: str
    tags: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)
    compound_score: float = 0.0


@dataclass
class SkillRefinement:
    """A suggested refinement to an existing PRIME skill.

    Attributes
    ----------
    skill_name : str
        Name of the PRIME skill to refine.
    reason : str
        Why the refinement is suggested.
    suggested_additions : list[str]
        Learning titles that inform the refinement.
    """

    skill_name: str
    reason: str
    suggested_additions: list[str] = field(default_factory=list)


class RetrospectionEngine:
    """Analyze session history and knowledge graph for compound patterns.

    Reads KEY_LEARNINGS.md and MISSION_JOURNAL.md to detect recurring
    themes, calculate compound impact scores, and suggest skill refinements.

    Parameters
    ----------
    kg_dir : Path | None
        Override path to the knowledge graph directory.
    """

    def __init__(self, kg_dir: Path | None = None) -> None:
        self.kg_dir = kg_dir or _KG_DIR
        self._learnings: list[LearningPattern] = []
        self._journal_entries: list[dict] = []

    def analyze_learnings(self) -> list[LearningPattern]:
        """Parse KEY_LEARNINGS.md, extract tagged patterns, count cross-references.

        Returns
        -------
        list[LearningPattern]
            Parsed learning patterns with tags and cross-references.
        """
        learnings_path = self.kg_dir / "KEY_LEARNINGS.md"
        if not learnings_path.exists():
            logger.warning("KEY_LEARNINGS.md not found at %s", learnings_path)
            return []

        text = learnings_path.read_text(encoding="utf-8")
        patterns: list[LearningPattern] = []

        # Parse learning blocks (## Learning N: TITLE)
        learning_re = re.compile(
            r"##\s+Learning\s+(\d+)[:\s]+(.+?)(?:\s*\((\d{4}-\d{2}-\d{2})\))?\s*$",
            re.MULTILINE,
        )

        matches = list(learning_re.finditer(text))
        for i, match in enumerate(matches):
            learning_id = int(match.group(1))
            title = match.group(2).strip()
            date = match.group(3) or ""

            # Extract body text until next learning
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end]

            # Extract tags from encoding lines
            tags: list[str] = []
            encoding_re = re.compile(r"brane=(\d+)")
            for m in encoding_re.finditer(body):
                tags.append(f"brane-{m.group(1)}")

            # Extract cross-references to other learnings/skills
            cross_refs: list[str] = []
            ref_re = re.compile(r"Learning\s+(\d+)|([A-Z_]+_PRIME)")
            for m in ref_re.finditer(body):
                ref = m.group(0)
                cross_refs.append(ref)

            pattern = LearningPattern(
                id=learning_id,
                title=title,
                date=date,
                tags=tags,
                cross_references=cross_refs,
            )
            patterns.append(pattern)

        self._learnings = patterns
        return patterns

    def calculate_compound_scores(self) -> dict[str, float]:
        """Score each learning by how often it is referenced by other learnings.

        Returns
        -------
        dict[str, float]
            Mapping of learning/skill name to compound score (0-1).
        """
        if not self._learnings:
            self.analyze_learnings()

        # Count incoming references for each learning
        ref_counts: dict[int, int] = {}
        all_refs: list[str] = []

        for pattern in self._learnings:
            for ref in pattern.cross_references:
                all_refs.append(ref)
                # Extract learning ID from "Learning N" references
                m = re.match(r"Learning\s+(\d+)", ref)
                if m:
                    ref_id = int(m.group(1))
                    ref_counts[ref_id] = ref_counts.get(ref_id, 0) + 1

        # Also count skill references
        skill_refs: dict[str, int] = {}
        for ref in all_refs:
            if "_PRIME" in ref:
                skill_refs[ref] = skill_refs.get(ref, 0) + 1

        # Normalize scores (0-1 range)
        max_count = max(ref_counts.values()) if ref_counts else 1
        scores: dict[str, float] = {}

        for pattern in self._learnings:
            incoming = ref_counts.get(pattern.id, 0)
            outgoing = len(pattern.cross_references)
            # Score = normalized(incoming refs) + 0.3 * normalized(outgoing refs)
            score = (incoming / max_count) + 0.3 * (
                outgoing / max(len(self._learnings), 1)
            )
            scores[f"Learning {pattern.id}: {pattern.title}"] = round(
                min(score, 1.0), 3
            )

        # Add skill scores
        max_skill = max(skill_refs.values()) if skill_refs else 1
        for skill, count in skill_refs.items():
            scores[skill] = round(count / max_skill, 3)

        return scores

    def generate_session_report(self, session_facts: dict) -> str:
        """Generate a structured retrospective report from session facts.

        Parameters
        ----------
        session_facts : dict
            Keys like ``"intent"``, ``"files_created"``, ``"files_modified"``,
            ``"tests_added"``, ``"tests_passing"``, ``"capabilities_used"``.

        Returns
        -------
        str
            Markdown-formatted retrospective report.
        """
        lines = ["# Session Retrospective Report", ""]

        if "intent" in session_facts:
            lines.append(f"## Intent\n{session_facts['intent']}\n")

        if "files_created" in session_facts:
            lines.append("## Files Created")
            for f in session_facts["files_created"]:
                lines.append(f"- `{f}`")
            lines.append("")

        if "files_modified" in session_facts:
            lines.append("## Files Modified")
            for f in session_facts["files_modified"]:
                lines.append(f"- `{f}`")
            lines.append("")

        if "tests_passing" in session_facts:
            lines.append(
                f"## Test Results\n- Passing: {session_facts['tests_passing']}"
            )
            if "tests_added" in session_facts:
                lines.append(f"- New: {session_facts['tests_added']}")
            lines.append("")

        if "capabilities_used" in session_facts:
            lines.append("## Capabilities Used")
            for cap in session_facts["capabilities_used"]:
                lines.append(f"- {cap}")
            lines.append("")

        # Add compound analysis
        scores = self.calculate_compound_scores()
        if scores:
            top_scores = sorted(
                scores.items(), key=lambda x: x[1], reverse=True
            )[:10]
            lines.append("## Compound Impact (Top 10)")
            for name, score in top_scores:
                lines.append(f"- {name}: {score:.3f}")
            lines.append("")

        return "\n".join(lines)

    def suggest_skill_refinements(self) -> list[SkillRefinement]:
        """Identify skills that should be updated based on usage patterns.

        Returns
        -------
        list[SkillRefinement]
            Skills with 3+ learning references that may need updating.
        """
        if not self._learnings:
            self.analyze_learnings()

        refinements: list[SkillRefinement] = []

        # Count how many learnings reference each skill
        skill_learning_map: dict[str, list[str]] = {}
        for pattern in self._learnings:
            for ref in pattern.cross_references:
                if "_PRIME" in ref:
                    if ref not in skill_learning_map:
                        skill_learning_map[ref] = []
                    skill_learning_map[ref].append(pattern.title)

        # Skills referenced by 3+ learnings might need updating
        for skill, learning_titles in skill_learning_map.items():
            if len(learning_titles) >= 3:
                refinements.append(
                    SkillRefinement(
                        skill_name=skill,
                        reason=(
                            f"Referenced by {len(learning_titles)} learnings,"
                            " may need integration of new insights"
                        ),
                        suggested_additions=learning_titles[:5],
                    )
                )

        return refinements
