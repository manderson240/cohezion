"""GPU lease (task side): acquire/release, postconditions, events, CLI.

A REAL flock on tmp_path and a REAL subprocess holder; lemonade HTTP, meminfo, GTT and
SurrealDB are injected fakes. Never touches :13305/:13315.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from cohezion.platform import gpu_lease as gl


_HOLDER = (
    "import fcntl, os, sys, time\n"
    "fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o644)\n"
    "fcntl.flock(fd, fcntl.LOCK_EX)\n"
    "print('ready', flush=True)\n"
    "time.sleep(600)\n"
)


class FakeFleet:
    """lemonade health + unload, meminfo and GTT as plain state."""

    def __init__(self, resident: list[dict], mem_gb: float = 100.0, stuck: set[str] | None = None):
        self.resident = list(resident)
        self.mem_gb = mem_gb
        self.stuck = set(stuck or ())
        self.unload_calls: list[str] = []
        self.events: list[tuple[str, dict]] = []
        self.gtt = 40.0

    def read_resident(self):
        return list(self.resident)

    def unload(self, model_id: str) -> bool:
        self.unload_calls.append(model_id)
        if model_id in self.stuck:
            return False
        self.resident = [m for m in self.resident if m["model_name"] != model_id]
        self.gtt -= 10.0
        return True

    def io(self, **over) -> gl.LeaseIO:
        kw = {
            "read_resident": self.read_resident,
            "unload": self.unload,
            # the real /admission/status shape: an enforcing gate with nothing in flight
            "admission_status": lambda: {"reserved": [], "config": {"enforce": True}},
            "mem_available_gb": lambda: self.mem_gb,
            "gtt_used_gb": lambda: self.gtt,
            "publish": lambda t, p: self.events.append((t, p)) or True,
            "sleep": lambda _s: None,
        }
        kw.update(over)
        return gl.LeaseIO(**kw)


FLEET = [
    {"model_name": "Gemma-4-E4B-it-GGUF", "device": "gpu", "recipe": "llamacpp"},
    {"model_name": "Bonsai-8B-gguf", "device": "igpu", "recipe": "llamacpp", "pinned": True},
    {"model_name": "llama3.2-1b-FLM", "device": "npu", "recipe": "flm"},
    {"model_name": "Gemma-4-31B-it-GGUF", "device": "cpu", "recipe": "llamacpp"},
]


def _is_free(path: Path) -> bool:
    import fcntl

    fd = os.open(path, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False
    finally:
        os.close(fd)


class TestAcquireRelease:
    def test_grant_unloads_gpu_models_only_and_releases(self, _isolated_gpu_lease) -> None:
        fleet = FakeFleet(FLEET)
        with gl.gpu_lease("trainer", 20.0, io=fleet.io()) as grant:
            assert sorted(fleet.unload_calls) == ["Bonsai-8B-gguf", "Gemma-4-E4B-it-GGUF"]
            assert sorted(grant.unloaded) == ["Bonsai-8B-gguf", "Gemma-4-E4B-it-GGUF"]
            assert grant.gtt_before_gb == 40.0 and grant.gtt_after_gb == 20.0
            assert not _is_free(_isolated_gpu_lease)
            side = json.loads(_isolated_gpu_lease.with_name("gpu-lease.holder.json").read_text())
            assert side["holder"] == "trainer" and side["pid"] == os.getpid()
        assert _is_free(_isolated_gpu_lease)
        assert _isolated_gpu_lease.exists()  # the lock file is never deleted
        assert not _isolated_gpu_lease.with_name("gpu-lease.holder.json").exists()
        types = [t for t, _ in fleet.events]
        assert types[0] == "gpu_lease_requested"
        assert types.count("gpu_model_unloaded") == 2
        assert types[-2:] == ["gpu_lease_granted", "gpu_lease_released"]
        assert fleet.events[-1][1]["exit_ok"] is True

    def test_body_exception_releases_with_exit_not_ok(self, _isolated_gpu_lease) -> None:
        fleet = FakeFleet([])
        with pytest.raises(ValueError), gl.gpu_lease("t", 1.0, io=fleet.io()):
            raise ValueError("job crashed")
        assert _is_free(_isolated_gpu_lease)
        assert fleet.events[-1] == ("gpu_lease_released", fleet.events[-1][1])
        assert fleet.events[-1][1]["exit_ok"] is False

    def test_drain_waits_for_reservations(self, _isolated_gpu_lease) -> None:
        on = {"config": {"enforce": True}}
        answers = iter(
            [{"reserved": ["x"], **on}, {"reserved": ["x"], **on}, {"reserved": [], **on}]
        )
        fleet = FakeFleet([])
        with gl.gpu_lease("t", 1.0, io=fleet.io(admission_status=lambda: next(answers))):
            pass  # granted only after the third status read

    def test_gate_unreachable_fails_closed(self, _isolated_gpu_lease, monkeypatch) -> None:
        monkeypatch.setattr(gl, "DRAIN_MAX_S", 0.0)
        fleet = FakeFleet([])
        with (
            pytest.raises(gl.GpuLeaseError) as ei,
            gl.gpu_lease("t", 1.0, io=fleet.io(admission_status=lambda: None)),
        ):
            pass
        assert ei.value.stage == "drain"
        assert _is_free(_isolated_gpu_lease)


class TestPostcondition:
    def test_model_still_resident_raises_and_releases(self, _isolated_gpu_lease) -> None:
        fleet = FakeFleet(FLEET, stuck={"Gemma-4-E4B-it-GGUF"})
        with pytest.raises(gl.GpuLeaseError) as ei, gl.gpu_lease("t", 1.0, io=fleet.io()):
            pytest.fail("body must not run")
        assert ei.value.stage == "postcondition"
        assert fleet.unload_calls.count("Gemma-4-E4B-it-GGUF") == 3  # bounded retries
        assert _is_free(_isolated_gpu_lease)
        refused = [p for t, p in fleet.events if t == "gpu_lease_refused"]
        assert refused and refused[0]["still_resident"] == ["Gemma-4-E4B-it-GGUF"]

    def test_unload_lies_but_model_remains_raises(self, _isolated_gpu_lease) -> None:
        # unload() says True yet the fresh census still lists it: the MEASURED state wins.
        fleet = FakeFleet(FLEET)
        fleet.unload = lambda m: True  # type: ignore[method-assign]
        with (
            pytest.raises(gl.GpuLeaseError) as ei,
            gl.gpu_lease("t", 1.0, io=fleet.io(unload=fleet.unload)),
        ):
            pass
        assert ei.value.stage == "postcondition"

    def test_mem_available_below_need_plus_floor_raises(self, _isolated_gpu_lease) -> None:
        fleet = FakeFleet([], mem_gb=35.9)  # need 20 + floor 16 = 36
        with pytest.raises(gl.GpuLeaseError) as ei, gl.gpu_lease("t", 20.0, io=fleet.io()):
            pass
        assert ei.value.stage == "postcondition"
        assert _is_free(_isolated_gpu_lease)

    def test_mem_available_unreadable_raises(self, _isolated_gpu_lease) -> None:
        fleet = FakeFleet([])
        with (
            pytest.raises(gl.GpuLeaseError),
            gl.gpu_lease("t", 1.0, io=fleet.io(mem_available_gb=lambda: None)),
        ):
            pass

    def test_exact_floor_is_granted(self, _isolated_gpu_lease) -> None:
        fleet = FakeFleet([], mem_gb=36.0)
        with gl.gpu_lease("t", 20.0, io=fleet.io()) as g:
            assert g.mem_available_gb == 36.0


class TestUnclassifiedDevice:
    def test_unknown_device_fails_postcondition(self, _isolated_gpu_lease) -> None:
        fleet = FakeFleet([{"model_name": "Mystery-GGUF", "device": "rocm", "recipe": "llamacpp"}])
        with pytest.raises(gl.GpuLeaseError) as ei, gl.gpu_lease("t", 1.0, io=fleet.io()):
            pass
        assert ei.value.stage == "postcondition"
        assert fleet.unload_calls == []  # it is not unloaded blind either


class TestKernelLockSemantics:
    def test_sigkilled_holder_frees_lease_without_ttl(self, _isolated_gpu_lease) -> None:
        proc = subprocess.Popen(
            [sys.executable, "-c", _HOLDER, str(_isolated_gpu_lease)],
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            assert proc.stdout is not None and proc.stdout.readline().strip() == "ready"
            fleet = FakeFleet([])
            with (
                pytest.raises(gl.GpuLeaseError) as ei,
                gl.gpu_lease("t", 1.0, acquire_timeout_s=0.0, io=fleet.io()),
            ):
                pass
            assert ei.value.stage == "acquire"
            proc.kill()
            proc.wait()
            with gl.gpu_lease("t", 1.0, acquire_timeout_s=0.0, io=fleet.io()) as g:
                assert g.holder == "t"
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()

    def test_watchdog_detects_replaced_lock_file(self, _isolated_gpu_lease) -> None:
        fd = os.open(_isolated_gpu_lease, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            assert gl._inode_matches(fd, _isolated_gpu_lease)
            os.unlink(_isolated_gpu_lease)
            _isolated_gpu_lease.write_text("")
            assert not gl._inode_matches(fd, _isolated_gpu_lease)
        finally:
            os.close(fd)


class TestEvents:
    def test_statement_error_with_http_200_is_failure(self) -> None:
        body = [{"status": "ERR", "result": "Couldn't coerce value for field `timestamp`"}]
        assert gl.publish_event("gpu_lease_granted", {"a": 1}, sql_fn=lambda q: body) is False

    def test_ok_statement_is_success_and_shape_is_schemafull(self) -> None:
        seen: list[str] = []

        def sql(q: str):
            seen.append(q)
            return [{"status": "OK", "result": [{"id": "data_product_event:x"}]}]

        assert gl.publish_event("GPU_LEASE_GRANTED", {"holder": "t"}, sql_fn=sql) is True
        rec = json.loads(seen[0].removeprefix("CREATE data_product_event CONTENT ").rstrip(";"))
        assert rec["event_type"] == "gpu_lease_granted"
        assert rec["source"] == "gpu_lease" and rec["priority"] == 1
        assert isinstance(rec["timestamp"], float)
        assert json.loads(rec["payload"]) == {"holder": "t"}
        assert set(rec) == {"event_type", "source", "payload", "priority", "timestamp"}

    def test_transport_error_is_fail_open(self) -> None:
        def boom(_q):
            raise OSError("surreal down")

        assert gl.publish_event("gpu_lease_granted", {}, sql_fn=boom) is False

    def test_dead_bus_does_not_block_grant(self, _isolated_gpu_lease) -> None:
        fleet = FakeFleet([])

        def boom(_t, _p):
            raise OSError("bus down")

        with gl.gpu_lease("t", 1.0, io=fleet.io(publish=boom)) as g:
            assert g.holder == "t"


class TestCli:
    def test_max_hold_terminates_child_group_then_releases(self, monkeypatch) -> None:
        monkeypatch.setattr(gl, "KILL_GRACE_S", 1.0)
        released: list[bool] = []

        from contextlib import contextmanager

        @contextmanager
        def fake_lease(holder, need_gb, acquire_timeout_s=600, **_kw):
            try:
                yield gl.Grant(holder, os.getpid(), [], None, None, 99.0, 0.0, time.time())
            finally:
                released.append(True)

        monkeypatch.setattr(gl, "gpu_lease", fake_lease)
        start = time.monotonic()
        rc = gl.main(["--holder", "t", "--need-gb", "1", "--max-hold", "1s", "--", "sleep", "30"])
        assert time.monotonic() - start < 10
        assert rc != 0 and released == [True]

    def test_child_exit_code_propagates(self, monkeypatch) -> None:
        from contextlib import contextmanager

        @contextmanager
        def fake_lease(holder, need_gb, acquire_timeout_s=600, **_kw):
            yield gl.Grant(holder, os.getpid(), [], None, None, 99.0, 0.0, time.time())

        monkeypatch.setattr(gl, "gpu_lease", fake_lease)
        assert gl.main(["--holder", "t", "--need-gb", "1", "--", "sh", "-c", "exit 3"]) == 3

    @pytest.mark.parametrize(("raw", "secs"), [("6h", 21600.0), ("90m", 5400.0), ("45", 45.0)])
    def test_parse_duration(self, raw, secs) -> None:
        assert gl.parse_duration(raw) == secs


class TestEventConsumerRouting:
    def _consumer(self, filed: list):
        from cohezion.data_mesh.event_consumer import EventConsumer

        return EventConsumer(
            sql_fn=lambda q: [{"status": "OK", "result": []}],
            summarize_fn=lambda t, p: f"{t}",
            file_work_item_fn=lambda *a: filed.append(a) or "wq-1",
        )

    def test_long_lease_is_routed_to_kanban(self) -> None:
        filed: list = []
        c = self._consumer(filed)
        ev = {
            "event_type": "gpu_lease_released",
            "payload": json.dumps({"holder": "t", "held_s": 13 * 3600.0}),
        }
        assert c.handle(ev)["work_item"] == "wq-1"
        assert "gpu_lease" in filed[0][0]

    def test_short_lease_is_tallied(self) -> None:
        filed: list = []
        c = self._consumer(filed)
        ev = {"event_type": "gpu_lease_released", "payload": json.dumps({"held_s": 60.0})}
        assert c.handle(ev) == {"action": "tally", "kind": "gpu_lease"}
        assert c.handle({"event_type": "gpu_model_unloaded", "payload": "{}"})["kind"] == (
            "gpu_lease"
        )
        assert filed == []

    def test_default_residency_service_gets_a_publisher(self, monkeypatch) -> None:
        import cohezion.inference.residency_service as rs

        captured: dict = {}

        class Spy:
            def __init__(self, **kw):
                captured.update(kw)

            def handle_event(self, event):
                return True

        monkeypatch.setattr(rs, "ResidencyService", Spy)
        c = self._consumer([])
        c.handle({"event_type": "model_needed", "model_id": "m"})
        assert callable(captured.get("publish"))


_PARENT = (
    "import subprocess, sys, time\n"
    "from cohezion.platform import gpu_lease as gl\n"
    "p = subprocess.Popen(['sleep', '60'], start_new_session=True,"
    " preexec_fn=gl._pdeathsig_preexec())\n"
    "print(p.pid, flush=True)\n"
    "time.sleep(60)\n"
)


def _proc_state(pid: int) -> str | None:
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except OSError:
        return None


def test_job_dies_when_lease_holder_is_sigkilled() -> None:
    env = {**os.environ, "PYTHONPATH": str(Path(gl.__file__).parents[2])}
    parent = subprocess.Popen(
        [sys.executable, "-c", _PARENT], stdout=subprocess.PIPE, text=True, env=env
    )
    assert parent.stdout is not None
    child = int(parent.stdout.readline())
    assert _proc_state(child) in ("S", "R")
    parent.kill()
    parent.wait()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and _proc_state(child) not in (None, "Z"):
        time.sleep(0.05)
    try:
        assert _proc_state(child) in (None, "Z")
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.kill(child, 9)
