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

    # Unswept packages are tracked in the ledger (human-curated) — not inferred here to avoid a
    # fabricated list; the caller passes them or reads the ledger.
    return propose_scope_frontier(
        empty_task_slots=empty_slots,
        unused_neuron_countries=unused_countries,
        unswept_packages=[],
    )
