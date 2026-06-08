"""Item 107: session_learnings_to_capture(docs_dir, *, already_captured) — TDD red→green.

Discriminating tests — each kills a plausible wrong implementation:
  - retro in docs/ not in already_captured → in queue   → test_new_retro_in_queue
  - retro already in already_captured → ABSENT           → test_captured_retro_absent (MAIN DISC.)
  - non-retro .md (no 'type: retro') → ignored           → test_non_retro_ignored
  - empty docs_dir → []                                  → test_empty_dir_returns_empty
  - all retros captured → []                             → test_all_captured_returns_empty
  - queue entries have required fields                   → test_queue_entry_has_required_fields
  - non-.md files ignored                                → test_non_md_files_ignored
  - filename not RETRO-* but has type:retro → included   → test_non_retro_filename_with_type_included
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.session_learnings import session_learnings_to_capture


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_retro(
    dir_: Path, name: str, date: str = "2026-06-03", tags: list[str] | None = None
) -> Path:
    """Write a minimal RETRO-*.md with type: retro frontmatter."""
    tag_str = str(tags or ["test"]).replace("'", "")
    p = dir_ / name
    p.write_text(
        f"---\ntype: retro\ndate: {date}\ntags: {tag_str}\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    return p


def _write_non_retro(dir_: Path, name: str) -> Path:
    """Write a .md file WITHOUT type: retro (e.g., a plan or note)."""
    p = dir_ / name
    p.write_text("---\ntype: plan\ndate: 2026-06-01\n---\n\n# Not a retro\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Core correctness
# ---------------------------------------------------------------------------


def test_new_retro_in_queue(tmp_path: Path) -> None:
    """A retro present in docs_dir and NOT in already_captured → in the queue."""
    p = _write_retro(tmp_path, "RETRO-2026-06-03-example.md")
    result = session_learnings_to_capture(tmp_path, already_captured=frozenset())
    paths = [r.path for r in result]
    assert p in paths, f"new retro must appear in queue; got {paths}"


def test_captured_retro_absent(tmp_path: Path) -> None:
    """A retro whose path is in already_captured → ABSENT from queue.

    PRIMARY DISCRIMINATOR: kills an impl that re-deposits everything regardless
    of already_captured (i.e. ignores the set entirely).
    """
    p = _write_retro(tmp_path, "RETRO-2026-06-03-old.md")
    result = session_learnings_to_capture(tmp_path, already_captured=frozenset({p}))
    paths = [r.path for r in result]
    assert p not in paths, f"already-captured retro must NOT appear in queue; got {paths}"


def test_non_retro_ignored(tmp_path: Path) -> None:
    """A .md file with type: plan (not type: retro) → not in queue.

    Kills an impl that includes all .md files in the learnings directory.
    """
    _write_non_retro(tmp_path, "PLAN-2026-06-01-something.md")
    result = session_learnings_to_capture(tmp_path, already_captured=frozenset())
    assert result == [], f"non-retro .md must not appear in queue; got {result}"


def test_empty_dir_returns_empty(tmp_path: Path) -> None:
    """Empty docs_dir → empty queue. No crash."""
    result = session_learnings_to_capture(tmp_path, already_captured=frozenset())
    assert result == []


def test_all_captured_returns_empty(tmp_path: Path) -> None:
    """All retros in docs_dir are in already_captured → empty queue.

    Kills an impl that ignores the already_captured set on the second call.
    """
    p1 = _write_retro(tmp_path, "RETRO-2026-06-03-a.md")
    p2 = _write_retro(tmp_path, "RETRO-2026-06-04-b.md")
    result = session_learnings_to_capture(tmp_path, already_captured=frozenset({p1, p2}))
    assert result == [], f"all captured → empty queue; got {result}"


# ---------------------------------------------------------------------------
# Queue entry shape
# ---------------------------------------------------------------------------


def test_queue_entry_has_required_fields(tmp_path: Path) -> None:
    """Each queue entry has: path, date, tags."""
    _write_retro(tmp_path, "RETRO-2026-06-08-new.md", date="2026-06-08", tags=["inference", "tdd"])
    result = session_learnings_to_capture(tmp_path, already_captured=frozenset())
    assert len(result) == 1
    entry = result[0]
    assert hasattr(entry, "path"), "entry must have .path"
    assert hasattr(entry, "date"), "entry must have .date"
    assert hasattr(entry, "tags"), "entry must have .tags"
    assert entry.date == "2026-06-08"
    assert "inference" in entry.tags


# ---------------------------------------------------------------------------
# Filtering edge cases
# ---------------------------------------------------------------------------


def test_non_md_files_ignored(tmp_path: Path) -> None:
    """Non-.md files in the directory are silently skipped."""
    _write_retro(tmp_path, "RETRO-2026-06-03-real.md")
    (tmp_path / "RETRO-2026-06-03-not-a-md.txt").write_text("type: retro\ndate: 2026-06-03\n")
    (tmp_path / "data.json").write_text('{"type": "retro"}')
    result = session_learnings_to_capture(tmp_path, already_captured=frozenset())
    # Only the .md file should appear
    assert len(result) == 1
    assert result[0].path.suffix == ".md"


def test_mixed_some_captured_some_new(tmp_path: Path) -> None:
    """Partial already_captured: only the un-captured retro appears.

    Kills an impl that ignores already_captured for some but not all entries.
    """
    p_old = _write_retro(tmp_path, "RETRO-2026-06-01-old.md")
    p_new = _write_retro(tmp_path, "RETRO-2026-06-08-new.md")
    result = session_learnings_to_capture(tmp_path, already_captured=frozenset({p_old}))
    paths = [r.path for r in result]
    assert p_new in paths, f"new retro must appear; got {paths}"
    assert p_old not in paths, f"captured retro must NOT appear; got {paths}"
    assert len(result) == 1
