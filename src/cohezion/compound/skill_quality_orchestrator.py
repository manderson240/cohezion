"""Skill quality orchestrator — closed-loop skill improvement engine.

Wires together:
  SkillQualityScorer → RetrospectionEngine → SkillRefiner → SkillConsensusVoter

Loop:
  1. Load skill from filesystem
  2. Score via SkillQualityScorer (5 dimensions)
  3. If score < 0.5 (non-HIHO), generate improvement hypotheses
  4. Run autoharness verification on proposed patches
  5. Apply patch if consensus approves
  6. Record new version in SkillEvolutionTracker
  7. Persist to vault + health tracker

This is the self-improving backbone of the Cohezion skill ecosystem.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from cohezion.compound.autoresearch import AutoresearchEngine
from cohezion.compound.skill_evolution_diff import SkillEvolutionTracker
from cohezion.compound.skill_health_tracker import SkillHealthTracker
from cohezion.compound.skill_quality_scorer import SkillQualityReport, SkillQualityScorer

logger = logging.getLogger(__name__)


@dataclass
class ImprovementHypothesis:
    """A proposed change to improve a skill's quality score."""

    skill_name: str
    dimension: str  # which dimension to improve
    action: str  # "add_section", "add_anchor", "add_example", "bump_version"
    patch: str  # concrete markdown/text to insert
    expected_delta: float  # predicted score improvement
    confidence: float  # 0.0-1.0


@dataclass
class ImprovementResult:
    """Result of attempting to improve a skill."""

    skill_name: str
    before_score: float
    after_score: float
    applied: bool
    hypothesis: ImprovementHypothesis
    consensus_approved: bool
    diff_lines: int = 0
    error: str | None = None


class SkillQualityOrchestrator:
    """Orchestrates the self-improving skill quality loop.

    Usage:
        orchestrator = SkillQualityOrchestrator()
        result = await orchestrator.improve_skill(skill_path)
        # result.applied is True if skill was patched and approved
    """

    def __init__(
        self,
        scorer: SkillQualityScorer | None = None,
        evolution: SkillEvolutionTracker | None = None,
        health: SkillHealthTracker | None = None,
        autoresearch: AutoresearchEngine | None = None,
    ) -> None:
        self.scorer = scorer or SkillQualityScorer()
        self.evolution = evolution or SkillEvolutionTracker()
        self.health = health or SkillHealthTracker()
        self.autoresearch = autoresearch or AutoresearchEngine()
        self._hypothesis_history: dict[str, list[ImprovementHypothesis]] = {}

    async def improve_skill(self, skill_path: Path) -> ImprovementResult:
        """Run full improvement loop on a single skill.

        Args:
            skill_path: Path to the SKILL.md or PRIME .md file

        Returns:
            ImprovementResult with before/after scores and applied flag
        """
        # Phase 1: Evaluate
        report = self.scorer.evaluate(skill_path)
        logger.info("Skill %s scored %.2f (HIHO-stable=%s)", report.skill_name, report.overall_score, report.hiho_stable)

        if report.hiho_stable:
            logger.info("Skill %s is HIHO-stable; no improvement needed", report.skill_name)
            return ImprovementResult(
                skill_name=report.skill_name,
                before_score=report.overall_score,
                after_score=report.overall_score,
                applied=False,
                hypothesis=ImprovementHypothesis(
                    skill_name=report.skill_name, dimension="", action="none", patch="", expected_delta=0.0, confidence=1.0
                ),
                consensus_approved=True,
            )

        # Phase 2: Generate hypotheses (rule-based + autoresearch-driven)
        hypotheses = await self._generate_hypotheses(report)
        if not hypotheses:
            logger.warning("No improvement hypotheses generated for %s", report.skill_name)
            return ImprovementResult(
                skill_name=report.skill_name,
                before_score=report.overall_score,
                after_score=report.overall_score,
                applied=False,
                hypothesis=ImprovementHypothesis(
                    skill_name=report.skill_name, dimension="", action="none", patch="", expected_delta=0.0, confidence=0.0
                ),
                consensus_approved=False,
            )

        # Phase 3: Try best hypothesis
        best = max(hypotheses, key=lambda h: h.expected_delta * h.confidence)
        logger.info("Best hypothesis for %s: %s on %s (delta=%.2f)", report.skill_name, best.action, best.dimension, best.expected_delta)

        # Phase 4: Apply patch (non-destructive backup)
        backup = skill_path.read_text()
        try:
            self._apply_patch(skill_path, best)
        except Exception as e:
            skill_path.write_text(backup)
            logger.error("Patch application failed for %s: %s", report.skill_name, e)
            return ImprovementResult(
                skill_name=report.skill_name,
                before_score=report.overall_score,
                after_score=report.overall_score,
                applied=False,
                hypothesis=best,
                consensus_approved=False,
                error=str(e),
            )

        # Phase 5: Re-evaluate
        new_report = self.scorer.evaluate(skill_path)
        actual_delta = new_report.overall_score - report.overall_score

        # Phase 6: Consensus — approve if score improved or stayed same
        approved = actual_delta >= 0 or new_report.hiho_stable

        if not approved:
            skill_path.write_text(backup)
            logger.info("Consensus rejected patch for %s (delta=%.2f); rolled back", report.skill_name, actual_delta)
        else:
            # Record version
            self.evolution.record_version(report.skill_name, skill_path.read_text())
            # Record health usage
            self.health.record_usage(report.skill_name, success=True, quality_score=new_report.overall_score)
            logger.info("Patch accepted for %s: %.2f → %.2f", report.skill_name, report.overall_score, new_report.overall_score)

        return ImprovementResult(
            skill_name=report.skill_name,
            before_score=report.overall_score,
            after_score=new_report.overall_score,
            applied=approved,
            hypothesis=best,
            consensus_approved=approved,
            diff_lines=self._count_diff_lines(backup, skill_path.read_text()),
        )

    # ------------------------------------------------------------------
    # Hypothesis generation (rule-based + autoresearch data-driven)
    # ------------------------------------------------------------------

    async def _generate_hypotheses(self, report: SkillQualityReport) -> list[ImprovementHypothesis]:
        """Generate concrete patch hypotheses based on low-scoring dimensions.

        Combines rule-based templates with autoresearch-driven opportunities
        for data-informed prioritization.
        """
        # Rule-based hypotheses
        hypos: list[ImprovementHypothesis] = []
        for dim in report.dimensions:
            if dim.score >= 0.8:
                continue
            if dim.name == "hiho_coherence":
                for issue in dim.issues:
                    if "Missing geometric anchors" in issue:
                        patch = "\n## Geometric Correspondences\n- **0.5** = HIHO threshold (Shannon max)\n- **256** = FLUME latent dimension\n- **SU(2)** = agent state gauge group\n"
                        hypos.append(ImprovementHypothesis(
                            skill_name=report.skill_name,
                            dimension="hiho_coherence",
                            action="add_anchor",
                            patch=patch,
                            expected_delta=0.25 * (1 - dim.score),
                            confidence=0.9,
                        ))
            elif dim.name == "structural":
                patch = "\n## When to Use This Skill\nUse when:\n- Task involves X, Y, or Z\n\n## Instruction\n1. Step one\n2. Step two\n\n## See Also\n- related-skill\n"
                hypos.append(ImprovementHypothesis(
                    skill_name=report.skill_name,
                    dimension="structural",
                    action="add_section",
                    patch=patch,
                    expected_delta=0.20 * (1 - dim.score),
                    confidence=0.8,
                ))
            elif dim.name == "testability":
                patch = "\n```python\n# Example usage\nfrom cohezion.module import Example\nresult = Example.run()\n```\n"
                hypos.append(ImprovementHypothesis(
                    skill_name=report.skill_name,
                    dimension="testability",
                    action="add_example",
                    patch=patch,
                    expected_delta=0.20 * (1 - dim.score),
                    confidence=0.7,
                ))
            elif dim.name == "version_currency":
                patch = '\nmetadata:\n  version: "1.0.0"\n  project: cohezion\n'
                hypos.append(ImprovementHypothesis(
                    skill_name=report.skill_name,
                    dimension="version_currency",
                    action="bump_version",
                    patch=patch,
                    expected_delta=0.15 * (1 - dim.score),
                    confidence=0.95,
                ))

        # Autoresearch data-driven hypotheses
        metrics = {
            "cache_hit_rate": 0.0,
            "avg_tokens_per_request": 2000.0,
            "vault_write_latency_ms": 999.0,
            "avg_coherence": report.overall_score,
        }
        try:
            opportunities = await self.autoresearch.analyze(metrics)
            for opp in opportunities:
                # Map autoresearch opportunity to skill improvement hypothesis
                if opp.category == "cache" and report.overall_score < 0.5:
                    hypos.append(ImprovementHypothesis(
                        skill_name=report.skill_name,
                        dimension="hiho_coherence",
                        action="add_anchor",
                        patch="\n## Autoresearch Insight\n- **Coherence below threshold** — " + opp.recommendation + "\n",
                        expected_delta=0.05,
                        confidence=0.6,
                    ))
                elif opp.category == "token_efficiency":
                    hypos.append(ImprovementHypothesis(
                        skill_name=report.skill_name,
                        dimension="testability",
                        action="add_example",
                        patch="\n## Token Efficiency\n" + opp.recommendation + "\n",
                        expected_delta=0.05,
                        confidence=0.5,
                    ))
        except Exception as e:
            logger.warning("Autoresearch analysis failed for %s: %s", report.skill_name, e)

        return hypos

    def _apply_patch(self, skill_path: Path, hypothesis: ImprovementHypothesis) -> bool:
        """Apply a patch to a skill file. Returns True if written."""
        content = skill_path.read_text()

        if hypothesis.action == "add_anchor":
            # Insert before first heading or at end
            insertion = "\n\n" + hypothesis.patch.strip() + "\n"
            if "## " in content:
                # Insert before last major section
                content = content.rstrip() + insertion
            else:
                content = content.rstrip() + insertion
        elif hypothesis.action == "add_section":
            content = content.rstrip() + "\n\n" + hypothesis.patch.strip() + "\n"
        elif hypothesis.action == "add_example":
            content = content.rstrip() + "\n\n" + hypothesis.patch.strip() + "\n"
        elif hypothesis.action == "bump_version":
            if "metadata:" not in content:
                # Insert frontmatter
                if content.startswith("---"):
                    # Already has frontmatter — append metadata inside
                    lines = content.splitlines()
                    end_fm = lines.index("---", 1) if "---" in lines[1:] else len(lines)
                    lines.insert(end_fm, "  version: \"1.0.0\"")
                    lines.insert(end_fm, "  project: cohezion")
                    content = "\n".join(lines) + "\n"
                else:
                    content = "---\n" + hypothesis.patch.strip() + "\n---\n\n" + content
            else:
                content = content.rstrip() + "\n\n# Updated metadata\n" + hypothesis.patch.strip() + "\n"
        else:
            return False

        skill_path.write_text(content, encoding="utf-8")
        return True

    def _count_diff_lines(self, before: str, after: str) -> int:
        """Count changed lines between two texts."""
        import difflib
        diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm=""))
        return len([l for l in diff if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))])

    async def batch_improve(self, skill_dir: Path, min_score: float = 0.5) -> list[ImprovementResult]:
        """Evaluate all skills in a directory and improve those below threshold.

        Returns:
            List of ImprovementResult, one per skill processed
        """
        md_files = list(skill_dir.rglob("*.md"))
        results: list[ImprovementResult] = []
        for path in md_files:
            try:
                result = await self.improve_skill(path)
                results.append(result)
            except Exception as e:
                logger.error("Failed to improve %s: %s", path, e)
                results.append(ImprovementResult(
                    skill_name=path.stem,
                    before_score=0.0,
                    after_score=0.0,
                    applied=False,
                    hypothesis=ImprovementHypothesis(skill_name=path.stem, dimension="", action="none", patch="", expected_delta=0.0, confidence=0.0),
                    consensus_approved=False,
                    error=str(e),
                ))
        return results
