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
import subprocess
from pathlib import Path


logger = logging.getLogger(__name__)

# Mirrors SkillRefiner.SKILLS_DIR (skill_refiner.py lives one level up).
_SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"

# Section heading written by SkillRefiner._create_refinement_section().
_REFINEMENT_HEADING_RE = re.compile(r"^## Learned Refinement \(.*?\)\s*$", re.MULTILINE)

# Any subsequent H2 heading terminates a refinement section.
_NEXT_HEADING_RE = re.compile(r"^## ", re.MULTILINE)


def find_prime_file_in_registry(skill_name: str, skills_dir: Path) -> Path | None:
    """Resolve *skill_name* through the authoritative skill registry, or None.

    Shared by the WRITER (SkillRefiner) and this READER: when only the writer had the registry
    step, "research-actioner" refinements were written to RESEARCH_ACTIONER_PRIME.md and the
    reader returned None for it -- written, never read (review 2026-09-22 C8).
    """
    try:
        from cohezion.registry.skill_discovery import canonical_skill_key
        from cohezion.registry.skill_registry import load_registry

        wanted = canonical_skill_key(skill_name)
        hits = []
        for key, entry in load_registry().items():
            if canonical_skill_key(key) != wanted or not isinstance(entry, dict):
                continue
            # Registry paths are repo-relative ("src/cohezion/skills/X.md" or a bundle's
            # ".../<dir>/SKILL.md"); re-root below skills_dir so both shapes resolve.
            rel = Path(str(entry.get("path", ""))).parts
            if "skills" in rel:
                path = skills_dir.joinpath(*rel[rel.index("skills") + 1 :])
                if path.suffix == ".md" and path.is_file():
                    hits.append(path)
        if len(hits) == 1:
            return hits[0]
        if hits:  # two registry skills canonicalise alike: refining either would be a guess
            logger.warning("ambiguous registry match for %s: %s", skill_name, hits)
    except (OSError, ValueError, ImportError) as exc:
        logger.debug("registry lookup for %s failed: %s", skill_name, exc)
    return None


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

    return find_prime_file_in_registry(skill_name, skills_dir)


def overlay_path(prime_file: Path) -> Path:
    """Out-of-repo file holding refinements NOT promoted into a git-tracked PRIME file.

    ``$COHEZION_REFINEMENT_OVERLAY_DIR`` or ``~/.cohezion/skill_refinements``; a bundle's
    ``<dir>/SKILL.md`` is keyed by its directory so two bundles cannot collide.
    """
    base = os.environ.get("COHEZION_REFINEMENT_OVERLAY_DIR") or str(
        Path.home() / ".cohezion" / "skill_refinements"
    )
    name = prime_file.name
    if name == "SKILL.md":
        name = f"{prime_file.parent.name}__SKILL.md"
    return Path(base) / name


def is_git_tracked(path: Path) -> bool:
    """True when *path* is tracked by an enclosing git repo; UNKNOWN answers True (safe side)."""
    root = next((d for d in path.resolve().parents if (d / ".git").exists()), None)
    if root is None:
        return False
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", str(path.resolve())],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return True
    return proc.returncode == 0


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
        base_dir = skills_dir if skills_dir is not None else _SKILLS_DIR
        prime_file = _find_prime_file(skill_name, base_dir)
        if prime_file is None:
            return []

        # PRIME first, then the overlay (written only after the PRIME's promoted sections).
        overlay = overlay_path(prime_file)
        sources = [prime_file] + ([overlay] if overlay.is_file() else [])
        sections: list[str] = []
        for source in sources:
            content = source.read_text(encoding="utf-8")
            for match in _REFINEMENT_HEADING_RE.finditer(content):
                next_heading = _NEXT_HEADING_RE.search(content, match.end())
                end = next_heading.start() if next_heading else len(content)
                sections.append(content[match.start() : end].strip())

        sections.reverse()  # most recent first
        return sections[:max_sections]

    except (OSError, ValueError) as e:
        logger.debug("Failed to load refined guidance for %s: %s", skill_name, e)
        return []
