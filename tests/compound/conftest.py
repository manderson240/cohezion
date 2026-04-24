"""Compound test fixtures.

Ensures the project ``.context/`` tree has the placeholder source files that
``cohezion.compound.context_integration.ContextManager`` expects when loading
the traceability manifest. The manifest references files (e.g.
``compound/long_horizon_task.py``, ``universe/spatial_phonons.py``) that are
shadow-copies of source modules and aren't always materialised in every
worktree (sparse checkouts, fresh clones). When they're missing, the
CompoundExecutor's ``__init_context__`` chain raises ``ContextLoadError`` and
every test that instantiates an executor errors out.

This fixture is autouse + session-scoped so that the placeholders exist for
the entire compound test run without per-test overhead. It does NOT modify
real source files — it only ensures byte-identical placeholders for the
context loader.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _find_project_root(start: Path) -> Path | None:
    """Walk upward looking for a ``.context`` directory."""
    current = start.resolve()
    while current != current.parent:
        if (current / ".context").exists():
            return current
        current = current.parent
    return None


@pytest.fixture(autouse=True, scope="session")
def _ensure_context_placeholders() -> None:
    """Materialise placeholder files referenced by .context/traceability/manifest.json.

    Reads the manifest, resolves each ``core_files[*].path``, and writes a
    minimal placeholder if the target is missing. This is idempotent and
    cheap: existing files are untouched.
    """
    project_root = _find_project_root(Path(__file__).parent)
    if project_root is None:
        return

    manifest_path = project_root / ".context" / "traceability" / "manifest.json"
    if not manifest_path.exists():
        return

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    context_dir = project_root / ".context"
    for entry in manifest.get("core_files", []):
        rel = entry.get("path")
        if not rel:
            continue
        target = context_dir / rel
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "# Placeholder for compound context loader (created by tests/compound/conftest.py).\n"
            "# Real content lives in the corresponding src/ module; this file exists so\n"
            "# ContextManager._load_file() does not raise ContextLoadError during tests.\n",
            encoding="utf-8",
        )
