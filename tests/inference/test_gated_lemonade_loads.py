"""Lemonade auto-load bypass closure: model_eval and hybrid router loads MUST be gated.

Regression tests for the 2026-09-14 OOM spiral. Lemonade (:13305) auto-loads any model
named in a ``/v1/chat/completions`` request, so a raw POST is a load. Both bypass sites
must now consult ``hotswap.ensure_resident`` FIRST:

* a refusal is a SUCCESSFUL gate outcome => NO chat-completion POST is made (asserted by
  an unstubbed-HTTP boom), the call falls through to the existing fallback shape, and
  the direct-port lanes are NOT used as a blind bypass;
* an ok gate (already resident or freshly loaded) => the request proceeds and the
  response content flows through unchanged.

Mocking convention (AGENTS.md): patch WHERE USED, i.e. the name in the module under
test — ``cohezion.inference.dynamic_model_evaluator.ensure_resident`` /
``cohezion.inference.unified_hybrid_router.ensure_resident``. No test touches the
network.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from cohezion.inference import hotswap
from cohezion.inference.dynamic_model_evaluator import DynamicModelEvaluator
from cohezion.inference.hotswap import SwapResult
from cohezion.inference.unified_hybrid_router import TaskClass, UnifiedHybridRouter
from cohezion.reliability.oom_guard import MemoryState


def _ok(model: str, *, already_resident: bool = False) -> SwapResult:
    return SwapResult(True, model, "already resident" if already_resident else "loaded")


def _refuse(model: str) -> SwapResult:
    return SwapResult(False, model, "insufficient RAM — refused before evicting")


@pytest.fixture
def evaluator() -> DynamicModelEvaluator:
    return DynamicModelEvaluator()


def _boom_urlopen(*_a, **_k):
    raise AssertionError("unstubbed chat-completions POST in gated-load test")


@pytest.fixture
def no_network(monkeypatch):
    """Fail loudly if a test forgets to stub a network seam."""

    def _boom(*_a, **_k):  # pragma: no cover - only fires on a test bug
        raise AssertionError("unstubbed HTTP call in gated-load test")

    monkeypatch.setattr(hotswap, "_post", _boom)
    monkeypatch.setattr(hotswap, "resident_models", lambda: [])
    monkeypatch.setattr(hotswap, "_catalog_sizes", dict)
    monkeypatch.setattr(hotswap, "free_gb", lambda: 100.0)
    monkeypatch.setattr("urllib.request.urlopen", _boom_urlopen)


# ---------------------------------------------------------------------------
# DynamicModelEvaluator — the gate on the :13305 + direct-port chat lanes
# ---------------------------------------------------------------------------


class TestEvaluatorGate:
    def test_refusal_skips_all_endpoints_no_http_post(self, evaluator, no_network):
        """Gate refusal => NO POST to :13305 or the direct port (unstubbed HTTP would raise)."""
        ev = DynamicModelEvaluator()
        with patch(
            "cohezion.inference.dynamic_model_evaluator.ensure_resident",
            return_value=_refuse("HUGE-MODEL"),
        ):
            out, latency_ms, tps = ev.query_model("HUGE-MODEL", "say hi")

        assert "gate refused" in out
        assert tps == 0.0
        assert latency_ms >= 0.0

    def test_refusal_skips_13305_but_still_tries_the_running_direct_port(
        self, evaluator, no_network
    ):
        """A refusal closes only the :13305 lane (the one that auto-loads).

        DIRECT_PORTS are Lemonade's own already-running per-model backends; a request there
        cannot load anything. Skipping them after a refusal (the first port of this fix)
        made every DIRECT_PORTS-only model unreachable, e.g. one missing from the catalog.
        """
        ev = DynamicModelEvaluator()
        assert "Bonsai-8B-gguf" in ev.DIRECT_PORTS
        urls: list[str] = []
        body = json.dumps({"choices": [{"message": {"content": "hi"}}]}).encode()

        def fake_urlopen(req, timeout=None):
            urls.append(req.full_url)
            return _Ctx(body)

        with (
            patch(
                "cohezion.inference.dynamic_model_evaluator.ensure_resident",
                return_value=_refuse("Bonsai-8B-gguf"),
            ),
            patch(
                "cohezion.inference.dynamic_model_evaluator.urllib.request.urlopen",
                side_effect=fake_urlopen,
            ),
        ):
            out, _latency_ms, tps = ev.query_model("Bonsai-8B-gguf", "say hi")

        port = ev.DIRECT_PORTS["Bonsai-8B-gguf"]
        assert urls == [f"http://127.0.0.1:{port}/v1/chat/completions"]
        assert ":13305" not in "".join(urls)
        assert out == "hi" and tps > 0.0

    def test_ok_proceeds_and_measures_latency_and_tps(self, evaluator, no_network):
        """Gate ok => the POST happens; latency/tps semantics unchanged."""
        ev = DynamicModelEvaluator()
        body = json.dumps(
            {"choices": [{"message": {"content": "```python\ndef f():\n    return 1\n```"}}]}
        ).encode()

        with (
            patch(
                "cohezion.inference.dynamic_model_evaluator.ensure_resident",
                return_value=_ok("M"),
            ),
            patch(
                "cohezion.inference.dynamic_model_evaluator.urllib.request.urlopen",
                return_value=_Ctx(body),
            ),
        ):
            out, latency_ms, tps = ev.query_model("M", "say hi")

        assert out == "```python\ndef f():\n    return 1\n```"
        assert latency_ms > 0.0
        assert tps > 0.0

    def test_gate_ctx_size_bounded_and_nonzero(self, evaluator, no_network):
        """ctx_size must be sane: never 0 (GTT crasher), never above hotswap.MAX_CTX."""
        seen: dict = {}

        def fake_gate(model, *, ctx_size=hotswap.MAX_CTX):
            seen["ctx_size"] = ctx_size
            return _ok(model)

        ev = DynamicModelEvaluator()
        with (
            patch(
                "cohezion.inference.dynamic_model_evaluator.ensure_resident",
                side_effect=fake_gate,
            ),
            patch(
                "cohezion.inference.dynamic_model_evaluator.urllib.request.urlopen",
                side_effect=_boom_urlopen,
            ),
        ):
            ev.query_model("M", "say hi")

        assert 0 < seen["ctx_size"] <= hotswap.MAX_CTX

    def test_refusal_marks_shootout_scorecard(self, evaluator, no_network):
        """A refused shootout candidate produces a zero-quality scorecard, not a blind load."""
        ev = DynamicModelEvaluator()
        with patch(
            "cohezion.inference.dynamic_model_evaluator.ensure_resident",
            return_value=_refuse("HUGE-MODEL"),
        ):
            [sc] = ev.run_comparative_shootout(
                candidates=[("HUGE-MODEL", "iGPU")],
                task_id="t",
                prompt="p",
                test_fn=lambda env: 1.0,
            )

        assert sc.quality_score == 0.0
        assert sc.test_pass_rate == 0.0
        assert "gate refused" in sc.details["code_snippet"]


class _Ctx:
    """Minimal context manager for a urlopen response."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return self._body


class _HttpxResponse:
    """Minimal stand-in for httpx.Response (status_code + .json())."""

    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _HealthOK:
    """Minimal stand-in for lemonade_health.LemonadeHealth with ok=True."""

    ok = True
    summary = "ok"


def _safe_memory() -> MemoryState:
    return MemoryState(
        available_gb=50.0,
        total_gb=128.0,
        swap_used_gb=0.0,
        shmem_gb=0.5,
        is_safe=True,
        dynamic_floor_gb=20.0,
    )


# ---------------------------------------------------------------------------
# UnifiedHybridRouter — the gate on aquery_lemonade_local + aquery_embedding
# ---------------------------------------------------------------------------


class TestHybridRouterGate:
    @pytest.mark.asyncio
    async def test_refusal_returns_none_no_chat_post(self, no_network):
        """Gate refusal => aquery_lemonade_local returns None; no :13305 POST is attempted."""
        router = UnifiedHybridRouter(prefer_local=True)
        with patch(
            "cohezion.inference.unified_hybrid_router.ensure_resident",
            return_value=_refuse("HUGE-MODEL"),
        ):
            out = await router.aquery_lemonade_local("hello", "HUGE-MODEL")

        assert out is None

    @pytest.mark.asyncio
    async def test_refusal_falls_through_to_tier2_cloud(self, no_network):
        """route_by_capability: refused Tier-1 load must land on the existing Tier-2 path."""
        router = UnifiedHybridRouter(prefer_local=True)

        def fake_gate(model, **_k):
            return _refuse(model)

        async def fake_cloud(prompt, model):
            return "cloud response"

        with (
            patch(
                "cohezion.inference.unified_hybrid_router.ensure_resident",
                side_effect=fake_gate,
            ),
            patch(
                "cohezion.inference.unified_hybrid_router.probe_lemonade",
                return_value=_HealthOK(),
            ),
            patch(
                "cohezion.reliability.oom_guard.OOMGuard.get_memory_state",
                return_value=_safe_memory(),
            ),
            patch.object(router, "aquery_ollama_cloud", side_effect=fake_cloud),
        ):
            res = await router.route_by_capability("hello", task_class=TaskClass.REASONING)

        assert res.tier_used == "Tier 2 (Ollama Cloud)"
        assert res.verified is True

    @pytest.mark.asyncio
    async def test_ok_proceeds_with_chat_completion(self, no_network):
        """Gate ok => the :13305 POST happens and the content flows through unchanged."""
        router = UnifiedHybridRouter(prefer_local=True)
        resp = _HttpxResponse(
            200,
            {"choices": [{"message": {"content": "local answer"}}]},
        )

        with (
            patch(
                "cohezion.inference.unified_hybrid_router.ensure_resident",
                return_value=_ok("M"),
            ),
            patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=resp),
        ):
            out = await router.aquery_lemonade_local("hello", "M")

        assert out == "local answer"

    @pytest.mark.asyncio
    async def test_embedding_refusal_skips_endpoint(self, no_network):
        """/v1/embeddings auto-loads too: a refusal must skip it (no POST)."""
        router = UnifiedHybridRouter(prefer_local=True)
        with patch(
            "cohezion.inference.unified_hybrid_router.ensure_resident",
            return_value=_refuse("HUGE-EMBED"),
        ):
            out = await router.aquery_embedding("hello", "HUGE-EMBED")

        assert out is None

    @pytest.mark.asyncio
    async def test_embedding_ok_proceeds(self, no_network):
        """Gate ok => the embedding POST happens and the vector flows through."""
        router = UnifiedHybridRouter(prefer_local=True)
        resp = _HttpxResponse(200, {"data": [{"embedding": [0.1, 0.2, 0.3]}]})

        with (
            patch(
                "cohezion.inference.unified_hybrid_router.ensure_resident",
                return_value=_ok("embed-gemma-300m-FLM"),
            ),
            patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=resp),
        ):
            out = await router.aquery_embedding("hello", "embed-gemma-300m-FLM")

        assert out == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_gate_ctx_size_bounded_and_nonzero(self, no_network):
        """ctx_size must be sane: never 0 (GTT crasher), never above hotswap.MAX_CTX."""
        router = UnifiedHybridRouter(prefer_local=True)
        seen: dict = {}

        def fake_gate(model, *, ctx_size=hotswap.MAX_CTX):
            seen["ctx_size"] = ctx_size
            return _refuse(model)

        with patch(
            "cohezion.inference.unified_hybrid_router.ensure_resident",
            side_effect=fake_gate,
        ):
            await router.aquery_lemonade_local("hello", "M")

        assert 0 < seen["ctx_size"] <= hotswap.MAX_CTX

    @pytest.mark.asyncio
    async def test_gate_ctx_size_covers_a_long_prompt(self, no_network):
        """A load fixes the window for every later caller: it must hold prompt + reply.

        Sizing from max_tokens alone gave 2048 for a ~5000-word prompt (review S4).
        """
        router = UnifiedHybridRouter(prefer_local=True)
        prompt = "word " * 5000  # 25,000 chars, ~6-8k tokens
        seen: dict = {}

        def fake_gate(model, *, ctx_size=hotswap.MAX_CTX):
            seen["ctx_size"] = ctx_size
            return _refuse(model)

        with patch(
            "cohezion.inference.unified_hybrid_router.ensure_resident", side_effect=fake_gate
        ):
            await router.aquery_lemonade_local(prompt, "llama3.2-1b-FLM")

        assert seen["ctx_size"] >= len(prompt) // 4 + 1024
        assert seen["ctx_size"] <= hotswap.MAX_CTX

    @pytest.mark.asyncio
    async def test_embedding_gate_is_not_llm_cap_gated(self, no_network):
        seen: dict = {}

        def fake_gate(model, **kw):
            seen.update(kw)
            return _refuse(model)

        router = UnifiedHybridRouter(prefer_local=True)
        with patch(
            "cohezion.inference.unified_hybrid_router.ensure_resident", side_effect=fake_gate
        ):
            await router.aquery_embedding("hi", "nomic-embed-text-v2-moe-GGUF")

        assert seen.get("kind") == "embedding"

    def test_sync_route_query_gates_through_async_path(self, no_network):
        """route_query -> query_lemonade_local -> aquery_lemonade_local: refusal => Tier-2."""
        router = UnifiedHybridRouter(prefer_local=True)

        def fake_gate(model, **_k):
            return _refuse(model)

        async def fake_acloud(prompt, model):
            return "cloud via route_query"

        with (
            patch(
                "cohezion.inference.unified_hybrid_router.ensure_resident",
                side_effect=fake_gate,
            ),
            patch(
                "cohezion.reliability.oom_guard.OOMGuard.get_memory_state",
                return_value=_safe_memory(),
            ),
            patch.object(router, "aquery_ollama_cloud", side_effect=fake_acloud),
        ):
            res = router.route_query("hello")

        assert res.tier_used == "Tier 2 (Ollama Cloud)"
        assert res.content == "cloud via route_query"
