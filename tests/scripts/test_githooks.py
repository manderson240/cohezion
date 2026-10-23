"""Git hooks under .githooks/ are code that gates every commit; test them like code.

Why this exists (2026-10-22): .githooks/pre-commit ran ``pytest tests/kaggle/`` unconditionally.
On a checkout without that directory pytest exits 4, ``set -e`` aborted every commit, and the
workaround became ``--no-verify`` (51 commits), which silently skips the SemVer, import-smoke and
security steps too. A gate whose precondition cannot hold disables every other gate in the hook.
These tests make that class of defect a CI failure instead of a habit.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO / ".githooks"
HOOKS = sorted(p for p in HOOKS_DIR.iterdir() if p.is_file() and not p.name.endswith(".disabled"))

_PYTEST_TARGET = re.compile(r"\bpytest\s+(\S+)")


@pytest.mark.parametrize("hook", HOOKS, ids=lambda p: p.name)
def test_hook_parses(hook: Path) -> None:
    """``bash -n`` catches syntax errors before git runs the hook on a real commit."""
    result = subprocess.run(["bash", "-n", str(hook)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("hook", HOOKS, ids=lambda p: p.name)
def test_hook_is_executable(hook: Path) -> None:
    """git silently skips a hook it cannot execute, which reads as "all gates passed"."""
    assert hook.stat().st_mode & 0o111, f"{hook.name} is not executable"


@pytest.mark.parametrize("hook", HOOKS, ids=lambda p: p.name)
def test_pytest_targets_exist_or_are_guarded(hook: Path) -> None:
    """Every ``pytest <path>`` in a hook must name a path that exists on THIS checkout, or sit
    behind an explicit ``[ -d <path> ]`` / ``[ -e <path> ]`` precondition. Otherwise pytest exits
    4 and ``set -e`` aborts the commit for every checkout that lacks the path."""
    text = hook.read_text()
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    for match in _PYTEST_TARGET.finditer(code):
        target = match.group(1)
        if target.startswith("-"):
            continue  # an option, not a path
        path = target.rstrip("/")
        if (REPO / path).exists():
            continue
        guard = re.compile(r"\[\s+-[de]\s+" + re.escape(path) + r"/?\s+\]")
        assert guard.search(text), (
            f"{hook.name}: `pytest {target}` names a path absent on this checkout and is not "
            f"guarded by `[ -d {path} ]`; the hook would exit 4 and abort every commit"
        )
