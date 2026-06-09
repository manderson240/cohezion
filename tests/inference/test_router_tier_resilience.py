"""F3/F4 resilience tests (adversarial audit 2026-06-09).

The triune router tiers preload a model on the single :13305 router. Two defects the
audit found and these tests pin:

* F4 — ``_ensure_loaded`` set ``_loaded=True`` in ``finally`` even when the load POST
  FAILED, so the next chat proceeded and the router auto-loaded the model (possibly at
  an unbounded ctx if the card was not hardened — the N3 OOM crasher). A failed preload
  must NOT mark the tier loaded; the next call must RETRY the bounded load.
* F3 — ``_ensure_loaded`` had no lock, so N concurrent ``run_batch`` coroutines each
  fired their own ``/api/v1/load`` POST (the storm that saturated :13305 and starved the
  live bot, item 113). Concurrent preloads must serialize to exactly ONE load.
* F3 — ``build_triune_orchestrator`` never set ``_max_concurrent``, so ``run_batch`` ran
  an UNBOUNDED ``asyncio.gather`` against the single router. The factory must set a cap.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cohezion.inference.direct_tier import RouterTier


def _patch_async_post(post_mock: AsyncMock):
    """Patch ``httpx.AsyncClient`` so ``async with httpx.AsyncClient(...) as client``
    yields a client whose ``.post`` is ``post_mock``."""
    client = MagicMock()
    client.post = post_mock
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return patch("httpx.AsyncClient", return_value=cm)


def _ok_response() -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock(return_value=None)  # 2xx, does not raise
    return resp


@pytest.mark.asyncio
async def test_ensure_loaded_does_not_mark_loaded_on_failure():
    """F4: a failed preload must NOT set ``_loaded`` (else the next chat triggers an
    unbounded router auto-load). The pre-fix ``finally: self._loaded = True`` set it
    regardless — this test fails against that impl."""
    tier = RouterTier(model_id="llama3.2-1b-FLM", backend="npu")
    post = AsyncMock(side_effect=httpx.ConnectError("router down"))
    with _patch_async_post(post):
        await tier._ensure_loaded()
    assert tier._loaded is False, "failed preload must not mark the tier loaded (F4)"


@pytest.mark.asyncio
async def test_ensure_loaded_marks_loaded_on_success():
    tier = RouterTier(model_id="llama3.2-1b-FLM", backend="npu")
    post = AsyncMock(return_value=_ok_response())
    with _patch_async_post(post):
        await tier._ensure_loaded()
    assert tier._loaded is True


@pytest.mark.asyncio
async def test_concurrent_ensure_loaded_fires_single_load():
    """F3: 8 concurrent preloads must serialize to exactly ONE /api/v1/load POST, not 8
    (the storm that saturated :13305, item 113). The pre-fix lock-less impl fires 8."""
    tier = RouterTier(model_id="llama3.2-1b-FLM", backend="npu")

    async def _slow_ok(*_a, **_k):
        # Yield to the loop so all 8 coroutines genuinely overlap inside _ensure_loaded
        # BEFORE any sets _loaded — otherwise an AsyncMock completes coro-1 atomically and
        # the test passes hollowly against the lock-less impl.
        await asyncio.sleep(0.01)
        return _ok_response()

    post = AsyncMock(side_effect=_slow_ok)
    with _patch_async_post(post):
        await asyncio.gather(*[tier._ensure_loaded() for _ in range(8)])
    assert post.await_count == 1, f"expected 1 load POST, got {post.await_count} (no lock)"


# --------------------------------------------------------------------------- #
# Behavioral coverage closing the Phase 2 verification gap (scientific-rigor audit):
# the prod RouterTier had ZERO tests that exercised payload selection or dispatch —
# the 27 Phase 2 tests asserted only `.label` strings, which pass for a wrong impl.
# --------------------------------------------------------------------------- #


def test_build_load_payload_omits_backend_for_npu_and_auto():
    for backend in ("npu", "auto"):
        payload = RouterTier(model_id="some-model", backend=backend)._build_load_payload()
        assert "llamacpp_backend" not in payload, f"{backend} must omit llamacpp_backend"
        assert 1 <= payload["ctx_size"] <= 16384  # N3 bound


def test_build_load_payload_includes_backend_for_vulkan_nonflm():
    payload = RouterTier(model_id="Gemma-4-E4B-it-GGUF", backend="vulkan")._build_load_payload()
    assert payload["llamacpp_backend"] == "vulkan"


def test_build_load_payload_omits_backend_for_flm_model_even_with_cpu_backend():
    """Discriminating: an FLM-recipe model must NEVER get ``llamacpp_backend``, even when
    the backend hint is 'cpu'. Kills an impl that only checks ``backend not in (npu,auto)``
    and forgets the FLM-model check (the router 500s on llamacpp_backend for FLM models)."""
    payload = RouterTier(model_id="llama3.2-1b-FLM", backend="cpu")._build_load_payload()
    assert "llamacpp_backend" not in payload


@pytest.mark.asyncio
async def test_router_tier_dispatches_to_13305_and_returns_content():
    """Behavioral: RouterTier.run must POST the chat to :13305 and return the model's
    content. A label-only test passes even if it routed to a wrong port or dropped the
    response — this fails for both."""
    tier = RouterTier(model_id="llama3.2-1b-FLM", backend="npu")
    posted_urls: list[str] = []

    async def _router_post(url, **_kwargs):
        posted_urls.append(url)
        resp = MagicMock()
        resp.raise_for_status = MagicMock(return_value=None)
        if "/v1/chat/completions" in url:
            resp.json = MagicMock(
                return_value={"choices": [{"message": {"content": "  hi there  "}}]}
            )
        return resp

    post = AsyncMock(side_effect=_router_post)
    with _patch_async_post(post):
        result = await tier.run("ping")

    chat_posts = [u for u in posted_urls if "/v1/chat/completions" in u]
    assert chat_posts, f"RouterTier never POSTed a chat request; urls={posted_urls}"
    assert "localhost:13305" in chat_posts[0], f"chat routed to wrong endpoint: {chat_posts[0]}"
    assert result.text == "hi there", f"response dropped/garbled: {result.text!r}"
    assert result.error is None


@pytest.mark.asyncio
async def test_dispatch_falls_back_to_reasoning_content_for_thinking_models():
    """F2 (adversarial audit): thinking models (deepseek-r1, FLM) emit the answer in
    ``reasoning_content`` with empty ``content``. The tier path read only ``content``, so the
    iGPU reasoning lane systematically returned '' and escalated. It must fall back to
    reasoning_content. Discriminating: content is empty, the answer is ONLY in reasoning."""
    tier = RouterTier(model_id="deepseek-r1-0528-8b-FLM", backend="vulkan")

    async def _router_post(url, **_kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock(return_value=None)
        if "/v1/chat/completions" in url:
            resp.json = MagicMock(
                return_value={
                    "choices": [{"message": {"content": "", "reasoning_content": "the real answer"}}]
                }
            )
        return resp

    post = AsyncMock(side_effect=_router_post)
    with _patch_async_post(post):
        result = await tier.run("solve this")

    assert result.text == "the real answer", f"dropped reasoning_content: {result.text!r}"
    assert result.error is None


def test_build_triune_orchestrator_sets_concurrency_cap():
    """F3: build_triune_orchestrator must bound run_batch concurrency (item 113), else
    asyncio.gather is unbounded against the single :13305. Pre-fix returns None."""
    from cohezion.inference.triune_orchestrator import build_triune_orchestrator

    orch = build_triune_orchestrator(include_cloud=False)
    cap = getattr(orch, "_max_concurrent", None)
    assert cap is not None and cap >= 1, "run_batch must carry a fleet-fairness cap (item 113)"
