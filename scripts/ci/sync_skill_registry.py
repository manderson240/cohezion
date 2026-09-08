#!/usr/bin/env python3
"""Sync the skill registry with what is actually on disk.

``validate_registry.py`` reports drift; this closes it. Both share one scan
(``cohezion.registry.skill_discovery``) so they cannot disagree.

Registry drift is not a one-off: it was measured growing at roughly 2.5 skills
per day (26 unregistered on 2026-08-23, 40 on 2026-08-27), which is why this is
a rerunnable script rather than a hand-applied patch.

Both mutations are opt-in and print what they will do:

    sync_skill_registry.py --add     # register skills that exist on disk
    sync_skill_registry.py --prune   # drop entries whose file is gone
    sync_skill_registry.py --add --prune --apply

Without ``--apply`` nothing is written -- the run is a dry preview.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cohezion.registry.skill_discovery import discover_skills
from cohezion.registry.skill_registry import load_registry


SKILLS_DIR = Path("src/cohezion/skills")
REGISTRY_FILE = Path("src/cohezion/registry/skill_registry.json")

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)
DESCRIPTION_MAX = 300

# Largest share of the registry --prune will remove without an explicit override.
# Real cleanup is a few dead pointers (today's was 5 of 245, ~2%); anything past
# this looks like an incomplete tree, not a deletion someone intended.
_MAX_PRUNE_FRACTION = 0.20
# Words too generic to route on; keywords are a coarse index, not a summary.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "into",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "use",
        "used",
        "using",
        "when",
        "with",
        "you",
        "your",
        "this",
        "these",
        "specialist",
        "skill",
        "prime",
        "know",
        "understand",
        "understands",
    }
)


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Extract top-level ``key: value`` pairs from a YAML frontmatter block.

    Deliberately not a YAML parser: only flat string scalars are needed, and a
    hand-rolled reader keeps this script dependency-free and predictable on the
    nested/JSON-ish metadata blocks some skills carry.
    """
    match = _FRONTMATTER.search(text)
    if not match:
        return {}

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line or line[0].isspace() or ":" not in line:
            continue  # nested value, list item, or continuation
        key, _, value = line.partition(":")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            # Quoted scalar: drop the delimiters, then unescape what YAML escaped
            # inside them. Without this the inner \" survives into JSON as \\",
            # which renders back as a literal backslash in the description.
            quote = value[0]
            value = value[1:-1].replace("\\" + quote, quote).replace("\\\\", "\\")
        if value:
            fields[key.strip()] = value
    return fields


def _body_description(text: str) -> str:
    """Recover a description from a skill's prose when it has no frontmatter.

    15 of the 40 skills registered on 2026-08-27 carry no YAML at all -- they
    open with ``# SKILL: NAME`` then ``## DOMAIN EXPERTISE`` and a paragraph.
    That paragraph is the description. Falling back to a placeholder instead
    would register the skill without making it routable: green CI, no gain.
    """
    body = _FRONTMATTER.sub("", text, count=1)
    paragraph: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "---")):
            if paragraph:
                break  # blank/heading ends the first prose paragraph
            continue
        if line.startswith(("-", "*", "|", ">", "```")):
            break  # a list or code block is structure, not a summary
        paragraph.append(line)
    return " ".join(paragraph).strip()


def _truncate(text: str, limit: int) -> str:
    """Cap *text* at *limit* without splitting the final word."""
    if len(text) <= limit:
        return text
    clipped = text[:limit]
    head, sep, _ = clipped.rpartition(" ")
    return (head if sep else clipped).rstrip()


def _keywords(name: str, description: str) -> list[str]:
    """Derive a small, stable keyword set for routing lookups."""
    words = re.findall(r"[a-z0-9]{3,}", f"{name} {description}".lower())
    seen: list[str] = []
    for word in words:
        if word not in _STOPWORDS and word not in seen:
            seen.append(word)
    return sorted(seen[:12])


def build_entry(name: str, path: Path) -> dict[str, Any]:
    """Build a registry entry for *name* from its file's frontmatter."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:  # unreadable file: register it, flag it, do not crash
        text = ""
        print(f"  WARN: could not read {path}: {exc}")

    description = _parse_frontmatter(text).get("description", "").strip()
    if not description:
        description = _body_description(text)
    if not description:
        description = f"Skill defined in {path.as_posix()} (no description found)."
    description = _truncate(description, DESCRIPTION_MAX)

    return {
        "name": name,
        "description": description,
        "keywords": _keywords(name, description),
        "path": path.as_posix(),
        "version": "1.0.0",
        "last_updated": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "generated_from": "sync_skill_registry",
    }


def _write_atomic(path: Path, text: str) -> None:
    """Write *text* to *path* so an interrupted run cannot truncate the file.

    The registry is the routing index for the whole skill library; a half-written
    JSON file takes every skill offline at once. Write to a sibling temp file and
    rename, which is atomic within a filesystem.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--add", action="store_true", help="register skills found on disk")
    parser.add_argument("--prune", action="store_true", help="drop entries whose file is gone")
    parser.add_argument("--apply", action="store_true", help="write changes (default: preview)")
    parser.add_argument(
        "--allow-mass-prune",
        action="store_true",
        help=f"permit removing more than {_MAX_PRUNE_FRACTION:.0%} of the registry at once",
    )
    args = parser.parse_args(argv)

    if not (args.add or args.prune):
        parser.error("nothing to do: pass --add and/or --prune")

    registry = load_registry()
    on_disk = discover_skills(SKILLS_DIR)

    unregistered = sorted(set(on_disk) - set(registry))
    orphaned = sorted(set(registry) - set(on_disk))

    additions: dict[str, Any] = {}
    if args.add:
        print(f"ADD: {len(unregistered)} skill(s) on disk but not registered")
        for name in unregistered:
            additions[name] = build_entry(name, on_disk[name])
            print(f"  + {name}  <- {on_disk[name].as_posix()}")

    if args.prune:
        print(f"\nPRUNE: {len(orphaned)} registry entry/entries with no file on disk")
        for name in orphaned:
            print(f"  - {name}  (was {registry[name].get('path', '?')})")

    if not args.apply:
        print("\nDRY RUN -- nothing written. Re-run with --apply to persist.")
        return 0

    # A scan that found nothing is indistinguishable from "every skill was
    # deleted", and discover_skills() deliberately returns {} for a missing
    # directory. Pruning on that wipes the whole registry -- a renamed folder,
    # the wrong cwd, or an unmounted volume is enough. Deletion requires
    # positive evidence that the skills tree was actually read.
    if args.prune and not on_disk:
        print(
            f"\nABORT: no skills discovered under {SKILLS_DIR} -- refusing to prune "
            f"{len(orphaned)} entries. An empty scan means the tree could not be read, "
            "not that every skill was deleted. Re-run with --add only, or fix the path."
        )
        return 1

    # The empty scan above is only the EXTREME of a broader hazard, and guarding
    # it alone left the class open: with a single file on disk this deleted all
    # 275 entries and exited 0 (reproduced 2026-08-27). A partial checkout, a
    # bad glob or a half-finished move all look exactly like mass deletion.
    # Routine cleanup is a handful of dead pointers; anything larger wants a
    # human to say so out loud.
    if args.prune and orphaned and not args.allow_mass_prune:
        share = len(orphaned) / len(registry) if registry else 1.0
        if share > _MAX_PRUNE_FRACTION:
            print(
                f"\nABORT: disproportionate prune -- {len(orphaned)} of {len(registry)} "
                f"entries ({share:.0%}) would be removed, over the "
                f"{_MAX_PRUNE_FRACTION:.0%} threshold. Only {len(on_disk)} skill(s) were "
                f"found on disk, which usually means the tree is incomplete rather than "
                f"that the skills are gone.\n"
                f"   If the deletion is real, say so: --allow-mass-prune"
            )
            return 1

    updated = dict(registry)
    updated.update(additions)
    if args.prune:
        for name in orphaned:
            updated.pop(name, None)

    _write_atomic(
        REGISTRY_FILE,
        json.dumps(dict(sorted(updated.items())), indent=2, ensure_ascii=False) + "\n",
    )
    print(f"\nWROTE {REGISTRY_FILE}: {len(registry)} -> {len(updated)} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
