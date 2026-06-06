"""Frontier-exhaustion oracle (item 40, 2026-06-06) — the build loop's STOP condition as a predicate.

`frontier_is_human_gated(proposals, gated_targets)` is True iff EVERY remaining ScopeProposal.target
is human-gated (or there are no proposals) — i.e. scope cannot be expanded without a human. A
`from_state` variant reads `gated_targets` from the ledger's '## Swept packages' Needs-human column.

Each test fails a plausible wrong impl:
  - `any(...)`/non-empty-intersection instead of `all(...)` → test_unrelated_gated_does_not_force_true,
  - forgetting the empty-proposals → True case → test_no_proposals_is_gated,
  - treating a '0 (note)' Needs-human cell as gated (cell != '0') → test_ledger_zero_with_note_not_gated,
  - parsing the whole file not just the Swept-packages section → test_ledger_section_scoped.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.scope_frontier import (
    ScopeProposal,
    frontier_is_human_gated,
    frontier_is_human_gated_from_state,
    gated_targets_from_ledger,
)


def _prop(target: str) -> ScopeProposal:
    return ScopeProposal(kind="unswept_package", target=target, falsifiable_stub="stub")


def test_all_proposals_gated_is_true() -> None:
    proposals = [_prop("swarm"), _prop("cache")]
    assert frontier_is_human_gated(proposals, gated_targets={"swarm", "cache", "rl"}) is True


def test_one_nongated_proposal_is_false() -> None:
    proposals = [_prop("swarm"), _prop("freshpkg")]
    assert frontier_is_human_gated(proposals, gated_targets={"swarm"}) is False


def test_no_proposals_is_gated() -> None:
    # No frontier left to expand → the STOP condition holds (all([]) == True).
    assert frontier_is_human_gated([], gated_targets=set()) is True


def test_unrelated_gated_does_not_force_true() -> None:
    # A non-gated proposal remains; gated_targets contains only UNRELATED entries.
    # An `any(target in gated)` impl returns False here only because none overlap — so make the
    # discriminating case one where an `intersection` impl would wrongly say True: a gated target
    # present AND a separate non-gated proposal still pending → must be False.
    proposals = [_prop("swarm"), _prop("freshpkg")]
    assert frontier_is_human_gated(proposals, gated_targets={"swarm", "cache"}) is False


def test_ledger_gated_column_parsed(tmp_path: Path) -> None:
    led = tmp_path / "L.md"
    led.write_text(
        "# Ledger\n\n"
        "## Swept packages\n"
        "| Package | Swept | Candidates | A wired | A remaining | B/C/D | Needs-human |\n"
        "|---|---|---|---|---|---|---|\n"
        "| compound | **DONE** | 24 | 9 | 0 | 13 B | 3 (below) |\n"
        "| swarm | classified | 24 | 0 | 12 | - | circular import (below) |\n"
        "| audio | **DONE** | 5 | 0 | 0 | 2 B | 0 |\n"
        "| hookify | **DONE** | 3 | 1 | 0 | 2 reachable | 0 (name-hazard verified distinct) |\n"
        "\n## Next tick\nprose mentioning | pipe | not a table.\n"
    )
    gated = gated_targets_from_ledger(led)
    assert "swarm" in gated  # non-numeric note → gated
    assert "compound" in gated  # count 3 > 0 → gated (even though DONE)
    assert "audio" not in gated  # 0 → not gated
    assert "hookify" not in gated  # '0 (...)' leading-zero → NOT gated


def test_ledger_zero_with_note_not_gated(tmp_path: Path) -> None:
    led = tmp_path / "L.md"
    led.write_text(
        "## Swept packages\n"
        "| Package | Swept | Candidates | A wired | A remaining | B/C/D | Needs-human |\n"
        "|---|---|---|---|---|---|---|\n"
        "| x | **DONE** | 1 | 0 | 0 | - | 0 (verified distinct) |\n"
    )
    assert gated_targets_from_ledger(led) == set()


def test_ledger_section_scoped(tmp_path: Path) -> None:
    # A 7-col pipe row OUTSIDE the Swept-packages section must NOT be parsed as a gated package.
    led = tmp_path / "L.md"
    led.write_text(
        "## Needs human decision\n"
        "| notreal | a | b | c | d | e | 9 |\n"
        "## Swept packages\n"
        "| Package | Swept | Candidates | A wired | A remaining | B/C/D | Needs-human |\n"
        "|---|---|---|---|---|---|---|\n"
        "| realpkg | classified | 1 | 0 | 1 | - | 1 (dup) |\n"
    )
    gated = gated_targets_from_ledger(led)
    assert gated == {"realpkg"}


def test_missing_ledger_is_empty(tmp_path: Path) -> None:
    assert gated_targets_from_ledger(tmp_path / "nope.md") == set()


def test_from_state_returns_bool() -> None:
    # Live composition must not crash and must return a bool (fail-soft over registry + ledger).
    assert isinstance(frontier_is_human_gated_from_state(), bool)
