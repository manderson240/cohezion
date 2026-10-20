"""Every nested CLAUDE.md must have a sibling AGENTS.md that is a git symlink to it.

Claude Code reads CLAUDE.md; Antigravity and other AGENTS.md-standard harnesses read AGENTS.md.
One file per directory, two names: a symlink cannot drift. (A 2026-09-03 retro recorded ten
nested AGENTS.md files that never landed on any branch — non-Claude harnesses saw only the
root file for weeks.) Symlink rather than an `@AGENTS.md` import: Claude Code's docs do not
say whether imports in on-demand nested CLAUDE.md files expand, so an import could silently
strip subsystem guidance from Claude sessions.

Reads the git index, not the filesystem, so it holds in any checkout (including read-only
worktrees where the link is not materialised).
"""

from __future__ import annotations

import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def _index_entries() -> dict[str, tuple[str, str]]:
    out = subprocess.run(
        ["git", "ls-files", "-s", "-z"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    entries: dict[str, tuple[str, str]] = {}
    for rec in filter(None, out.split("\0")):
        meta, path = rec.split("\t", 1)
        mode, sha, _stage = meta.split()
        entries[path] = (mode, sha)
    return entries


def _blob(sha: str) -> str:
    return subprocess.run(
        ["git", "cat-file", "-p", sha], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout


def test_every_nested_claude_md_has_an_agents_md_symlink() -> None:
    entries = _index_entries()
    nested = [p for p in entries if p.endswith("/CLAUDE.md")]
    assert nested, "no nested CLAUDE.md found — the scan itself is broken"
    problems = []
    for claude in nested:
        agents = claude[: -len("CLAUDE.md")] + "AGENTS.md"
        if agents not in entries:
            problems.append(f"{agents}: missing")
            continue
        mode, sha = entries[agents]
        if mode != "120000":
            problems.append(f"{agents}: mode {mode}, expected symlink 120000 (a copy can drift)")
        elif _blob(sha) != "CLAUDE.md":
            problems.append(f"{agents}: links to {_blob(sha)!r}, expected 'CLAUDE.md'")
    assert not problems, "\n".join(problems)
