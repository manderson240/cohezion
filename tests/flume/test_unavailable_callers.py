"""Former never-raise callers of the text latent now make a deliberate, visible choice when the
canonical latent is unavailable (see flume/canonical_latent.py). Each test fails if the caller
goes back to swallowing the error or fabricating a value."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from cohezion.flume.canonical_latent import CanonicalTextLatent, TextLatentUnavailable


class _AsyncNull:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _dead() -> CanonicalTextLatent:
    def loader():
        raise OSError("weights missing")

    return CanonicalTextLatent(loader)


def test_curator_refuses_before_writing_anything(tmp_path):
    from cohezion.integrations.kaggle_curation import KaggleCurator

    src = tmp_path / "in.jsonl"
    src.write_text(json.dumps({"question": "q", "answer": "a"}) + "\n")
    out = tmp_path / "out.jsonl"
    curator = KaggleCurator()
    curator.encoder = _dead()
    with pytest.raises(TextLatentUnavailable):
        asyncio.run(curator.process_dataset(src, out))
    assert not out.exists()


def test_translator_propagates():
    from cohezion.flume.manifolds.translator import ManifoldTranslator

    with pytest.raises(TextLatentUnavailable):
        asyncio.run(ManifoldTranslator(encoder=_dead()).encode_to_manifold("x"))


def test_invest_bridge_propagates():
    from cohezion.compound.invest.bridge import InVESTBridge

    state = SimpleNamespace(
        model_name="m", biophysical_value=1.0, tradeoff_index=0.5, metrics={"a": 1}
    )
    with pytest.raises(TextLatentUnavailable):
        InVESTBridge(_dead()).quantify_to_latent(state)


def test_evo_visualizer_propagates(tmp_path):
    from cohezion.flume.evo_visualizer import EVOJourneyVisualizer
    from cohezion.physics.evo_model import ExoticVacuumObject

    viz = EVOJourneyVisualizer(output_path=str(tmp_path / "g.json"))
    viz.vae_encoder = _dead()
    evo = ExoticVacuumObject(agent_id="a", universe_id="u")
    evo.condense()
    with pytest.raises(TextLatentUnavailable):
        viz.process_evo(evo, ["step"])


def test_daemon_records_explicit_marker_not_empty_topologies(monkeypatch, tmp_path):
    from cohezion.researcher import continuous_experiment_daemon as d

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(d.PreflightFleetCheck, "run", staticmethod(lambda: (True, [])))
    monkeypatch.setattr(d, "route", AsyncMock(return_value=SimpleNamespace(model="m")))
    monkeypatch.setattr(
        d.EVOJourneyVisualizer,
        "process_evo",
        MagicMock(side_effect=TextLatentUnavailable("no weights")),
    )
    lock = MagicMock()
    lock.acquire = lambda *a, **k: _AsyncNull()
    daemon = d.ContinuousExperimentDaemon(fleet_lock=lock)
    daemon.bus = SimpleNamespace(publish=AsyncMock())
    daemon._persist_surreal = lambda r: True
    daemon._persist_kanban = lambda r: {}
    result = asyncio.run(daemon.run_single_experiment())
    assert result.topologies == ["latent_unavailable"]
    assert result.nodes_classified == 0
