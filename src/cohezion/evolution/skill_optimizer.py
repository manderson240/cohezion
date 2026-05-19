"""Wires ReflectionOptimizer into Cohezion's PRIME skill files.

Provides SkillOptimizer: reads a PRIME .md skill, wraps its Instructions
section as a trainable Variable, runs ReflectionOptimizer using LearningSignal
feedback as gradients, and rewrites the PRIME file when improvement is confirmed.

Called by SkillRefiner.refine() when confidence >= threshold and Lemonade is up.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from cohezion.evolution.reflection_optimizer import ReflectionOptimizer
from cohezion.evolution.variable import from_prime_section


logger = logging.getLogger(__name__)

# Default model — DeepSeek-Qwen3-8B is fast and capable on local iGPU
_DEFAULT_MODEL = "DeepSeek-Qwen3-8B-GGUF:latest"
# Sections of PRIME .md files that can be optimized
_TRAINABLE_SECTIONS = ("Instructions", "Procedure", "Rules", "Guidelines", "Steps")


def _parse_prime_sections(content: str) -> dict[str, str]:
    """Split a PRIME markdown file into named sections.

    Returns a dict mapping section header names to their content.
    The 'frontmatter' key holds the YAML front-matter block.
    """
    sections: dict[str, str] = {}

    # Extract YAML front-matter
    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if fm_match:
        sections["frontmatter"] = f"---\n{fm_match.group(1)}\n---"
        rest = content[fm_match.end() :]
    else:
        sections["frontmatter"] = ""
        rest = content

    # Split remaining content by level-2 headers (## Heading)
    parts = re.split(r"^(#{1,3} .+)$", rest, flags=re.MULTILINE)
    current_header = "_preamble"
    buf = ""
    for part in parts:
        if re.match(r"^#{1,3} ", part):
            if buf.strip():
                sections[current_header] = buf.strip()
            current_header = part.strip().lstrip("#").strip()
            buf = part + "\n"
        else:
            buf += part
    if buf.strip():
        sections[current_header] = buf.strip()

    return sections


def _rebuild_prime(sections: dict[str, str]) -> str:
    """Reassemble a PRIME .md file from parsed sections."""
    parts = []
    if sections.get("frontmatter"):
        parts.append(sections["frontmatter"])
        parts.append("")

    # Preserve original order: preamble first, then sections in insertion order
    for key, value in sections.items():
        if key in ("frontmatter", "_preamble"):
            if key == "_preamble" and value:
                parts.append(value)
        else:
            parts.append(value)

    return "\n\n".join(p for p in parts if p) + "\n"


class SkillOptimizer:
    """Applies Autogenesis-inspired reflection optimization to PRIME skill files.

    Usage (via SkillRefiner)::

        optimizer = SkillOptimizer()
        result = optimizer.optimize_prime(
            prime_path=Path("skills/my_skill.md"),
            feedback=["failed on X pattern", "over-broad on Y"],
            task="improve routing accuracy for code-generation prompts",
        )
        if result:
            print(f"Improved {result}")
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        max_steps: int = 2,
        confidence_threshold: float = 0.65,
    ) -> None:
        self.model = model
        self.max_steps = max_steps
        self.confidence_threshold = confidence_threshold
        self._optimizer: ReflectionOptimizer | None = None

    @property
    def optimizer(self) -> ReflectionOptimizer:
        if self._optimizer is None:
            self._optimizer = ReflectionOptimizer(
                model=self.model,
                max_steps=self.max_steps,
            )
        return self._optimizer

    def optimize_prime(
        self,
        prime_path: Path,
        feedback: list[str],
        task: str,
        confidence: float = 0.0,
    ) -> Path | None:
        """Improve a PRIME skill file using reflection optimization.

        Reads the file, wraps the first trainable section (Instructions,
        Procedure, Rules, etc.) as a Variable, runs the optimizer, and
        rewrites the file if improvement is confirmed.

        Args:
            prime_path: Path to the PRIME .md skill file.
            feedback: List of feedback strings (text gradients).
            task: Description of the skill improvement goal.
            confidence: LearningSignal confidence (skip if below threshold).

        Returns:
            Path to the modified file, or None if no improvement was made.
        """
        if confidence < self.confidence_threshold:
            logger.debug(
                "Skipping reflection optimization: confidence %.2f < %.2f",
                confidence,
                self.confidence_threshold,
            )
            return None

        if not prime_path.exists():
            return None

        try:
            original = prime_path.read_text(encoding="utf-8")
            sections = _parse_prime_sections(original)

            # Find the first trainable section
            target_section: str | None = None
            for name in _TRAINABLE_SECTIONS:
                if name in sections:
                    target_section = name
                    break

            if not target_section:
                logger.debug("No trainable section found in %s", prime_path.name)
                return None

            var = from_prime_section(target_section, sections[target_section], require_grad=True)
            results = self.optimizer.optimize(
                variables=[var],
                task=task,
                feedback=feedback,
            )

            if not results:
                return None

            # Check if any result was satisfied
            best = next((r for r in reversed(results) if r.satisfied), None)
            if not best:
                logger.debug(
                    "Reflection optimizer: no satisfying improvement for %s", prime_path.name
                )
                return None

            # Rewrite the section with the improved content
            sections[target_section] = best.new_value
            new_content = _rebuild_prime(sections)

            # Bump version in frontmatter
            new_content = self._bump_version_in_frontmatter(new_content)

            prime_path.write_text(new_content, encoding="utf-8")
            logger.info(
                "reflection-optimized %s [%s]: %s",
                prime_path.name,
                target_section,
                best.reasoning[:80],
            )
            return prime_path

        except Exception as e:
            logger.debug("SkillOptimizer failed (non-blocking): %s", e)
            return None

    @staticmethod
    def _bump_version_in_frontmatter(content: str) -> str:
        """Increment the patch version in YAML front-matter if present."""

        def _bump(m: re.Match) -> str:
            major, minor, patch = m.group(1), m.group(2), m.group(3)
            return f"version: {major}.{minor}.{int(patch) + 1}"

        return re.sub(
            r"version:\s*(\d+)\.(\d+)\.(\d+)",
            _bump,
            content,
            count=1,
        )
