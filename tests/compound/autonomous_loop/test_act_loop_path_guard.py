"""C1 (security review 2026-09-22): the ACT spec's paths must not escape src/ and tests/.

THE DEFECT: ``file.startswith("src/")`` accepted ``src/../scripts/ci/gate.py`` (the loop then
committed edits to CI/auth code), *oracle* was never checked (``/tmp/x_test.py`` ran with the
conftest.py beside it), and an exception from the commit left the model's text on disk.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from cohezion.compound.autonomous_loop import act_loop as act_loop_mod
from cohezion.compound.autonomous_loop.act_loop import act_loop


MOD = '"""m."""\n\n\ndef value():\n    return 1\n'
FIX = "```python\ndef value():\n    return 2\n```"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def _repo(root: Path) -> Path:
    repo = root / "repo"
    (repo / "src/pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "scripts").mkdir()
    (repo / "src/pkg/__init__.py").write_text("")
    (repo / "src/pkg/mod.py").write_text(MOD)
    (repo / "scripts/gate.py").write_text(MOD)
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
    return repo


def _run(repo: Path, tmp_path: Path, **kw):
    args = {
        "repo": repo,
        "file": "src/pkg/mod.py",
        "targets": ["value"],
        "oracle": "tests/test_mod.py",
        "extra_tests": [],
        "task": "t",
        "task_id": "t1",
        "model": "m",
        "chat": lambda _p: {"text": FIX},
        "python": sys.executable,
        "max_iters": 1,
        "log": tmp_path / "log.jsonl",
        "callers": [],
        "confirm_repeats": 1,
    }
    args.update(kw)
    return act_loop(**args)


def test_dotdot_edit_target_outside_src_is_refused(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    head = _git(repo, "rev-parse", "HEAD")
    with pytest.raises(ValueError):
        _run(repo, tmp_path, file="src/../scripts/gate.py")
    assert (repo / "scripts/gate.py").read_text() == MOD
    assert _git(repo, "rev-parse", "HEAD") == head


def test_absolute_oracle_is_refused_and_its_conftest_never_runs(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    evil = tmp_path / "evil"
    evil.mkdir()
    marker = tmp_path / "PWNED"
    (evil / "conftest.py").write_text(f"open({str(marker)!r}, 'w').write('x')\n")
    (evil / "x_test.py").write_text("def test_x():\n    assert False\n")
    with pytest.raises(ValueError):
        _run(repo, tmp_path, oracle=str(evil / "x_test.py"))
    assert not marker.exists()


def test_symlinked_edit_target_is_refused(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "src/pkg/link.py").symlink_to(repo / "scripts/gate.py")
    _git(repo, "add", "src/pkg/link.py")
    _git(repo, "commit", "-qm", "link")
    with pytest.raises(ValueError):
        _run(repo, tmp_path, file="src/pkg/link.py")
    assert (repo / "scripts/gate.py").read_text() == MOD


def test_untracked_edit_target_is_refused(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "src/pkg/new.py").write_text(MOD)
    with pytest.raises(ValueError):
        _run(repo, tmp_path, file="src/pkg/new.py")


@pytest.mark.parametrize(
    ("file", "oracle", "targets"),
    [
        ("src/../x.py", "tests/t.py", ["f"]),
        ("/abs/src/x.py", "tests/t.py", ["f"]),
        ("src/x.txt", "tests/t.py", ["f"]),
        ("src/x.py", "tests/../conftest.py", ["f"]),
        ("src/x.py", "-p evil", ["f"]),
        ("src/x.py", "tests/t.py", ["f\nCo-Authored-By: x"]),
        ("src/x.py", "tests/t.py", []),
    ],
)
def test_check_act_spec_rejects(file: str, oracle: str, targets: list[str]) -> None:
    with pytest.raises(ValueError):
        act_loop_mod.check_act_spec(file, oracle, targets)


def test_check_act_spec_accepts_a_node_id() -> None:
    act_loop_mod.check_act_spec("src/pkg/mod.py", "tests/test_mod.py::test_v", ["value"])


def test_commit_failure_restores_the_original_file(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)

    def boom(*_a, **_k):
        raise subprocess.CalledProcessError(1, ["git", "commit"])

    monkeypatch.setattr(act_loop_mod, "_commit", boom)
    res = _run(repo, tmp_path)
    assert res["status"] == "COMMIT_FAILED", res
    assert (repo / "src/pkg/mod.py").read_text() == MOD


def test_exception_mid_verify_restores_the_original_file(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    calls = {"n": 0}

    def runner(repo, python, tests, timeout=300):
        calls["n"] += 1
        if calls["n"] == 1:
            return False, "1 failed"
        raise OSError("runner died after the model's edit was written")

    monkeypatch.setattr(act_loop_mod, "run_tests", runner)
    with pytest.raises(OSError):
        _run(repo, tmp_path)
    assert (repo / "src/pkg/mod.py").read_text() == MOD
