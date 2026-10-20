"""The ACT commit must contain exactly the bytes that were verified (correctness C7).

THE DEFECT: ``_commit`` ran ``ruff format`` / ``ruff check --fix`` AFTER the K=3 confirmation
runs, so the committed file was never tested (ruff can delete an unused import that another
module re-imports). Here a fixer that changes behaviour stands in for that rewrite.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from cohezion.compound.autonomous_loop.act_loop import act_loop


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def test_a_post_verify_rewrite_cannot_reach_the_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src/pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src/pkg/__init__.py").write_text("")
    (repo / "src/pkg/mod.py").write_text('"""m."""\n\n\ndef value():\n    return 1\n')
    (repo / "tests/test_mod.py").write_text(
        "from pkg.mod import value\n\n\ndef test_v():\n    assert value() == 2\n"
    )
    for c in (
        ["init", "-q"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["add", "."],
        ["commit", "-q", "-m", "base"],
    ):
        _git(repo, *c)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python = bin_dir / "python"
    python.write_text(f'#!/bin/sh\nexec {sys.executable} "$@"\n')
    python.chmod(0o755)
    ruff = bin_dir / "ruff"  # a "fixer" whose rewrite changes behaviour
    ruff.write_text("#!/bin/sh\nsed -i 's/return 2/return 99/' \"$2\" 2>/dev/null; exit 0\n")
    ruff.chmod(0o755)
    res = act_loop(
        repo=repo,
        file="src/pkg/mod.py",
        targets=["value"],
        oracle="tests/test_mod.py",
        extra_tests=[],
        task="t",
        task_id="t1",
        model="m",
        chat=lambda _p: {"text": "```python\ndef value():\n    return 2\n```"},
        python=str(python),
        max_iters=1,
        log=tmp_path / "log.jsonl",
        callers=[],
        confirm_repeats=1,
    )
    committed = _git(repo, "show", "HEAD:src/pkg/mod.py")
    assert "return 99" not in committed, f"untested bytes committed ({res['status']})"
