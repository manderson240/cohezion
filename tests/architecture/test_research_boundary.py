"""Research boundary: core platform packages may not grow new imports of research code.

``cohezion.physics`` and ``cohezion.worldviews`` hold physics-inspired and exploratory
research. Some of it is still called from core packages, mostly from non-blocking
telemetry and healing steps in the compound executor. That list is frozen here so it
can only shrink:

* a NEW edge from a core package into research code fails ``test_no_new_edges``;
* an edge that has been removed but is still listed fails ``test_allowlist_is_not_stale``,
  so the allowlist is trimmed in the same change that removes the import.
"""

from __future__ import annotations

import ast
from pathlib import Path


SRC = Path(__file__).resolve().parents[2] / "src"

CORE_PACKAGES = ("compound", "inference", "security", "mcp", "core", "reliability", "cache")
RESEARCH_PREFIXES = ("cohezion.physics", "cohezion.worldviews")

# Frozen 2026-11-04. Remove entries as the imports are removed; never add one.
ALLOWED_EDGES: frozenset[tuple[str, str]] = frozenset(
    {
        ("cohezion/cache/semantic_cache_system.py", "cohezion.physics.poincare_manifold"),
        ("cohezion/compound/degradation_detector.py", "cohezion.physics.ouroboros_bridge"),
        ("cohezion/compound/executor.py", "cohezion.physics.bioelectric_model"),
        ("cohezion/compound/executor.py", "cohezion.physics.natural_capital"),
        ("cohezion/compound/executor.py", "cohezion.physics.ouroboros_bridge"),
        (
            "cohezion/compound/grand_unified_compound_pipeline.py",
            "cohezion.physics.poincare_manifold",
        ),
        ("cohezion/compound/greek_parameters.py", "cohezion.physics.hiho_kernel"),
        ("cohezion/compound/journey_tracker.py", "cohezion.physics.bioelectric_model"),
        ("cohezion/compound/journey_tracker.py", "cohezion.physics.observer_patch"),
        ("cohezion/compound/journey_tracker.py", "cohezion.physics.spinor"),
        ("cohezion/compound/post_execution.py", "cohezion.physics.bioelectric_model"),
        ("cohezion/compound/post_execution.py", "cohezion.physics.natural_capital"),
        ("cohezion/compound/post_execution.py", "cohezion.physics.ouroboros_bridge"),
        ("cohezion/compound/self_evolving_refiner.py", "cohezion.physics.mereon_projector"),
        ("cohezion/core/grand_unified_wiring_bus.py", "cohezion.physics.hiho_sonification"),
        ("cohezion/core/journey_worker.py", "cohezion.physics.ouroboros_bridge"),
        ("cohezion/core/master_orchestrator.py", "cohezion.physics.poincare_manifold"),
        ("cohezion/core/master_orchestrator.py", "cohezion.physics.smoke_ring_manifold"),
        ("cohezion/inference/fleet.py", "cohezion.physics.spinor"),
        ("cohezion/mcp/cohezion_agi_server.py", "cohezion.physics.hiho_sonification"),
        ("cohezion/mcp/cohezion_agi_server.py", "cohezion.physics.poincare_manifold"),
        ("cohezion/mcp/marimo_walkthroughs_mcp.py", "cohezion.physics.thermodynamic_gravity"),
        ("cohezion/mcp/servers/plasma/server.py", "cohezion.physics.manifold_utils"),
    }
)


def research_edges(src: Path = SRC) -> set[tuple[str, str]]:
    """Every (core file, research module) import edge, including lazy in-function imports."""
    edges: set[tuple[str, str]] = set()
    for pkg in CORE_PACKAGES:
        for path in sorted((src / "cohezion" / pkg).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                elif isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                else:
                    continue
                for module in modules:
                    if module.startswith(RESEARCH_PREFIXES):
                        edges.add((path.relative_to(src).as_posix(), module))
    return edges


def test_no_new_edges() -> None:
    new = research_edges() - ALLOWED_EDGES
    assert not new, (
        "Core platform code gained an import of research code. Keep research out of "
        f"the platform path, or move the code out of research first: {sorted(new)}"
    )


def test_allowlist_is_not_stale() -> None:
    stale = ALLOWED_EDGES - research_edges()
    assert not stale, f"These imports are gone; delete them from ALLOWED_EDGES: {sorted(stale)}"


def test_scanner_sees_lazy_imports(tmp_path: Path) -> None:
    """Discriminating: a lazy import inside a function must count as an edge."""
    pkg = tmp_path / "cohezion" / "compound"
    pkg.mkdir(parents=True)
    (pkg / "x.py").write_text(
        "def f():\n    from cohezion.physics.lenr import LENRHamiltonian\n", encoding="utf-8"
    )
    (pkg / "y.py").write_text("from cohezion.inference import router\n", encoding="utf-8")
    assert research_edges(tmp_path) == {("cohezion/compound/x.py", "cohezion.physics.lenr")}
