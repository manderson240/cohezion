"""Fixtures for compound integration tests.

Compound test fixtures.

Ensures the project ``.context/`` tree has the placeholder source files that
``cohezion.compound.context_integration.ContextManager`` expects when loading
the traceability manifest. The manifest references files (e.g.
``compound/long_horizon_task.py``, ``universe/spatial_phonons.py``) that are
shadow-copies of source modules and aren't always materialised in every
worktree (sparse checkouts, fresh clones). When they're missing, the
CompoundExecutor's ``__init_context__`` chain raises ``ContextLoadError`` and
every test that instantiates an executor errors out.

This fixture is autouse + session-scoped so that the placeholders exist for
the entire compound test run without per-test overhead. It does NOT modify
real source files — it only ensures byte-identical placeholders for the
context loader.
"""

from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from cohezion.core.mcp_client import MCPClient


class _MockVirtualMemory:
    """Fake psutil result — reports 50% memory so resource guardrails don't fire.

    Includes all attributes used by silicon_guard.py, resource_monitor, and executor:
      - percent: used by executor guardrail (threshold ~85-90%)
      - total: 128 GiB (Strix Halo spec)
      - available: 64 GiB free
    """

    percent = 50.0
    total = 128 * 1024**3  # 128 GiB
    available = 64 * 1024**3  # 64 GiB free
    used = 64 * 1024**3


@pytest.fixture(autouse=True)
def _mock_psutil_resources():
    """Auto-patch psutil virtual_memory and cpu_percent for all compound tests.

    The resource guardrail in CompoundExecutor blocks execution when system
    memory exceeds ~85% or CPU exceeds ~80%. On a busy machine (running background
    agents, EVO loop, etc.) real resources can exceed these thresholds, causing
    every test that calls execute_task to fail.
    Mocking at conftest level fixes this suite-wide without touching each test.
    """
    with (
        patch("psutil.virtual_memory", return_value=_MockVirtualMemory()),
        patch("psutil.cpu_percent", return_value=25.0),
    ):
        yield


# Discard port — nothing listens, so httpx fails with an immediate ECONNREFUSED
# rather than a multi-second connect timeout.
_DEAD_SURREAL_URL = "http://127.0.0.1:9/sql"

# Modules that read a module-level ``_SURREAL_URL`` at CALL time (verified: every
# reference below is inside a function body, so patching the module attribute takes
# effect). ``cohezion.compound.vmodel_harness`` also binds it as a default argument at
# def time — that binding is NOT covered here and remains a live-network seam.
_SURREAL_URL_MODULES = (
    "cohezion.compound.prompt_version_registry",
    "cohezion.compound.qa_gate",
    "cohezion.compound.compound_persist",
    "cohezion.compound.token_ledger",
    "cohezion.compound.vmodel_harness",
)

# Lemonade (:13305) endpoints reached WITHOUT a ``lemonade_available`` gate, so the
# fuse above does not stop them. ``_fast_local_chat`` in particular posts to
# ``_FAST_CHAT_URL`` with ``timeout=180`` — the only client-side bound in this suite
# long enough to explain the multi-minute stalls, and it fires from ``refine()``'s
# fixture bootstrap.
#
# This is a targeted redirect of the constants the compound suite actually exercises,
# NOT a general egress block: other modules (``consortium_instigator``,
# ``rubric_middleware``, ``gaia_loop``, ``coherence_v3``) hold their own :13305 URLs,
# and ``skill_refiner`` builds one inline at call time, so they are not covered here.
_LEMONADE_URL_ATTRS = (
    ("cohezion.compound.prompt_version_registry", "_FAST_CHAT_URL"),
    ("cohezion.compound.prompt_version_registry", "_EMBED_URL"),
)
_DEAD_LEMONADE_URL = "http://127.0.0.1:9/v1/chat/completions"


@pytest.fixture(autouse=True)
def _offline_fuse(request):
    """Force the compound suite offline so results do not depend on service state.

    Three seams made this suite non-hermetic (audit:
    ``~/vaults/cohezion-vault/reports/20260727-compound-test-hermeticity.md``):

    1. ``lemonade_available`` — probed live on :13305 by ``make_executor`` and
       ``build_live_jepa_gate``. When Lemonade is UP, JG3 wires a real LLM-backed
       JepaGate whose verdict can flip mid-suite, so identical code produced
       different results depending on which models happened to be resident.
    2. ``LemonadeEmbedBridge.is_available`` — ``JourneyTracker.__init__`` probes it on
       EVERY instantiation.
    3. ``_SURREAL_URL`` — ``refine()``'s fixture bootstrap WROTE rows into the
       production ``golden_fixture`` table, and the bootstrap short-circuits when rows
       exist. That made run N take a different branch than run N-1 of identical code.
    4. ``frontier_complete_sync`` — ``refine()`` -> ``_adversarial_review_gate`` runs a
       CLOUD cascade (Fable -> Opus -> ``agy``) via ``subprocess.run``, each leg bounded
       at 90s. Measured: ONE test spent 243s here. This is the true source of the
       multi-minute stalls (not the Lemonade HTTP path), and no HTTP-level mock can see
       it because it shells out to CLI binaries. Fusing it to raise makes tests take the
       pre-existing "frontier unavailable -> local fallback" branch; production routing
       is unchanged.

    Patching ``lemonade_available`` at its DEFINITION module is correct here (not at
    each importer) precisely because all three production call sites use function-local
    imports, so none of them holds a stale reference — the name is resolved from the
    patched module at call time.

    Tests marked ``integration`` are EXEMPT: without a tier that actually runs against
    live services, this fuse would silently convert JG3-class wiring regressions into
    invisible ones — a coverage regression disguised as a fix.
    """
    if request.node.get_closest_marker("integration"):
        yield
        return

    from cohezion.inference.lemonade_embed_bridge import LemonadeEmbedBridge

    with ExitStack() as stack:
        stack.enter_context(
            patch("cohezion.compound.local_inference.lemonade_available", return_value=False)
        )
        stack.enter_context(patch.object(LemonadeEmbedBridge, "is_available", return_value=False))
        for module in _SURREAL_URL_MODULES:
            # No create=True: if the attribute is renamed the fuse must fail LOUDLY
            # rather than silently resume writing to the production database.
            stack.enter_context(patch(f"{module}._SURREAL_URL", _DEAD_SURREAL_URL))
        for module, attr in _LEMONADE_URL_ATTRS:
            stack.enter_context(patch(f"{module}.{attr}", _DEAD_LEMONADE_URL))
        stack.enter_context(
            patch(
                "cohezion.inference.frontier_oracle.frontier_complete_sync",
                side_effect=RuntimeError("frontier oracle fused off in tests"),
            )
        )
        yield


@pytest_asyncio.fixture
async def mcp_client():
    """Create mock MCP client for testing."""
    return MagicMock(spec=MCPClient)


import pytest


def _find_project_root(start: Path) -> Path | None:
    """Walk upward looking for a ``.context`` directory."""
    current = start.resolve()
    while current != current.parent:
        if (current / ".context").exists():
            return current
        current = current.parent
    return None


@pytest.fixture(autouse=True, scope="session")
def _ensure_context_placeholders() -> None:
    """Materialise placeholder files referenced by .context/traceability/manifest.json.

    Reads the manifest, resolves each ``core_files[*].path``, and writes a
    minimal placeholder if the target is missing. This is idempotent and
    cheap: existing files are untouched. (Σ4 Ω12 Patch 7)
    cheap: existing files are untouched.
    """
    project_root = _find_project_root(Path(__file__).parent)
    if project_root is None:
        return

    manifest_path = project_root / ".context" / "traceability" / "manifest.json"
    if not manifest_path.exists():
        return

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    context_dir = project_root / ".context"
    for entry in manifest.get("core_files", []):
        rel = entry.get("path")
        if not rel:
            continue
        target = context_dir / rel
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "# Placeholder for compound context loader (created by tests/compound/conftest.py).\n"
            "# Real content lives in the corresponding src/ module; this file exists so\n"
            "# ContextManager._load_file() does not raise ContextLoadError during tests.\n",
            encoding="utf-8",
        )
