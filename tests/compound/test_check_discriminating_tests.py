"""Item 511: check_discriminating_tests CI script — PRIMARY DISC. gate (2026-06-08).

``check_discriminating_tests.py``: scans ``tests/compound/`` for TIDE-convention test
files (module docstring starts with ``Item NNN:``) and exits 1 if any lack a
discriminating-test marker.  Exit 0 = all files compliant.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: clean corpus (all files have marker) → exit 0.
     Kills impl that always returns 1.
  2. Single gap file → exit 1 AND names the offending file.
     Kills impl that exits 1 but does not identify the gap.
  3. Non-TIDE files (no "Item NNN:" docstring) are excluded from the count.
     Kills impl that flags ALL test_*.py files regardless of TIDE convention.
  4. Legacy "MAIN DISC." marker accepted as equivalent to "PRIMARY DISC."
     Kills impl that only accepts "PRIMARY DISC." literally.
  5. Empty directory → exit 0 (no TIDE files = no gaps).
     Kills impl that crashes on an empty corpus or returns 1 for 0 files.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the CI script helpers via sys.path injection
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).parent.parent.parent / "scripts" / "ci"


def _import_check() -> object:  # type: ignore[return]
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))
    import importlib
    return importlib.import_module("check_discriminating_tests")


_mod = _import_check()


# ---------------------------------------------------------------------------
# Helpers to build synthetic TIDE test files
# ---------------------------------------------------------------------------


def _tide_file_with_marker(tmp_path: Path, name: str, marker: str = "PRIMARY DISC.") -> Path:
    """Write a minimal TIDE test file that CONTAINS the given marker."""
    p = tmp_path / name
    p.write_text(
        f'"""Item 999: synthetic_{name} — TDD.\n\n'
        f"  1. {marker}: kills wrong impl.\n"
        '"""\n\n\ndef test_placeholder() -> None:\n    pass\n',
        encoding="utf-8",
    )
    return p


def _tide_file_no_marker(tmp_path: Path, name: str) -> Path:
    """Write a minimal TIDE test file that LACKS any recognised marker."""
    p = tmp_path / name
    p.write_text(
        '"""Item 999: synthetic — TDD.\n\nSimple happy path only.\n"""\n\n'
        "def test_placeholder() -> None:\n    pass\n",
        encoding="utf-8",
    )
    return p


def _non_tide_file(tmp_path: Path, name: str) -> Path:
    """Write a test file that does NOT start with 'Item NNN:' — not a TIDE file."""
    p = tmp_path / name
    p.write_text(
        '"""Integration test for the batch executor (legacy, no item number).\n"""\n\n'
        "def test_placeholder() -> None:\n    pass\n",
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# 1. PRIMARY DISC.: clean corpus → exit 0
# ---------------------------------------------------------------------------


def test_clean_corpus_exits_zero(tmp_path: Path) -> None:
    """PRIMARY DISC.: all TIDE files have markers → exit 0.

    Kills impl that always returns 1.
    """
    _tide_file_with_marker(tmp_path, "test_alpha.py", "PRIMARY DISC.")
    _tide_file_with_marker(tmp_path, "test_beta.py", "MAIN DISC.")
    total, passing, gaps = _mod.check_directory(tmp_path)
    assert gaps == [], "No gaps expected; got " + repr([str(g) for g in gaps])
    assert total == 2, f"Expected 2 TIDE files; got {total}"
    assert passing == 2, f"Expected 2 passing; got {passing}"


# ---------------------------------------------------------------------------
# 2. Gap file → exit 1 AND the file is named in the gap list
# ---------------------------------------------------------------------------


def test_gap_file_named_in_output(tmp_path: Path) -> None:
    """Single gap file causes exit 1 and the gap list contains the filename.

    Kills impl that exits 1 but does not identify the specific file.
    """
    _tide_file_with_marker(tmp_path, "test_compliant.py")
    gap_file = _tide_file_no_marker(tmp_path, "test_missing_marker.py")

    total, passing, gaps = _mod.check_directory(tmp_path)
    assert len(gaps) == 1, f"Expected 1 gap; got {len(gaps)}: {gaps}"
    assert gaps[0] == gap_file, f"Expected gap {gap_file}; got {gaps[0]}"
    assert total == 2
    assert passing == 1

    # Verify main() exits 1 for this dir
    rc = _mod.main(["--dir", str(tmp_path)])
    assert rc == 1, f"Expected exit code 1; got {rc}"


# ---------------------------------------------------------------------------
# 3. Non-TIDE files excluded from check
# ---------------------------------------------------------------------------


def test_non_tide_files_excluded(tmp_path: Path) -> None:
    """Non-TIDE files (no 'Item NNN:' docstring) not counted as gaps.

    Kills impl that flags ALL test_*.py files including legacy non-TIDE tests.
    """
    _non_tide_file(tmp_path, "test_legacy_integration.py")
    _non_tide_file(tmp_path, "test_autoresearch.py")

    total, passing, gaps = _mod.check_directory(tmp_path)
    assert total == 0, f"Non-TIDE files should not be counted; got total={total}"
    assert gaps == [], f"Non-TIDE files should not be gaps; got {gaps}"


# ---------------------------------------------------------------------------
# 4. Legacy "MAIN DISC." marker accepted
# ---------------------------------------------------------------------------


def test_main_disc_legacy_accepted(tmp_path: Path) -> None:
    """'MAIN DISC.' legacy marker is accepted as equivalent to 'PRIMARY DISC.'.

    Kills impl that only accepts the exact 'PRIMARY DISC.' string.
    """
    _tide_file_with_marker(tmp_path, "test_legacy.py", "MAIN DISC.")
    total, passing, gaps = _mod.check_directory(tmp_path)
    assert gaps == [], f"MAIN DISC. should be accepted; got gaps={gaps}"
    assert passing == 1


# ---------------------------------------------------------------------------
# 5. Empty directory → exit 0 (zero files, zero gaps)
# ---------------------------------------------------------------------------


def test_empty_directory_exits_zero(tmp_path: Path) -> None:
    """Empty directory has no TIDE files and no gaps → exit 0.

    Kills impl that crashes on empty corpus or returns 1 for 0 files.
    """
    total, passing, gaps = _mod.check_directory(tmp_path)
    assert total == 0
    assert passing == 0
    assert gaps == [], f"Empty dir must have no gaps; got {gaps}"

    rc = _mod.main(["--dir", str(tmp_path)])
    assert rc == 0, f"Empty dir should exit 0; got {rc}"
