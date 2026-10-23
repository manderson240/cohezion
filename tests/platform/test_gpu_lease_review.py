"""Adversarial-review findings on the GPU lease, each pinned as the SAFE behaviour.

Most tests reproduce a review finding against 66ce8526e (the reviewers' counterexamples,
inverted to assert what the lease must guarantee: user priority 1, the box never OOMs, and
displaced work that waits or falls back instead of failing). Run against that revision
they fail, but partly for an incidental reason: the shared ``_gate`` helper now injects
``read_mem_available``, which that revision's gate does not accept. Two tests pin spec
behaviour rather than a defect: ``test_chat_to_non_resident_gguf_still_waits_then_503``
(no fallback on non-load routes) and ``test_npu_swaps_never_exhaust_the_lease_bound``.
``test_hold_polls_the_lease_not_the_gate`` exists to kill the busy-spin mutant of the hold
loop and was run against it. Real flocks, real subprocesses, real uvicorn where the
behaviour lives in the transport; lemonade, SurrealDB, meminfo and the cgroup are fakes.
"""

from __future__ import annotations

import contextlib
import json
import os
import signal
import socket
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from cohezion.platform import gpu_lease as gl
from cohezion.platform.admission_gate import AdmissionGate, GateConfig, probe_gpu_lease
from cohezion.platform.admission_proxy import build_app
from tests.platform.test_gpu_lease import FakeFleet, quiet_status
from tests.platform.test_gpu_lease_gate import CATALOG, FLM, GGUF, _gate, _upstream, holder


__all__ = ["holder"]  # pytest fixture re-export

SRC = str(Path(gl.__file__).parents[2])
SDCPP = "SD-Turbo"


def _alive(pid: int) -> bool:
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except OSError:
        return False
    return state != "Z"


def _wait_file(path: Path, timeout_s: float = 120.0) -> str:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if path.exists() and path.read_text().strip():
            return path.read_text().strip()
        time.sleep(0.05)
    raise AssertionError(f"{path} never written")


def _run_cli(tmp: Path, cmd: list[str], grace_s: float = 5.0) -> tuple[Path, subprocess.Popen]:
    """The REAL gpu_lease.main + real flock on tmp; only the fleet side effects are faked."""
    lock = tmp / "gpu-lease.lock"
    script = tmp / "run.py"
    script.write_text(
        textwrap.dedent(f"""
        import os, pathlib, sys
        from cohezion.platform import gpu_lease as g
        g.KILL_GRACE_S = {grace_s}
        io = g.LeaseIO(read_resident=lambda: [], unload=lambda m: True,
                       admission_status=lambda: {{"reserved": [], "in_flight": 0,
                                                 "config": {{"enforce": True}},
                                                 "gpu_lease": {{"held": True,
                                                                "pid": os.getpid()}}}},
                       mem_available_gb=lambda: 500.0, gtt_used_gb=lambda: 0.0,
                       publish=lambda *a: None, sleep=lambda s: None)
        orig = g.gpu_lease
        g.gpu_lease = lambda h, n, t: orig(h, n, t, path=pathlib.Path({str(lock)!r}), io=io)
        raise SystemExit(g.main(["--holder", "t", "--need-gb", "1", "--"] + {cmd!r}))
        """)
    )
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([SRC, *sys.path])}
    return lock, subprocess.Popen([sys.executable, str(script)], env=env)


def _kill(pid: int) -> None:
    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, signal.SIGKILL)


# -- CLI: the lease lives exactly as long as the job tree ------------------------------------


def test_holder_sigkill_frees_lease_job_never_holds_it(tmp_path: Path) -> None:
    # SPEC CHANGE (third review, 2026-10-23): the job no longer inherits the lease fd, so
    # the lease lives exactly as long as its holder. Before, a passed fd let any job process
    # (a setsid escapee, a forked child) hold the lease forever after the holder released.
    # Residual, stated: a SIGKILLed holder frees the GPU while a grandchild may still run
    # (PDEATHSIG kills only the direct child); a normal exit stops the whole group first.
    gpid = tmp_path / "gpid"
    lock, p = _run_cli(tmp_path, ["sh", "-c", f"sleep 300 & echo $! > {gpid}; wait"])
    grandchild = int(_wait_file(gpid))
    try:
        assert probe_gpu_lease(lock) == "held"
        p.send_signal(signal.SIGKILL)
        p.wait()
        deadline = time.monotonic() + 5
        while probe_gpu_lease(lock) == "held" and time.monotonic() < deadline:
            time.sleep(0.05)
        assert probe_gpu_lease(lock) == "free", "a job process still holds the lease"
    finally:
        _kill(grandchild)


def test_normal_exit_kills_background_grandchild_before_release(tmp_path: Path) -> None:
    pidf = tmp_path / "gc.pid"
    lock, p = _run_cli(tmp_path, ["bash", "-c", f"sleep 300 & echo $! > {pidf}; exit 0"])
    assert p.wait(120) == 0
    gc = int(pidf.read_text())
    try:
        assert probe_gpu_lease(lock) == "free"
        assert not _alive(gc), f"lease released while job's process group member {gc} lives"
    finally:
        _kill(gc)


def test_second_sigterm_in_grace_never_frees_lease_with_child_alive(tmp_path: Path) -> None:
    pidf = tmp_path / "c.pid"
    cmd = ["bash", "-c", f"trap '' TERM; echo $$ > {pidf}; while true; do sleep 0.2; done"]
    lock, p = _run_cli(tmp_path, cmd, grace_s=2.0)
    child = int(_wait_file(pidf))
    try:
        p.send_signal(signal.SIGTERM)
        time.sleep(0.5)
        p.send_signal(signal.SIGTERM)  # an operator / systemd repeating the stop
        bad = 0
        t = time.monotonic()
        while time.monotonic() - t < 4:
            if probe_gpu_lease(lock) == "free" and _alive(child):
                bad += 1
            time.sleep(0.002)
        p.wait(120)
        assert bad == 0, f"{bad} samples with lease free AND child alive"
        assert not _alive(child)
    finally:
        _kill(child)


# -- acquire: never grant on a lease nothing enforces, nor on a fleet nobody saw ------------


@pytest.mark.parametrize("status", [{"enforce": False}, {}])
def test_grant_refused_when_gate_is_not_enforcing(_isolated_gpu_lease, status) -> None:
    fleet = FakeFleet([])
    io = fleet.io(admission_status=lambda: {**quiet_status(), "config": status})
    with pytest.raises(gl.GpuLeaseError) as ei, gl.gpu_lease("t", 1.0, io=io):
        pass
    assert ei.value.stage == "enforce"
    assert probe_gpu_lease(_isolated_gpu_lease) == "free"


def test_health_200_without_model_list_is_unreadable_for_the_lease(monkeypatch) -> None:
    import cohezion.compound.oom_guard as og

    req = httpx.Request("GET", "http://x/api/v1/health")
    monkeypatch.setattr(
        og.httpx, "get", lambda *a, **k: httpx.Response(200, json={"status": "ok"}, request=req)
    )
    assert og.fetch_loaded_models(base_url="http://x", strict=True) is None
    assert og.fetch_loaded_models(base_url="http://x") == []  # default callers unchanged
    assert gl._read_resident() is None


def test_grant_publishes_memory_terms_for_the_gate(_isolated_gpu_lease) -> None:
    fleet = FakeFleet([], mem_gb=80.0)
    with gl.gpu_lease("trainer", 20.0, io=fleet.io()) as grant:
        side = json.loads(_isolated_gpu_lease.with_name("gpu-lease.holder.json").read_text())
        assert side["need_gb"] == 20.0 and side["grant_mem_gb"] == 80.0
        assert grant.fd >= 0


# -- gate/proxy: displaced work completes ---------------------------------------------------


def test_cpu_resident_model_serves_inference_under_lease(holder) -> None:
    seen: list[httpx.Request] = []
    gate = _gate(resident=[{"model_name": GGUF, "recipe": "llamacpp", "device": "cpu"}])
    app = build_app(gate, client=_upstream(seen), lease_hold_s=0.3, lease_poll_s=0.05)
    with TestClient(app) as c:
        r = c.post("/v1/chat/completions", json={"model": GGUF, "messages": []})
    assert r.status_code == 200 and len(seen) == 1


@pytest.mark.parametrize(
    ("resident", "path", "extra"),
    [
        (None, "v1/chat/completions", {}),  # census unreadable: fail closed
        ([{"model_name": GGUF, "device": "gpu"}], "v1/chat/completions", {}),
        ([{"model_name": GGUF, "device": "cpu"}], "v1/chat/completions", {"llamacpp_args": "x"}),
    ],
)
def test_cpu_reuse_is_refused_without_fresh_cpu_proof(holder, resident, path, extra) -> None:
    gate = AdmissionGate(
        config=GateConfig(enforce=True),
        read_resident=lambda: resident,
        read_cgroup=lambda: (0.0, 30.0),
        read_size_gb=lambda m: 5.0,
        read_catalog=lambda: CATALOG,
        read_mem_available=lambda: 200.0,
    )
    gate.refresh_catalog()
    d = gate.decide(GGUF, path, body={"model": GGUF, **extra})
    assert not d.allow and d.kind == "gpu_lease"


def test_chat_to_non_resident_gguf_waits_then_503_when_cpu_cannot_fit(holder) -> None:
    # SPEC CHANGE (third review, 2026-10-23): a chat to a non-resident GGUF is served on the
    # CPU when it fits (test_gpu_lease_review3). When the CPU budget cannot fit it, it is
    # held for the hold window and then refused with the lease headers, never loaded.
    seen: list[httpx.Request] = []
    app = build_app(
        _gate(working_set=26.0), client=_upstream(seen), lease_hold_s=0.3, lease_poll_s=0.05
    )
    with TestClient(app) as c:
        r = c.post("/v1/chat/completions", json={"model": GGUF, "messages": []})
    assert r.status_code == 503 and r.headers["X-Cohezion-Refusal"] == "gpu_lease"
    assert seen == []


def test_cpu_fallback_never_persists_a_cpu_pin(holder) -> None:
    seen: list[httpx.Request] = []
    app = build_app(_gate(), client=_upstream(seen), lease_hold_s=0.2, lease_poll_s=0.05)
    with TestClient(app) as c:
        r = c.post("/api/v1/load", json={"model_name": GGUF, "save_options": True})
    assert r.status_code == 200
    sent = json.loads(seen[0].content)
    assert sent["llamacpp_backend"] == "cpu" and sent["save_options"] is False


def _terms(lock: Path, need: float, grant_mem: float) -> None:
    lock.with_name("gpu-lease.holder.json").write_text(
        json.dumps(
            {"holder": "t", "pid": 1, "since": 2.0, "need_gb": need, "grant_mem_gb": grant_mem}
        )
    )


def test_cpu_fallback_cannot_take_the_holders_memory(holder, _isolated_gpu_lease) -> None:
    # Granted at exactly need + floor, before the job has allocated: there is no spare
    # room, so a 20 GB CPU load must be refused even though lemond's cgroup has headroom.
    _terms(_isolated_gpu_lease, need=10.0, grant_mem=26.0)
    seen: list[httpx.Request] = []
    gate = _gate(mem_available=26.0)
    gate._read_size_gb = lambda m: 20.0
    app = build_app(gate, client=_upstream(seen), lease_hold_s=0.2, lease_poll_s=0.05)
    with TestClient(app) as c:
        r = c.post("/api/v1/load", json={"model_name": GGUF})
    assert r.status_code == 503 and seen == []


def test_small_npu_load_admitted_after_holder_allocated(holder, _isolated_gpu_lease) -> None:
    # The job has allocated its whole need (MemAvailable 18 of a 60 GB grant): a 1 GB FLM
    # load still leaves the floor, so the NPU is not starved for the whole lease.
    _terms(_isolated_gpu_lease, need=40.0, grant_mem=60.0)
    d = _gate(mem_available=18.0).decide(FLM, "api/v1/chat/completions")
    assert d.allow, d.reason


def _flm_gate(names: list[str], resident: list[dict]) -> AdmissionGate:
    cat = {**CATALOG, **{n: {"id": n, "size": 1.0, "recipe": "flm"} for n in names}}
    gate = AdmissionGate(
        config=GateConfig(enforce=True),
        read_resident=lambda: list(resident),
        read_cgroup=lambda: (0.0, 30.0),
        read_size_gb=lambda m: 1.0,
        read_catalog=lambda: cat,
        read_mem_available=lambda: 200.0,
    )
    gate.refresh_catalog()
    return gate


def test_distinct_lease_admits_accumulate_against_spare_room(holder, _isolated_gpu_lease) -> None:
    _terms(_isolated_gpu_lease, need=10.0, grant_mem=28.5)  # 2.5 GB spare
    names = ["a-FLM", "b-FLM", "c-FLM"]
    gate = _flm_gate(names, [])
    assert gate.decide(names[0], "api/v1/embeddings").allow
    assert gate.decide(names[1], "api/v1/embeddings").allow  # 2 distinct GB
    d = gate.decide(names[2], "api/v1/embeddings")  # a third would exceed 2.5
    assert not d.allow and d.kind == "gpu_lease"


def test_npu_swaps_never_exhaust_the_lease_bound(holder, _isolated_gpu_lease) -> None:
    # npu-ascension swaps FLM models every ~48 s: re-admitting a model already counted must
    # cost nothing, or a multi-hour lease starves the NPU (held, then 503) part-way through.
    _terms(_isolated_gpu_lease, need=10.0, grant_mem=31.0)  # 5 GB spare
    names = ["a-FLM", "b-FLM"]
    resident: list[dict] = []
    gate = _flm_gate(names, resident)
    for i in range(20):
        name = names[i % 2]
        resident[:] = []  # the other model was evicted by the swap
        d = gate.decide(name, "api/v1/chat/completions")
        assert d.allow, (i, d.reason)
        gate.release(name)
        resident[:] = [{"model_name": name, "recipe": "flm", "device": "npu"}]
        gate._resident_cache = None  # the next decide sees this round's census


def test_no_lease_admit_before_terms_are_published(holder, _isolated_gpu_lease) -> None:
    _isolated_gpu_lease.with_name("gpu-lease.holder.json").unlink()
    d = _gate().decide(FLM, "api/v1/chat/completions")
    assert not d.allow and d.kind == "gpu_lease"


def test_lease_exempt_covers_only_the_rewritten_model(holder) -> None:
    cat = {**CATALOG, SDCPP: {"id": SDCPP, "size": 6.0, "recipe": "sd-cpp"}}
    gate = AdmissionGate(
        config=GateConfig(enforce=True),
        read_resident=lambda: [],
        read_cgroup=lambda: (0.0, 30.0),
        read_size_gb=lambda m: 1.0,
        read_catalog=lambda: cat,
        read_mem_available=lambda: 200.0,
    )
    gate.refresh_catalog()
    assert not gate.decide(SDCPP, "api/v1/load", lease_exempt=GGUF).allow
    seen: list[httpx.Request] = []
    app = build_app(gate, client=_upstream(seen), lease_hold_s=0.2, lease_poll_s=0.05)
    with TestClient(app) as c:
        r = c.post("/api/v1/load", json={"model_name": GGUF, "draft_model": SDCPP})
    assert r.status_code == 503 and seen == []


def test_query_string_override_is_refused_under_lease(holder) -> None:
    seen: list[httpx.Request] = []
    app = build_app(_gate(), client=_upstream(seen), lease_hold_s=0.2, lease_poll_s=0.05)
    with TestClient(app) as c:
        r = c.post("/api/v1/load?flm_args=--foo", json={"model_name": FLM})
        r2 = c.post("/api/v1/load?llamacpp_backend=rocm", json={"model_name": GGUF})
    assert r.status_code == 503 and r2.status_code == 503 and seen == []


def test_multipart_override_is_refused_under_lease(holder) -> None:
    seen: list[httpx.Request] = []
    app = build_app(_gate(), client=_upstream(seen), lease_hold_s=0.2, lease_poll_s=0.05)
    with TestClient(app) as c:
        r = c.post(
            "/api/v1/load", files={"model_name": (None, FLM), "llamacpp_backend": (None, "rocm")}
        )
    assert r.status_code == 503 and seen == []


def test_landed_reservation_does_not_stall_the_drain() -> None:
    resident: list[dict] = []
    gate = AdmissionGate(
        config=GateConfig(enforce=True),
        read_resident=lambda: list(resident),
        read_cgroup=lambda: (0.0, 30.0),
        read_size_gb=lambda m: 1.0,
        read_catalog=lambda: CATALOG,
    )
    gate.refresh_catalog()
    assert gate.decide(FLM, "api/v1/load").reason.startswith("fits")
    resident.append({"model_name": FLM, "recipe": "flm", "device": "npu"})
    time.sleep(1.6)  # past the residency cache TTL
    assert gate.reserved_models() == []


def test_hold_polls_the_lease_not_the_gate(holder) -> None:
    gate = _gate(resident=[{"model_name": GGUF}])
    calls = [0]
    orig = gate.decide

    def counting(*a, **k):
        calls[0] += 1
        return orig(*a, **k)

    gate.decide = counting  # type: ignore[method-assign]
    app = build_app(gate, client=_upstream([]), lease_hold_s=0.5, lease_poll_s=0.1)
    with TestClient(app) as c:
        r = c.post("/v1/chat/completions", json={"model": GGUF, "messages": []})
    assert r.status_code == 503
    assert calls[0] < 10, f"decide() called {calls[0]} times during one hold"


def test_abandoned_held_request_is_not_forwarded(holder) -> None:
    import uvicorn

    seen: list[httpx.Request] = []
    # CPU cannot fit the model, so the request is held (no implicit CPU load) until abandoned.
    gate = _gate(working_set=26.0)
    app = build_app(gate, client=_upstream(seen), lease_hold_s=5.0, lease_poll_s=0.05)
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
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
        assert seen == [], "proxy forwarded a GPU load for a client that had already gone"
    finally:
        server.should_exit = True
        th.join(5)


# -- a lease that is never released still reaches the kanban --------------------------------


def test_overdue_lease_is_reported_while_still_held(_isolated_gpu_lease, monkeypatch) -> None:
    monkeypatch.setattr(gl, "WATCHDOG_S", 0.05)
    monkeypatch.setenv("COHEZION_GPU_LEASE_WARN_H", str(0.1 / 3600))
    fleet = FakeFleet([])
    with gl.gpu_lease("lib", 1.0, io=fleet.io()):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not any(
            t == "gpu_lease_overdue" for t, _ in fleet.events
        ):
            time.sleep(0.05)
        assert [t for t, _ in fleet.events].count("gpu_lease_overdue") == 1
    assert fleet.events[-1][1]["overdue_reported"] is True

    from cohezion.data_mesh.event_consumer import EventConsumer

    filed: list = []
    c = EventConsumer(
        sql_fn=lambda q: [{"status": "OK", "result": []}],
        summarize_fn=lambda t, p: t,
        file_work_item_fn=lambda *a: filed.append(a) or "wq-1",
    )
    overdue = {"event_type": "gpu_lease_overdue", "payload": json.dumps({"held_s": 1.0})}
    assert c.handle(overdue)["work_item"] == "wq-1"
    released = {
        "event_type": "gpu_lease_released",
        "payload": json.dumps({"held_s": 13 * 3600.0, "overdue_reported": True}),
    }
    assert c.handle(released) == {"action": "tally", "kind": "gpu_lease"}  # filed once
    assert len(filed) == 1
