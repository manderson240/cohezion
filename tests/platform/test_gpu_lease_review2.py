"""Second adversarial review of the GPU lease, each finding pinned as the SAFE behaviour.

Reviewer counterexamples asserted the unsafe outcome; these assert what the lease must
guarantee (user priority 1: tasks complete, the box never OOMs; displaced work waits or
falls back instead of failing). Real flocks, real subprocesses and a real uvicorn where the
behaviour lives in the transport; lemonade, SurrealDB, meminfo and the cgroup are fakes.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
from email.message import Message
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from cohezion.platform import admission_proxy
from cohezion.platform import gpu_lease as gl
from cohezion.platform.admission_gate import AdmissionGate, GateConfig, probe_gpu_lease
from cohezion.platform.admission_proxy import build_app
from tests.platform.test_gpu_lease import FakeFleet
from tests.platform.test_gpu_lease_gate import FLM, _hold, _upstream, holder
from tests.platform.test_gpu_lease_review import _alive, _run_cli, _wait_file


__all__ = ["holder"]  # pytest fixture re-export

GGUF = "Gemma-4-E4B-it-GGUF"
GGUF2 = "Qwen3-4B-GGUF"
E2B = "Gemma-4-E2B-it-GGUF"
CATALOG = {
    GGUF: {"id": GGUF, "size": 5.0, "recipe": "llamacpp"},
    GGUF2: {"id": GGUF2, "size": 4.0, "recipe": "llamacpp"},
    E2B: {"id": E2B, "size": 3.0, "recipe": "llamacpp"},
    FLM: {"id": FLM, "size": 1.0, "recipe": "flm"},
}


def _mk_gate(lock: Path | None = None, **kw) -> AdmissionGate:
    args = {
        "read_resident": lambda: [],
        "read_cgroup": lambda: (0.0, 100.0),
        "read_size_gb": lambda m: CATALOG[m]["size"] if m in CATALOG else 25.0,
        "read_catalog": lambda: CATALOG,
        "read_mem_available": lambda: 200.0,
    }
    args.update(kw)
    cfg = (
        GateConfig(enforce=True) if lock is None else GateConfig(enforce=True, gpu_lease_path=lock)
    )
    gate = AdmissionGate(cfg, **args)
    gate.refresh_catalog()
    return gate


def _status_of(gate: AdmissionGate):
    """The real /admission/status shape, read live from *gate*."""
    return lambda: {
        "reserved": gate.reserved_models(),
        "in_flight": gate.in_flight(),
        "config": {"enforce": True},
        "gpu_lease": gate.lease_status(),
    }


def _serve(app) -> tuple[int, uvicorn.Server, threading.Thread]:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)
    return port, server, th


# -- 1. TOCTOU: a lease granted while a request is being decided ----------------------------


def test_gpu_load_refused_when_lease_granted_mid_decision(_isolated_gpu_lease) -> None:
    """decide() probes the lease, then reads health (slow). A lease that flocks, drains,
    unloads and grants inside that window must still see this request refused."""
    entered, release = threading.Event(), threading.Event()
    calls = {"n": 0}

    def read_resident():
        calls["n"] += 1
        if calls["n"] == 1:
            entered.set()
            release.wait(10)
        return []

    gate = _mk_gate(read_resident=read_resident)
    out: dict = {}
    t = threading.Thread(
        target=lambda: out.setdefault("d", gate.decide(GGUF, "v1/chat/completions"))
    )
    t.start()
    assert entered.wait(5)
    fleet = FakeFleet([])
    with gl.gpu_lease(
        "job", 10.0, path=_isolated_gpu_lease, io=fleet.io(admission_status=_status_of(gate))
    ):
        release.set()
        t.join(5)
        d = out["d"]
        assert not d.allow and d.kind == "gpu_lease", d
    assert gate.reserved_models() == [] and gate.in_flight() == 0


def test_lease_drain_waits_for_a_request_admitted_before_the_flock(_isolated_gpu_lease) -> None:
    """An admit decided just before the flock is in flight until the proxy forwards it; the
    drain must wait for it, whatever path admitted it (fits, resident reuse, cgroup blind)."""
    gate = _mk_gate(read_cgroup=lambda: None)  # admits with no reservation
    d = gate.decide(GGUF, "v1/chat/completions")
    assert d.allow and gate.reserved_models() == []
    assert gate.in_flight() == 1
    status = _status_of(gate)
    polls = {"n": 0}

    def drain_status():
        polls["n"] += 1
        if polls["n"] == 3:  # the proxy forwarded it and upstream answered
            gate.finish(d)
        return status()

    fleet = FakeFleet([])
    with gl.gpu_lease(
        "job", 1.0, path=_isolated_gpu_lease, io=fleet.io(admission_status=drain_status)
    ):
        assert polls["n"] >= 3


def test_resident_reuse_admit_is_in_flight() -> None:
    res = [{"model_name": GGUF, "recipe": "llamacpp", "device": "gpu"}]
    gate = _mk_gate(read_resident=lambda: res)
    d = gate.decide(GGUF, "v1/chat/completions")
    assert d.allow and d.reason.startswith("resident")
    assert gate.in_flight() == 1
    gate.finish(d)
    assert gate.in_flight() == 0


def test_lease_checked_admits_never_block_the_drain(holder) -> None:
    gate = _mk_gate(read_resident=lambda: [{"model_name": FLM, "recipe": "flm", "device": "npu"}])
    d = gate.decide(FLM, "v1/chat/completions")
    assert d.allow and gate.in_flight() == 0


# -- 2. A6 settles: a model that lands after the first census refuses the grant ---------------


def test_gpu_model_appearing_after_unload_refuses_the_grant(_isolated_gpu_lease) -> None:
    fleet = FakeFleet([{"model_name": GGUF, "device": "gpu", "recipe": "llamacpp"}])
    reads = {"n": 0}
    orig = fleet.read_resident

    def read_resident():
        reads["n"] += 1
        if reads["n"] == 3:  # after A5's unload and A6's first census: a reload lands
            fleet.resident.append({"model_name": GGUF, "device": "gpu", "recipe": "llamacpp"})
        return orig()

    with (
        pytest.raises(gl.GpuLeaseError) as ei,
        gl.gpu_lease("t", 1.0, io=fleet.io(read_resident=read_resident)),
    ):
        pass
    assert ei.value.stage == "postcondition"
    assert probe_gpu_lease(_isolated_gpu_lease) == "free"


# -- 3. CPU reuse matches the resident model exactly, never a checkpoint-stem alias -----------


def test_checkpoint_stem_alias_is_not_cpu_reuse(holder) -> None:
    mtp, base = "Gemma-4-31B-it-MTP-GGUF", "Gemma-4-31B-it-GGUF"
    cat = {
        mtp: {"id": mtp, "size": 19.0, "recipe": "llamacpp"},
        base: {"id": base, "size": 19.0, "recipe": "llamacpp"},
    }
    resident = [
        {
            "model_name": mtp,
            "recipe": "llamacpp",
            "device": "cpu",
            "checkpoint": "unsloth/gemma-4-31B-it-GGUF:Q4_K_M",
        }
    ]
    gate = _mk_gate(
        read_resident=lambda: list(resident), read_catalog=lambda: cat, read_size_gb=lambda m: 25.0
    )
    d = gate.decide(base, "v1/chat/completions", body={"model": base})
    assert not d.allow and d.kind == "gpu_lease", d
    ok = gate.decide(mtp, "v1/chat/completions", body={"model": mtp})
    assert ok.allow, ok  # the model that IS resident on the CPU is still reused


# -- 4. CPU reuse waits while a load (which may evict it) is in flight ------------------------


def test_cpu_reuse_refused_while_cpu_fallback_load_in_flight(holder) -> None:
    resident = [{"model_name": GGUF, "recipe": "llamacpp", "device": "cpu"}]
    gate = _mk_gate(read_resident=lambda: list(resident), read_cgroup=lambda: (5.0, 100.0))
    fb = gate.decide(
        GGUF2,
        "api/v1/load",
        body={"model_name": GGUF2, "llamacpp_backend": "cpu"},
        lease_exempt=GGUF2,
    )
    assert fb.allow and gate.reserved_models() == [GGUF2.lower()]
    chat = gate.decide(GGUF, "v1/chat/completions", body={"model": GGUF})
    assert not chat.allow and chat.kind == "gpu_lease", chat
    resident.append({"model_name": GGUF2, "recipe": "llamacpp", "device": "cpu"})
    time.sleep(1.6)  # past the census cache: Y landed, its reservation is gone
    assert gate.decide(GGUF, "v1/chat/completions", body={"model": GGUF}).allow


# -- 5. the enforcer must see THIS lease --------------------------------------------------


@pytest.mark.parametrize("same_path", [True, False])
def test_grant_requires_the_enforcer_to_see_the_lease(tmp_path: Path, same_path) -> None:
    lock = tmp_path / "holder-side.lock"
    gate = _mk_gate(lock if same_path else tmp_path / "gate-side.lock")
    fleet = FakeFleet([{"model_name": GGUF, "device": "gpu", "recipe": "llamacpp"}])
    granted = gpu_admitted = False
    try:
        with gl.gpu_lease("job", 10, 1, path=lock, io=fleet.io(admission_status=_status_of(gate))):
            granted = True
            gpu_admitted = gate.decide(GGUF, "v1/chat/completions").allow
    except gl.GpuLeaseError as exc:
        assert exc.stage == "enforce"
    if same_path:
        assert granted and not gpu_admitted
    else:
        assert not granted


def test_grant_refused_when_gate_reports_lease_not_held(_isolated_gpu_lease) -> None:
    io = FakeFleet([]).io(
        admission_status=lambda: {
            "reserved": [],
            "in_flight": 0,
            "config": {"enforce": True},
            "gpu_lease": {"held": False, "holder": None, "pid": None, "since": None},
        }
    )
    with pytest.raises(gl.GpuLeaseError) as ei, gl.gpu_lease("t", 1.0, 5, io=io):
        pass
    assert ei.value.stage == "enforce"
    assert probe_gpu_lease(_isolated_gpu_lease) == "free"


def test_grant_refused_when_gate_sees_another_holder(_isolated_gpu_lease) -> None:
    io = FakeFleet([]).io(
        admission_status=lambda: {
            "reserved": [],
            "in_flight": 0,
            "config": {"enforce": True},
            "gpu_lease": {"held": True, "holder": "other", "pid": os.getpid() + 1, "since": 1.0},
        }
    )
    with pytest.raises(gl.GpuLeaseError) as ei, gl.gpu_lease("t", 1.0, 5, io=io):
        pass
    assert ei.value.stage == "enforce"


# -- 6. CLI: SIGHUP / SIGQUIT stop the job tree before the lease is released -----------------


@pytest.mark.parametrize("sig", [signal.SIGHUP, signal.SIGQUIT])
def test_hangup_stops_the_job_tree_then_releases(tmp_path: Path, sig) -> None:
    gpid = tmp_path / "gpid"
    lock, p = _run_cli(tmp_path, ["sh", "-c", f"sleep 300 & echo $! > {gpid}; wait"])
    gc = int(_wait_file(gpid))
    try:
        p.send_signal(sig)
        p.wait(60)
        assert not _alive(gc), "job worker outlived the lease holder"
        assert probe_gpu_lease(lock) == "free"
        assert not lock.with_name("gpu-lease.holder.json").exists()
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.kill(gc, signal.SIGKILL)


# -- 7. mutation survivors: each lease tightening pinned -------------------------------------


def _pinned(lock, **kw):
    base = {"read_cgroup": lambda: (0.0, 30.0), "read_size_gb": lambda m: 1.0}
    base.update(kw)
    return _mk_gate(lock, **base)


def test_unreadable_cgroup_refuses_flm_load_under_lease(holder, _isolated_gpu_lease) -> None:
    g = _pinned(_isolated_gpu_lease, read_cgroup=lambda: None)
    assert not g.decide(FLM, "v1/chat/completions").allow


def test_unknown_size_refuses_flm_load_under_lease(holder, _isolated_gpu_lease) -> None:
    g = _pinned(_isolated_gpu_lease, read_size_gb=lambda m: None)
    assert not g.decide(FLM, "v1/chat/completions").allow


def test_realtime_memavailable_floor_refuses_under_lease(holder, _isolated_gpu_lease) -> None:
    # the grant leaves 174 GB spare, but MemAvailable is 16.5 GB now: 1 GB more breaks the floor
    g = _pinned(_isolated_gpu_lease, read_mem_available=lambda: 16.5)
    assert not g.decide(FLM, "v1/chat/completions").allow


def test_stale_catalog_refuses_flm_under_lease(holder, _isolated_gpu_lease) -> None:
    g = _pinned(_isolated_gpu_lease)
    g._catalog_at = time.monotonic() - 10_000  # the catalog says flm, but it is stale
    assert not g.decide(FLM, "v1/chat/completions").allow


def test_model_resident_on_cpu_and_gpu_is_not_cpu_reuse(holder, _isolated_gpu_lease) -> None:
    both = [
        {"model_name": GGUF, "device": "cpu", "recipe": "llamacpp"},
        {"model_name": GGUF, "device": "gpu", "recipe": "llamacpp"},
    ]
    assert (
        not _pinned(_isolated_gpu_lease, read_resident=lambda: both)
        .decide(GGUF, "v1/chat/completions")
        .allow
    )


def test_proxy_refuses_unnamed_unparseable_post_under_lease(holder, _isolated_gpu_lease) -> None:
    seen: list[httpx.Request] = []
    app = build_app(
        _pinned(_isolated_gpu_lease), client=_upstream(seen), lease_hold_s=0.2, lease_poll_s=0.05
    )
    with TestClient(app) as c:
        r = c.post(
            "/api/v1/load",
            content=b"model_name=Gemma-4-E4B-it-GGUF",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
    assert r.status_code == 503 and seen == [], (r.status_code, len(seen))


def test_proxy_unnamed_write_without_lease_is_tracked_until_forwarded(_isolated_gpu_lease) -> None:
    """A form-encoded load decided while the lease is free must count as in flight until it
    has been answered, or a lease granted meanwhile cannot drain it."""
    gate = _mk_gate()
    during: list[int] = []

    def upstream(req: httpx.Request) -> httpx.Response:
        during.append(gate.in_flight())
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(upstream), base_url="http://up.test")
    with TestClient(build_app(gate, client=client)) as c:
        r = c.post(
            "/api/v1/load",
            content=b"model_name=x",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
    assert r.status_code == 200 and during == [1]
    assert gate.in_flight() == 0


def test_abandoned_held_request_answers_499_and_is_counted(holder) -> None:
    seen: list[httpx.Request] = []
    gate = _mk_gate()
    app = build_app(gate, client=_upstream(seen), lease_hold_s=5.0, lease_poll_s=0.05)
    port, server, th = _serve(app)
    try:
        with contextlib.suppress(httpx.TimeoutException):
            httpx.post(
                f"http://127.0.0.1:{port}/v1/chat/completions",
                json={"model": GGUF, "messages": []},
                timeout=0.5,
            )
        holder.kill()
        holder.wait()
        time.sleep(1.5)
        status = httpx.get(f"http://127.0.0.1:{port}/admission/status", timeout=10).json()
        assert seen == []
        assert status["gpu_lease_counters"]["abandoned"] == 1
        assert status["in_flight"] == 0
    finally:
        server.should_exit = True
        th.join(5)


# -- 8. clients wait out a lease instead of failing or escalating ---------------------------


def test_local_router_client_timeout_exceeds_the_hold() -> None:
    from cohezion.inference import gaia_adapter

    assert gaia_adapter.LOCAL_ROUTER_TIMEOUT_S > admission_proxy.LEASE_HOLD_S_DEFAULT + 60


class _Refusing:
    """A chat client refused N times (lease held), then answering."""

    def __init__(self, refusals: int, exc_factory):
        self.left = refusals
        self.calls = 0
        self.exc_factory = exc_factory

    def chat_completions(self, **_kw):
        self.calls += 1
        if self.left:
            self.left -= 1
            raise self.exc_factory()
        return {"choices": [{"message": {"content": "answer"}}], "usage": {"completion_tokens": 1}}


def _http_503() -> urllib.error.HTTPError:
    hdrs = Message()
    hdrs["Retry-After"] = "15"
    hdrs["X-Cohezion-Refusal"] = "gpu_lease"
    return urllib.error.HTTPError("http://x", 503, "Service Unavailable", hdrs, None)


@pytest.mark.parametrize(
    "exc_factory",
    [
        _http_503,  # stdlib _LocalRouterClient: only the headers say why
        lambda: RuntimeError(
            "status 503: {'type': 'admission_refused', 'message': 'GPU lease held: x'}"
        ),
    ],
)
def test_shim_waits_out_a_lease_refusal_and_retries(monkeypatch, exc_factory) -> None:
    from cohezion.inference import gaia_adapter

    slept: list[float] = []
    monkeypatch.setattr(gaia_adapter, "_lease_sleep", slept.append)
    client = _Refusing(2, exc_factory)
    shim = gaia_adapter._GaiaLLMClientShim(client, GGUF, max_tokens=8, temperature=0.7)
    assert shim.prompt("hi") == "answer"
    assert client.calls == 3 and slept == [15.0, 15.0]


def test_shim_does_not_retry_other_errors(monkeypatch) -> None:
    from cohezion.inference import gaia_adapter

    monkeypatch.setattr(gaia_adapter, "_lease_sleep", lambda s: pytest.fail("slept"))
    client = _Refusing(1, lambda: RuntimeError("status 503: cgroup headroom"))
    shim = gaia_adapter._GaiaLLMClientShim(client, GGUF, max_tokens=8, temperature=0.7)
    with pytest.raises(RuntimeError):
        shim.prompt("hi")
    assert client.calls == 1


def test_shim_lease_wait_is_bounded(monkeypatch) -> None:
    from cohezion.inference import gaia_adapter

    monkeypatch.setenv("COHEZION_GPU_LEASE_CLIENT_WAIT_S", "40")
    monkeypatch.setattr(gaia_adapter, "_lease_sleep", lambda s: None)
    client = _Refusing(10**6, _http_503)
    shim = gaia_adapter._GaiaLLMClientShim(client, GGUF, max_tokens=8, temperature=0.7)
    with pytest.raises(urllib.error.HTTPError):
        shim.prompt("hi")
    assert client.calls == 3  # two 15 s waits (30 s); a third would pass the 40 s budget


def test_triune_cascade_task_completes_when_the_lease_ends(
    _isolated_gpu_lease, monkeypatch
) -> None:
    """Displaced GGUF tiers wait for the lease instead of failing the task."""
    from cohezion.inference import gaia_adapter

    proc = _hold(_isolated_gpu_lease)
    _isolated_gpu_lease.with_name("gpu-lease.holder.json").write_text(
        json.dumps(
            {"holder": "t", "pid": proc.pid, "since": 1.0, "need_gb": 10, "grant_mem_gb": 200}
        )
    )
    waits: list[float] = []

    def short_sleep(s: float) -> None:
        waits.append(s)
        if proc.poll() is None:
            proc.kill()  # the lease ends while the client waits
            proc.wait()
        time.sleep(0.2)

    monkeypatch.setattr(gaia_adapter, "_lease_sleep", short_sleep)
    forwarded: list[str] = []

    def upstream(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content or b"{}")
        model = body.get("model", req.url.path)
        forwarded.append(model)
        text = "OK" if model == FLM else "A long answer about memory hierarchies. " * 40
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}
                ],
                "usage": {"completion_tokens": 1},
            },
        )

    gate = _mk_gate(read_resident=lambda: [{"model_name": FLM, "recipe": "flm", "device": "npu"}])
    app = build_app(
        gate,
        client=httpx.AsyncClient(transport=httpx.MockTransport(upstream), base_url="http://up"),
        lease_hold_s=0.5,
        lease_poll_s=0.1,
    )
    port, server, th = _serve(app)
    try:
        from cohezion.inference.triune_orchestrator import build_triune_omni_orchestrator

        orch = build_triune_omni_orchestrator(base_url=f"http://127.0.0.1:{port}/api/v1")
        result = asyncio.run(orch.run("Write a detailed 2000-word essay on memory hierarchies."))
    finally:
        server.should_exit = True
        th.join(5)
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    assert waits, "the client never waited on the lease"
    assert GGUF in forwarded, forwarded
    assert result.text and not result.error, (result.error, forwarded)


def _swarm():
    import importlib.util

    path = Path(__file__).parents[2] / "scripts" / "research_swarm.py"
    spec = importlib.util.spec_from_file_location("research_swarm_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod  # its dataclasses resolve their module at class creation
    spec.loader.exec_module(mod)
    return mod


def test_research_swarm_lemonade_query_waits_out_a_lease(monkeypatch) -> None:
    swarm = _swarm()
    runs: list[list[str]] = []

    def fake_run(cmd, **_kw):
        runs.append(cmd)
        if len(runs) == 1:
            return subprocess.CompletedProcess(
                cmd, 1, "", "status 503 GPU lease held: x is not an FLM"
            )
        if len(runs) == 2:  # the real `gaia llm` shape: exit 0, refusal logged on stdout
            out = "ERROR | Error in chat completions (status 503): GPU lease held: x"
            return subprocess.CompletedProcess(cmd, 0, out, "Lemonade server is not running")
        return subprocess.CompletedProcess(cmd, 0, "the answer", "")

    slept: list[float] = []
    monkeypatch.setattr(swarm.subprocess, "run", fake_run)
    monkeypatch.setattr(swarm.time, "sleep", slept.append)
    assert swarm.lemonade_query(GGUF, "q") == (True, "the answer")
    assert len(runs) == 3 and slept == [15.0, 15.0]


def test_research_swarm_lemonade_query_other_failure_not_retried(monkeypatch) -> None:
    swarm = _swarm()
    runs: list = []
    monkeypatch.setattr(
        swarm.subprocess,
        "run",
        lambda cmd, **k: runs.append(cmd) or subprocess.CompletedProcess(cmd, 1, "", "boom"),
    )
    monkeypatch.setattr(swarm.time, "sleep", lambda s: pytest.fail("slept"))
    assert swarm.lemonade_query(GGUF, "q") == (False, "boom")
    assert len(runs) == 1
