"""Discriminating tests for autonomous unswept-package detection (item 31, 2026-06-06).

`unswept_packages_from_ledger()` closes item-26's manual gap: it reads the wiring-sweep ledger's
'## Swept packages' table and returns the packages whose Swept cell is NOT **DONE**. Then
`propose_scope_frontier_from_state` feeds them as unswept_package proposals.

Each test fails a plausible wrong impl:
  - return every package (ignore the **DONE** filter) → T_all_done,
  - parse the whole file (not just the Swept-packages section) → T_scoping,
  - crash on a missing ledger → T_missing,
  - the from_state integration drops the ledger packages → T_wiring.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.scope_frontier import (
    propose_scope_frontier_from_state,
    unswept_packages_from_ledger,
)


_SWEPT_TABLE = """# Ledger

## Swept packages
| Package | Swept | Candidates | A wired | A remaining |
|---|---|---|---|---|
| compound | **DONE** | 24 | 9 | 0 |
| swarm | classified | 24 | 0 | 12 |
| cache | classified | 4 | 0 | 1 |

## Next tick
some prose.
"""


def test_non_done_packages_surface(tmp_path: Path) -> None:
    led = tmp_path / "L.md"
    led.write_text(_SWEPT_TABLE)
    got = unswept_packages_from_ledger(led)
    # Only the non-DONE rows; compound (**DONE**) excluded; header/separator skipped.
    assert got == ["swarm", "cache"]


def test_all_done_ledger_returns_empty(tmp_path: Path) -> None:
    led = tmp_path / "L.md"
    led.write_text(
        "## Swept packages\n| Package | Swept |\n|---|---|\n"
        "| compound | **DONE** |\n| inference | **DONE** |\n"
    )
    # Every package swept → nothing owed. A wrong impl that returns all packages fails here.
    assert unswept_packages_from_ledger(led) == []


def test_only_swept_packages_section_is_parsed(tmp_path: Path) -> None:
    # A different table (Classification) has non-DONE-looking 2nd cells but is NOT the swept table.
    led = tmp_path / "L.md"
    led.write_text(
        "## Classification\n| Class | Meaning | Action |\n|---|---|---|\n"
        "| A | no importer | WIRE |\n\n"
        "## Swept packages\n| Package | Swept |\n|---|---|\n"
        "| swarm | classified |\n| compound | **DONE** |\n"
    )
    got = unswept_packages_from_ledger(led)
    # 'A' (from the Classification table) must NOT leak in; only swarm from the swept table.
    assert got == ["swarm"]


def test_missing_ledger_returns_empty_no_crash(tmp_path: Path) -> None:
    assert unswept_packages_from_ledger(tmp_path / "nope.md") == []


def test_from_state_wires_ledger_unswept_packages() -> None:
    # Integration: from_state's unswept_package proposals must exactly mirror the ledger helper
    # (proving the wiring, independent of which packages happen to be non-DONE in the live ledger).
    proposals = propose_scope_frontier_from_state()
    proposed_pkgs = sorted(p.target for p in proposals if p.kind == "unswept_package")
    assert proposed_pkgs == sorted(unswept_packages_from_ledger())
