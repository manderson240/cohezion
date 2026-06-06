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
