"""Fourth adversarial review of the GPU lease (against 286f7fd6d): the reviewer's executed
counterexamples, inverted into the SAFE behaviour.

User priority 1: tasks COMPLETE (no OOM, no failed or cloud-escalated fleet work).
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import textwrap
import threading
import time
import urllib.error

import httpx
import pytest
from fastapi.testclient import TestClient

from cohezion.platform import gpu_lease as gl
from cohezion.platform.admission_gate import LEASE_FREE, LEASE_HELD, probe_gpu_lease
from cohezion.platform.admission_proxy import build_app
from tests.platform.test_gpu_lease import FakeFleet
from tests.platform.test_gpu_lease_gate import holder
from tests.platform.test_gpu_lease_review2 import GGUF, _http_503, _mk_gate, _status_of, _swarm
from tests.platform.test_gpu_lease_review3 import _gate_for, _Lemond


__all__ = ["holder"]  # pytest fixture re-export

_TAKE_AND_DIE = """
import fcntl, os, sys, time
fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o644)
fcntl.flock(fd, fcntl.LOCK_EX)
st = os.fstat(fd)
print(f"{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}:{st.st_ino}", flush=True)
time.sleep(60)
"""


def _dead_holders_lock_id(path) -> str:
    """The lock id a real holder recorded before it was SIGKILLed (sidecar left behind)."""
    p = subprocess.Popen([sys.executable, "-c", _TAKE_AND_DIE, str(path)], stdout=subprocess.PIPE)
    assert p.stdout is not None
    lock_id = p.stdout.readline().decode().strip()
    p.send_signal(signal.SIGKILL)
    p.wait()
    return lock_id


def _sidecar(path, **info) -> None:
    path.with_name("gpu-lease.holder.json").write_text(
        json.dumps({"holder": "dead", "since": 1.0, "lock": str(path), **info})
    )


# -- 1. a waiting acquirer never recreates a lock file deleted under a live holder -----------


def test_waiting_acquirer_recreating_deleted_lock_makes_gate_free(_isolated_gpu_lease, monkeypatch):
    monkeypatch.setattr(gl, "WATCHDOG_S", 3600)  # the holder's watchdog has not fired yet
    p = _isolated_gpu_lease
    gate = _mk_gate()
    with gl.gpu_lease("H", 1.0, io=FakeFleet([]).io()):
        p.unlink()
        assert probe_gpu_lease(p) == LEASE_HELD
        code = textwrap.dedent(f"""
            import time, pathlib
            from cohezion.platform import gpu_lease as gl
            class IO:
                clock = staticmethod(time.monotonic); sleep = staticmethod(time.sleep)
            try:
                gl._flock(pathlib.Path({str(p)!r}), 3.0, IO())
                print("ACQUIRED")
            except gl.GpuLeaseError as e:
                print("TIMEOUT", e)
        """)
        b = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
        time.sleep(1.5)
        during = probe_gpu_lease(p)
        out = b.communicate(timeout=30)[0]
        after = probe_gpu_lease(p)
        gate._resident_cache = None
        d = gate.decide(GGUF, "v1/chat/completions")
        assert out.startswith("TIMEOUT"), out
        assert during == LEASE_HELD and after == LEASE_HELD and not d.allow, d.reason


def test_lock_file_recreated_by_someone_else_under_live_holder_reads_held(
    _isolated_gpu_lease, monkeypatch
) -> None:
    monkeypatch.setattr(gl, "WATCHDOG_S", 3600)
    p = _isolated_gpu_lease
    with gl.gpu_lease("H", 1.0, io=FakeFleet([]).io()):
        p.unlink()
        p.touch()  # a fresh, unlocked inode at the path the gate probes
        assert probe_gpu_lease(p) == LEASE_HELD
    assert probe_gpu_lease(p) == LEASE_FREE


# -- 2. a stale sidecar never wedges the lease -----------------------------------------------


def test_stale_sidecar_with_live_foreign_pid_blocks_acquire(_isolated_gpu_lease) -> None:
    """A SIGKILLed holder's sidecar whose pid is now someone else's (pid 1: EPERM)."""
    p = _isolated_gpu_lease
    p.touch()
    _sidecar(p, pid=1)
    assert probe_gpu_lease(p) == LEASE_FREE
    with gl.gpu_lease("new", 1.0, acquire_timeout_s=3, io=FakeFleet([]).io()):
        pass
    p.unlink()
    _sidecar(p, pid=1)
    assert probe_gpu_lease(p) == LEASE_FREE


def test_dead_holders_sidecar_with_missing_lock_is_free_and_acquirable(_isolated_gpu_lease):
    p = _isolated_gpu_lease
    lock_id = _dead_holders_lock_id(p)
    p.unlink()
    _sidecar(p, pid=1, lock_id=lock_id, pidns=gl._pidns())
    assert probe_gpu_lease(p) == LEASE_FREE
    with gl.gpu_lease("new", 1.0, acquire_timeout_s=3, io=FakeFleet([]).io()):
        assert probe_gpu_lease(p) == LEASE_HELD


def test_holder_from_another_pid_namespace(_isolated_gpu_lease, monkeypatch) -> None:
    """A sandboxed holder's pid and lock are invisible from a nested namespace: unknown is
    HELD there, but the host gate (init namespace) sees every lock and reads a dead one FREE,
    and an acquirer stops waiting once a live holder's watchdog would have recreated it."""
    p = _isolated_gpu_lease
    lock_id = _dead_holders_lock_id(p)
    p.unlink()
    _sidecar(p, pid=5, lock_id=lock_id, pidns=1)
    assert probe_gpu_lease(p) == LEASE_HELD  # cannot tell from here: tighten
    monkeypatch.setattr(gl, "_INIT_PIDNS", gl._pidns())  # read as the host gate
    assert probe_gpu_lease(p) == LEASE_FREE
    monkeypatch.undo()
    monkeypatch.setenv("COHEZION_GPU_LEASE_PATH", str(p))
    monkeypatch.setattr(gl, "WATCHDOG_S", 0.5)
    with gl.gpu_lease("new", 1.0, acquire_timeout_s=5, io=FakeFleet([]).io()):
        assert probe_gpu_lease(p) == LEASE_HELD


# -- 3. the lease never unloads a model under a generation that has not finished ----------


@pytest.mark.parametrize("stream", [False, True])
def test_lease_unloads_model_under_an_unfinished_chat(_isolated_gpu_lease, stream) -> None:
    fleet = FakeFleet([{"model_name": GGUF, "device": "gpu", "recipe": "llamacpp"}])
    gate = _mk_gate(read_resident=fleet.read_resident)
    chat_open, release, done = threading.Event(), threading.Event(), threading.Event()
    unloaded_mid_chat: list[bool] = []

    async def body():
        yield b"data: 1\n\n"
        await asyncio.get_running_loop().run_in_executor(None, release.wait, 10)
        yield b"data: [DONE]\n\n"

    async def slow(request: httpx.Request) -> httpx.Response:
        chat_open.set()
        if stream:
            return httpx.Response(200, content=body())
        await asyncio.get_running_loop().run_in_executor(None, release.wait, 10)
        return httpx.Response(200, json={"ok": True})

    def unload(m: str) -> bool:
        unloaded_mid_chat.append(not done.is_set())
        return fleet.unload(m)

    def sleep(_s: float) -> None:  # the lease waits: the generation finishes meanwhile
        release.set()
        done.wait(10)

    client = httpx.AsyncClient(transport=httpx.MockTransport(slow), base_url="http://up")
    with TestClient(build_app(gate, client=client)) as tc:

        def chat() -> None:
            tc.post("/v1/chat/completions", json={"model": GGUF, "stream": stream})
            time.sleep(0.2)  # the response's background task (stream end) has run
            done.set()

        t = threading.Thread(target=chat)
        t.start()
        assert chat_open.wait(5)
        time.sleep(0.3)
        io = fleet.io(admission_status=_status_of(gate), unload=unload, sleep=sleep)
        with gl.gpu_lease("job", 1.0, io=io):
            pass
        release.set()
        t.join(10)
    assert unloaded_mid_chat == [False]
    assert gate.in_use() == {}


# -- 4. CPU placement is proven without lemond's device label --------------------------------


class _GpuLabelLemond(_Lemond):
    """lemond 2026.41 logs a llamacpp_backend=cpu load as 'device: gpu' (the label follows
    the model type, not the backend); /health carries the backend process's pid and url."""

    def __init__(self) -> None:
        super().__init__()
        self.pid = 4242

    async def handle(self, request: httpx.Request) -> httpx.Response:
        resp = await super().handle(request)
        for e in self.resident:
            e.setdefault("pid", self.pid)
            e.setdefault("backend_url", f"http://127.0.0.1:{8000 + e['pid'] % 100}")
            e["device"] = "gpu"
        return resp


@pytest.mark.parametrize("explicit", [False, True])
def test_cpu_load_labelled_gpu_still_serves_the_task(holder, explicit) -> None:
    lemond = _GpuLabelLemond()
    app = build_app(_gate_for(lemond), client=lemond.client(), lease_hold_s=0.5)
    with TestClient(app) as c:
        if explicit:
            assert c.post("/api/v1/load", json={"model_name": GGUF}).status_code == 200
        r = c.post("/v1/chat/completions", json={"model": GGUF, "messages": []})
        assert r.status_code == 200, r.text
        # The instance is replaced (evicted, reloaded by anyone, anywhere): proof is gone.
        lemond.resident[0]["pid"] = 999
        r2 = c.post("/v1/chat/completions", json={"model": GGUF, "messages": []})
    assert r2.status_code == 503
    assert [q.url.path for q in lemond.seen].count("/v1/chat/completions") == 1


# -- 5. local_executor waits out a lease refusal instead of failing the task --------------


def test_local_executor_retries_a_lease_503(monkeypatch) -> None:
    from cohezion.compound.autonomous_loop import local_executor as le

    calls: list[int] = []

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "local"}}]}).encode()

    def urlopen(req, timeout=None):
        calls.append(1)
        if len(calls) <= 2:
            raise _http_503()
        return _Resp()

    monkeypatch.setattr(le.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(le.time, "sleep", lambda _s: None)
    out = le._chat_complete("http://x", GGUF, "hi")
    assert out["choices"][0]["message"]["content"] == "local" and len(calls) == 3


def test_local_executor_non_lease_503_still_raises(monkeypatch) -> None:
    from cohezion.compound.autonomous_loop import local_executor as le

    def urlopen(req, timeout=None):
        raise urllib.error.HTTPError("http://x", 503, "busy", None, None)  # type: ignore[arg-type]

    monkeypatch.setattr(le.urllib.request, "urlopen", urlopen)
    with pytest.raises(urllib.error.HTTPError):
        le._chat_complete("http://x", GGUF, "hi")


# -- 6. research_swarm never takes gaia's error log for an answer -------------------------


def test_lemonade_query_error_log_on_exit_0_is_a_failure(monkeypatch) -> None:
    swarm = _swarm()
    log = (
        "2026-10-23 18:06:01 | ERROR | gaia.llm.lemonade_client._load_model_leased | Failed to "
        "load Gemma-4-E4B-it-GGUF: Request failed with status 503 ... lemond cgroup headroom: "
        "26.0GB working set + 0.0GB reserved - 0.0GB NPU swap + 5.0GB = 31.0GB > 27.0GB"
    )
    monkeypatch.setattr(
        swarm.subprocess, "run", lambda cmd, **_kw: subprocess.CompletedProcess(cmd, 0, log, "")
    )
    ok, out = swarm.lemonade_query(GGUF, "q")
    assert not ok and "503" in out


def test_proxy_docs_do_not_claim_clients_retry_the_lease_marker() -> None:
    from cohezion.platform import admission_proxy

    src = open(admission_proxy.__file__).read()  # noqa: SIM115
    assert "retry a 503 with the lease marker" not in src
    assert os.path.exists(admission_proxy.__file__)


def test_client_leaving_mid_stream_releases_the_model() -> None:
    """A client that hangs up mid-generation must not leave its model 'in use' (for
    IN_USE_TTL_S every lease naming it as a victim would fail its drain)."""
    from tests.platform.test_gpu_lease_review2 import _serve

    gate = _mk_gate(read_resident=lambda: [{"model_name": GGUF, "device": "gpu"}])
    release = threading.Event()

    async def body():
        yield b"data: 1\n\n"
        await asyncio.get_running_loop().run_in_executor(None, release.wait, 10)
        yield b"data: [DONE]\n\n"

    async def up(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body())

    client = httpx.AsyncClient(transport=httpx.MockTransport(up), base_url="http://up")
    port, server, th = _serve(build_app(gate, client=client))
    try:
        with httpx.stream(
            "POST", f"http://127.0.0.1:{port}/v1/chat/completions", json={"model": GGUF}
        ) as r:
            next(r.iter_raw())
            assert gate.in_use() == {GGUF.lower(): 1}
        deadline = time.monotonic() + 5
        while gate.in_use() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert gate.in_use() == {}
    finally:
        release.set()
        server.should_exit = True
        th.join(5)
