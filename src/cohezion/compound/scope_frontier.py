"""Scope-frontier proposer — operationalizes "expand scope each tick" (item 26).

A REPORT-ONLY mechanism: given the system's remaining gaps (empty `Task` specialist slots, unused
neuron `country` regions, unswept wiring packages), it emits the next falsifiable frontier-item
stubs. It PROPOSES, never auto-appends to the backlog (human-gated, exactly like the item-14
specialist recruiter). When every frontier is closed it proposes nothing — which is the signal
that scope cannot be expanded without a human decision (the loop's termination condition).

The pure `propose_scope_frontier` takes the gaps as explicit lists (deterministic, testable);
`propose_scope_frontier_from_state` reads them from the live FleetRegistry + neuron-country
allowlist so a caller can ask "what's the next thing to grow?" without wiring the sources by hand.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_LEDGER = _REPO / "docs" / "audits" / "WIRING_SWEEP_LEDGER.md"


@dataclass(frozen=True)
class ScopeProposal:
    """A proposed next frontier item. ``kind`` is the gap type; ``target`` the specific gap;
    ``falsifiable_stub`` a one-line check the eventual backlog item must satisfy."""

    kind: str  # "empty_task_slot" | "unused_neuron_country" | "unswept_package"
    target: str
    falsifiable_stub: str


def propose_scope_frontier(
    *,
    empty_task_slots: list[str],
    unused_neuron_countries: list[str],
    unswept_packages: list[str],
) -> list[ScopeProposal]:
    """Emit one frontier proposal per open gap. All gaps closed → ``[]`` (nothing to propose).

    Report-only: returns proposals, never mutates the backlog or any registry. Each proposal
    carries a falsifiable stub so the appended item is testable by construction.
    """
    proposals: list[ScopeProposal] = []
    for task in empty_task_slots:
        proposals.append(
            ScopeProposal(
                kind="empty_task_slot",
                target=task,
                falsifiable_stub=(
                    f"register a verified specialist for Task.{task}; for_task({task}) returns it; "
                    f"verified_working=False until a serving proof passes (research-gated id)"
                ),
            )
        )
    for country in unused_neuron_countries:
        proposals.append(
            ScopeProposal(
                kind="unused_neuron_country",
                target=country,
                falsifiable_stub=(
                    f"a country='{country}' neuron is deposited iff its evidence gate passes; "
                    f"a failing gate deposits none; pytest never writes the real graph"
                ),
            )
        )
    for package in unswept_packages:
        proposals.append(
            ScopeProposal(
                kind="unswept_package",
                target=package,
                falsifiable_stub=(
                    f"{package}/ file-level swept; each genuine-A orphan wired with a discriminating "
                    f"test; 0 genuine-A remaining (both-import-order robust)"
                ),
            )
        )
    return proposals


def unswept_packages_from_ledger(ledger_path: Path | None = None) -> list[str]:
    """Packages in the ledger's '## Swept packages' table NOT marked ``**DONE**`` (item 31).

    Closes item-26's one manual gap: `propose_scope_frontier_from_state` previously passed
    ``unswept_packages=[]``. This parses the wiring-sweep ledger's swept-package table and returns
    the package names whose *Swept* cell is anything other than ``**DONE**`` (e.g. ``classified``,
    ``BLOCKED``, ``in progress``) — the packages the wiring loop still owes a full sweep.

    Read-only and fail-soft: scoped strictly to the ``## Swept packages`` section (other ledger
    tables are ignored); the header/separator rows are skipped; a missing/unreadable ledger or a
    table with no non-DONE rows yields ``[]`` (never raises).
    """
    path = ledger_path or _DEFAULT_LEDGER
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    in_section = False
    unswept: list[str] = []
    for line in lines:
        if line.startswith("## "):
            in_section = line.strip().lower().startswith("## swept packages")
            continue
        if not in_section or not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        pkg, status = cells[0], cells[1]
        if pkg.lower() == "package" or set(pkg) <= set("-: "):
            continue  # header row or |---| separator
        if status != "**DONE**":
            unswept.append(pkg)
    return unswept


def propose_scope_frontier_from_state() -> list[ScopeProposal]:
    """Read the live gaps and propose. Empty task slots come from the FleetRegistry; the neuron
    countries that already have a deposit path (inference/skill/cerebellum) count as used.

    Fail-soft: if the registry can't be read, returns ``[]`` rather than raising.
    """
    empty_slots: list[str] = []
    try:
        from cohezion.inference.registry import Task, get_registry

        reg = get_registry()
        empty_slots = [t.name for t in Task if not reg.for_task(t)]
    except Exception:
        empty_slots = []

    # Neuron countries with a deposit path wired (items 15/16/24). Allowlist minus these = unused.
    wired_countries = {"inference", "skill", "cerebellum"}
    unused_countries: list[str] = []
    try:
        from cohezion.governance.knowledge_bridge import _NEURON_COUNTRIES

        unused_countries = sorted(set(_NEURON_COUNTRIES) - wired_countries)
    except Exception:
        unused_countries = []

    # Unswept packages now read from the live ledger (item 31) — no longer a hardcoded [].
    # Fail-soft: a missing ledger yields [] inside the helper.
    unswept = unswept_packages_from_ledger()
    return propose_scope_frontier(
        empty_task_slots=empty_slots,
        unused_neuron_countries=unused_countries,
        unswept_packages=unswept,
    )


def frontier_is_human_gated(
    proposals: list[ScopeProposal], *, gated_targets: Iterable[str]
) -> bool:
    """The build loop's STOP condition as a pure, testable predicate (item 40).

    Returns True iff EVERY remaining proposal's ``target`` is in ``gated_targets`` (or there are no
    proposals) — i.e. scope cannot be expanded without a human decision. Returns False as soon as
    ONE proposal is auto-actionable (its target is NOT gated): the loop should keep working while
    any gap is auto-actionable. Uses ``all(...)`` (not ``any``/intersection) so a single gated
    target among auto-actionable ones does NOT prematurely declare the frontier exhausted.
    ``all([]) == True`` gives the no-proposals → gated case for free. Pure (no I/O).
    """
    gated = set(gated_targets)
    return all(p.target in gated for p in proposals)


def _ledger_cell_is_gated(cell: str) -> bool:
    """A Needs-human cell is gated when its leading token is a positive count or a non-numeric note.

    ``"0"`` / ``"0 (verified distinct)"`` (leading zero) → NOT gated; ``"3 (below)"`` → gated;
    ``"circular import (below)"`` (non-numeric note) → gated; empty → NOT gated.
    """
    cell = cell.strip()
    if not cell:
        return False
    first = cell.split()[0]
    try:
        return int(first) > 0
    except ValueError:
        return True


def gated_targets_from_ledger(ledger_path: Path | None = None) -> set[str]:
    """Package names flagged human-gated in the ledger's '## Swept packages' Needs-human column (item 40).

    A package is gated when its Needs-human cell ``_ledger_cell_is_gated``. Section-scoped strictly
    to ``## Swept packages`` (mirrors ``unswept_packages_from_ledger``) and fail-soft: a missing or
    unreadable ledger, or a table without the 7th column, yields ``set()`` (never raises).
    """
    path = ledger_path or _DEFAULT_LEDGER
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return set()

    in_section = False
    gated: set[str] = set()
    for line in lines:
        if line.startswith("## "):
            in_section = line.strip().lower().startswith("## swept packages")
            continue
        if not in_section or not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            continue  # not the 7-col swept-package row (header/separator/short row)
        pkg, needs_human = cells[0], cells[-1]
        if pkg.lower() == "package" or set(pkg) <= set("-: "):
            continue  # header row or |---| separator
        if _ledger_cell_is_gated(needs_human):
            gated.add(pkg)
    return gated


def frontier_is_human_gated_from_state() -> bool:
    """Live composition (item 40): the current frontier proposals are ALL human-gated.

    Composes ``propose_scope_frontier_from_state`` (items 26/31) with ``gated_targets_from_ledger``.
    True = the build loop's scope-expansion is exhausted without a human decision. Fail-soft via
    its two constituents (each returns empty on error → predicate over [] is True).
    """
    return frontier_is_human_gated(
        propose_scope_frontier_from_state(),
        gated_targets=gated_targets_from_ledger(),
    )
