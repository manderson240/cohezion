"""Discriminating test for the wiring-sweep edge: cost_optimization → cost_dashboard (2026-06-06).

`cost_dashboard` was a genuine Class-A orphan in cost_optimization/: its public surface
(CostDashboard / get_cost_dashboard + the CostBreakdown/SpendRate/BudgetStatus/TrendPoint
dataclasses) had ZERO production importers — only one test edge (tests/compound/test_cost_dashboard).
Its siblings budget_enforcer + cost_tracker were already re-exported by the package __init__; the
dashboard was simply never added to that public surface. Wired non-destructively by adding it to the
existing __init__ re-export block (same absolute-import + __all__ convention).

Falsifiable: fails if the edge is removed. Each name must resolve FROM the package, be the source
module's own object (identity), and appear in __all__.
"""

from __future__ import annotations


_NAMES = (
    "CostDashboard",
    "get_cost_dashboard",
    "CostBreakdown",
    "SpendRate",
    "BudgetStatus",
    "TrendPoint",
)


def test_cost_dashboard_reexported_from_cost_optimization() -> None:
    import cohezion.cost_optimization as co
    import cohezion.cost_optimization.cost_dashboard as src

    for name in _NAMES:
        assert hasattr(co, name), f"cost_optimization.{name} unreachable — wiring edge missing"
        assert getattr(co, name) is getattr(src, name), f"{name} is not the source object"
        assert name in co.__all__, f"{name} missing from cost_optimization.__all__"


def test_edge_holds_when_submodule_imported_first() -> None:
    import cohezion.cost_optimization.cost_dashboard as src  # noqa: I001
    import cohezion.cost_optimization as co

    assert co.CostDashboard is src.CostDashboard
