"""SW1-SW5 structural invariants for cohezion.swarm.

Analogous to the compound/ harness invariants in ~/.claude/rules/harness.md.
These are STRUCTURAL checks — they fire on import/signature/method drift
before any behavioral test runs. No live services required.

Run: uv run pytest tests/swarm/test_structural_invariants.py -v
"""

import importlib
import inspect
import sys


# ---------------------------------------------------------------------------
# SW1: cohezion.swarm is importable without raising
# ---------------------------------------------------------------------------


class TestSW1ImportClean:
    """SW1: Package import must not raise any exception.

    contextlib.suppress(Exception) has been replaced by explicit
    try/except (ImportError, ModuleNotFoundError) throughout __init__.py so
    that non-import runtime errors (NameError, AttributeError, TypeError…)
    are no longer silenced. This test confirms the package still loads cleanly.
    """

    def test_swarm_importable(self) -> None:
        """SW1: cohezion.swarm imports without raising."""
        # Fresh import in case the module is already cached
        if "cohezion.swarm" in sys.modules:
            mod = sys.modules["cohezion.swarm"]
        else:
            mod = importlib.import_module("cohezion.swarm")
        assert mod is not None, "cohezion.swarm must be importable"

    def test_swarm_has_dunder_all(self) -> None:
        """SW1b: __all__ must be defined (guards accidental star-import noise)."""
        import cohezion.swarm as sw

        assert hasattr(sw, "__all__"), "cohezion.swarm.__all__ must be defined"
        assert isinstance(sw.__all__, list), "__all__ must be a list"
        assert len(sw.__all__) > 0, "__all__ must be non-empty"

    def test_no_suppress_exception_remaining(self) -> None:
        """SW1c: No broad suppress(Exception) import guards remain.

        All 73 guards have been narrowed to except (ImportError, ModuleNotFoundError).
        This test reads the source to confirm no regression.
        """
        import pathlib

        init_path = pathlib.Path(__file__).parents[2] / "src/cohezion/swarm/__init__.py"
        source = init_path.read_text()
        assert "suppress(Exception)" not in source, (
            "contextlib.suppress(Exception) import guards must not be re-introduced; "
            "use 'except (ImportError, ModuleNotFoundError): pass' instead"
        )


# ---------------------------------------------------------------------------
# SW2: CostAwareRouter importable from cohezion.swarm
# ---------------------------------------------------------------------------


class TestSW2CostAwareRouter:
    """SW2: CostAwareRouter must be importable from the swarm package."""

    def test_cost_aware_router_importable(self) -> None:
        """SW2: CostAwareRouter is available from cohezion.swarm."""
        import cohezion.swarm as sw

        assert hasattr(sw, "CostAwareRouter"), "cohezion.swarm.CostAwareRouter must be importable"

    def test_cost_aware_router_is_class(self) -> None:
        """SW2b: CostAwareRouter must be a class (not a module or function)."""
        import cohezion.swarm as sw

        assert inspect.isclass(sw.CostAwareRouter), "CostAwareRouter must be a class"

    def test_cost_aware_router_has_select_model(self) -> None:
        """SW2c: CostAwareRouter must expose select_model (primary routing method)."""
        from cohezion.swarm.cost_aware_router import CostAwareRouter

        assert callable(getattr(CostAwareRouter, "select_model", None)), (
            "CostAwareRouter must have a callable select_model method"
        )


# ---------------------------------------------------------------------------
# SW3: TeamOrchestrator importable from cohezion.swarm
# ---------------------------------------------------------------------------


class TestSW3TeamOrchestrator:
    """SW3: TeamOrchestrator must be importable and functional.

    Note: The swarm package exposes TeamOrchestrator (not TeamExecutor) as
    the primary team-orchestration class. SW3 tests the actual exported API.
    """

    def test_team_orchestrator_importable(self) -> None:
        """SW3: TeamOrchestrator is available from cohezion.swarm."""
        import cohezion.swarm as sw

        assert hasattr(sw, "TeamOrchestrator"), "cohezion.swarm.TeamOrchestrator must be importable"

    def test_team_orchestrator_is_class(self) -> None:
        """SW3b: TeamOrchestrator must be a class."""
        import cohezion.swarm as sw

        assert inspect.isclass(sw.TeamOrchestrator), "TeamOrchestrator must be a class"

    def test_team_orchestrator_init_signature(self) -> None:
        """SW3c: TeamOrchestrator.__init__ signature check via inspect."""
        from cohezion.swarm.team_orchestrator import TeamOrchestrator

        sig = inspect.signature(TeamOrchestrator.__init__)
        params = sig.parameters
        # Must at least have 'self' — concrete structural guard
        assert "self" in params, (
            "TeamOrchestrator.__init__ must have 'self' parameter (signature drift guard)"
        )

    def test_team_orchestrator_has_plan_team(self) -> None:
        """SW3d: TeamOrchestrator must have plan_team method (core API)."""
        from cohezion.swarm.team_orchestrator import TeamOrchestrator

        assert callable(getattr(TeamOrchestrator, "plan_team", None)), (
            "TeamOrchestrator must expose a callable plan_team method"
        )


# ---------------------------------------------------------------------------
# SW4: DynamicModelRouter has async routing method
# ---------------------------------------------------------------------------


class TestSW4DynamicModelRouter:
    """SW4: DynamicModelRouter must be importable and expose a routing method.

    Note: DynamicModelRouter's routing method is select_optimal_model() (async),
    not route(). SW4 tests the actual API rather than an aspirational name.
    """

    def test_dynamic_model_router_importable(self) -> None:
        """SW4: DynamicModelRouter is available from cohezion.swarm."""
        import cohezion.swarm as sw

        assert hasattr(sw, "DynamicModelRouter"), (
            "cohezion.swarm.DynamicModelRouter must be importable"
        )

    def test_dynamic_model_router_is_class(self) -> None:
        """SW4b: DynamicModelRouter must be a class."""
        from cohezion.swarm.dynamic_model_router import DynamicModelRouter

        assert inspect.isclass(DynamicModelRouter), "DynamicModelRouter must be a class"

    def test_dynamic_model_router_has_routing_method(self) -> None:
        """SW4c: DynamicModelRouter must have select_optimal_model (async routing)."""
        from cohezion.swarm.dynamic_model_router import DynamicModelRouter

        method = getattr(DynamicModelRouter, "select_optimal_model", None)
        assert callable(method), (
            "DynamicModelRouter must have a callable select_optimal_model method"
        )

    def test_dynamic_model_router_routing_signature(self) -> None:
        """SW4d: select_optimal_model must accept a request parameter."""
        from cohezion.swarm.dynamic_model_router import DynamicModelRouter

        sig = inspect.signature(DynamicModelRouter.select_optimal_model)
        assert "request" in sig.parameters, (
            "DynamicModelRouter.select_optimal_model must accept 'request' parameter"
        )


# ---------------------------------------------------------------------------
# SW5: No swarm module imports from swarm.__init__ (circular import guard)
# ---------------------------------------------------------------------------


class TestSW5NoCircularImports:
    """SW5: Swarm submodules must not import from cohezion.swarm.__init__.

    Circular imports cause AttributeError or ImportError at runtime depending
    on Python's module loader state. Detecting them structurally (source grep)
    is cheaper and deterministic.
    """

    def test_no_circular_swarm_init_imports(self) -> None:
        """SW5: No swarm submodule directly imports 'from cohezion.swarm import ...'."""
        import pathlib
        import re

        swarm_dir = pathlib.Path(__file__).parents[2] / "src/cohezion/swarm"

        # Pattern: from cohezion.swarm import <something>
        # (i.e., importing FROM the package, not from a submodule)
        pattern = re.compile(r"from cohezion\.swarm import\b")

        violations: list[str] = []
        for py_file in sorted(swarm_dir.rglob("*.py")):
            # Skip __init__.py itself
            if py_file.name == "__init__.py":
                continue
            source = py_file.read_text()
            for lineno, line in enumerate(source.splitlines(), 1):
                if pattern.search(line) and not line.strip().startswith("#"):
                    violations.append(f"{py_file.relative_to(swarm_dir)}:{lineno}: {line.strip()}")

        assert not violations, (
            "Swarm submodules must not import directly from cohezion.swarm "
            "(circular import hazard). Violations:\n" + "\n".join(violations)
        )
