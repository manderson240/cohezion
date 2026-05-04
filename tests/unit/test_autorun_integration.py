"""Integration tests for autocontext wiring in autorun_2h.py.

Mocks all heavy EVO dependencies so the loop can run 2 cycles quickly.
Verifies:
  - ctx_monitor() is called at the start of each cycle
  - ctx_compress() is called when the context warning level fires (pct >= 0.80)
  - budget() gates continuation: safe_to_continue=False stops the loop early

Strategy: import autorun_2h as a regular module (scripts/ is on sys.path via path
setup in conftest or the module itself), then patch cohezion.research.autocontext
symbols at source so the `from … import monitor as ctx_monitor` in main() binds
the mocks. Heavy evo deps (journey_worker, telemetry_bus, overnight_evo_loop) are
all stubbed via sys.modules + patch.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────


def _safe_ctx(pct: float = 0.10) -> dict:
    return {
        "pct": pct,
        "status": "OK",
        "safe": True,
        "warn": False,
        "critical": False,
        "monitor_ms": 1.0,
    }


def _warn_ctx(pct: float = 0.85) -> dict:
    return {
        "pct": pct,
        "status": "WARNING",
        "safe": False,
        "warn": True,
        "critical": False,
        "monitor_ms": 1.0,
    }


def _budget(safe: bool = True) -> dict:
    return {
        "remaining_experiments": 200 if safe else 0,
        "safe_to_continue": safe,
        "pct": 0.10,
        "elapsed_ms": 0.1,
    }


def _make_evo_stub() -> types.ModuleType:
    """Minimal fake overnight_evo_loop with instant async experiment stubs."""
    evo = types.ModuleType("overnight_evo_loop")
    evo.LEMONADE_BASE = "http://localhost:13306"

    async def _noop(**kwargs) -> dict:  # type: ignore[return]
        return {"delta": 0.1, "coherence_delta": 0.1, "gain": 0.1}

    evo.experiment_e63_mycelium_closed_loop = _noop
    evo.experiment_e50_db_informed_proposals = _noop
    evo.experiment_e51_evo_quality_sensitivity = _noop
    return evo


@contextmanager
def _autorun_module(tmp_log: Path):
    """Context manager: yields a freshly loaded autorun_2h module with heavy deps stubbed.

    The module is loaded once per context; SESSION_LOG is overridden to tmp_log.
    autocontext symbols are NOT patched here — tests do that themselves.
    """
    _REPO = Path(__file__).parent.parent.parent
    scripts_path = str(_REPO / "scripts")

    evo = _make_evo_stub()

    mock_bus = AsyncMock()
    mock_worker = AsyncMock()
    mock_worker._db = MagicMock()
    mock_worker._db.connected = False

    # Pre-register evo stub so autorun_2h's importlib.util call finds it
    sys.modules.setdefault("overnight_evo_loop", evo)

    # Stub the persistence modules so heavy SurrealDB deps aren't needed
    _tb_mod = types.ModuleType("cohezion.core.telemetry_bus")
    _tb_mod.get_telemetry_bus = lambda: mock_bus  # type: ignore[attr-defined]
    _jw_mod = types.ModuleType("cohezion.core.journey_worker")
    _jw_mod.get_journey_worker = lambda: mock_worker  # type: ignore[attr-defined]
    # Also stub httpx so LLM probe doesn't fail oddly
    _httpx_mod = types.ModuleType("httpx")
    _httpx_mod.AsyncClient = MagicMock()  # type: ignore[attr-defined]

    stub_modules = {
        "cohezion.core.telemetry_bus": _tb_mod,
        "cohezion.core.journey_worker": _jw_mod,
    }

    # Intercept spec_from_file_location so overnight_evo_loop load is a no-op
    import importlib.util as _util

    _orig_spec = _util.spec_from_file_location

    def _patched_spec(name, location=None, *a, **kw):  # type: ignore[return]
        if name == "overnight_evo_loop":
            stub_spec = MagicMock()
            stub_spec.loader = MagicMock()
            stub_spec.loader.exec_module = lambda m: None
            return stub_spec
        return _orig_spec(name, location, *a, **kw)

    def _patched_module_from_spec(spec):
        if getattr(spec, "_is_evo_stub", False) or (
            hasattr(spec, "name") and spec.name == "overnight_evo_loop"
        ):
            return evo
        try:
            return _util.module_from_spec.__wrapped__(spec)  # type: ignore[attr-defined]
        except AttributeError:
            pass
        # Fallback to real implementation via the original approach
        return types.ModuleType(getattr(spec, "name", "unknown"))

    # Load the module fresh (purge any cached version)
    cached_key = next((k for k in sys.modules if "autorun_2h" in k and "_test_" not in k), None)
    if cached_key:
        del sys.modules[cached_key]

    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)

    with (
        patch.dict(sys.modules, stub_modules),
        patch("importlib.util.spec_from_file_location", side_effect=_patched_spec),
    ):
        mod = importlib.import_module("autorun_2h")
        mod.SESSION_LOG = tmp_log  # type: ignore[attr-defined]

    yield mod


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_monitor_called_each_cycle(tmp_path: Path) -> None:
    """ctx_monitor() must be called once per cycle; stop after 2 cycles via budget."""
    call_count: list[int] = []

    def _monitor():
        call_count.append(1)
        return _safe_ctx()

    compress_mock = MagicMock(return_value={"kept": 0, "compressed": 0, "summaries_emitted": 0})
    budget_seq = [_budget(True), _budget(False)]  # safe, then exhausted

    with _autorun_module(tmp_path / "sess.jsonl") as mod:
        with (
            patch("cohezion.research.autocontext.monitor", side_effect=_monitor),
            patch("cohezion.research.autocontext.compress", compress_mock),
            patch("cohezion.research.autocontext.budget", side_effect=iter(budget_seq)),
        ):
            asyncio.run(mod.main(hours=0.001, use_llm=False))  # type: ignore[attr-defined]

    assert len(call_count) >= 2, (
        f"Expected ctx_monitor >=2 calls (one per cycle), got {len(call_count)}"
    )
    compress_mock.assert_not_called()


@pytest.mark.unit
def test_compress_called_on_warn(tmp_path: Path) -> None:
    """ctx_compress(SESSION_LOG, keep_recent=200) must be called when warn=True."""
    monitor_seq = [_warn_ctx(0.85), _safe_ctx()]
    compress_mock = MagicMock(return_value={"kept": 200, "compressed": 50, "summaries_emitted": 5})
    budget_seq = [_budget(True), _budget(False)]

    with _autorun_module(tmp_path / "sess.jsonl") as mod:
        with (
            patch("cohezion.research.autocontext.monitor", side_effect=iter(monitor_seq)),
            patch("cohezion.research.autocontext.compress", compress_mock),
            patch("cohezion.research.autocontext.budget", side_effect=iter(budget_seq)),
        ):
            asyncio.run(mod.main(hours=0.001, use_llm=False))  # type: ignore[attr-defined]

    compress_mock.assert_called_once()
    args, kwargs = compress_mock.call_args
    keep_recent = kwargs.get("keep_recent", args[1] if len(args) > 1 else None)
    assert keep_recent == 200, f"Expected keep_recent=200, got {keep_recent}"


@pytest.mark.unit
def test_budget_exhaustion_stops_after_one_cycle(tmp_path: Path) -> None:
    """Loop breaks immediately when budget.safe_to_continue=False after cycle 0."""
    call_count: list[int] = []

    def _monitor():
        call_count.append(1)
        return _safe_ctx()

    compress_mock = MagicMock()
    budget_seq = [_budget(False)]  # exhausted from the very first check

    with _autorun_module(tmp_path / "sess.jsonl") as mod:
        with (
            patch("cohezion.research.autocontext.monitor", side_effect=_monitor),
            patch("cohezion.research.autocontext.compress", compress_mock),
            patch("cohezion.research.autocontext.budget", side_effect=iter(budget_seq)),
        ):
            asyncio.run(mod.main(hours=0.001, use_llm=False))  # type: ignore[attr-defined]

    assert len(call_count) == 1, (
        f"Expected exactly 1 cycle (budget halt), got {len(call_count)} monitor calls"
    )
