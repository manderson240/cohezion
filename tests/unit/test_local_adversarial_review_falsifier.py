"""run_falsifier must not let a model-authored falsifier write files or run inline code.

Adversarial review 2026-09-21: the prefix allow-list admitted ``python3 -c`` (arbitrary code),
``git log --output=<file>`` and ``sed`` write/exec commands, and 0c11fe151's sys.executable
fallback made the ``python -c`` path reachable in every venv-less worktree. The falsifier is
chosen by a local model reading an untrusted diff, so it is untrusted input.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "local_adversarial_review.py"
_spec = importlib.util.spec_from_file_location("local_adversarial_review_under_test", _PATH)
assert _spec and _spec.loader
lar = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = lar
_spec.loader.exec_module(lar)


@pytest.fixture
def no_exec(monkeypatch):
    """Record argv instead of executing; a refused command must never reach subprocess."""
    ran: list[list[str]] = []

    def _fake_run(argv, **_kw):
        ran.append(list(argv))

        class _P:
            returncode = 0
            stdout = ""
            stderr = ""

        return _P()

    monkeypatch.setattr(lar.subprocess, "run", _fake_run)
    return ran


@pytest.mark.parametrize(
    "cmd",
    [
        "python3 -c \"open('x','w')\"",
        'python -c "print(1)"',
        '.venv/bin/python3 -c "print(1)"',
        "git log --output=/tmp/x",
        "git log -1 --output /tmp/x",
        "git show HEAD --output=/tmp/x",
        "git log --ext-diff -1",
        "git -c core.pager=touch log -1",
        "git grep -O touch foo",
        "git grep -nOtouch foo",
        "pytest -psome_plugin tests/unit",
        "pytest -c /tmp/evil.ini tests/unit",
        "sed -n 'w /tmp/x' README.md",
        "sed -n '1W /tmp/x' README.md",
        "sed -n '1e touch x' README.md",
        "sed -i 's/a/b/' README.md",
        "sed -n -i 1p README.md",
        "sed --in-place -n 1p README.md",
        "sed -n -f script.sed README.md",
        "sed -n -e 1p -e 'w /tmp/x' README.md",
        "rg --pre touch foo",
        ".venv/bin/python3 scripts/ci/phantom_attr_scan.py --out /tmp/x",
        "pytest --junitxml=/tmp/x tests/unit",
        "pytest -p some_plugin tests/unit",
    ],
)
def test_file_writing_or_code_executing_falsifiers_are_refused(cmd, no_exec):
    status, evidence = lar.run_falsifier(cmd)
    assert status == "falsifier-failed", evidence
    assert "refused" in evidence
    assert no_exec == []


@pytest.mark.parametrize(
    "cmd",
    [
        "grep -n def README.md",
        "git log -1 --oneline",
        "git show HEAD --stat",
        "git grep -n run_falsifier",
        "sed -n 1,5p README.md",
        "head -5 README.md",
        "wc -l README.md",
        "cat README.md",
        "rg -n run_falsifier scripts",
        "pytest -q tests/unit/test_import_smoke.py",
        "python3 -m pytest -q -k smoke tests/unit/test_import_smoke.py",
        ".venv/bin/python3 scripts/ci/phantom_attr_scan.py --self-test",
    ],
)
def test_read_only_falsifiers_still_run(cmd, no_exec):
    status, evidence = lar.run_falsifier(cmd)
    assert status == "evidence-attached", evidence
    assert len(no_exec) == 1


def test_benign_falsifier_really_executes():
    """Un-mocked: the allow-list did not turn run_falsifier into a no-op."""
    status, evidence = lar.run_falsifier("git log -1 --oneline")
    assert status == "evidence-attached"
    assert "[exit 0]" in evidence
