"""Exclusive GPU lease: a kernel flock that a heavy GPU job holds while it runs.

The lease is ``flock(LOCK_EX)`` on ``~/dev/cohezion/.cache/gpu-lease.lock`` (env
``COHEZION_GPU_LEASE_PATH`` overrides; never /tmp or /run/user, both of which are wiped).
The kernel drops it when the holder dies, so there is no TTL and no heartbeat. The lock file
is never deleted: unlinking it would hand the next acquirer a different inode than the
gate probes.

Enforcement lives ONLY in the :13305 admission gate (``admission_gate.decide``), which under a
held lease refuses every load except FLM (NPU) and never relaxes a check. This module clears
the GPU and then holds the lock. Datamesh events are audit/notification only: they are
fail-open and nothing waits on their delivery.

Acquire: A0 requested event, A1 flock (retry 1 s up to ``acquire_timeout_s``) + sidecar,
A2 drain the gate's in-flight reservations, A3 upstream health readable, A4 victims = every
GPU-resident model (pinned included, never NPU), A5 unload each (3 tries, 10 s apart),
A6 MEASURED postcondition (no GPU model resident AND MemAvailable >= need + 16 GiB),
A7 granted event. Any failure releases the lock and raises :class:`GpuLeaseError`.
Release never reloads models; Lemonade reloads on demand once the gate admits again.

CLI: ``python -m cohezion.platform.gpu_lease --holder X --need-gb N [--max-hold 6h] -- cmd``.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import fcntl
import json
import logging
import os
import pathlib
import signal
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

FLOOR_GB = 16.0  # same RAM floor as hotswap.RAM_FLOOR_GB
UPSTREAM = "http://localhost:13315"  # lemond itself, not the proxy
GATE_STATUS_URL = "http://127.0.0.1:13305/admission/status"
DRAIN_MAX_S = 180.0
HEALTH_MAX_S = 120.0
UNLOAD_ATTEMPTS = 3
UNLOAD_RETRY_S = 10.0
WATCHDOG_S = 30.0
KILL_GRACE_S = 60.0
_GPU_DEVICES = frozenset({"igpu"})  # silicon_residency.normalize_device maps gpu -> igpu


def lease_path() -> pathlib.Path:
    raw = os.environ.get("COHEZION_GPU_LEASE_PATH")
    if raw:
        return pathlib.Path(raw)
    return pathlib.Path.home() / "dev" / "cohezion" / ".cache" / "gpu-lease.lock"


def sidecar_path(lock: pathlib.Path) -> pathlib.Path:
    return lock.with_name("gpu-lease.holder.json")


class GpuLeaseError(RuntimeError):
    def __init__(self, stage: str, detail: str = "") -> None:
        super().__init__(f"gpu lease refused at {stage}: {detail}")
        self.stage = stage


@dataclass
class Grant:
    holder: str
    pid: int
    unloaded: list[str]
    gtt_before_gb: float | None
    gtt_after_gb: float | None
    mem_available_gb: float
    waited_s: float
    acquired_at: float


# -- events (audit only, fail-open) ---------------------------------------------------------


def publish_event(
    event_type: str,
    payload: dict,
    *,
    source: str = "gpu_lease",
    sql_fn: Callable[[str], object] | None = None,
) -> bool:
    """CREATE one ``data_product_event`` row. True only when every statement reports OK.

    SurrealDB answers HTTP 200 for statement errors, so the per-statement status is the
    success signal. Never raises: an audit failure must not change the lease outcome.
    """
    record = {
        "event_type": event_type.lower(),
        "source": source,
        "payload": json.dumps(payload, sort_keys=True, default=str),
        "priority": 1,
        "timestamp": float(time.time()),
    }
    try:
        if sql_fn is None:
            from cohezion.data_mesh.event_consumer import _default_sql as sql_fn
        res = sql_fn(f"CREATE data_product_event CONTENT {json.dumps(record)};")
        ok = (
            isinstance(res, list)
            and bool(res)
            and all(isinstance(r, dict) and r.get("status") == "OK" for r in res)
        )
    except Exception as exc:  # transport, JSON, anything: log and carry on
        logger.warning("gpu_lease: event %s not written: %s", event_type, exc)
        return False
    if not ok:
        logger.warning("gpu_lease: event %s rejected by SurrealDB: %s", event_type, res)
    return ok


# -- default probes ------------------------------------------------------------------------


def _read_resident() -> list[dict] | None:
    from cohezion.compound.oom_guard import fetch_loaded_models

    return fetch_loaded_models(base_url=UPSTREAM)


def _unload(model_id: str) -> bool:
    from cohezion.inference import hotswap

    return hotswap.unload(model_id)


def _admission_status() -> dict | None:
    import httpx

    try:
        r = httpx.get(GATE_STATUS_URL, timeout=5.0)
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError):
        return None


def _mem_available_gb() -> float | None:
    """MemAvailable in GiB, None when unreadable (the postcondition then fails)."""
    try:
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / (1024.0**2)
    except (OSError, ValueError, IndexError):
        return None
    return None


def _gtt_used_gb() -> float | None:
    from cohezion.core.resource_management.session_monitor import _read_gtt_used_gb

    return _read_gtt_used_gb()


def _publish(event_type: str, payload: dict) -> bool:
    return publish_event(event_type, payload)


@dataclass
class LeaseIO:
    """Every side effect, injectable so tests never reach lemonade or SurrealDB."""

    read_resident: Callable[[], list[dict] | None] = _read_resident
    unload: Callable[[str], bool] = _unload
    admission_status: Callable[[], dict | None] = _admission_status
    mem_available_gb: Callable[[], float | None] = _mem_available_gb
    gtt_used_gb: Callable[[], float | None] = _gtt_used_gb
    publish: Callable[[str, dict], object] = _publish
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = field(default=time.monotonic)


def _emit(io: LeaseIO, event_type: str, payload: dict) -> None:
    try:
        io.publish(event_type, payload)
    except Exception as exc:
        logger.warning("gpu_lease: publish %s failed (ignored): %s", event_type, exc)


def _gpu_models(entries: list[dict]) -> list[str]:
    """GPU-resident model names from a health list, via the shared census parser."""
    from cohezion.inference.silicon_residency import parse_census

    census = parse_census({"all_models_loaded": entries})
    return [m.name for m in census.residents if m.device in _GPU_DEVICES and m.recipe != "flm"]


def _wait_for(io: LeaseIO, max_s: float, probe: Callable[[], bool]) -> bool:
    deadline = io.clock() + max_s
    while True:
        if probe():
            return True
        if io.clock() >= deadline:
            return False
        io.sleep(1.0)


def _inode_matches(fd: int, path: pathlib.Path) -> bool:
    try:
        return os.fstat(fd).st_ino == os.stat(path).st_ino
    except OSError:
        return False


# -- the lease -----------------------------------------------------------------------------


class _Held:
    def __init__(self, fd: int, path: pathlib.Path) -> None:
        self.fd = fd
        self.path = path
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch, name="gpu-lease-watchdog", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _watch(self) -> None:
        while not self._stop.wait(WATCHDOG_S):
            if not _inode_matches(self.fd, self.path):
                # The gate probes the path, so a replaced/deleted file means enforcement is
                # gone. This is an operator error; shout, do not silently continue.
                logger.error(
                    "gpu_lease: lock file %s was replaced or deleted while held -- "
                    "the admission gate can no longer see this lease",
                    self.path,
                )

    def close(self) -> None:
        self._stop.set()
        with contextlib.suppress(OSError):
            os.close(self.fd)  # closing the only fd drops the flock


def _flock(path: pathlib.Path, timeout_s: float, io: LeaseIO) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)  # no O_TRUNC, never unlinked
    deadline = io.clock() + timeout_s
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BlockingIOError as exc:
            if io.clock() >= deadline:
                os.close(fd)
                raise GpuLeaseError(
                    "acquire", f"held by another process after {timeout_s}s"
                ) from exc
            io.sleep(1.0)


def _write_sidecar(path: pathlib.Path, info: dict) -> None:
    side = sidecar_path(path)
    tmp = side.with_suffix(".tmp")
    tmp.write_text(json.dumps(info))
    os.replace(tmp, side)


def _acquire(holder: str, need_gb: float, timeout_s: float, path: pathlib.Path, io: LeaseIO):
    started = io.clock()
    _emit(io, "gpu_lease_requested", {"holder": holder, "pid": os.getpid(), "need_gb": need_gb})
    fd = _flock(path, timeout_s, io)  # raises before any state exists
    held = _Held(fd, path)
    stage = "sidecar"
    still: list[str] = []
    try:
        _write_sidecar(path, {"holder": holder, "pid": os.getpid(), "since": time.time()})

        stage = "drain"  # A2: loads admitted just before the lock must land first
        if not _wait_for(
            io, DRAIN_MAX_S, lambda: (io.admission_status() or {}).get("reserved") == []
        ):
            raise GpuLeaseError(stage, "gate reservations did not drain (or gate unreachable)")

        stage = "health"  # A3
        entries: list[dict] = []

        def _health() -> bool:
            got = io.read_resident()
            if got is None:
                return False
            entries[:] = got
            return True

        if not _wait_for(io, HEALTH_MAX_S, _health):
            raise GpuLeaseError(stage, "upstream health unreadable")

        stage = "unload"  # A4 + A5
        gtt_before = io.gtt_used_gb()
        unloaded: list[str] = []
        for model in _gpu_models(entries):
            ok = False
            for attempt in range(1, UNLOAD_ATTEMPTS + 1):
                if io.unload(model):
                    ok = True
                    break
                if attempt < UNLOAD_ATTEMPTS:
                    io.sleep(UNLOAD_RETRY_S)
            if ok:
                unloaded.append(model)
            _emit(io, "gpu_model_unloaded", {"holder": holder, "model": model, "ok": ok})

        stage = "postcondition"  # A6: measured, not inferred from unload() answers
        fresh = io.read_resident()
        still = _gpu_models(fresh) if fresh is not None else ["<health unreadable>"]
        mem = io.mem_available_gb()
        gtt_after = io.gtt_used_gb()
        logger.info("gpu_lease: mem_info_gtt_used %s -> %s GiB", gtt_before, gtt_after)
        if still or mem is None or mem < need_gb + FLOOR_GB:
            raise GpuLeaseError(
                stage, f"still_resident={still} mem_available={mem} need={need_gb}+{FLOOR_GB}"
            )
    except GpuLeaseError as exc:
        _release_lock(held, path)
        _emit(
            io,
            "gpu_lease_refused",
            {"holder": holder, "stage": exc.stage, "still_resident": still, "detail": str(exc)},
        )
        raise
    except BaseException:
        _release_lock(held, path)
        raise
    grant = Grant(
        holder=holder,
        pid=os.getpid(),
        unloaded=unloaded,
        gtt_before_gb=gtt_before,
        gtt_after_gb=gtt_after,
        mem_available_gb=mem,
        waited_s=round(io.clock() - started, 3),
        acquired_at=time.time(),
    )
    _emit(
        io,
        "gpu_lease_granted",
        {
            "holder": holder,
            "pid": grant.pid,
            "unloaded": unloaded,
            "gtt_before_gb": gtt_before,
            "gtt_after_gb": gtt_after,
            "mem_available_gb": mem,
            "waited_s": grant.waited_s,
        },
    )
    held.start()
    return held, grant


def _release_lock(held: _Held, path: pathlib.Path) -> None:
    with contextlib.suppress(OSError):
        sidecar_path(path).unlink()
    held.close()


@contextlib.contextmanager
def gpu_lease(
    holder: str,
    need_gb: float,
    acquire_timeout_s: float = 600,
    *,
    path: pathlib.Path | None = None,
    io: LeaseIO | None = None,
) -> Iterator[Grant]:
    """Hold the GPU exclusively for the ``with`` body. Raises GpuLeaseError if not granted."""
    io = io or LeaseIO()
    path = path or lease_path()
    held, grant = _acquire(holder, need_gb, acquire_timeout_s, path, io)
    exit_ok = False
    try:
        yield grant
        exit_ok = True
    finally:
        _release_lock(held, path)
        _emit(
            io,
            "gpu_lease_released",
            {
                "holder": holder,
                "pid": grant.pid,
                "held_s": round(time.time() - grant.acquired_at, 3),
                "exit_ok": exit_ok,
            },
        )


# -- CLI -----------------------------------------------------------------------------------


def parse_duration(raw: str) -> float:
    units = {"s": 1.0, "m": 60.0, "h": 3600.0}
    raw = raw.strip().lower()
    if raw and raw[-1] in units:
        return float(raw[:-1]) * units[raw[-1]]
    return float(raw)


def _die_with_parent() -> None:
    """Child preexec: SIGKILL the job if the lease holder dies, so no orphan keeps the GPU
    busy after the kernel has already freed the lease (PR_SET_PDEATHSIG = 1)."""
    with contextlib.suppress(OSError, AttributeError):
        ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL)


def _stop_group(proc: subprocess.Popen) -> int:
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGTERM)
    try:
        return proc.wait(timeout=KILL_GRACE_S)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        return proc.wait()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cohezion.platform.gpu_lease")
    ap.add_argument("--holder", required=True)
    ap.add_argument("--need-gb", type=float, required=True)
    ap.add_argument("--max-hold", default="6h")
    ap.add_argument("--acquire-timeout", type=float, default=600.0)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args(argv)
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    if not cmd:
        ap.error("a command is required after --")
    max_hold = parse_duration(args.max_hold)

    def _term(signum, _frame):
        raise KeyboardInterrupt(f"signal {signum}")

    signal.signal(signal.SIGTERM, _term)
    try:
        with gpu_lease(args.holder, args.need_gb, args.acquire_timeout) as grant:
            logger.info("gpu lease granted to %s: unloaded %s", grant.holder, grant.unloaded)
            proc = subprocess.Popen(cmd, start_new_session=True, preexec_fn=_die_with_parent)
            try:
                rc = proc.wait(timeout=max_hold)
            except subprocess.TimeoutExpired:
                logger.warning("gpu lease max-hold %.0fs reached: stopping %s", max_hold, cmd)
                _stop_group(proc)
                rc = 124
            except KeyboardInterrupt:
                _stop_group(proc)
                rc = 130
            if rc != 0:
                raise _ChildFailedError(rc)  # release event records exit_ok=False
            return 0
    except _ChildFailedError as exc:
        return exc.rc
    except GpuLeaseError as exc:
        logger.error("%s", exc)
        return 75  # EX_TEMPFAIL


class _ChildFailedError(Exception):
    def __init__(self, rc: int) -> None:
        super().__init__(rc)
        self.rc = rc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())
