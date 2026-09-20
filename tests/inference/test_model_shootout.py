"""V-Model verification for model_shootout (producer/consumer contract).

Left side (decomposition / design) pins the contracts the module must honor:

  1. CONSUMER contract — the shootout RIDES the daemon-maintained resident
     fleet instead of forcing its own cold loads:
       - an already-resident candidate is queried directly (no gate, no load)
       - a non-resident candidate goes through the orchestrator (gate + lock)
       - embeddings are excluded from the default candidate set
  2. PRODUCER contract — the shootout is a DataMesh producer:
       - emits a DATA_PRODUCT_UPDATED event per successfully scored candidate
       - persists `model` + `quality_score` to SurrealDB `model_performance`
         (the table the adaptive router already reads)

Right side (verification): every unit test exercises the module with all
external I/O mocked at source (@patch / monkeypatch), mirroring the
conventions in tests/inference/test_model_sprint_orchestrator.py.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from cohezion.inference import hotswap
from cohezion.inference.evaluation_harness import evaluate_quality_simple
from cohezion.inference.model_shootout import (
    ModelShootout,
    ShootoutResult,
    default_candidates,
    run_model_shootout,
    write_model_performance,
)
from cohezion.inference.model_sprint_orchestrator import SprintResult
from cohezion.inference.transports.lemonade import LemonadeTransport, TransportResponse

RESIDENT_MODELS = [
    {"model_name": "Gemma-4-26B-A4B-it-GGUF", "last_use": 1, "is_busy": False, "loaded": True},
    {"model_name": "Gemma-4-E4B-it-GGUF", "last_use": 2, "is_busy": False, "loaded": True},
    {"model_name": "nomic-embed-text-v2-moe-GGUF", "last_use": 3, "is_busy": False, "loaded": True},
]


@pytest.fixture(autouse=True)
def _no_network_write(monkeypatch):
    """Block real SurrealDB writes in every test by default."""
    monkeypatch.setattr(
        "cohezion.inference.model_shootout.write_model_performance", lambda **k: True
    )


def _make_transport(monkeypatch, content: str) -> None:
    """Make the transport return a canned response regardless of model."""

    async def _fake_query(self, prompt, model_id, params=None):
        return TransportResponse(
            content=content,
            model_name=model_id,
            latency_ms=123.4,
            verified=True,
        )

    monkeypatch.setattr(LemonadeTransport, "query", _fake_query)


class TestConsumerContract:
    """CONSUMER: ride the daemon fleet, don't force cold loads."""

    def test_default_candidates_are_resident_models_only(self, monkeypatch):
        """C1: embeddings excluded, non-embed resident models returned."""
        monkeypatch.setattr(hotswap, "resident_models", lambda: list(RESIDENT_MODELS))
        cands = default_candidates()
        assert "nomic-embed-text-v2-moe-GGUF" not in cands
        assert "Gemma-4-26B-A4B-it-GGUF" in cands
        assert "Gemma-4-E4B-it-GGUF" in cands

    def test_default_candidates_fallback_when_fleet_empty(self, monkeypatch):
        """C2: empty daemon fleet falls back to the curated list, not failure."""
        monkeypatch.setattr(hotswap, "resident_models", lambda: [])
        cands = default_candidates()
        assert len(cands) >= 2

    def test_already_resident_skips_orchestrator_load(self, monkeypatch):
        """C3: a resident candidate is queried directly — no load/gate path."""
        monkeypatch.setattr(hotswap, "resident_models", lambda: list(RESIDENT_MODELS))
        _make_transport(monkeypatch, "balance amt is an integer; no overdraft check; float money.")

        calls: list[str] = []

        class _FakeOrc:
            async def ensure_model(self, model, **kw):
                calls.append(model)
                return SprintResult("code", model, True, "loaded")

        shootout = ModelShootout(
            candidates=["Gemma-4-E4B-it-GGUF"],
            min_free_gb=20.0,
        )
        shootout._orchestrator = _FakeOrc()  # type: ignore[assignment]  # inject seam post-construction (repo convention)
        report = asyncio.run(shootout.run())

        assert calls == []  # orchestrator never invoked for a resident model
        assert report.results[0].loaded is True
        assert report.results[0].reason == "already resident (daemon-maintained fleet)"

    def test_non_resident_goes_through_orchestrator(self, monkeypatch):
        """C4: a cold candidate DOES go through the orchestrator (gate+lock)."""
        monkeypatch.setattr(hotswap, "resident_models", lambda: list(RESIDENT_MODELS))
        _make_transport(monkeypatch, "balance amt integer float overdraft.")

        calls: list[str] = []

        class _FakeOrc:
            async def ensure_model(self, model, **kw):
                calls.append(model)
                return SprintResult("code", model, True, "loaded")

        shootout = ModelShootout(
            candidates=["Qwen3-Coder-30B-A3B-Instruct-GGUF"],
        )
        shootout._orchestrator = _FakeOrc()  # type: ignore[assignment]
        report = asyncio.run(shootout.run())

        assert calls == ["Qwen3-Coder-30B-A3B-Instruct-GGUF"]
        assert report.results[0].loaded is True

    def test_load_refusal_is_recorded_not_fatal(self, monkeypatch):
        """C5: an orchestrator refusal yields a FAILED result, shootout continues."""
        monkeypatch.setattr(hotswap, "resident_models", lambda: [])
        _make_transport(monkeypatch, "balance amt.")

        class _FakeOrc:
            async def ensure_model(self, model, **kw):
                return SprintResult("code", model, False, "insufficient RAM")

        shootout = ModelShootout(
            candidates=["Qwen3-Coder-30B"],
        )
        shootout._orchestrator = _FakeOrc()  # type: ignore[assignment]
        report = asyncio.run(shootout.run())

        assert report.results[0].ok is False
        assert "insufficient RAM" in report.results[0].reason
        assert report.results[0].quality_score == 0.0


class TestProducerContract:
    """PRODUCER: DataMesh event + SurrealDB persistence."""

    def test_emits_data_product_updated(self, monkeypatch):
        """P1: a scored candidate publishes DATA_PRODUCT_UPDATED."""
        monkeypatch.setattr(hotswap, "resident_models", lambda: list(RESIDENT_MODELS))
        _make_transport(
            monkeypatch,
            "Critical: balance logic is non-atomic; amt should be validated as a positive "
            "integer, not float; and it can go overdraft without a check.",
        )

        events: list[Any] = []

        class _FakeBus:
            _running = True

            async def publish(self, event):
                events.append(event)

            def publish_sync(self, event):
                events.append(event)

        shootout = ModelShootout(
            candidates=["Gemma-4-E4B-it-GGUF"],
        )
        shootout._bus = _FakeBus()  # type: ignore[assignment]
        report = asyncio.run(shootout.run())

        assert events, "expected at least one event"
        updated = [e for e in events if e.type.name == "DATA_PRODUCT_UPDATED"]
        assert updated, "no DATA_PRODUCT_UPDATED event emitted"
        assert updated[0].payload["name"] == "Gemma-4-E4B-it-GGUF"
        assert updated[0].payload["role"] == "code"
        assert updated[0].payload["quality_score"] > 0.5  # GOLD tier on a good answer
        # ranking is quality-first: winner is the top-scorer in the report
        assert report.quality_ranked()[0].model == "Gemma-4-E4B-it-GGUF"

    def test_writes_model_performance_row(self, monkeypatch):
        """P2: a scored candidate persists a model_performance row for the router."""
        monkeypatch.setattr(hotswap, "resident_models", lambda: list(RESIDENT_MODELS))
        _make_transport(monkeypatch, "balance amt integer float overdraft.")
        written: list[dict] = []
        monkeypatch.setattr(
            "cohezion.inference.model_shootout.write_model_performance",
            lambda **kw: written.append(kw) or True,
        )

        class _FakeOrc:
            async def ensure_model(self, model, **kw):
                return SprintResult("code", model, True, "loaded")

        shootout = ModelShootout(
            candidates=["Gemma-4-E4B-it-GGUF"],
            min_free_gb=20.0,
        )
        shootout._orchestrator = _FakeOrc()  # type: ignore[assignment]
        asyncio.run(shootout.run())

        assert len(written) == 1
        assert written[0]["model"] == "Gemma-4-E4B-it-GGUF"
        assert written[0]["quality_score"] > 0.5
        assert written[0]["outcome"] == "pass"

    def test_quality_score_from_evaluate_quality_simple(self, monkeypatch):
        """P3: quality = fraction of expected tokens present (matches the scorer)."""
        text = "the balance and the amt: it is an integer, float money, and no overdraft guard."
        expected = ["balance", "amt", "overdraft", "integer", "float"]
        direct = evaluate_quality_simple(text, expected)
        assert direct == 1.0  # all 5 present


def test_write_model_performance_builds_valid_surql(monkeypatch):
    """P4: the SurrealDB writer constructs a CREATE with all required fields."""
    import json as _json
    import urllib.request

    sent: dict[str, Any] = {}
    seen_payload: list[str] = []

    class _Resp:
        status = 200

        def read(self):
            return b'[{"status": "OK", "result": []}]'

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def _fake_urlopen(req, timeout=5.0):
        payload = req.data.decode()
        seen_payload.append(payload)
        # Parse the CONTENT {...} clause out of the SURQL.
        content_part = payload.split("CONTENT ", 1)[1].rstrip().rstrip(";")
        sent.update(_json.loads(content_part))
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    ok = write_model_performance(
        model="Gemma-4-E4B-it-GGUF",
        quality_score=0.6,
        task="review",
        role="code",
        tps=31.7,
        outcome="pass",
    )
    assert ok is True
    assert sent["model"] == "Gemma-4-E4B-it-GGUF"
    assert sent["quality_score"] == 0.6
    assert sent["role"] == "code"
    assert sent["tps"] == 31.7
    assert sent["outcome"] == "pass"
    assert seen_payload and "model_performance" in seen_payload[0]
    assert sent["ts"]


def test_run_model_shootout_one_shot(monkeypatch):
    """P5: the convenience one-shot returns a quality-ranked ShootoutResult list."""
    monkeypatch.setattr(hotswap, "resident_models", lambda: list(RESIDENT_MODELS))
    _make_transport(monkeypatch, "balance amt integer float overdraft.")

    report = asyncio.run(run_model_shootout(candidates=["Gemma-4-E4B-it-GGUF"]))
    assert all(isinstance(r, ShootoutResult) for r in report.results)
    assert report.results[0].quality_score > 0.5
