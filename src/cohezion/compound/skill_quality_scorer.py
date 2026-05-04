"""Skill quality scoring harness for the self-improving skill ecosystem.

Evaluates PRIME/Hermes skills across multiple quality dimensions:
- HIHO coherence (geometric anchor references)
- Structural completeness (frontmatter, sections, linked files)
- Testability (code examples that can be executed)
- Version currency (fresh metadata)
- Usage health (from SkillHealthTracker)

Produces a normalized 0.0-1.0 quality score with per-dimension breakdowns.
Scores feed the SkillQualityOrchestrator for autoresearch-driven improvement.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cohezion.compound.skill_health_tracker import SkillHealthTracker


logger = logging.getLogger(__name__)


@dataclass
class DimensionScore:
    """Score for a single quality dimension."""

    name: str
    score: float  # 0.0-1.0
    weight: float
    issues: list[str] = field(default_factory=list)

    @property
    def weighted(self) -> float:
        return self.score * self.weight


@dataclass
class SkillQualityReport:
    """Full quality evaluation for a single skill."""

    skill_name: str
    skill_path: Path
    overall_score: float  # 0.0-1.0 weighted composite
    dimensions: list[DimensionScore]
    hiho_stable: bool  # overall_score >= 0.5
    actionable_recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "skill_path": str(self.skill_path),
            "overall_score": round(self.overall_score, 3),
            "hiho_stable": self.hiho_stable,
            "dimensions": [
                {"name": d.name, "score": round(d.score, 3), "weight": d.weight, "issues": d.issues}
                for d in self.dimensions
            ],
            "recommendations": self.actionable_recommendations,
        }


class SkillQualityScorer:
    """Evaluates skill quality across structured dimensions.

    Weights default to geometric priority:
    - hiho_coherence 0.25  (must reference 0.5, 256, SU(2))
    - structural 0.20      (frontmatter, description, instruction, see_also)
    - testability 0.20     (code examples, linked references)
    - version_currency 0.15  (version, metadata freshness)
    - usage_health 0.20    (from SkillHealthTracker if available)
    """

    # Geometric anchors that define HIHO-stable skills
    HIHO_ANCHORS = ["0.5", "256", "SU(2)", "HIHO", "FLUME"]
    STRUCTURAL_SECTIONS = ["description", "instruction", "see also", "when to use"]

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        health_tracker: SkillHealthTracker | None = None,
    ) -> None:
        self.weights = weights or {
            "hiho_coherence": 0.25,
            "structural": 0.20,
            "testability": 0.20,
            "version_currency": 0.15,
            "usage_health": 0.20,
        }
        self._health = health_tracker

    def evaluate(self, skill_path: Path, skill_name: str = "") -> SkillQualityReport:
        """Evaluate a single skill file and return a quality report.

        Args:
            skill_path: Path to the SKILL.md or PRIME .md file
            skill_name: Optional name override (extracted from file if empty)

        Returns:
            SkillQualityReport with per-dimension scores and recommendations
        """
        if not skill_path.exists():
            return self._empty_report(skill_name or skill_path.stem, skill_path)

        content = skill_path.read_text(encoding="utf-8")
        name = skill_name or self._extract_name(content, skill_path.stem)

        dims: list[DimensionScore] = [
            self._score_hiho(content, name),
            self._score_structural(content, name),
            self._score_testability(content, name),
            self._score_version(content, name),
            self._score_usage(name),
        ]

        total_weight = sum(d.weight for d in dims)
        overall = sum(d.weighted for d in dims) / total_weight if total_weight > 0 else 0.0

        recs = self._generate_recommendations(dims)

        return SkillQualityReport(
            skill_name=name,
            skill_path=skill_path,
            overall_score=overall,
            dimensions=dims,
            hiho_stable=overall >= 0.5,
            actionable_recommendations=recs,
        )

    # ------------------------------------------------------------------
    # Dimension scorers
    # ------------------------------------------------------------------

    def _score_hiho(self, content: str, name: str) -> DimensionScore:
        """Score geometric anchor references (0.5, 256D, SU(2), HIHO, FLUME)."""
        found = sum(1 for anchor in self.HIHO_ANCHORS if anchor in content)
        score = found / len(self.HIHO_ANCHORS)
        issues = []
        if score < 1.0:
            missing = [a for a in self.HIHO_ANCHORS if a not in content]
            issues.append(f"Missing geometric anchors: {', '.join(missing)}")
        return DimensionScore(name="hiho_coherence", score=score, weight=self.weights["hiho_coherence"], issues=issues)

    def _score_structural(self, content: str, name: str) -> DimensionScore:
        """Score presence of required sections."""
        content_lower = content.lower()
        found = sum(1 for sec in self.STRUCTURAL_SECTIONS if sec in content_lower)
        score = found / len(self.STRUCTURAL_SECTIONS)
        issues = []
        if "---" not in content[:200]:
            issues.append("Missing YAML frontmatter")
            score = max(score - 0.2, 0.0)
        if score < 1.0:
            missing = [s for s in self.STRUCTURAL_SECTIONS if s not in content_lower]
            issues.append(f"Missing sections: {', '.join(missing)}")
        return DimensionScore(name="structural", score=score, weight=self.weights["structural"], issues=issues)

    def _score_testability(self, content: str, name: str) -> DimensionScore:
        """Score presence of executable code examples and linked references."""
        code_blocks = len(re.findall(r"```python", content))
        has_references = "references/" in content or "see also" in content.lower()
        score = min(1.0, (code_blocks * 0.25) + (0.3 if has_references else 0.0))
        issues = []
        if code_blocks == 0:
            issues.append("No executable Python code examples")
        if not has_references:
            issues.append("No linked references or See Also section")
        return DimensionScore(name="testability", score=score, weight=self.weights["testability"], issues=issues)

    def _score_version(self, content: str, name: str) -> DimensionScore:
        """Score version currency and metadata completeness."""
        has_version = bool(re.search(r'version:\s*"?[\d.]+"?', content))
        has_project = "project:" in content.lower()
        has_metadata = "metadata:" in content.lower()
        score = sum([has_version, has_project, has_metadata]) / 3.0
        issues = []
        if not has_version:
            issues.append("Missing version in frontmatter")
        if not has_project:
            issues.append("Missing project field")
        if not has_metadata:
            issues.append("Missing metadata block")
        return DimensionScore(name="version_currency", score=score, weight=self.weights["version_currency"], issues=issues)

    def _score_usage(self, name: str) -> DimensionScore:
        """Score from SkillHealthTracker if available; default neutral if not tracked."""
        if self._health is None:
            return DimensionScore(name="usage_health", score=0.5, weight=self.weights["usage_health"], issues=["No health tracker attached"])
        record = self._health.get_health(name)
        if record is None:
            return DimensionScore(name="usage_health", score=0.3, weight=self.weights["usage_health"], issues=["Skill never used"])
        score = record.health_score
        issues = []
        if score < 0.5:
            issues.append(f"Health score {score:.2f} below HIHO threshold")
        if record.total_invocations < 3:
            issues.append(f"Only {record.total_invocations} invocations (insufficient data)")
        return DimensionScore(name="usage_health", score=score, weight=self.weights["usage_health"], issues=issues)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_name(self, content: str, fallback: str) -> str:
        """Extract skill name from frontmatter or first heading."""
        m = re.search(r'^name:\s*(\S+)', content, re.MULTILINE)
        if m:
            return m.group(1).strip()
        m = re.search(r'^#\s*SKILL:\s*(\S+)', content, re.MULTILINE)
        if m:
            return m.group(1).strip()
        return fallback

    def _generate_recommendations(self, dims: list[DimensionScore]) -> list[str]:
        """Turn low scores into actionable recommendations."""
        recs = []
        for d in dims:
            if d.score < 0.5:
                for issue in d.issues:
                    recs.append(f"[{d.name}] {issue}")
        return recs

    def _empty_report(self, name: str, path: Path) -> SkillQualityReport:
        dims = [
            DimensionScore("hiho_coherence", 0.0, self.weights["hiho_coherence"], ["Skill file not found"]),
            DimensionScore("structural", 0.0, self.weights["structural"], ["Skill file not found"]),
            DimensionScore("testability", 0.0, self.weights["testability"], ["Skill file not found"]),
            DimensionScore("version_currency", 0.0, self.weights["version_currency"], ["Skill file not found"]),
            DimensionScore("usage_health", 0.0, self.weights["usage_health"], ["Skill file not found"]),
        ]
        return SkillQualityReport(
            skill_name=name,
            skill_path=path,
            overall_score=0.0,
            dimensions=dims,
            hiho_stable=False,
            actionable_recommendations=["Skill file missing — create or restore"],
        )

    def batch_evaluate(self, skill_paths: list[Path]) -> list[SkillQualityReport]:
        """Evaluate multiple skills and return sorted by overall_score ascending (worst first)."""
        reports = [self.evaluate(p) for p in skill_paths]
        return sorted(reports, key=lambda r: r.overall_score)
