"""C2 (security review 2026-09-22): model text must not run code, read secrets, or reach git.

THE DEFECTS: ``splice`` accepted ``X = __import__("os").system(...)`` (runs at import, during
pytest), new decorators, and replacements of NON-target functions; ``run_tests`` handed the
daemon's whole environment (credentials) to model code; and model code running under pytest
could write ``.git/hooks/pre-commit``, which ``_commit``'s ``git commit`` then executed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from cohezion.compound.autonomous_loop import act_loop as act_loop_mod
from cohezion.compound.autonomous_loop.act_loop import act_loop


SRC = (
    "import functools\n\n\n"
    "@functools.cache\ndef value():\n    return 1\n\n\n"
    "def other():\n    return 0\n\n\n"
    "class K:\n    A = 1\n\n    def m(self):\n        return 1\n"
)


def _splice(rep: str, allowed: set[str]) -> str:
    # Keyword-only, required: a default would be a bypass (pre-fix signature has none).
    return act_loop_mod.splice(SRC, rep, anchor="value", allowed=allowed)


@pytest.mark.parametrize(
    "rep",
    [
        'X = __import__("os").system("touch /tmp/pwn")\n',  # import-time call, non-target
        "def other():\n    return 99\n",  # non-target def
        '@__import__("atexit").register\ndef value():\n    return 2\n',  # new decorator
        'def value(x=__import__("os").getcwd()):\n    return 2\n',  # call in a default
        "class K:\n    A = print('x')\n",  # class body when K is not a target
    ],
)
def test_splice_refuses_code_that_runs_at_import_or_escapes_targets(rep: str) -> None:
    with pytest.raises(ValueError):
        _splice(rep, {"value"})


def test_splice_refuses_calls_in_a_targeted_class_body() -> None:
    with pytest.raises(ValueError):
        _splice("class K:\n    A = __import__('os').getpid()\n", {"K"})


def test_splice_refuses_call_valued_constant_even_when_targeted() -> None:
    src = "N = 1\n\n\ndef value():\n    return N\n"
    with pytest.raises(ValueError):
        act_loop_mod.splice(src, "N = __import__('os').getpid()\n", anchor="value", allowed={"N"})


def test_splice_still_accepts_legitimate_edits() -> None:
    out = _splice("@functools.cache\ndef value():\n    import os\n    return 2\n", {"value"})
    assert "return 2" in out and "def other():\n    return 0" in out
    out = _splice("class K:\n    A = 2\n\n    def m(self):\n        return 2\n", {"K"})
    assert "A = 2" in out


# ---------------------------------------------------------------- integration (real pytest)
MOD = '"""m."""\n\n\ndef value():\n    return 1\n'


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def _repo(root: Path) -> Path:
    repo = root / "repo"
    (repo / "src/pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src/pkg/__init__.py").write_text("")
    (repo / "src/pkg/mod.py").write_text(MOD)
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


def _run(repo: Path, tmp_path: Path, body: str) -> dict:
    return act_loop(
        repo=repo,
        file="src/pkg/mod.py",
        targets=["value"],
        oracle="tests/test_mod.py",
        extra_tests=[],
        task="t",
        task_id="t1",
        model="m",
        chat=lambda _p: {"text": f"```python\ndef value():\n{body}\n```"},
        python=sys.executable,
        max_iters=1,
        log=tmp_path / "log.jsonl",
        callers=[],
        confirm_repeats=1,
    )


def test_verify_run_gets_no_daemon_credentials(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SURREAL_PASS_FAKE_SECRET", "<key>")
    repo = _repo(tmp_path)
    body = "    import os\n    return 3 if 'SURREAL_PASS_FAKE_SECRET' in os.environ else 2"
    res = _run(repo, tmp_path, body)
    assert res["status"] == "GREEN", res  # the model code never saw the secret


def test_hook_planted_by_model_code_never_runs_and_aborts_commit(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    head = _git(repo, "rev-parse", "HEAD")
    marker = tmp_path / "HOOK_RAN"
    hook = repo / ".git/hooks/pre-commit"
    body = (
        "    import os\n"
        f"    p = {str(hook)!r}\n"
        f"    open(p, 'w').write('#!/bin/sh\\ntouch {marker}\\n')\n"
        "    os.chmod(p, 0o755)\n"
        "    return 2"
    )
    res = _run(repo, tmp_path, body)
    assert not marker.exists(), "a hook written by model code was executed"
    assert res["status"] == "TAMPERED", res
    assert _git(repo, "rev-parse", "HEAD") == head
    assert (repo / "src/pkg/mod.py").read_text() == MOD


def test_untracked_conftest_planted_by_model_code_aborts_commit(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    head = _git(repo, "rev-parse", "HEAD")
    body = f"    open({str(repo / 'tests/conftest.py')!r}, 'w').write('# planted\\n')\n    return 2"
    res = _run(repo, tmp_path, body)
    assert res["status"] == "TAMPERED", res
    assert _git(repo, "rev-parse", "HEAD") == head


def test_commit_runs_with_hooks_disabled(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    marker = tmp_path / "HOOK_RAN"
    hook = repo / ".git/hooks/pre-commit"
    hook.write_text(f"#!/bin/sh\ntouch {marker}\n")  # present BEFORE the loop: baseline
    hook.chmod(0o755)
    res = _run(repo, tmp_path, "    return 2")
    assert res["status"] == "GREEN", res
    assert not marker.exists(), "model commits must be made with hooks disabled"


def test_verify_argv_isolates_when_namespaces_are_available(tmp_path: Path, monkeypatch) -> None:
    fake = ("bwrap", "--ro-bind", "/", "/", "--tmpfs", "/tmp", "--unshare-all", "--chdir", "/tmp")
    monkeypatch.setattr(act_loop_mod, "_namespace_prefix", lambda: fake)
    argv = act_loop_mod.verify_argv(tmp_path, sys.executable, tmp_path / "s")
    assert argv[: len(fake)] == list(fake) and "--unshare-all" in argv
    assert argv[-2:] == ["--chdir", str(tmp_path.resolve())]
    assert act_loop_mod.verify_isolation() == "bwrap"
    monkeypatch.setattr(act_loop_mod, "_namespace_prefix", lambda: ())
    assert act_loop_mod.verify_argv(tmp_path, sys.executable, tmp_path / "s") == []
    assert act_loop_mod.verify_isolation() == "env-scrub-only"
