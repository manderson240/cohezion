"""Human-gate decision report (item 59, 2026-06-06) — item-40's boolean oracle made ACTIONABLE.

`human_gate_report(proposals, gated_reasons)` returns, for each currently human-gated frontier
proposal, `HumanGateDecision{target, kind, gate_reason}` — the concrete decisions a human must make
to unblock auto-scope-expansion. It composes item-26/31 `propose_scope_frontier_from_state` with a
new `gated_reasons_from_ledger` (extends item-40 `gated_targets_from_ledger` from a set to a
`{target: reason}` map, reason = the EXACT ledger Needs-human cell). Report-only, pure.

Each test fails a plausible wrong impl:
  - lists EVERY proposal (not just gated ones) → test_auto_actionable_proposal_absent,
  - fabricates/blanks the reason instead of the exact ledger cell → test_gated_proposal_carries_exact_reason,
  - blows up / fabricates a reason when a gated target has an empty cell → test_empty_reason_not_fabricated,
  - drops the proposal's kind → test_kind_preserved,
  - `gated_reasons_from_ledger` returns a set / loses the cell text → test_reasons_map_carries_cell.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.scope_frontier import (
    ScopeProposal,
    gated_reasons_from_ledger,
    human_gate_report,
    human_gate_report_from_state,
)


def _prop(target: str, kind: str = "unswept_package") -> ScopeProposal:
    return ScopeProposal(kind=kind, target=target, falsifiable_stub="stub")


def test_gated_proposal_carries_exact_reason() -> None:
    proposals = [_prop("swarm")]
    report = human_gate_report(proposals, gated_reasons={"swarm": "circular import (below)"})
    assert len(report) == 1
    assert report[0].target == "swarm"
    assert report[0].gate_reason == "circular import (below)"  # EXACT cell, not paraphrased


def test_auto_actionable_proposal_absent() -> None:
    # Only "swarm" is gated; "freshpkg" is auto-actionable → it must NOT appear in the report.
    proposals = [_prop("swarm"), _prop("freshpkg")]
    report = human_gate_report(proposals, gated_reasons={"swarm": "3 (below)"})
    assert [d.target for d in report] == ["swarm"]  # an impl that lists every proposal fails here


def test_empty_reason_not_fabricated() -> None:
    # A target gated (a key) but with an empty cell → honest empty reason, never invented.
    proposals = [_prop("core")]
    report = human_gate_report(proposals, gated_reasons={"core": ""})
    assert len(report) == 1 and report[0].gate_reason == ""


def test_kind_preserved() -> None:
    proposals = [_prop("OCR_DOC", kind="empty_task_slot")]
    report = human_gate_report(proposals, gated_reasons={"OCR_DOC": "needs serving proof"})
    assert report[0].kind == "empty_task_slot"


def test_empty_and_all_actionable() -> None:
    assert human_gate_report([], gated_reasons={}) == []
    assert human_gate_report([_prop("a"), _prop("b")], gated_reasons={}) == []  # nothing gated


def test_reasons_map_carries_cell(tmp_path: Path) -> None:
    led = tmp_path / "L.md"
    led.write_text(
        "## Swept packages\n"
        "| Package | Swept | Candidates | A wired | A remaining | B/C/D | Needs-human |\n"
        "|---|---|---|---|---|---|---|\n"
        "| compound | **DONE** | 24 | 9 | 0 | 13 B | 3 (below) |\n"
        "| swarm | classified | 24 | 0 | 12 | - | circular import (below) |\n"
        "| audio | **DONE** | 5 | 0 | 0 | 2 B | 0 |\n"
    )
    reasons = gated_reasons_from_ledger(led)
    assert reasons["compound"] == "3 (below)"  # exact cell, not just membership
    assert reasons["swarm"] == "circular import (below)"
    assert "audio" not in reasons  # 0 → not gated (mirrors gated_targets_from_ledger)


def test_reasons_map_missing_ledger_empty(tmp_path: Path) -> None:
    assert gated_reasons_from_ledger(tmp_path / "nope.md") == {}


def test_from_state_returns_list() -> None:
    # Live composition must not crash and must return a list (fail-soft over registry + ledger).
    assert isinstance(human_gate_report_from_state(), list)
