"""Canonical on-disk skill discovery.

One implementation, shared by ``scripts/ci/validate_registry.py`` (which reports
drift) and ``scripts/ci/sync_skill_registry.py`` (which closes it). Keeping the
scan in one place is the point: when the two disagreed, the drift report was
itself drifting.

Two layouts are recognised, matching what is actually on disk:

* **flat** -- ``NAME.md`` at the top level; the skill name is the file stem.
* **bundle** -- ``NAME/SKILL.md``; the skill name is the DIRECTORY name. A
  bundle's ``README.md`` and ``references/*.md`` are supporting material, not
  skills.

A purely recursive ``*.md`` scan would promote that supporting material to
skills (12 such files in this repo), which is why bundles are resolved by their
marker file rather than by globbing every markdown file.
"""

from __future__ import annotations

import logging
from pathlib import Path


logger = logging.getLogger(__name__)

# Directories whose contents are intentionally retired or are not skills at all.
EXCLUDED_DIR_NAMES = frozenset({".archive", "archive", "__pycache__"})

# Marker file that makes a directory a skill bundle (Agent Skills convention).
# Matched case-INSENSITIVELY: Linux filesystems are case-sensitive, so a bundle
# written `skill.md` was invisible to the scan and therefore indistinguishable
# from having no skill at all.
BUNDLE_MARKER = "SKILL.md"


def discover_skills(skills_dir: Path) -> dict[str, Path]:
    """Map every discoverable skill name to the file that defines it.

    Returns an empty mapping when *skills_dir* is absent, so a bad path surfaces
    as "0 on disk" rather than a traceback.
    """
    if not skills_dir.is_dir():
        return {}

    found: dict[str, Path] = {path.stem: path for path in sorted(skills_dir.glob("*.md"))}

    marker_lower = BUNDLE_MARKER.lower()
    for marker in sorted(skills_dir.rglob("*.md")):
        if marker.name.lower() != marker_lower:
            continue
        if marker.parent == skills_dir:
            continue
        if EXCLUDED_DIR_NAMES.intersection(marker.relative_to(skills_dir).parts[:-1]):
            continue

        name = marker.parent.name
        existing = found.get(name)
        if existing is not None:
            # Flat file keeps precedence, but say so. Silently dropping the
            # bundle would make it vanish from the registry with no diagnostic
            # anywhere -- the exact failure mode this scan exists to remove.
            logger.warning(
                "skill name collision: %r defined by both %s and %s; keeping %s",
                name,
                existing,
                marker,
                existing,
            )
            continue
        found[name] = marker

    return found
