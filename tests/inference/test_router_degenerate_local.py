"""A collapsed local reply is a miss, not a verified answer.

2026-11-05/06: qwen3.6-moe-35b-a3b-FLM (the router's default ``npu_model``) returned only "/"
on every prompt under FLM 1.0.12. ``route_query`` accepted any non-empty local text and
returned it as ``verified=True``. These tests pin that a one-symbol reply is rejected at both
local acceptance points (``aquery_lemonade_local`` and ``LemonadeTransport.query``) while
low-entropy but legitimate output (DNA, binary, tables) is kept.
"""

from __future__ import annotations

import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.inference.anti_spiral_watchdog import COLLAPSE_MIN_CHARS, is_collapsed
from cohezion.inference.transports.lemonade import LemonadeTransport
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter
from cohezion.reliability.oom_guard import MemoryState


SAFE = MemoryState(
    available_gb=50.0,
    total_gb=128.0,
    swap_used_gb=0.0,
    shmem_gb=0.5,
    is_safe=True,
    dynamic_floor_gb=20.0,
)
_rng = random.Random(7)
COLLAPSED = ["/" * 2048, "/ " * 1000, "/\n" * 1000, "aaaa " * 200]
LEGIT = [
    "391",
    "The product of 17 and 23 is 391, since 17*20 = 340 and 17*3 = 51.",
    "| a | b |\n| --- | --- |\n| --- | --- |\n| 1 | 2 |\n" * 4,
    "".join(_rng.choice("ACGT") for _ in range(500)),
    "".join(_rng.choice("01") for _ in range(512)),
    " ".join(f"{_rng.getrandbits(8):08b}" for _ in range(64)),
]


def _client_returning(message: dict) -> MagicMock:
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"choices": [{"message": message}]}
    client = MagicMock()
    client.post = AsyncMock(return_value=resp)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=ctx)


@pytest.mark.parametrize("text", COLLAPSED)
def test_is_collapsed_flags_one_symbol_replies(text: str) -> None:
    assert is_collapsed(text)


@pytest.mark.parametrize("text", LEGIT)
def test_is_collapsed_keeps_low_entropy_real_output(text: str) -> None:
    assert not is_collapsed(text)


def test_is_collapsed_length_boundary() -> None:
    assert not is_collapsed("/" * (COLLAPSE_MIN_CHARS - 1))
    assert is_collapsed("/" * COLLAPSE_MIN_CHARS)


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["content", "reasoning_content"])
@pytest.mark.parametrize("text", COLLAPSED)
async def test_aquery_lemonade_local_rejects_collapse(field: str, text: str) -> None:
    router = UnifiedHybridRouter()
    with patch("httpx.AsyncClient", _client_returning({field: text})):
        assert await router.aquery_lemonade_local("q", "qwen3.6-moe-35b-a3b-FLM") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("text", LEGIT)
async def test_aquery_lemonade_local_keeps_real_answers(text: str) -> None:
    router = UnifiedHybridRouter()
    with patch("httpx.AsyncClient", _client_returning({"content": text})):
        assert await router.aquery_lemonade_local("q", "qwen3.6-moe-35b-a3b-FLM") == text.strip()


@pytest.mark.asyncio
async def test_lemonade_transport_rejects_collapse_and_keeps_answers() -> None:
    t = LemonadeTransport()
    with patch(
        "cohezion.inference.transports.lemonade.httpx.AsyncClient",
        _client_returning({"content": "/" * 2048}),
    ):
        assert await t.query("q", "m") is None
    with patch(
        "cohezion.inference.transports.lemonade.httpx.AsyncClient",
        _client_returning({"content": "391"}),
    ):
        res = await t.query("q", "m")
    assert res is not None and res.content == "391" and res.verified is True


def test_route_query_falls_through_on_collapsed_local() -> None:
    router = UnifiedHybridRouter(prefer_local=True)
    with (
        patch("httpx.AsyncClient", _client_returning({"content": "/" * 2048})),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=SAFE,
        ),
        patch.object(router, "query_ollama_cloud", return_value=None) as cloud,
    ):
        res = router.route_query("What is 17*23?")
    cloud.assert_called_once()
    assert res.verified is False
    assert "/" * 64 not in res.content
