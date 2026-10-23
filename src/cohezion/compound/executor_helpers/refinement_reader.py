"""Learned-refinement reader — closes the SkillRefiner → next-execution loop.

``SkillRefiner._append_refinement`` writes "## Learned Refinement (<timestamp>)"
sections into a skill's PRIME file, but until this module nothing read them
back. ``load_refined_guidance`` extracts those sections so
``fetch_experience_guidance`` can merge them into the guidance dict consumed
by ``CompoundExecutor.execute_task`` — a refinement written on run N reaches
run N+1.

Fail-open: a missing file or any parse error returns ``[]`` — reading learned
refinements must never break guidance fetching.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# Mirrors SkillRefiner.SKILLS_DIR (skill_refiner.py lives one level up).
_SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"

# Env override shared with SkillRefiner so reader and writer agree on ONE directory.
# Set by benchmarks (docs/benchmarks/compound_loop) to run the loop against an isolated
# copy of a skill instead of mutating the repo's PRIME files.
SKILLS_DIR_ENV = "COHEZION_SKILLS_DIR"


def resolve_skills_dir(default: Path | None = None) -> Path:
    """Skills directory: ``$COHEZION_SKILLS_DIR`` when set, else ``default`` / repo dir."""
    override = os.environ.get(SKILLS_DIR_ENV)
    if override:
        return Path(override)
    return default if default is not None else _SKILLS_DIR


def guidance_to_prompt_text(guidance: Any) -> str:
    """Flatten an experience-guidance dict into the text an execute_fn puts in its prompt.

    Until 2026-10-22 ``make_local_execute_fn`` read only ``guidance["guidance"]`` -- a key
    ``fetch_experience_guidance`` never sets -- so the ``learned_refinements`` it DOES set
    reached no prompt: the SkillRefiner loop was open at its consumption point. This is the
    single place that decides what a refinement looks like inside a prompt.
    """
    if guidance is None:
        return ""
    if not isinstance(guidance, dict):
        return str(guidance)
    parts: list[str] = []
    base = guidance.get("guidance") or ""
    if base:
        parts.append(str(base))
    sections = guidance.get("learned_refinements") or []
    parts.extend(str(s) for s in sections if s)
    return "\n\n".join(parts)


# Section heading written by SkillRefiner._create_refinement_section().
_REFINEMENT_HEADING_RE = re.compile(r"^## Learned Refinement \(.*?\)\s*$", re.MULTILINE)

# Any subsequent H2 heading terminates a refinement section.
_NEXT_HEADING_RE = re.compile(r"^## ", re.MULTILINE)


def _find_prime_file(skill_name: str, skills_dir: Path) -> Path | None:
    """Resolve the PRIME file — same logic as SkillRefiner._find_prime_file."""
    # Try exact match
    prime_path = skills_dir / f"{skill_name.upper()}_PRIME.md"
    if prime_path.exists():
        return prime_path

    # Try fuzzy match
    for file in skills_dir.glob("*_PRIME.md"):
        if skill_name.lower() in file.stem.lower():
            return file

    return None


def load_refined_guidance(
    skill_name: str,
    skills_dir: Path | None = None,
    max_sections: int = 5,
) -> list[str]:
    """Load "## Learned Refinement" sections from a skill's PRIME file.

    Args:
        skill_name: Name of skill (e.g., 'SYSTEM_GUARDRAILS').
        skills_dir: Override for the skills directory (defaults to the same
            directory SkillRefiner writes to).
        max_sections: Cap on returned sections to bound prompt growth.

    Returns:
        Refinement section texts, most recent first (SkillRefiner appends new
        sections after existing ones, so file order is oldest-to-newest).
        Empty list on missing skill/file or any read error (fail-open).
    """
    try:
        base_dir = skills_dir if skills_dir is not None else resolve_skills_dir()
        prime_file = _find_prime_file(skill_name, base_dir)
        if prime_file is None:
            return []

        content = prime_file.read_text(encoding="utf-8")

        sections: list[str] = []
        for match in _REFINEMENT_HEADING_RE.finditer(content):
            next_heading = _NEXT_HEADING_RE.search(content, match.end())
            end = next_heading.start() if next_heading else len(content)
            sections.append(content[match.start() : end].strip())

        sections.reverse()  # most recent first
        return sections[:max_sections]

    except (OSError, ValueError) as e:
        logger.debug("Failed to load refined guidance for %s: %s", skill_name, e)
        return []
