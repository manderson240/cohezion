"""Tests for scripts/ci/self_test_coverage.py.

The meta-gate exists because `ruff_ratchet.py` failed unconditionally for weeks
while reporting "this PR adds new lint debt" -- nothing could distinguish "the
gate is broken" from "your change is bad". These tests pin the two properties
that make the meta-gate worth having:

* a NEW CI gate that cannot verify itself is rejected;
* the meta-gate never passes vacuously -- if it derives no gates at all, it
  fails loudly instead of reporting success over an empty set. Every defect
  found on 2026-08-27 was a silent one, and a checker that checks nothing while
  printing a tick is the purest form of that failure.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "self_test_coverage.py"


def _load():
    spec = importlib.util.spec_from_file_location("self_test_coverage", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def gate(tmp_path, monkeypatch):
    """Meta-gate pointed at a synthetic scripts/ci tree and workflow file."""
    module = _load()
    ci_dir = tmp_path / "ci"
    ci_dir.mkdir()
    workflow = tmp_path / "workflow.yml"
    monkeypatch.setattr(module, "CI_DIR", ci_dir)
    monkeypatch.setattr(module, "GATE_SOURCES", (workflow,))
    monkeypatch.setattr(module, "REPO", tmp_path)
    monkeypatch.setattr(module.sys, "argv", ["self_test_coverage.py"])

    def add_gate(name: str, *, self_tests: bool, self_test_passes: bool = True) -> None:
        if not self_tests:
            body = "print('hi')\n"
        else:
            # A real script: the meta-gate EXECUTES it, so a stub string is not enough.
            rc = 0 if self_test_passes else 1
            body = f"import sys\nif '--self-test' in sys.argv:\n    sys.exit({rc})\n"
        (ci_dir / name).write_text(body, encoding="utf-8")
        workflow.write_text(
            workflow.read_text(encoding="utf-8") if workflow.exists() else "",
            encoding="utf-8",
        )
        with workflow.open("a", encoding="utf-8") as fh:
            fh.write(f"run: python scripts/ci/{name}\n")

    module.add_gate = add_gate  # type: ignore[attr-defined]
    return module


def test_gate_whose_self_test_FAILS_is_rejected(gate, capsys):
    """DISCRIMINATING: red while the meta-gate only greps for the flag.

    doc_code_consistency.py carried a --self-test that printed "BROKEN -- a check
    cannot fail" and exited 1 for an unknown period. It satisfied a substring
    check while being unable to detect anything, and CI stayed red-and-ignored
    behind it. Presence of the flag is not evidence of health; only running it is.
    """
    gate.add_gate("rotted_gate.py", self_tests=True, self_test_passes=False)

    assert gate.main() == 1
    out = capsys.readouterr().out
    assert "rotted_gate.py" in out
    assert "FAILS" in out


def test_gate_whose_self_test_passes_is_accepted(gate, capsys):
    """Negative control: a healthy self-test must not be reported as rotted."""
    gate.add_gate("healthy_gate.py", self_tests=True, self_test_passes=True)

    assert gate.main() == 0
    assert "FAILS" not in capsys.readouterr().out


def test_new_gate_without_self_test_is_rejected(gate, capsys):
    """DISCRIMINATING: red if a non-self-testing gate is allowed through."""
    gate.add_gate("brand_new_gate.py", self_tests=False)

    assert gate.main() == 1
    out = capsys.readouterr().out
    assert "brand_new_gate.py" in out
    assert "cannot verify themselves" in out


def test_new_gate_with_self_test_passes(gate, capsys):
    """The compliant path: a gate that can check itself is accepted."""
    gate.add_gate("good_gate.py", self_tests=True)

    assert gate.main() == 0
    assert "1/1 CI gates self-test" in capsys.readouterr().out


def test_grandfathered_gate_is_tolerated(gate, capsys):
    """Pre-existing debt does not block; it is named and carried."""
    gate.add_gate("legacy_gate.py", self_tests=False)
    gate.GRANDFATHERED = frozenset({"legacy_gate.py"})

    assert gate.main() == 0
    assert "grandfathered" in capsys.readouterr().out


def test_grandfathered_gate_that_gains_self_test_is_reported(gate, capsys):
    """The ratchet's downward step: tell the author to shrink the list."""
    gate.add_gate("legacy_gate.py", self_tests=True)
    gate.GRANDFATHERED = frozenset({"legacy_gate.py"})

    assert gate.main() == 0
    out = capsys.readouterr().out
    assert "now" in out and "self-test" in out
    assert "only shrinks" in out


def test_empty_derivation_fails_rather_than_passing_vacuously(gate, capsys):
    """DISCRIMINATING: red if a gate that found nothing reports success.

    If the workflow files move or become unreadable, the derived gate set is
    empty. Printing a tick over an empty set is exactly the silent-failure mode
    this whole meta-gate exists to eliminate.
    """
    assert gate.main() == 1
    out = capsys.readouterr().out
    assert "ZERO gates" in out
    assert "blind" in out


def test_self_test_flag_exercises_the_detector(gate, monkeypatch, capsys):
    """The meta-gate must itself satisfy the rule it enforces."""
    monkeypatch.setattr(gate.sys, "argv", ["self_test_coverage.py", "--self-test"])
    assert gate.main() == 0
    assert "SELF-TEST OK" in capsys.readouterr().out


def test_grandfathered_list_has_no_stale_entries() -> None:
    """Every grandfathered name must still be a real CI gate.

    A stale entry silently exempts nothing, and hides that the list stopped
    describing reality -- the same rot that made the lint baseline meaningless.
    """
    module = _load()
    gates = module.ci_invoked_gates()
    assert gates, "no CI gates derived — the workflow sources moved"
    stale = sorted(module.GRANDFATHERED - gates)
    assert not stale, f"GRANDFATHERED names scripts CI no longer runs: {stale}"
