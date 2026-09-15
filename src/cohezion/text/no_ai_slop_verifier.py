"""No AI Slop Verifier and Style Auditor.

Deterministic linter and sanitizer based on petergyang/no-ai-slop.
Detects and neutralizes 20+ patterns of AI slop, boilerplate metadiscourse,
and banned buzzwords while preserving authentic technical voice.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


BANNED_WORDS = [
    "delve",
    "foster",
    "leverage",
    "utilize",
    "facilitate",
    "empower",
    "streamline",
    "robust",
    "cutting-edge",
    "paradigm shift",
    "game changer",
    "this is huge",
    "this changes everything",
    "tapestry",
    "realm",
    "beacon",
    "multifaceted",
    "meticulous",
    "intricate",
    "paramount",
    "transformative",
    "elevate",
    "embark",
    "supercharge",
    "ever-evolving",
]

THROAT_CLEARING_PATTERNS = [
    (r"\b(?:here's the thing|here is the thing)\b", "Directly state the point instead of clearing your throat."),
    (r"\b(?:let me be clear)\b", "Cut conversational filler and state the claim."),
    (r"\b(?:the uncomfortable truth is)\b", "State the finding directly."),
    (r"\b(?:i'll be honest|to be completely honest)\b", "Cut filler; be direct."),
    (r"\b(?:at the end of the day)\b", "State the core conclusion directly."),
    (r"\b(?:it's worth noting that|it is worth noting that)\b", "State the note directly without prefacing."),
    (r"\b(?:it's important to note that|it is important to note that)\b", "State the fact directly."),
    (r"\b(?:in today's world|in today's fast-paced world)\b", "Cut temporal platitude."),
    (r"\b(?:in the age of ai)\b", "Specify the concrete context or cut."),
    (r"\b(?:let's dive in|let us dive in)\b", "Cut introductory fluff and start with substance."),
]

FAUX_INSIGHT_PATTERNS = [
    (r"\b(?:what most people (?:get wrong|miss|overlook))\b", "State your thesis or finding without flattering yourself."),
    (r"\b(?:here's what nobody tells you|what nobody tells you)\b", "State the mechanism or truth directly."),
    (r"\b(?:this is the part most people skip)\b", "Explain why the step matters without dramatic framing."),
    (r"\b(?:the part everyone misses)\b", "State the critical factor plainly."),
]

IMPORTANCE_PUFFERY_PATTERNS = [
    (r"\b(?:stands as a testament)\b", "State the concrete accomplishment or evidence."),
    (r"\b(?:marks a pivotal moment)\b", "State the milestone and its measurable effect."),
    (r"\b(?:plays a vital role)\b", "Specify the exact responsibility or mechanism."),
    (r"\b(?:solidifies its position)\b", "State the benchmark or outcome directly."),
    (r"\b(?:underscores the significance of)\b", "Show the evidence instead of telling the reader it is significant."),
]

METADISCOURSE_PATTERNS = [
    (r"\b(?:that last part matters more than it sounds)\b", "Cut meta-commentary; explain the mechanism."),
    (r"\b(?:as you can see)\b", "Cut filler phrase."),
    (r"\b(?:in other words)\b", "Cut redundant rephrasing if the first sentence is clear."),
]

WEASEL_ATTRIBUTION_PATTERNS = [
    (r"\b(?:experts agree that)\b", "Cite the specific author, paper, or benchmark."),
    (r"\b(?:studies show that)\b", "Name the study, dataset, or experiment."),
    (r"\b(?:widely regarded as)\b", "Provide supporting evidence or metric."),
]

SUMMARY_RECAP_PATTERNS = [
    (r"^\s*(?:in conclusion,|in summary,|to wrap up,|ultimately,)", "End on the final concrete takeaway, code, or next step."),
]


@dataclass
class SlopViolation:
    category: str
    line_number: int
    snippet: str
    recommendation: str
    severity: str = "warning"


@dataclass
class SlopAuditReport:
    violations: list[SlopViolation] = field(default_factory=list)
    score: float = 1.0
    total_words: int = 0
    clean_content: str | None = None

    @property
    def is_clean(self) -> bool:
        return len(self.violations) == 0


class NoAiSlopVerifier:
    """Audits and cleans text to remove AI slop patterns."""

    def __init__(self, banned_words: list[str] | None = None) -> None:
        self.banned_words = banned_words or BANNED_WORDS
        self._compile_regexes()

    def _compile_regexes(self) -> None:
        word_pattern = r"\b(" + "|".join(re.escape(w) for w in self.banned_words) + r")\b"
        self.banned_re = re.compile(word_pattern, re.IGNORECASE)

        self.throat_res = [
            (re.compile(pat, re.IGNORECASE), rec) for pat, rec in THROAT_CLEARING_PATTERNS
        ]
        self.faux_res = [
            (re.compile(pat, re.IGNORECASE), rec) for pat, rec in FAUX_INSIGHT_PATTERNS
        ]
        self.puffery_res = [
            (re.compile(pat, re.IGNORECASE), rec) for pat, rec in IMPORTANCE_PUFFERY_PATTERNS
        ]
        self.meta_res = [
            (re.compile(pat, re.IGNORECASE), rec) for pat, rec in METADISCOURSE_PATTERNS
        ]
        self.weasel_res = [
            (re.compile(pat, re.IGNORECASE), rec) for pat, rec in WEASEL_ATTRIBUTION_PATTERNS
        ]
        self.recap_res = [
            (re.compile(pat, re.IGNORECASE), rec) for pat, rec in SUMMARY_RECAP_PATTERNS
        ]

    def audit_text(self, text: str) -> SlopAuditReport:
        """Audits text line-by-line, skipping code blocks and frontmatter."""
        lines = text.splitlines()
        violations: list[SlopViolation] = []
        in_code_block = False
        in_frontmatter = False

        total_words = len(re.findall(r"\w+", text))

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if idx == 1 and stripped == "---":
                in_frontmatter = True
                continue
            if in_frontmatter:
                if stripped == "---":
                    in_frontmatter = False
                continue

            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            # Check banned words
            for match in self.banned_re.finditer(line):
                violations.append(
                    SlopViolation(
                        category="banned_word",
                        line_number=idx,
                        snippet=match.group(0),
                        recommendation=f"Remove or replace AI buzzword '{match.group(0)}' with concrete action.",
                    )
                )

            # Check throat-clearing
            for pattern, rec in self.throat_res:
                for match in pattern.finditer(line):
                    violations.append(
                        SlopViolation(
                            category="throat_clearing",
                            line_number=idx,
                            snippet=match.group(0),
                            recommendation=rec,
                        )
                    )

            # Check faux-insight
            for pattern, rec in self.faux_res:
                for match in pattern.finditer(line):
                    violations.append(
                        SlopViolation(
                            category="faux_insight",
                            line_number=idx,
                            snippet=match.group(0),
                            recommendation=rec,
                        )
                    )

            # Check puffery
            for pattern, rec in self.puffery_res:
                for match in pattern.finditer(line):
                    violations.append(
                        SlopViolation(
                            category="importance_puffery",
                            line_number=idx,
                            snippet=match.group(0),
                            recommendation=rec,
                        )
                    )

            # Check metadiscourse
            for pattern, rec in self.meta_res:
                for match in pattern.finditer(line):
                    violations.append(
                        SlopViolation(
                            category="metadiscourse",
                            line_number=idx,
                            snippet=match.group(0),
                            recommendation=rec,
                        )
                    )

            # Check weasel attribution
            for pattern, rec in self.weasel_res:
                for match in pattern.finditer(line):
                    violations.append(
                        SlopViolation(
                            category="weasel_attribution",
                            line_number=idx,
                            snippet=match.group(0),
                            recommendation=rec,
                        )
                    )

            # Check summary recap
            for pattern, rec in self.recap_res:
                for match in pattern.finditer(line):
                    violations.append(
                        SlopViolation(
                            category="summary_recap",
                            line_number=idx,
                            snippet=match.group(0),
                            recommendation=rec,
                        )
                    )

        # Calculate score (1.0 = perfect, deducted per violation normalized)
        penalty = len(violations) * 0.05
        score = max(0.0, 1.0 - penalty)

        return SlopAuditReport(
            violations=violations,
            score=round(score, 3),
            total_words=total_words,
        )

    def clean_text(self, text: str) -> tuple[str, list[str]]:
        """Applies automated deterministic replacements for common slop patterns."""
        lines = text.splitlines()
        new_lines: list[str] = []
        changes: list[str] = []
        in_code_block = False
        in_frontmatter = False

        replacements = [
            (re.compile(r"\butilize\b", re.I), "use"),
            (re.compile(r"\butilized\b", re.I), "used"),
            (re.compile(r"\butilizing\b", re.I), "using"),
            (re.compile(r"\bleverage\b", re.I), "use"),
            (re.compile(r"\bleveraged\b", re.I), "used"),
            (re.compile(r"\bleveraging\b", re.I), "using"),
            (re.compile(r"\bfacilitate\b", re.I), "help"),
            (re.compile(r"\bfacilitates\b", re.I), "helps"),
            (re.compile(r"\bstreamline\b", re.I), "simplify"),
            (re.compile(r"\bstreamlines\b", re.I), "simplifies"),
            (re.compile(r"\brobust\b", re.I), "reliable"),
            (re.compile(r"\bcutting-edge\b", re.I), "modern"),
            (re.compile(r"\bparamount\b", re.I), "essential"),
            (re.compile(r"\btransformative\b", re.I), "significant"),
            (re.compile(r"\belevate\b", re.I), "improve"),
            (re.compile(r"\bsupercharge\b", re.I), "accelerate"),
            (re.compile(r"\bdelve into\b", re.I), "examine"),
            (re.compile(r"\bdelve\b", re.I), "explore"),
            (re.compile(r"\bIt's worth noting that\s*", re.I), ""),
            (re.compile(r"\bIt is worth noting that\s*", re.I), ""),
            (re.compile(r"\bIt's important to note that\s*", re.I), ""),
            (re.compile(r"\bAt the end of the day,\s*", re.I), ""),
            (re.compile(r"\bHere's the thing:\s*", re.I), ""),
            (re.compile(r"\bLet me be clear:\s*", re.I), ""),
        ]

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if idx == 1 and stripped == "---":
                in_frontmatter = True
                new_lines.append(line)
                continue
            if in_frontmatter:
                if stripped == "---":
                    in_frontmatter = False
                new_lines.append(line)
                continue

            if stripped.startswith("```"):
                in_code_block = not in_code_block
                new_lines.append(line)
                continue

            if in_code_block:
                new_lines.append(line)
                continue

            current_line = line
            for pat, repl in replacements:
                if pat.search(current_line):
                    new_line = pat.sub(repl, current_line)
                    changes.append(f"Line {idx}: '{current_line.strip()}' -> '{new_line.strip()}'")
                    current_line = new_line

            new_lines.append(current_line)

        return "\n".join(new_lines), changes


def main() -> int:
    parser = argparse.ArgumentParser(description="No AI Slop text and markdown verifier")
    parser.add_argument("paths", nargs="+", help="Files or directories to audit")
    parser.add_argument("--fix", action="store_true", help="Apply automated cleanups in-place")
    parser.add_argument("--min-score", type=float, default=0.8, help="Minimum passing score (default: 0.8)")
    args = parser.parse_args()

    verifier = NoAiSlopVerifier()
    total_violations = 0
    failed_files = 0

    for path_str in args.paths:
        path = Path(path_str)
        files = [path] if path.is_file() else list(path.glob("**/*.md"))
        for f in files:
            if any(x in f.parts for x in [".git", ".venv", "site-packages", "node_modules"]):
                continue
            try:
                content = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            report = verifier.audit_text(content)
            if not report.is_clean:
                total_violations += len(report.violations)
                status = "FAIL" if report.score < args.min_score else "WARN"
                print(f"[{status}] {f} (Score: {report.score:.2f}, Violations: {len(report.violations)})")
                for v in report.violations[:5]:
                    print(f"    L{v.line_number}: [{v.category}] '{v.snippet}' -> {v.recommendation}")
                if len(report.violations) > 5:
                    print(f"    ... and {len(report.violations) - 5} more")

                if report.score < args.min_score:
                    failed_files += 1

                if args.fix:
                    cleaned, changes = verifier.clean_text(content)
                    if changes:
                        f.write_text(cleaned, encoding="utf-8")
                        print(f"    [FIXED] Applied {len(changes)} corrections in {f}")

    if failed_files > 0:
        print(f"\nAudit failed: {failed_files} file(s) below minimum score {args.min_score}")
        return 1

    print(f"\nAudit passed. Total violations: {total_violations}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
