"""
R-Zero Skill Improvement Pipeline
=================================
Applies Challenger/Solver/Pragmatist methodology to improve skill quality.

The R-Zero triad:
1. Challenger: Identifies weaknesses, gaps, and potential issues
2. Solver: Proposes improvements and additions
3. Pragmatist: Validates feasibility and enforces standards
"""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("r_zero_skills")


@dataclass
class SkillEvaluation:
    """Result of R-Zero evaluation on a skill."""

    skill_path: Path
    challenger_issues: list[str] = field(default_factory=list)
    solver_proposals: list[str] = field(default_factory=list)
    pragmatist_verdict: str = ""
    quality_score: float = 0.0
    improved: bool = False


@dataclass
class SkillMetrics:
    """Metrics for tracking skill improvement."""

    total_evaluated: int = 0
    total_improved: int = 0
    avg_quality_before: float = 0.0
    avg_quality_after: float = 0.0
    issues_found: int = 0
    improvements_applied: int = 0


class RZeroSkillPipeline:
    """
    Pipeline for improving skills using R-Zero methodology.
    """

    QUALITY_CRITERIA = {
        "has_domain_expertise": 10,
        "has_key_concepts": 10,
        "has_instruction": 15,
        "has_code_examples": 15,
        "has_applications": 10,
        "has_see_also": 5,
        "has_version": 5,
        "no_placeholders": 10,
        "proper_markdown": 10,
        "has_mathematical_foundation": 10,
    }

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.metrics = SkillMetrics()

    def list_skills(self) -> list[Path]:
        """List all PRIME skills."""
        return sorted(self.skills_dir.glob("*_PRIME.md"))

    def evaluate_skill(self, skill_path: Path) -> SkillEvaluation:
        """Apply R-Zero triad to evaluate a skill."""
        content = skill_path.read_text()
        evaluation = SkillEvaluation(skill_path=skill_path)

        # === CHALLENGER PHASE ===
        evaluation.challenger_issues = self._run_challenger(content)

        # === SOLVER PHASE ===
        evaluation.solver_proposals = self._run_solver(content, evaluation.challenger_issues)

        # === PRAGMATIST PHASE ===
        evaluation.pragmatist_verdict, evaluation.quality_score = self._run_pragmatist(
            content, evaluation.challenger_issues, evaluation.solver_proposals
        )

        return evaluation

    def _run_challenger(self, content: str) -> list[str]:
        """Challenger finds weaknesses and gaps."""
        issues = []

        # Check for required sections
        if "## DOMAIN EXPERTISE" not in content:
            issues.append("Missing DOMAIN EXPERTISE section")
        if "## INSTRUCTION" not in content:
            issues.append("Missing INSTRUCTION section")
        if "## KEY" not in content and "## KEY TEXTS" not in content:
            issues.append("Missing KEY TEXTS/CONCEPTS section")

        # Check for code examples
        if "```" not in content:
            issues.append("No code examples provided")
        elif content.count("```") < 4:
            issues.append("Insufficient code examples (< 2 blocks)")

        # Check for placeholders
        if "${" in content:
            issues.append("Contains template placeholders (${...})")
        if "TODO" in content.upper():
            issues.append("Contains TODO markers")

        # Check for applications
        if "## APPLICATION" not in content and "## USE" not in content:
            issues.append("Missing APPLICATIONS section")

        # Check for version
        if "## VERSION" not in content:
            issues.append("Missing VERSION section")

        # Check for cross-references
        if "## SEE ALSO" not in content:
            issues.append("Missing SEE ALSO section for skill connections")

        # Check content depth
        word_count = len(content.split())
        if word_count < 200:
            issues.append(f"Content too shallow ({word_count} words, recommend 300+)")

        return issues

    def _run_solver(self, content: str, issues: list[str]) -> list[str]:
        """Solver proposes improvements for identified issues."""
        proposals = []

        for issue in issues:
            if "DOMAIN EXPERTISE" in issue:
                proposals.append("Add ## DOMAIN EXPERTISE section with role description")
            elif "INSTRUCTION" in issue:
                proposals.append("Add ## INSTRUCTION section with step-by-step guidance")
            elif "KEY TEXTS" in issue:
                proposals.append("Add ## KEY TEXTS & CONCEPTS section with references")
            elif "code examples" in issue.lower():
                proposals.append("Add at least 3 code blocks with practical examples")
            elif "placeholder" in issue.lower():
                proposals.append("Replace all ${...} placeholders with actual content")
            elif "APPLICATION" in issue:
                proposals.append("Add ## APPLICATIONS section listing use cases")
            elif "VERSION" in issue:
                proposals.append("Add ## VERSION section (e.g., v1.0)")
            elif "SEE ALSO" in issue:
                proposals.append("Add ## SEE ALSO section linking related skills")
            elif "shallow" in issue.lower():
                proposals.append("Expand content with more detail and examples")

        return proposals

    def _run_pragmatist(
        self, content: str, issues: list[str], proposals: list[str]
    ) -> tuple[str, float]:
        """Pragmatist validates and scores the skill."""
        score = 100.0

        # Deduct points for issues
        deduction_per_issue = 100 / len(self.QUALITY_CRITERIA)
        score -= len(issues) * (deduction_per_issue * 0.7)

        # Bonus for good practices
        if "## MATHEMATICAL FOUNDATION" in content:
            score += 5
        if content.count("```python") >= 3:
            score += 5
        if "## R-ZERO" in content:
            score += 3

        score = max(0, min(100, score))

        # Verdict
        if score >= 80:
            verdict = "APPROVED - High quality skill"
        elif score >= 60:
            verdict = "NEEDS_IMPROVEMENT - Apply solver proposals"
        else:
            verdict = "REJECTED - Requires significant rework"

        return verdict, score

    def generate_report(self, evaluations: list[SkillEvaluation]) -> str:
        """Generate improvement report."""
        report = ["# R-Zero Skill Improvement Report\n"]
        report.append(f"**Generated:** {__import__('datetime').datetime.now().isoformat()}\n")
        report.append(f"**Skills Evaluated:** {len(evaluations)}\n\n")

        # Summary
        approved = sum(1 for e in evaluations if e.quality_score >= 80)
        needs_work = sum(1 for e in evaluations if 60 <= e.quality_score < 80)
        rejected = sum(1 for e in evaluations if e.quality_score < 60)

        report.append("## Summary\n")
        report.append("| Status | Count |\n")
        report.append("|--------|-------|\n")
        report.append(f"| ✅ Approved | {approved} |\n")
        report.append(f"| ⚠️ Needs Improvement | {needs_work} |\n")
        report.append(f"| ❌ Rejected | {rejected} |\n\n")

        # Details
        report.append("## Detailed Evaluations\n\n")
        for eval in sorted(evaluations, key=lambda e: e.quality_score):
            status_icon = (
                "✅" if eval.quality_score >= 80 else ("⚠️" if eval.quality_score >= 60 else "❌")
            )
            report.append(f"### {status_icon} {eval.skill_path.name}\n")
            report.append(f"**Score:** {eval.quality_score:.1f}/100\n")
            report.append(f"**Verdict:** {eval.pragmatist_verdict}\n\n")

            if eval.challenger_issues:
                report.append("**Challenger Issues:**\n")
                for issue in eval.challenger_issues:
                    report.append(f"- {issue}\n")
                report.append("\n")

            if eval.solver_proposals:
                report.append("**Solver Proposals:**\n")
                for proposal in eval.solver_proposals:
                    report.append(f"- {proposal}\n")
                report.append("\n")

        return "".join(report)


async def main():
    """Run R-Zero improvement on all skills."""
    skills_dir = Path("src/cohezion/skills")
    pipeline = RZeroSkillPipeline(skills_dir)

    skills = pipeline.list_skills()
    logger.info(f"Found {len(skills)} PRIME skills")

    evaluations = []
    for skill_path in skills:
        eval_result = pipeline.evaluate_skill(skill_path)
        evaluations.append(eval_result)
        logger.info(
            f"{skill_path.name}: {eval_result.quality_score:.1f}/100 - {eval_result.pragmatist_verdict}"
        )

    # Generate report
    report = pipeline.generate_report(evaluations)
    report_path = Path("docs/R_ZERO_SKILL_REPORT.md")
    report_path.write_text(report)
    logger.info(f"Report saved to {report_path}")

    # Summary stats
    avg_score = sum(e.quality_score for e in evaluations) / len(evaluations) if evaluations else 0
    logger.info(f"Average skill quality: {avg_score:.1f}/100")


if __name__ == "__main__":
    asyncio.run(main())
