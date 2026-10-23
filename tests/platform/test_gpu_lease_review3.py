"""Third adversarial review of the GPU lease (against dffb62f5c), each finding pinned as the
SAFE behaviour. The reviewer's executed counterexamples, inverted.

User priority 1: tasks COMPLETE (no OOM, no failed or cloud-escalated fleet work). Real
flocks, real subprocesses and a real uvicorn where the behaviour lives in the transport;
lemonade, SurrealDB, meminfo and the cgroup are fakes.
"""

from __future__ import annotations

import asyncio
import contextlib
import fcntl
import json
import logging
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from cohezion.platform import admission_proxy
from cohezion.platform import gpu_lease as gl
from cohezion.platform.admission_gate import LEASE_FREE, LEASE_HELD, probe_gpu_lease
from cohezion.platform.admission_proxy import build_app
from tests.platform.test_gpu_lease import FakeFleet
from tests.platform.test_gpu_lease_gate import FLM, _hold, holder
from tests.platform.test_gpu_lease_review import _run_cli, _wait_file
from tests.platform.test_gpu_lease_review2 import CATALOG, GGUF, _mk_gate, _serve


__all__ = ["holder"]  # pytest fixture re-export

SDCPP = "SD-Turbo"


def _kill(pid: int) -> None:
    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, signal.SIGKILL)


def _flocked(path: Path) -> bool:
    """True when some process holds LOCK_EX on the file at *path* right now."""
    fd = os.open(path, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        return False
    except BlockingIOError:
        return True
    finally:
        os.close(fd)


# -- 1. release really releases: no process sharing the lock fd keeps the lease ------------


def test_library_release_frees_lease_despite_forked_child(_isolated_gpu_lease, caplog) -> None:
    """A library holder that forked (multiprocessing 'fork' workers) shares the locked open
    file description; os.close alone left the flock HELD for a lease nobody holds."""
    caplog.set_level(logging.WARNING, logger=gl.__name__)
    with gl.gpu_lease("t", 1.0, io=FakeFleet([]).io()):
        child = os.fork()
        if child == 0:  # pragma: no cover - child
            time.sleep(5)
            os._exit(0)
    try:
        assert probe_gpu_lease(_isolated_gpu_lease) == LEASE_FREE
        assert any(str(child) in r.getMessage() for r in caplog.records), "holder not logged"
    finally:
        _kill(child)
        os.waitpid(child, 0)


def test_cli_job_never_inherits_the_lease(tmp_path: Path) -> None:
    """A job descendant that setsid()s escapes the group kill; it must not keep the lease."""
    pidf = tmp_path / "escapee.pid"
    lock, p = _run_cli(
        tmp_path,
        [
            "sh",
            "-c",
            f"setsid sleep 60 >/dev/null 2>&1 </dev/null & echo $! > {pidf}; sleep 0.5",
        ],  # escapee setsid()s before the group kill
    )
    assert p.wait(120) == 0
    esc = int(_wait_file(pidf))
    try:
        assert probe_gpu_lease(lock) == LEASE_FREE, "holder exited rc=0 but lease still HELD"
        assert not lock.with_name("gpu-lease.holder.json").exists()
    finally:
        _kill(esc)


# -- 2. a deleted lock file never reads as a free GPU ---------------------------------------


def test_lock_file_deleted_while_held_still_refuses_gpu(_isolated_gpu_lease) -> None:
    gate = _mk_gate()
    with gl.gpu_lease("t", 1.0, io=FakeFleet([]).io()):
        assert not gate.decide(GGUF, "v1/chat/completions").allow
        _isolated_gpu_lease.unlink()
        d = gate.decide(GGUF, "v1/chat/completions")
        assert not d.allow and d.kind == "gpu_lease", d.reason


def test_missing_lock_with_dead_holders_sidecar_is_free(_isolated_gpu_lease) -> None:
    """A SIGKILLed holder leaves its sidecar behind: that must not lock the GPU forever."""
    dead = subprocess.Popen(["true"])
    dead.wait()
    _isolated_gpu_lease.with_name("gpu-lease.holder.json").write_text(
        json.dumps({"holder": "t", "pid": dead.pid, "since": 1.0, "lock": str(_isolated_gpu_lease)})
    )
    assert probe_gpu_lease(_isolated_gpu_lease) == LEASE_FREE


def test_missing_lock_with_another_locks_live_sidecar_is_free(tmp_path) -> None:
    """The sidecar name is per directory: a live holder of ANOTHER lock path must not make
    this missing lock read HELD (and so a gate on the wrong path must not see a lease)."""
    other = tmp_path / "other.lock"
    other.with_name("gpu-lease.holder.json").write_text(
        json.dumps({"holder": "t", "pid": os.getpid(), "since": 1.0, "lock": str(other)})
    )
    assert probe_gpu_lease(tmp_path / "gpu-lease.lock") == LEASE_FREE


def test_watchdog_recreates_and_relocks_a_deleted_lock(_isolated_gpu_lease, monkeypatch) -> None:
    monkeypatch.setattr(gl, "WATCHDOG_S", 0.05)
    fleet = FakeFleet([])
    side = _isolated_gpu_lease.with_name("gpu-lease.holder.json")
    with gl.gpu_lease("t", 1.0, io=fleet.io()):
        _isolated_gpu_lease.unlink()  # e.g. the whole .cache wiped: sidecar gone too
        side.unlink()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not (
            _isolated_gpu_lease.exists() and _flocked(_isolated_gpu_lease) and side.exists()
        ):
            time.sleep(0.05)
        assert _flocked(_isolated_gpu_lease), "lock file not recreated and re-locked"
        assert json.loads(side.read_text())["pid"] == os.getpid()
        assert "gpu_lease_lock_recreated" in [t for t, _ in fleet.events]
    assert probe_gpu_lease(_isolated_gpu_lease) == LEASE_FREE  # and release frees the new one


# -- 3. in flight = admits that can map NEW memory, never resident reuse ---------------------


def test_resident_reuse_generation_does_not_block_the_drain() -> None:
    """A long chat to an already-resident model must not hold the lease's drain (A2 gives
    up after DRAIN_MAX_S): reuse maps nothing new."""
    res = [{"model_name": GGUF, "device": "gpu", "recipe": "llamacpp"}]
    gate = _mk_gate(read_resident=lambda: res)
    release = threading.Event()
    seen: list[int] = []

    async def slow(request: httpx.Request) -> httpx.Response:
        seen.append(gate.in_flight())
        await asyncio.get_running_loop().run_in_executor(None, release.wait, 5)
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(slow), base_url="http://up")
    with TestClient(build_app(gate, client=client)) as tc:
        t = threading.Thread(
            target=lambda: tc.post("/v1/chat/completions", json={"model": GGUF, "stream": False})
        )
        t.start()
        time.sleep(1.0)
        during = gate.in_flight()
        release.set()
        t.join()
    assert seen == [0] and during == 0, (seen, during)


def test_reuse_from_stale_residency_stays_in_flight() -> None:
    """'Resident' from the 60 s last-good cache may be a model already gone: forwarding can
    auto-load it, so that admit is still drained."""
    answers = [[{"model_name": GGUF, "device": "gpu", "recipe": "llamacpp"}]]
    gate = _mk_gate(read_resident=lambda: answers[-1])
    fresh = gate.decide(GGUF, "v1/chat/completions")
    assert fresh.allow and gate.in_flight() == 0
    answers.append(None)  # health blocked (a load is under way)
    gate._resident_cache = None
    stale = gate.decide(GGUF, "v1/chat/completions")
    assert stale.allow and stale.reason.startswith("resident") and gate.in_flight() == 1
    gate.finish(stale)
    assert gate.in_flight() == 0


# -- 4. implicit loads under a held lease run on the CPU instead of failing the task --------


class _Lemond:
    """A stateful fake lemond: an /api/v1/load with llamacpp_backend=cpu makes the model
    resident on the CPU, which /health (the gate's census) then reports."""

    def __init__(self, resident: list[dict] | None = None, load_ok: bool = True) -> None:
        self.resident: list[dict] = list(resident or [])
        self.seen: list[httpx.Request] = []
        self.load_ok = load_ok

    def census(self) -> list[dict]:
        return list(self.resident)

    async def handle(self, request: httpx.Request) -> httpx.Response:
        self.seen.append(request)
        if request.url.path.endswith("/load"):
            await asyncio.sleep(0.2)  # a load takes a while
            if not self.load_ok:
                return httpx.Response(500, json={"error": "load failed"})
            body = json.loads(request.content)
            if body.get("llamacpp_backend") == "cpu" and not any(
                e["model_name"] == body["model_name"] for e in self.resident
            ):
                self.resident.append(
                    {"model_name": body["model_name"], "recipe": "llamacpp", "device": "cpu"}
                )
            return httpx.Response(200, json={"status": "success"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "local"}}]})

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handle), base_url="http://u")


def _gate_for(lemond: _Lemond, **kw):
    cat = {**CATALOG, SDCPP: {"id": SDCPP, "size": 6.0, "recipe": "sd-cpp"}}
    args = {"read_resident": lemond.census, "read_catalog": lambda: cat}
    args.update(kw)
    return _mk_gate(**args)


def test_chat_to_non_resident_gguf_loads_on_cpu_then_serves(holder) -> None:
    lemond = _Lemond()
    app = build_app(_gate_for(lemond), client=lemond.client(), lease_hold_s=0.3)
    chat = json.dumps({"model": GGUF, "messages": [{"role": "user", "content": "hi"}]})
    with TestClient(app) as c:
        r = c.post(
            "/api/v1/chat/completions",
            content=chat,
            headers={"content-type": "application/json"},
        )
    assert r.status_code == 200, r.text
    paths = [q.url.path for q in lemond.seen]
    assert paths == ["/api/v1/load", "/api/v1/chat/completions"], paths
    assert json.loads(lemond.seen[0].content) == {
        "model_name": GGUF,
        "llamacpp_backend": "cpu",
        "save_options": False,
    }
    assert lemond.seen[1].content == chat.encode()  # the original request, unchanged


@pytest.mark.parametrize(
    ("model", "resident", "working_set"),
    [
        (GGUF, [], 26.0),  # the CPU budget cannot fit the full footprint
        (SDCPP, [], 0.0),  # not a llamacpp recipe: no CPU placement to fall back to
        (GGUF, [{"model_name": GGUF, "recipe": "llamacpp", "device": "gpu"}], 0.0),
    ],
)
def test_no_implicit_fallback_holds_then_503(holder, model, resident, working_set) -> None:
    lemond = _Lemond(resident)
    gate = _gate_for(lemond, read_cgroup=lambda: (working_set, 30.0))
    app = build_app(gate, client=lemond.client(), lease_hold_s=0.3, lease_poll_s=0.05)
    with TestClient(app) as c:
        r = c.post("/v1/chat/completions", json={"model": model, "messages": []})
    assert r.status_code == 503 and r.headers["X-Cohezion-Refusal"] == "gpu_lease"
    assert lemond.seen == []


def test_implicit_fallback_with_backend_override_is_not_attempted(holder) -> None:
    lemond = _Lemond()
    app = build_app(_gate_for(lemond), client=lemond.client(), lease_hold_s=0.3)
    with TestClient(app) as c:
        r = c.post(
            "/v1/chat/completions",
            json={"model": GGUF, "messages": [], "llamacpp_backend": "vulkan"},
        )
    assert r.status_code == 503 and lemond.seen == []


@pytest.mark.parametrize("load_ok", [True, False])
def test_unproven_cpu_placement_is_never_forwarded(holder, load_ok) -> None:
    """The load answered 200 but /health does not show the model on the CPU (or the load
    failed): the original request is not forwarded blind, it holds and then 503s."""
    lemond = _Lemond(load_ok=load_ok)
    gate = _gate_for(lemond, read_resident=lambda: [])
    app = build_app(gate, client=lemond.client(), lease_hold_s=0.5, lease_poll_s=0.05)
    with TestClient(app) as c:
        r = c.post("/v1/chat/completions", json={"model": GGUF, "messages": []})
    assert r.status_code == 503
    assert [q.url.path for q in lemond.seen if not q.url.path.endswith("/load")] == []
    loads = [q for q in lemond.seen if q.url.path.endswith("/load")]
    assert len(loads) == 1  # attempted once per request, not on every hold poll
    if not load_ok:  # a failed load frees its reservation; an unproven one keeps it (safe)
        assert gate.reserved_models() == []


def test_concurrent_chats_issue_one_cpu_load(holder) -> None:
    lemond = _Lemond()
    app = build_app(_gate_for(lemond), client=lemond.client(), lease_hold_s=5.0)
    port, server, th = _serve(app)
    codes: list[int] = []

    def chat() -> None:
        r = httpx.post(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            json={"model": GGUF, "messages": []},
            timeout=20,
        )
        codes.append(r.status_code)

    try:
        ts = [threading.Thread(target=chat) for _ in range(3)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
    finally:
        server.should_exit = True
        th.join(5)
    assert codes == [200, 200, 200], codes
    assert [q.url.path for q in lemond.seen].count("/api/v1/load") == 1


def test_local_executor_completes_under_lease_within_its_timeout(holder) -> None:
    """local_executor escalates to the cloud after its timeout (90 s vs the old 120 s hold).
    Scaled: a 2 s client timeout against a 3 s hold must still get the local answer."""
    from cohezion.compound.autonomous_loop import local_executor as le

    lemond = _Lemond()
    app = build_app(_gate_for(lemond), client=lemond.client(), lease_hold_s=3.0)
    port, server, th = _serve(app)
    try:
        out = le._chat_complete(f"http://127.0.0.1:{port}", GGUF, "hi", timeout=2.0)
    finally:
        server.should_exit = True
        th.join(5)
    assert out["choices"][0]["message"]["content"] == "local"


def test_default_hold_is_below_the_shortest_client_timeout() -> None:
    assert admission_proxy.LEASE_HOLD_S_DEFAULT == 60.0  # research_daemon/local_executor: 90 s


def test_flm_still_served_and_explicit_load_fallback_unchanged(holder) -> None:
    lemond = _Lemond([{"model_name": FLM, "recipe": "flm", "device": "npu"}])
    app = build_app(_gate_for(lemond), client=lemond.client(), lease_hold_s=0.3)
    with TestClient(app) as c:
        assert c.post("/v1/chat/completions", json={"model": FLM, "messages": []}).is_success
        r = c.post("/api/v1/load", json={"model_name": GGUF, "ctx_size": 4096})
    assert r.status_code == 200
    sent = json.loads(lemond.seen[-1].content)
    assert sent == {
        "model_name": GGUF,
        "ctx_size": 4096,
        "llamacpp_backend": "cpu",
        "save_options": False,
    }


# -- 5. the client wait budget bounds WALL time, proxy holds included -------------------------


def test_shim_wait_budget_bounds_wall_time(_isolated_gpu_lease, monkeypatch) -> None:
    from cohezion.inference import gaia_adapter

    proc = _hold(_isolated_gpu_lease)
    _isolated_gpu_lease.with_name("gpu-lease.holder.json").write_text(
        json.dumps(
            {"holder": "t", "pid": proc.pid, "since": 1.0, "need_gb": 10, "grant_mem_gb": 200}
        )
    )
    monkeypatch.setenv("COHEZION_GPU_LEASE_CLIENT_WAIT_S", "3")
    monkeypatch.setattr(gaia_adapter, "_LEASE_RETRY_AFTER_S", 1.0)
    monkeypatch.setattr(admission_proxy, "RETRY_AFTER_S", 1)
    # SD-Turbo is not llamacpp: the proxy holds it (2 s) and then refuses.
    lemond = _Lemond()
    app = build_app(_gate_for(lemond), client=lemond.client(), lease_hold_s=2.0)
    port, server, th = _serve(app)
    try:
        c = gaia_adapter._LocalRouterClient(base_url=f"http://127.0.0.1:{port}/api/v1", model=SDCPP)
        shim = gaia_adapter._GaiaLLMClientShim(c, SDCPP, max_tokens=8, temperature=0.7)
        t0 = time.monotonic()
        with pytest.raises(Exception):  # noqa: B017 - the refusal, whatever its client type
            shim.prompt("hi")
        wall = time.monotonic() - t0
    finally:
        server.should_exit = True
        th.join(5)
        proc.kill()
        proc.wait()
    assert wall <= 3 + 2.5, f"wall {wall:.1f}s exceeds budget 3s + one hold"


def test_shim_reports_a_long_lease_wait_once(monkeypatch) -> None:
    from cohezion.inference import gaia_adapter
    from tests.platform.test_gpu_lease_review2 import _http_503, _Refusing

    clock = [0.0]
    monkeypatch.setattr(gaia_adapter.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        gaia_adapter, "_lease_sleep", lambda s: clock.__setitem__(0, clock[0] + 400.0)
    )
    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(gaia_adapter, "_publish_long_wait", lambda t, p: events.append((t, p)))
    shim = gaia_adapter._GaiaLLMClientShim(
        _Refusing(4, _http_503), GGUF, max_tokens=8, temperature=0.7
    )
    assert shim.prompt("hi") == "answer"
    assert [t for t, _ in events] == ["gpu_lease_client_wait_long"]
    assert events[0][1]["model"] == GGUF and events[0][1]["waited_s"] > 600


def test_research_swarm_wait_budget_counts_wall_time(monkeypatch) -> None:
    from tests.platform.test_gpu_lease_review2 import _swarm

    swarm = _swarm()
    clock = [0.0]
    runs: list = []

    def slow_refusal(cmd, **_kw):  # each `gaia llm` call is held by the proxy for an hour
        runs.append(cmd)
        clock[0] += 3600.0
        return subprocess.CompletedProcess(cmd, 0, "status 503: GPU lease held: x", "")

    events: list[str] = []
    monkeypatch.setattr(swarm.subprocess, "run", slow_refusal)
    monkeypatch.setattr(swarm.time, "sleep", lambda s: None)
    monkeypatch.setattr(swarm.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(swarm, "_publish_long_wait", lambda t, p: events.append(t))
    ok, _ = swarm.lemonade_query(GGUF, "q")
    assert not ok
    assert len(runs) <= 7, f"{len(runs)} hour-long holds against a 6 h budget"
    assert events == ["gpu_lease_client_wait_long"]


def test_long_wait_event_is_tallied_by_the_consumer() -> None:
    from cohezion.data_mesh.event_consumer import GPU_LEASE_EVENT_TYPES

    assert "gpu_lease_client_wait_long" in GPU_LEASE_EVENT_TYPES


__all__ += ["LEASE_HELD"]
