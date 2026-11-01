# ruff: noqa: F811
"""N6 (token-window boundary) and the surviving mutations M8a2/M8b/M8c (unavailable latent in the
platform callers) and M10b/M14b/M14c (encode off the event loop). Each test names the mutation it
kills. Plain tests (not requires_real_st): the window test drives the REAL `_load_minilm` closure
over a real Rust tokenizer via test_canonical_latent_concurrency."""

from __future__ import annotations

import asyncio
import pathlib
import threading
import types
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import numpy as np

from cohezion.flume.canonical_latent import CanonicalTextLatent
from tests.flume.test_canonical_latent_concurrency import WINDOW, real_loader  # noqa: F401


def _words(n: int) -> str:
    return " ".join(f"w{i % 50}" for i in range(n))


def _dead() -> CanonicalTextLatent:
    def loader():
        raise OSError("weights missing")

    return CanonicalTextLatent(loader)


# ---- N6 ---------------------------------------------------------------------------------------


def test_window_boundary_is_exactly_limit_inclusive(real_loader):
    """N6: `count > limit`. Fails for `>= limit` (WINDOW tokens would be refused) and for
    `> limit + 2` (WINDOW+1 and WINDOW+2 tokens would be accepted)."""
    enc = CanonicalTextLatent(real_loader)
    enc.encode("w1")  # load
    assert enc.max_tokens == WINDOW
    for n, over in [(WINDOW - 1, False), (WINDOW, False), (WINDOW + 1, True), (WINDOW + 2, True)]:
        assert enc.exceeds_token_limit(_words(n)) is over, n
        got = enc.encode_or_none(_words(n), strict_window=True)
        assert (got is None) is over, n


# ---- M8a2 / M8b / M8c: callers survive an unavailable latent ---------------------------------


def test_journey_logger_complete_survives_unavailable_latent():
    """M8a2: encode instead of encode_or_none at context_end raises TextLatentUnavailable."""
    from cohezion.platform.journey_logger import JourneyLogger

    jl = object.__new__(JourneyLogger)
    row = {
        "journey_id": "j",
        "journey_type": "t",
        "started_at": datetime.now().isoformat(),
        "coherence_at_start": 0.5,
    }
    jl.db = MagicMock()
    jl.db.query = AsyncMock(side_effect=[None, [row]])
    jl.vae = _dead()
    jl.coherence_tracker = MagicMock()
    jl.coherence_tracker.measure_system_coherence = AsyncMock(
        return_value=types.SimpleNamespace(coherence=0.5, hiho_stable=True)
    )
    journey = asyncio.run(jl.complete_journey("j", "done", "ctx end"))
    assert journey.journey_id == "j"
    assert jl.db.query.await_args_list[0].args[1]["flume_state_end"] == []


def test_observable_action_proposal_survives_unavailable_latent():
    """M8b: encode instead of encode_or_none in propose_action raises TextLatentUnavailable."""
    from cohezion.platform.observable_action import ObservableActionProposer

    p = object.__new__(ObservableActionProposer)
    p.vae = _dead()
    p.coherence_tracker = MagicMock()
    p.coherence_tracker.measure_system_coherence = AsyncMock(
        return_value=types.SimpleNamespace(coherence=0.5)
    )
    p.journey_logger = MagicMock()
    p._current_journey_id = None
    p._estimate_coherence_impact = AsyncMock(return_value=0.0)
    p._display_proposal = AsyncMock()
    seen = []
    ok = asyncio.run(
        p.propose_action(
            "update", "d", "r", 0.5, AsyncMock(), approval_callback=lambda pr: seen.append(pr) or True
        )
    )
    assert ok is True
    assert seen and seen[0].flume_state == []


def test_skill_tracker_event_survives_unavailable_latent():
    """M8c: encode instead of encode_or_none in create_skill_usage_event raises."""
    from cohezion.platform.skill_tracker_charter import CharterAlignedSkillTracker

    t = object.__new__(CharterAlignedSkillTracker)
    t.vae = _dead()
    ev = asyncio.run(t.create_skill_usage_event("s", 1, True, 1.0, 0.5, 0.5, "prompt"))
    assert ev.flume_state == []


# ---- M10b / M14b / M14c: encodes run off the event loop --------------------------------------


def test_call_ollama_final_encode_runs_off_the_event_loop(tmp_path, monkeypatch):
    """M10b: dropping asyncio.to_thread around _semantic_vector in the final post-processing step
    of _call_ollama puts the encode on the loop thread."""
    import cohezion.core.routing.router as router
    from cohezion.agents import base as base_mod
    from cohezion.swarm.swarm_types import SwarmConfig

    class _A(base_mod.BaseAgent):
        async def process(self, *a, **k):
            return None

    monkeypatch.chdir(tmp_path)
    tk = MagicMock()
    tk.log_event = AsyncMock()
    monkeypatch.setattr(base_mod, "get_time_keeper", lambda: tk)
    acc = MagicMock()
    acc.add_experience = AsyncMock()
    monkeypatch.setattr(base_mod, "get_accumulator", lambda: acc)
    import cohezion.learning.recorder as recorder

    monkeypatch.setattr(recorder, "get_learning_recorder", lambda: MagicMock())
    monkeypatch.setattr(router.LOCAL_ROUTER, "route_task", AsyncMock(return_value="an answer"))

    async def run():
        agent = _A("m", config=SwarmConfig(mrp_sync=False), cache_dir=pathlib.Path(tmp_path))
        seen: list[bool] = []

        def spy(text):
            seen.append(threading.current_thread() is threading.main_thread())
            return np.ones(4, dtype=np.float32)

        agent._semantic_vector = spy
        agent._get_cached = AsyncMock(return_value=None)
        agent._set_cached = AsyncMock()
        agent.self_evaluate = AsyncMock(return_value=(1.0, 1.0, {}))
        out = await agent._call_ollama("hello there")
        await asyncio.sleep(0)
        return out, seen

    out, seen = asyncio.run(run())
    assert str(out) == "an answer"
    assert seen == [False], seen  # exactly the final encode (get/set are mocked) and off-loop


def test_translator_encode_runs_off_the_event_loop():
    """M14b: calling encoder.encode directly in encode_to_manifold blocks the loop."""
    from cohezion.flume.manifolds.translator import ManifoldTranslator

    seen: list[bool] = []

    class Enc:
        def encode(self, text):
            seen.append(threading.current_thread() is threading.main_thread())
            return np.ones(256, dtype=np.float32)

    tr = ManifoldTranslator(encoder=Enc())
    # encode_to_manifold double-projects (project(project(latent))), and project() rejects a
    # ManifoldProjection; that separate pre-existing defect is neutralised here so the test only
    # observes the thread the encode ran on.
    tr.project = lambda x: x  # type: ignore[method-assign]
    asyncio.run(tr.encode_to_manifold("x"))
    assert seen == [False]


def test_daemon_topology_capture_runs_off_the_event_loop(monkeypatch, tmp_path):
    """M14c: calling viz.process_evo directly in run_single_experiment blocks the loop."""
    from cohezion.researcher import continuous_experiment_daemon as d

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(d.PreflightFleetCheck, "run", staticmethod(lambda: (True, [])))
    monkeypatch.setattr(d, "route", AsyncMock(return_value=types.SimpleNamespace(model="m")))
    seen: list[bool] = []

    def spy(self, evo, actions):
        seen.append(threading.current_thread() is threading.main_thread())
        return {"nodes": []}

    monkeypatch.setattr(d.EVOJourneyVisualizer, "process_evo", spy)

    class _Null:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    lock = MagicMock()
    lock.acquire = lambda *a, **k: _Null()
    daemon = d.ContinuousExperimentDaemon(fleet_lock=lock)
    daemon.bus = types.SimpleNamespace(publish=AsyncMock())
    daemon._persist_surreal = lambda r: True
    daemon._persist_kanban = lambda r: {}
    asyncio.run(daemon.run_single_experiment())
    assert seen == [False]
