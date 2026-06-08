"""Item 107: Session-learning → vault/SurrealDB capture bridge — report-only first step.

Scans ``docs_dir`` for ``RETRO-*.md`` files with ``type: retro`` frontmatter and
returns the subset that is NOT yet in ``already_captured`` — the **deposit queue**:
the list of retros that SHOULD be written into the vault / SurrealDB ``learnings``
table but have not been yet.

The ACTUAL vault/SurrealDB write is a separate, gated behavior-change step (item 107
motivation: "report-only first step that says WHAT to capture").  This module is
purely diagnostic — no writes are performed here.

Mirrors the vault-first rule (``CLAUDE.md``) and the ``experiential_learning_hook``'s
``narrative_learning`` path.  Pure (read-only .md parse; injected ``already_captured``
set; no live DB call).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class LearningRecord:
    """A retro document that needs to be deposited into the vault/SurrealDB (item 107).

    Attributes
    ----------
    path:
        Absolute path to the RETRO-*.md source file.
    date:
        ISO date string from the frontmatter ``date:`` field, or ``""`` if absent.
    tags:
        List of tag strings from the frontmatter ``tags:`` field (YAML list syntax).
        Empty list when the field is absent or unparseable.
    """

    path: Path
    date: str
    tags: list[str] = field(default_factory=list, compare=False, hash=False)


def _parse_frontmatter(md_path: Path) -> dict[str, str]:
    """Parse the YAML frontmatter block of a Markdown file.

    Returns a flat ``{key: raw_value_string}`` dict from the lines between the
    opening and closing ``---`` fences.  Stops at the closing fence.  Returns an
    empty dict if the file has no frontmatter or is unreadable.

    Intentionally minimal — no full YAML parse needed for the scalar fields we use.
    """
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm


def _parse_tags(raw: str) -> list[str]:
    """Parse a YAML inline list string like ``[a, b, c]`` into ``["a", "b", "c"]``.

    Returns an empty list for non-list or empty values.
    """
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1]
        return [t.strip().strip("'\"") for t in inner.split(",") if t.strip()]
    return []


def session_learnings_to_capture(
    docs_dir: Path,
    *,
    already_captured: frozenset[Path] | set[Path],
) -> list[LearningRecord]:
    """Return retros in ``docs_dir`` that have NOT yet been deposited (item 107). READ-ONLY.

    Scans ``docs_dir`` for ``*.md`` files whose YAML frontmatter contains
    ``type: retro``, then filters out any whose ``Path`` is in ``already_captured``.
    The remaining entries form the **deposit queue**: what the caller SHOULD write
    to the vault / SurrealDB ``learnings`` table.

    Args:
        docs_dir:
            Directory to scan for Markdown files (non-recursive — only direct children).
            Typically ``docs/ops/learnings/`` in the project tree.
        already_captured:
            Set of :class:`~pathlib.Path` objects for retros already deposited.
            Injected — no live DB query is made.

    Returns:
        List of :class:`LearningRecord` instances for uncaptured retros, sorted by
        ``date`` ascending (stable deterministic order).  Empty list when all retros
        have been captured or ``docs_dir`` contains no retros.

    Pure (read-only .md parse; no writes, no DB calls).
    """
    queue: list[LearningRecord] = []

    for md_path in sorted(docs_dir.glob("*.md")):
        if md_path in already_captured:
            continue
        fm = _parse_frontmatter(md_path)
        if fm.get("type", "").lower() != "retro":
            continue
        queue.append(
            LearningRecord(
                path=md_path,
                date=fm.get("date", ""),
                tags=_parse_tags(fm.get("tags", "")),
            )
        )

    return sorted(queue, key=lambda r: r.date)
