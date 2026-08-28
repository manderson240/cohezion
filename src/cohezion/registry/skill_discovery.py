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
import re
from pathlib import Path


logger = logging.getLogger(__name__)

# Trailing "_PRIME" token the skill-health namespace carries but the registry does not.
_PRIME_SUFFIX = re.compile(r"_prime$")


def canonical_skill_key(name: str) -> str:
    """Map any skill identifier to the registry's canonical namespace.

    The skill-health store and the registry are two node namespaces that were
    never joinable: health records key on ``ANIMATIONS_PRIME`` while the registry
    keys on ``animations`` (measured 2026-08-27: 0 of 73 old health records
    exact-matched the registry; 9 matched after this normalisation). Consumers
    that need to JOIN the two -- the capability matrix's skill axis, chiefly --
    route both sides through here, so a health record can be validated against,
    and keyed by, the real skill library.

    Deterministic and idempotent: a canonical registry key maps to itself.
    """
    key = name.strip().lower().replace("-", "_")
    return _PRIME_SUFFIX.sub("", key)


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
