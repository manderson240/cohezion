"""Card text in the ACT commit message must stay on one line (security review, minor).

THE DEFECT: ``_commit`` put the card's ``task_id`` straight into ``-m``; a newline forged
trailers such as ``Co-Authored-By`` or ``Signed-off-by`` on the model's commit.
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


def test_newline_in_task_id_cannot_forge_a_trailer(tmp_path: Path) -> None:
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
    res = act_loop(
        repo=repo,
        file="src/pkg/mod.py",
        targets=["value"],
        oracle="tests/test_mod.py",
        extra_tests=[],
        task="t",
        task_id="t1]\n\nCo-Authored-By: Mallory <m@evil>",
        model="m\r\nSigned-off-by: Mallory <m@evil>",
        chat=lambda _p: {"text": "```python\ndef value():\n    return 2\n```"},
        python=sys.executable,
        max_iters=1,
        log=tmp_path / "log.jsonl",
        callers=[],
        confirm_repeats=1,
    )
    assert res["status"] == "GREEN", res
    body = _git(repo, "log", "-1", "--format=%B").strip()
    assert "\n" not in body, body
    assert _git(repo, "log", "-1", "--format=%(trailers)").strip() == ""
