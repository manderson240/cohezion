"""Item 515: check_discriminating_tests --dir extension to tests/unit and tests/swarm (2026-06-08).

The CI script's ``--dir`` flag allows scanning any directory, not just
``tests/compound/``.  This item verifies the extension works correctly
for the ``tests/unit/`` and ``tests/swarm/`` directories.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: ``--dir tests/unit`` exits 0 on the current corpus.
     Kills impl that hardcodes "tests/compound" and errors on other dirs.
  2. ``--dir tests/swarm`` exits 0 on the current corpus.
     Kills impl that only handles one non-compound dir.
  3. A TIDE gap in a synthetic unit-style dir causes exit 1 + names the file.
     Kills impl that ignores gaps in non-compound dirs.
  4. Non-TIDE files in a unit-style dir are not flagged (0 TIDE files found).
     Kills impl that counts all test_*.py files regardless of Item prefix.
  5. Two independent directory scans return independent results (no cross-contamination).
     Kills impl that shares state between calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Import helpers from the CI script
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).parent.parent.parent / "scripts" / "ci"
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import importlib

_mod = importlib.import_module("check_discriminating_tests")

# Repo root for real directory references
_REPO_ROOT = Path(__file__).parent.parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tide_file_no_marker(tmp_path: Path, name: str) -> Path:
    """TIDE test file lacking any discriminating marker."""
    p = tmp_path / name
    p.write_text(
        '"""Item 999: synthetic_unit — TDD.\n\nHappy path only.\n"""\n\n'
        "def test_placeholder() -> None:\n    pass\n",
        encoding="utf-8",
    )
    return p


def _non_tide_file(tmp_path: Path, name: str) -> Path:
    """Non-TIDE test file (no Item NNN: prefix)."""
    p = tmp_path / name
    p.write_text(
        '"""Legacy integration test — no item number.\n"""\n\n'
        "def test_placeholder() -> None:\n    pass\n",
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# 1. PRIMARY DISC.: tests/unit exits 0 on current corpus
# ---------------------------------------------------------------------------


def test_unit_dir_exits_zero() -> None:
    """PRIMARY DISC.: --dir tests/unit exits 0 on the current corpus.

    Kills impl that hardcodes 'tests/compound' and refuses other dirs.
    """
    unit_dir = _REPO_ROOT / "tests" / "unit"
    if not unit_dir.is_dir():
        # If tests/unit doesn't exist yet, the scanner should still exit 0
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            rc = _mod.main(["--dir", td])
            assert rc == 0, f"Empty dir should exit 0; got {rc}"
        return
    rc = _mod.main(["--dir", str(unit_dir)])
    assert rc == 0, f"tests/unit should exit 0; got {rc}"


# ---------------------------------------------------------------------------
# 2. tests/swarm exits 0 on current corpus
# ---------------------------------------------------------------------------


def test_swarm_dir_exits_zero() -> None:
    """--dir tests/swarm exits 0 on the current corpus.

    Kills impl that only supports tests/unit as a second dir.
    """
    swarm_dir = _REPO_ROOT / "tests" / "swarm"
    if not swarm_dir.is_dir():
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            rc = _mod.main(["--dir", td])
            assert rc == 0, f"Empty dir should exit 0; got {rc}"
        return
    rc = _mod.main(["--dir", str(swarm_dir)])
    assert rc == 0, f"tests/swarm should exit 0; got {rc}"


# ---------------------------------------------------------------------------
# 3. A TIDE gap in a synthetic unit-style dir causes exit 1 + names the file
# ---------------------------------------------------------------------------


def test_gap_in_non_compound_dir_detected(tmp_path: Path) -> None:
    """TIDE gap in a unit-style synthetic dir causes exit 1 and names the file.

    Kills impl that only detects gaps in tests/compound.
    """
    gap_file = _tide_file_no_marker(tmp_path, "test_some_item.py")
    total, passing, gaps = _mod.check_directory(tmp_path)
    assert len(gaps) == 1, f"Expected 1 gap; got {gaps}"
    assert gaps[0] == gap_file, f"Expected gap={gap_file}; got {gaps[0]}"

    rc = _mod.main(["--dir", str(tmp_path)])
    assert rc == 1, f"Expected exit 1 for gap; got {rc}"


# ---------------------------------------------------------------------------
# 4. Non-TIDE files in unit-style dir not flagged (0 TIDE files)
# ---------------------------------------------------------------------------


def test_non_tide_files_in_unit_dir_not_flagged(tmp_path: Path) -> None:
    """Non-TIDE files in a unit-style dir produce 0 TIDE files, 0 gaps.

    Kills impl that flags all test_*.py files regardless of Item prefix.
    """
    _non_tide_file(tmp_path, "test_legacy_unit.py")
    _non_tide_file(tmp_path, "test_integration.py")

    total, passing, gaps = _mod.check_directory(tmp_path)
    assert total == 0, f"Non-TIDE files should not be TIDE-counted; got total={total}"
    assert gaps == [], f"Non-TIDE files should not be gaps; got {gaps}"


# ---------------------------------------------------------------------------
# 5. Two independent dir scans do not share state
# ---------------------------------------------------------------------------


def test_independent_dir_scans_no_cross_contamination(tmp_path: Path) -> None:
    """Two independent scans return independent results (no shared state).

    Kills impl that accumulates gaps across calls.
    """
    dir_a = tmp_path / "dir_a"
    dir_b = tmp_path / "dir_b"
    dir_a.mkdir()
    dir_b.mkdir()

    # dir_a: one TIDE file with no marker (gap)
    _tide_file_no_marker(dir_a, "test_a.py")
    # dir_b: empty (no TIDE files)

    total_a, passing_a, gaps_a = _mod.check_directory(dir_a)
    total_b, passing_b, gaps_b = _mod.check_directory(dir_b)

    assert len(gaps_a) == 1, f"dir_a should have 1 gap; got {gaps_a}"
    assert len(gaps_b) == 0, f"dir_b should have 0 gaps; got {gaps_b}"
    assert total_b == 0, "dir_b has no TIDE files"
    # Scan b did not inherit dir_a's gap
    assert gaps_a[0].parent == dir_a, "Gap must be in dir_a, not dir_b"
