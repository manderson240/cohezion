"""Tests for DirectLemonadeImageTier (SD-Turbo on OmniRouter :13305).

Live tests hit the real OmniRouter and skip cleanly when :13305 is down.
Mocked tests use httpx stubs and always run.
"""

from __future__ import annotations

import base64
import socket

import pytest

from cohezion.inference.image_tier import (
    DirectLemonadeImageTier,
    ImageRequest,
    ImageResult,
)


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def lemonade_reachable(host: str = "localhost", port: int = 13305) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def _image_model_loaded(host: str = "localhost", port: int = 13305) -> bool:
    """Check if an image generation model is loaded on the OmniRouter."""
    if not lemonade_reachable(host, port):
        return False
    try:
        import httpx

        resp = httpx.get(f"http://{host}:{port}/v1/models", timeout=2.0)
        if resp.status_code >= 500:
            return False
        models = resp.json().get("data", [])
        return any(
            "sd" in m.get("id", "").lower() or "image" in m.get("id", "").lower() for m in models
        )
    except Exception:
        return False


# ----- Pure-logic tests (no network) ----------------------------------------


def test_default_port_is_13305():
    """The 2026-06-10 design rule: only the OmniRouter. No per-lane ports."""
    assert DirectLemonadeImageTier.DEFAULT_PORT == 13305


def test_image_request_defaults():
    req = ImageRequest(prompt="x")
    assert req.size == "512x512"
    assert req.steps == 4
    assert req.n == 1
    assert req.model == "SD-Turbo"
    assert req.response_format == "b64_json"
    assert req.negative_prompt == ""


def test_image_result_ok_when_images_present():
    r = ImageResult(
        images=[PNG_MAGIC + b"x" * 100],
        mime_type="image/png",
        size="256x256",
        n=1,
        latency_ms=100.0,
        bytes_total=108,
        per_image_latency_ms=100.0,
        port=13305,
        model="SD-Turbo",
        prompt="x",
    )
    assert r.ok
    assert r.error is None


def test_image_result_not_ok_when_no_images():
    r = ImageResult(
        images=[],
        mime_type="",
        size="256x256",
        n=1,
        latency_ms=100.0,
        bytes_total=0,
        per_image_latency_ms=0.0,
        port=13305,
        model="SD-Turbo",
        prompt="x",
        error="err",
    )
    assert not r.ok
    assert r.error == "err"


def test_image_result_save_writes_bytes(tmp_path):
    r = ImageResult(
        images=[PNG_MAGIC + b"hello"],
        mime_type="image/png",
        size="256x256",
        n=1,
        latency_ms=100.0,
        bytes_total=len(PNG_MAGIC) + 5,
        per_image_latency_ms=100.0,
        port=13305,
        model="SD-Turbo",
        prompt="x",
    )
    p = tmp_path / "out.png"
    r.save(str(p))
    assert p.read_bytes() == PNG_MAGIC + b"hello"


# ----- Live tests against :13305 (skipped if router down) -------------------

LIVE = pytest.mark.skipif(
    not _image_model_loaded(),
    reason="lemonade OmniRouter not reachable or image model not loaded on :13305",
)


@LIVE
@pytest.mark.asyncio
async def test_image_render_256_live():
    tier = DirectLemonadeImageTier(port=13305)
    r = await tier.render(ImageRequest(prompt="a small red dot", size="256x256", steps=2))
    if r.error and (
        "500" in str(r.error) or "not loaded" in str(r.error) or "Server error" in str(r.error)
    ):
        pytest.skip("Image model not loaded into memory")
    assert r.ok, f"render failed: {r.error}"
    assert len(r.images) == 1
    assert r.images[0][:8] == PNG_MAGIC
    assert r.latency_ms < 5000
    assert r.port == 13305


@LIVE
@pytest.mark.asyncio
async def test_image_render_512_compound_prompt_live():
    tier = DirectLemonadeImageTier(port=13305)
    r = await tier.render(
        ImageRequest(
            prompt="abstract visualization of the HIHO balance point, deep blue and warm orange, no text",
            size="512x512",
            steps=4,
        )
    )
    assert r.ok
    assert r.images[0][:8] == PNG_MAGIC
    assert r.bytes_total > 100_000


@LIVE
@pytest.mark.asyncio
async def test_image_render_batch_n3_live():
    tier = DirectLemonadeImageTier(port=13305)
    r = await tier.render(ImageRequest(prompt="three options", size="256x256", steps=2, n=3))
    assert r.ok
    assert len(r.images) == 3
    for im in r.images:
        assert im[:8] == PNG_MAGIC


@pytest.mark.asyncio
async def test_image_render_error_path():
    bad = DirectLemonadeImageTier(port=9999)
    r = await bad.render(ImageRequest(prompt="x"))
    assert not r.ok
    assert r.error is not None
    assert "Connect" in r.error or "connect" in r.error


@LIVE
@pytest.mark.asyncio
async def test_image_is_alive_live():
    tier = DirectLemonadeImageTier(port=13305)
    assert await tier.is_alive()


# ----- Mocked test (always runs) --------------------------------------------


@pytest.mark.asyncio
async def test_image_render_mocked(monkeypatch):
    """Verify the request shape and response parsing without hitting the router."""
    import httpx

    fake_png = PNG_MAGIC + b"\x00" * 50
    fake_b64 = base64.b64encode(fake_png).decode()
    captured = {}

    class _Resp:
        status_code = 200

        def json(self):
            return {"data": [{"b64_json": fake_b64}]}

        def raise_for_status(self):
            pass

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def post(self, url, *, json):
            captured["url"] = url
            captured["json"] = json
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    tier = DirectLemonadeImageTier(port=13305)
    r = await tier.render(ImageRequest(prompt="mock test", size="256x256", steps=2))
    assert r.ok
    assert len(r.images) == 1
    assert r.images[0] == fake_png
    assert captured["url"] == "http://localhost:13305/v1/images/generations"
    body = captured["json"]
    assert body["model"] == "SD-Turbo"
    assert body["prompt"] == "mock test"
    assert body["size"] == "256x256"
    assert body["steps"] == 2
    assert body["response_format"] == "b64_json"
