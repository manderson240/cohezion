"""GPU lease enforcement at the :13305 admission gate and proxy.

Real kernel flocks on tmp_path and a real subprocess holder; only lemonade HTTP, the
cgroup and the catalog are faked. The lease may only TIGHTEN the gate.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from cohezion.platform.admission_gate import AdmissionGate, GateConfig
from cohezion.platform.admission_proxy import build_app


GGUF = "Gemma-4-E4B-it-GGUF"
FLM = "llama3.2-1b-FLM"
CATALOG = {
    GGUF: {"id": GGUF, "size": 5.0, "recipe": "llamacpp"},
    FLM: {"id": FLM, "size": 1.0, "recipe": "flm"},
}

_HOLDER = (
    "import fcntl, os, sys, time\n"
    "fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o644)\n"
    "fcntl.flock(fd, fcntl.LOCK_EX)\n"
    "print('ready', flush=True)\n"
    "time.sleep(600)\n"
)


def _hold(path: Path) -> subprocess.Popen:
    """A real separate process holding the lease flock."""
    proc = subprocess.Popen(
        [sys.executable, "-c", _HOLDER, str(path)], stdout=subprocess.PIPE, text=True
    )
    assert proc.stdout is not None
    assert proc.stdout.readline().strip() == "ready"
    return proc


@pytest.fixture
def holder(_isolated_gpu_lease):
    proc = _hold(_isolated_gpu_lease)
    yield proc
    if proc.poll() is None:
        proc.kill()
    proc.wait()


def _gate(
    resident: list[dict] | None = None,
    working_set: float = 0.0,
    catalog_fresh: bool = True,
) -> AdmissionGate:
    gate = AdmissionGate(
        config=GateConfig(enforce=True),
        read_resident=lambda: list(resident or []),
        read_cgroup=lambda: (working_set, 30.0),
        read_size_gb=lambda m: 5.0 if m == GGUF else 1.0,
        read_catalog=lambda: CATALOG,
    )
    if catalog_fresh:
        gate.refresh_catalog()
    return gate


class TestGateUnderLease:
    def test_held_lease_refuses_reload_of_resident_gguf(self, holder) -> None:
        # The resident shortcut must NOT run before the lease check: a steady client of a
        # resident GPU model would otherwise keep it pinned and hang the holder's unload.
        gate = _gate(resident=[{"model_name": GGUF, "recipe": "llamacpp"}])
        d = gate.decide(GGUF, "api/v1/chat/completions")
        assert not d.allow
        assert d.kind == "gpu_lease"

    def test_free_lease_admits_the_same_resident_request(self) -> None:
        gate = _gate(resident=[{"model_name": GGUF, "recipe": "llamacpp"}])
        d = gate.decide(GGUF, "api/v1/chat/completions")
        assert d.allow and d.kind != "gpu_lease"

    def test_flm_with_fresh_catalog_is_admitted(self, holder) -> None:
        d = _gate().decide(FLM, "api/v1/chat/completions")
        assert d.allow

    def test_flm_still_faces_the_cgroup_check(self, holder) -> None:
        # The lease never relaxes a check: an FLM load over the cgroup budget is refused.
        d = _gate(working_set=27.0).decide(FLM, "api/v1/chat/completions")
        assert not d.allow and d.kind != "gpu_lease"

    def test_flm_with_stale_catalog_is_refused(self, holder) -> None:
        d = _gate(catalog_fresh=False).decide(FLM, "api/v1/chat/completions")
        assert not d.allow and d.kind == "gpu_lease"

    @pytest.mark.parametrize("key", ["llamacpp_backend", "flm_args", "llamacpp_device"])
    def test_flm_with_backend_override_is_refused(self, holder, key) -> None:
        body = {"model_name": FLM, key: "vulkan"}
        d = _gate().decide(FLM, "api/v1/load", body=body)
        assert not d.allow and d.kind == "gpu_lease"

    @pytest.mark.parametrize("route", ["api/v1/unload", "v1/delete", "api/v1/pull"])
    def test_freeing_routes_always_forward(self, holder, route) -> None:
        assert _gate().decide(GGUF, route).allow

    def test_unnamed_post_on_load_path_is_refused(self, holder) -> None:
        d = _gate().decide(None, "api/v1/load", method="POST")
        assert not d.allow and d.kind == "gpu_lease"

    def test_unnamed_get_passes(self, holder) -> None:
        assert _gate().decide(None, "api/v1/health", method="GET").allow

    def test_sigkilled_holder_frees_the_lease_without_ttl(self, holder) -> None:
        gate = _gate(resident=[{"model_name": GGUF}])
        assert not gate.decide(GGUF, "v1/chat/completions").allow
        holder.send_signal(signal.SIGKILL)
        holder.wait()
        assert gate.decide(GGUF, "v1/chat/completions").allow
        assert gate.lease_status()["held"] is False

    def test_missing_lock_file_is_free(self, _isolated_gpu_lease) -> None:
        assert not _isolated_gpu_lease.exists()
        assert _gate().lease_status()["held"] is False

    @pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file modes")
    def test_unreadable_lock_fails_closed(self, _isolated_gpu_lease) -> None:
        _isolated_gpu_lease.write_text("")
        _isolated_gpu_lease.chmod(0)
        try:
            gate = _gate(resident=[{"model_name": GGUF}])
            assert not gate.decide(GGUF, "v1/chat/completions").allow
        finally:
            _isolated_gpu_lease.chmod(0o644)


def _upstream(seen: list[httpx.Request]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://up.test")


class TestProxyUnderLease:
    def test_hold_forwards_once_lease_released_within_window(self, holder) -> None:
        seen: list[httpx.Request] = []
        app = build_app(
            _gate(resident=[{"model_name": GGUF}]),
            client=_upstream(seen),
            lease_hold_s=10.0,
            lease_poll_s=0.1,
        )
        threading.Timer(0.8, holder.kill).start()
        start = time.monotonic()
        with TestClient(app) as c:
            r = c.post("/v1/chat/completions", json={"model": GGUF, "messages": []})
        assert r.status_code == 200
        assert len(seen) == 1
        assert 0.7 < time.monotonic() - start < 9.0

    def test_hold_expiry_returns_503_with_lease_headers(self, holder) -> None:
        seen: list[httpx.Request] = []
        app = build_app(
            _gate(resident=[{"model_name": GGUF}]),
            client=_upstream(seen),
            lease_hold_s=0.3,
            lease_poll_s=0.05,
        )
        with TestClient(app) as c:
            r = c.post("/v1/chat/completions", json={"model": GGUF, "messages": []})
        assert r.status_code == 503
        assert r.headers["Retry-After"] == "15"
        assert r.headers["X-Cohezion-Refusal"] == "gpu_lease"
        assert seen == []

    def test_cpu_fallback_on_gguf_load_without_override(self, holder) -> None:
        seen: list[httpx.Request] = []
        app = build_app(_gate(), client=_upstream(seen), lease_hold_s=0.2, lease_poll_s=0.05)
        with TestClient(app) as c:
            r = c.post("/api/v1/load", json={"model_name": GGUF, "ctx_size": 4096})
        assert r.status_code == 200
        import json

        sent = json.loads(seen[0].content)
        assert sent["llamacpp_backend"] == "cpu"
        assert sent["ctx_size"] == 4096

    def test_cpu_fallback_still_faces_cgroup_check(self, holder) -> None:
        seen: list[httpx.Request] = []
        app = build_app(
            _gate(working_set=26.0), client=_upstream(seen), lease_hold_s=0.2, lease_poll_s=0.05
        )
        with TestClient(app) as c:
            r = c.post("/api/v1/load", json={"model_name": GGUF})
        assert r.status_code == 503 and seen == []

    def test_no_fallback_when_body_already_overrides_backend(self, holder) -> None:
        seen: list[httpx.Request] = []
        app = build_app(_gate(), client=_upstream(seen), lease_hold_s=0.2, lease_poll_s=0.05)
        with TestClient(app) as c:
            r = c.post("/api/v1/load", json={"model_name": GGUF, "llamacpp_backend": "vulkan"})
        assert r.status_code == 503 and seen == []

    def test_no_fallback_on_non_load_routes(self, holder) -> None:
        seen: list[httpx.Request] = []
        app = build_app(_gate(), client=_upstream(seen), lease_hold_s=0.2, lease_poll_s=0.05)
        with TestClient(app) as c:
            r = c.post("/v1/chat/completions", json={"model": GGUF, "messages": []})
        assert r.status_code == 503 and seen == []

    def test_unload_forwards_under_lease(self, holder) -> None:
        seen: list[httpx.Request] = []
        app = build_app(_gate(), client=_upstream(seen), lease_hold_s=0.2)
        with TestClient(app) as c:
            r = c.post("/api/v1/unload", json={"model_name": GGUF, "force": True})
        assert r.status_code == 200 and len(seen) == 1

    def test_status_reports_lease_and_reservations(self, holder, _isolated_gpu_lease) -> None:
        sidecar = _isolated_gpu_lease.with_name("gpu-lease.holder.json")
        sidecar.write_text('{"holder": "trainer", "pid": 4242, "since": 1.5}')
        seen: list[httpx.Request] = []
        app = build_app(_gate(), client=_upstream(seen))
        with TestClient(app) as c:
            s = c.get("/admission/status").json()
        assert s["gpu_lease"] == {"held": True, "holder": "trainer", "pid": 4242, "since": 1.5}
        assert s["reserved"] == []


class TestFallbackNeverSkipsCgroup:
    def test_fallback_of_stale_resident_model_still_faces_cgroup(self, holder) -> None:
        # A5 unloaded the model but /health is blocked by an FLM load, so the gate's
        # last-good residency still lists it. The CPU fallback must not ride the resident
        # shortcut past the footprint check (the 2026-10-21 unchecked-CPU-load class).
        seen: list[httpx.Request] = []
        gate = _gate(resident=[{"model_name": GGUF}], working_set=26.0)
        app = build_app(gate, client=_upstream(seen), lease_hold_s=0.2, lease_poll_s=0.05)
        with TestClient(app) as c:
            r = c.post("/api/v1/load", json={"model_name": GGUF})
        assert r.status_code == 503 and seen == []
