"""Discriminating test for the wiring-sweep edge: cost_optimization → forecast_engine (2026-06-06).

`forecast_engine` was a genuine Class-A orphan in cost_optimization/ (same shape as cost_dashboard
wired the prior tick): its public surface (ForecastEngine / get_forecast_engine / reset_forecast_engine
+ Forecast/ForecastSummary/AnomalyScore) had ZERO production importers — only a test edge. Wired
non-destructively by adding it to the existing __init__ re-export block. This COMPLETES cost_optimization/.

Falsifiable: fails if the edge is removed. Each name must resolve FROM the package, be the source
module's own object (identity), and appear in __all__.
"""

from __future__ import annotations


_NAMES = (
    "ForecastEngine",
    "get_forecast_engine",
    "reset_forecast_engine",
    "Forecast",
    "ForecastSummary",
    "AnomalyScore",
)


def test_forecast_engine_reexported_from_cost_optimization() -> None:
    import cohezion.cost_optimization as co
    import cohezion.cost_optimization.forecast_engine as src

    for name in _NAMES:
        assert hasattr(co, name), f"cost_optimization.{name} unreachable — wiring edge missing"
        assert getattr(co, name) is getattr(src, name), f"{name} is not the source object"
        assert name in co.__all__, f"{name} missing from cost_optimization.__all__"


def test_edge_holds_when_submodule_imported_first() -> None:
    import cohezion.cost_optimization.forecast_engine as src  # noqa: I001
    import cohezion.cost_optimization as co

    assert co.ForecastEngine is src.ForecastEngine
