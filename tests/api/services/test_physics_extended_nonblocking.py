"""/api/physics handlers must not block the event loop (review follow-up 2026-09-21).

Every handler in physics_extended does synchronous numpy/torch work and awaits nothing.
Declared ``async def``, that work runs ON the event loop, so one slow request stalls every
other request the server is handling. Declared ``def``, FastAPI runs it in a threadpool.

Behavioral, not structural: a deliberately slow MHD request is in flight while a cheap
Bismuth request is issued; the cheap one must not wait for the slow one.
"""

from __future__ import annotations

import asyncio
import time

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from cohezion.api.services.physics_extended import physics_ext_router

_SLOW_S = 0.6


@pytest.mark.asyncio
async def test_slow_physics_request_does_not_stall_a_concurrent_one(monkeypatch):
    import cohezion.physics.mhd_plasma as mhd_plasma

    real = mhd_plasma.MHDEquilibrium

    class _SlowMHD(real):  # type: ignore[misc, valid-type]
        def __init__(self, *a, **k):
            time.sleep(_SLOW_S)  # stands in for blocking CPU work
            super().__init__(*a, **k)

    monkeypatch.setattr(mhd_plasma, "MHDEquilibrium", _SlowMHD)

    app = FastAPI()
    app.include_router(physics_ext_router, prefix="/api")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        await c.get("/api/physics/bismuth/status")  # warm imports outside the timing

        async def cheap(issue_at: float) -> float:
            # issue_at is fixed BEFORE gather: a blocked loop delays even the start of this
            # coroutine, and that stall must count against the cheap request.
            await asyncio.sleep(max(0.0, issue_at - time.perf_counter()))
            r = await c.get("/api/physics/bismuth/status")
            assert r.status_code == 200
            return time.perf_counter() - issue_at

        issue_at = time.perf_counter() + 0.05  # let the slow request start first
        slow_resp, cheap_s = await asyncio.gather(
            c.get("/api/physics/mhd/status"), cheap(issue_at)
        )

    assert slow_resp.status_code == 200
    assert cheap_s < _SLOW_S / 2, f"cheap request waited {cheap_s:.3f}s behind the slow one"
