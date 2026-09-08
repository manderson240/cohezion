"""Tests for scripts/ci/ruff_ratchet.py baseline provenance.

Guards the 2026-08-27 root-cause finding. Commit 66f5186d5 hand-edited the
baseline 749 -> 471 while the tree actually held 683 -> 758 violations. Because
``--update`` can only ever write the *measured* count, that number was typed,
not measured. The gate then failed unconditionally and told every author "this
PR adds new lint debt" -- false and unactionable -- so the team learned to
ignore it, and with policing gone the count drifted to 1302.

Two behaviours are pinned here, and both must be discriminating:

* an UNVERIFIED baseline is reported as a gate misconfiguration, never as the
  author's debt (blaming the wrong person is what got the gate ignored);
* ``--update`` may raise ONCE to replace a fiction with a measurement, but stays
  down-only afterwards. Without that exemption the only way out of a
  permanently-red gate is to hand-edit the file again -- the very act that
  caused the failure.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_RATCHET = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "ruff_ratchet.py"


def _load():
    spec = importlib.util.spec_from_file_location("ruff_ratchet", _RATCHET)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def ratchet(tmp_path, monkeypatch):
    """Ratchet module with a temp baseline file and a stubbed violation count.

    ``sys.argv`` is monkeypatched (not assigned) so --update mode cannot leak
    from one test into the next.
    """
    module = _load()
    monkeypatch.setattr(module, "BASELINE_FILE", tmp_path / "lint_baseline.txt")
    monkeypatch.setattr(module.sys, "argv", ["ruff_ratchet.py"])

    def set_count(n: int) -> None:
        monkeypatch.setattr(module, "_current_count", lambda: n)

    def update_mode() -> None:
        monkeypatch.setattr(module.sys, "argv", ["ruff_ratchet.py", "--update"])

    module.set_count = set_count  # type: ignore[attr-defined]
    module.update_mode = update_mode  # type: ignore[attr-defined]
    return module


def _write(module, text: str) -> None:
    module.BASELINE_FILE.write_text(text, encoding="utf-8")


def test_unverified_baseline_reports_misconfiguration_not_author_debt(ratchet, capsys):
    """DISCRIMINATING: red if an unstamped baseline is treated as ordinary debt.

    This is the historical case verbatim: baseline 471, tree at 758.
    """
    _write(ratchet, "471\n")
    ratchet.set_count(758)

    assert ratchet.main() == 1
    out = capsys.readouterr().out
    assert "UNVERIFIED" in out
    assert "misconfiguration" in out.lower()
    assert "adds new lint debt" not in out, (
        "an unmeasured baseline must not be reported as the author's fault -- "
        "blaming the wrong person is precisely why this gate was ignored"
    )


def test_measured_baseline_over_budget_still_blames_the_change(ratchet, capsys):
    """The other half: with a real baseline, new debt IS the author's to fix."""
    _write(ratchet, f"471\n{ratchet._PROVENANCE}\n")
    ratchet.set_count(758)

    assert ratchet.main() == 1
    out = capsys.readouterr().out
    assert "adds new lint debt" in out
    assert "UNVERIFIED" not in out


def test_update_may_raise_once_to_replace_an_unverified_baseline(ratchet):
    """DISCRIMINATING: red while down-only blocks repair of a fictitious value.

    Without this, a permanently-red gate has no sanctioned fix and the only
    available action is hand-editing -- the original defect.
    """
    _write(ratchet, "471\n")
    ratchet.set_count(615)

    ratchet.update_mode()
    assert ratchet.main() == 0
    assert ratchet.BASELINE_FILE.read_text().splitlines()[0] == "615"


def test_update_refuses_to_raise_a_measured_baseline(ratchet):
    """The exemption is one-shot: a stamped baseline stays down-only."""
    _write(ratchet, f"471\n{ratchet._PROVENANCE}\n")
    ratchet.set_count(615)
    ratchet.update_mode()

    assert ratchet.main() == 1
    assert ratchet.BASELINE_FILE.read_text().splitlines()[0] == "471", (
        "a measured baseline must never be inflated"
    )


def test_update_writes_the_provenance_stamp(ratchet):
    """A measured baseline is self-declaring, so the gate can trust it."""
    _write(ratchet, "900\n")
    ratchet.set_count(615)
    ratchet.update_mode()
    ratchet.main()

    assert ratchet._PROVENANCE in ratchet.BASELINE_FILE.read_text()
    assert ratchet._read_baseline() == (615, True)


def test_read_baseline_ignores_comments_and_reports_provenance(ratchet):
    """Parsing must survive the stamp and any future commentary."""
    _write(ratchet, f"{ratchet._PROVENANCE}\n615\n# a note\n")
    assert ratchet._read_baseline() == (615, True)

    _write(ratchet, "615\n# a note\n")
    assert ratchet._read_baseline() == (615, False)


def test_equal_to_measured_baseline_passes(ratchet, capsys):
    """The green path is unchanged."""
    _write(ratchet, f"615\n{ratchet._PROVENANCE}\n")
    ratchet.set_count(615)

    assert ratchet.main() == 0
    assert "no new lint debt" in capsys.readouterr().out
