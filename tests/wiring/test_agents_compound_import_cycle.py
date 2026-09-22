"""Two import cycles into ``cohezion.compound`` stay cut.

Cycle 1 (``cohezion.agents`` first): `cohezion.swarm.topological_router` used to import `cohezion.compound.topological_persistence`
at module level. Because `cohezion.agents.base` reaches `cohezion.swarm` (via
`cohezion.universe.factory`), importing `cohezion.agents` FIRST executed the whole
`cohezion.compound` package while `agents.base` was half-loaded. The guarded re-exports in
`cohezion.compound.tdd_adversarial` and `cohezion.compound` swallowed the ImportError, so four
public names silently vanished -- only in that import order. Found by
scripts/ci/hidden_import_cycle_scan.py (2026-09-22).

Cycle 2 (e.g. ``cohezion.simulations`` / ``cohezion.api`` first): ``compound.eco_symphony`` and
``compound.resilience_loop`` imported ``EcoResilienceAgent`` at runtime for annotations only, so
agents.specialists.ecoresilience_agent -> compound (package init) -> eco_symphony ->
[resilience_loop ->] ecoresilience_agent (half-loaded) dropped CompoundEcoSymphony /
EcoResilienceCompoundEngine.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest


SRC = Path(__file__).resolve().parents[2] / "src"
ROUTER = SRC / "cohezion" / "swarm" / "topological_router.py"
COMPOUND = SRC / "cohezion" / "compound"

_NAMES = (
    "from cohezion.compound.tdd_adversarial import AdversarialCritique, AdversarialRedTeamAgent\n"
    "from cohezion.compound import CompoundEcoSymphony, EcoResilienceCompoundEngine\n"
)


def _run(first_import: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(SRC), "COHEZION_JOURNEY_PERSIST": "0"}
    return subprocess.run(
        [sys.executable, "-c", f"{first_import}\n{_NAMES}print('NAMES_OK')"],
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
        check=False,
    )


@pytest.mark.parametrize(
    "first_import",
    [
        "import cohezion.agents",
        "import cohezion.agents.specialists.ecoresilience_agent",
        "import cohezion.simulations",
        "import cohezion.api",
        "import cohezion.compound",
    ],
)
def test_names_survive_import_order(first_import: str) -> None:
    """DISCRIMINATING: restoring any cut import makes one of the non-compound-first orders fail."""
    proc = _run(first_import)
    assert "NAMES_OK" in proc.stdout, f"{first_import!r} first -> {proc.stderr[-600:]}"


def _module_level_imports(path: Path, prefix: str) -> list[str]:
    tree = ast.parse(path.read_text())
    return [
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(prefix)
    ]


@pytest.mark.parametrize(
    ("path", "prefix"),
    [
        (ROUTER, "cohezion.compound"),
        (COMPOUND / "eco_symphony.py", "cohezion.agents"),
        (COMPOUND / "resilience_loop.py", "cohezion.agents"),
    ],
    ids=["topological_router", "eco_symphony", "resilience_loop"],
)
def test_cut_edges_stay_off_module_scope(path: Path, prefix: str) -> None:
    """Structural companion: the cut edges must not come back at module scope."""
    offenders = _module_level_imports(path, prefix)
    assert offenders == [], f"module-level {prefix} import in {path.name}: {offenders}"


def test_analyze_agent_still_reaches_persistence_summary() -> None:
    """Consumer check: the lazy import resolves and feeds the real persistence summary."""
    from cohezion.swarm.topological_router import TopologicalRouter

    router = TopologicalRouter(min_trajectory_length=5)
    rng = np.random.default_rng(0)
    for point in rng.normal(size=(12, 12)):
        router.record_trajectory_point("a", point)
    topo = router.analyze_agent("a")
    assert topo.trajectory_length == 12
    assert topo.total_persistence > 0.0, "persistence summary was not computed"
