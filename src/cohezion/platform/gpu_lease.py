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
A2 drain the gate's reservations AND admits still in flight, and require that the gate
enforces and sees THIS lease, A3 upstream health readable, A4 victims = every GPU-resident
model (pinned included, never NPU), A5 unload each (3 tries, 10 s apart), A6 MEASURED
postcondition (no GPU model resident, re-checked after a settle with the gate still quiet
and still seeing the lease, AND MemAvailable >= need + 16 GiB), A7 granted event. Any failure releases the lock and raises :class:`GpuLeaseError`.
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
GROUP_POLL_S = 0.2
SETTLE_S = 3.0  # A6 re-measures after this: a reload already under way must show by then
_STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT)
_GPU_DEVICES = frozenset({"igpu"})  # silicon_residency.normalize_device maps gpu -> igpu


def lease_path() -> pathlib.Path:
    raw = os.environ.get("COHEZION_GPU_LEASE_PATH")
    if raw:
        return pathlib.Path(raw)
    return pathlib.Path.home() / "dev" / "cohezion" / ".cache" / "gpu-lease.lock"


def sidecar_path(lock: pathlib.Path) -> pathlib.Path:
    return lock.with_name("gpu-lease.holder.json")


def warn_after_s() -> float:
    """A lease held longer than this is reported (``gpu_lease_overdue``) while still held."""
    return float(os.environ.get("COHEZION_GPU_LEASE_WARN_H", "12")) * 3600.0


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
    # The locked fd. A job given this fd (Popen pass_fds) keeps the flock alive for as long
    # as ANY process in its tree holds it: flock belongs to the open file description.
    fd: int = -1


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

    # strict: a 200 without an all_models_loaded list is "cannot see", never "empty fleet".
    return fetch_loaded_models(base_url=UPSTREAM, strict=True)


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


def _unclassified(entries: list[dict]) -> list[str]:
    """Non-FLM residents whose device the census cannot classify. The postcondition fails on
    these: a census that cannot place a model cannot claim zero GPU models."""
    from cohezion.inference.silicon_residency import parse_census

    census = parse_census({"all_models_loaded": entries})
    return [m.name for m in census.residents if m.device == "unknown" and m.recipe != "flm"]


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
        self.overdue_reported = False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch, name="gpu-lease-watchdog", daemon=True)
        self._io: LeaseIO | None = None
        self._holder = ""
        self._since = 0.0

    def start(self, io: LeaseIO, holder: str, since: float) -> None:
        self._io, self._holder, self._since = io, holder, since
        self._thread.start()

    def _watch(self) -> None:
        while not self._stop.wait(WATCHDOG_S):
            held_s = time.time() - self._since
            if not self.overdue_reported and held_s > warn_after_s() and self._io is not None:
                # A library holder may never release, so its release event can never carry
                # the over-long hold to the kanban: report it while it is still held.
                self.overdue_reported = True
                _emit(
                    self._io,
                    "gpu_lease_overdue",
                    {"holder": self._holder, "pid": os.getpid(), "held_s": round(held_s, 3)},
                )
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
        status: dict = {}

        def _drained() -> bool:
            got = io.admission_status()
            status.clear()
            status.update(got or {})
            return got is not None and _quiet(got)

        if not _wait_for(io, DRAIN_MAX_S, _drained):
            raise GpuLeaseError(stage, "gate reservations did not drain (or gate unreachable)")
        stage = "enforce"
        _check_enforced(status)

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
        still = _still_resident(io)
        if not still:
            # Settle, then measure again: a request forwarded before the flock may have
            # started a reload that only shows on a later census.
            io.sleep(SETTLE_S)
            after = io.admission_status()
            if after is None or not _quiet(after):
                still = ["<gate not quiet after settle>"]
            else:
                stage = "enforce"
                _check_enforced(after)
                stage = "postcondition"
                still = _still_resident(io)
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
        fd=fd,
    )
    # Publish the grant's memory terms: the gate bounds every load it admits under the lease
    # by them. Until this write the sidecar has no need_gb and the gate admits no load.
    with contextlib.suppress(OSError):
        _write_sidecar(
            path,
            {
                "holder": holder,
                "pid": grant.pid,
                "since": grant.acquired_at,
                "need_gb": need_gb,
                "grant_mem_gb": mem,
            },
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
    held.start(io, holder, grant.acquired_at)
    return held, grant


def _quiet(status: dict) -> bool:
    """Nothing the gate admitted before the flock is still loading or in flight. A gate that
    does not report a field is not quiet (it predates the check: fail closed)."""
    return status.get("reserved") == [] and status.get("in_flight") == 0


def _check_enforced(status: dict) -> None:
    """The gate is the ONLY enforcer: it must enforce, and it must see THIS lease. A gate in
    shadow mode, or one probing another lock path (a different HOME or
    COHEZION_GPU_LEASE_PATH in its unit), would admit every GPU load during the job."""
    if (status.get("config") or {}).get("enforce") is not True:
        raise GpuLeaseError("enforce", "admission gate is not enforcing (shadow mode)")
    seen = status.get("gpu_lease") or {}
    if seen.get("held") is not True or seen.get("pid") != os.getpid():
        raise GpuLeaseError("enforce", f"admission gate does not see this lease: {seen}")


def _still_resident(io: LeaseIO) -> list[str]:
    fresh = io.read_resident()
    if fresh is None:
        return ["<health unreadable>"]
    return _gpu_models(fresh) + _unclassified(fresh)


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
                "overdue_reported": held.overdue_reported,
            },
        )


# -- CLI -----------------------------------------------------------------------------------


def parse_duration(raw: str) -> float:
    units = {"s": 1.0, "m": 60.0, "h": 3600.0}
    raw = raw.strip().lower()
    if raw and raw[-1] in units:
        return float(raw[:-1]) * units[raw[-1]]
    return float(raw)


def _pdeathsig_preexec() -> Callable[[], None] | None:
    """A preexec_fn that SIGKILLs the job if the lease holder dies (PR_SET_PDEATHSIG = 1),
    so no orphan keeps the GPU busy after the kernel has freed the lease.

    libc is resolved HERE, before fork: dlopen inside a forked child of a threaded process
    (the watchdog thread is running) can deadlock. The child only makes the C call.
    """
    try:
        prctl = ctypes.CDLL(None, use_errno=True).prctl
    except (OSError, AttributeError):
        logger.warning("gpu_lease: prctl unavailable; the job will not die with the holder")
        return None

    def _preexec() -> None:
        prctl(1, signal.SIGKILL)

    return _preexec


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_group(proc: subprocess.Popen, timeout_s: float) -> bool:
    """Reap the leader and wait until no process is left in its group. False on timeout."""
    deadline = time.monotonic() + timeout_s
    while True:
        proc.poll()
        if proc.returncode is not None and not _group_alive(proc.pid):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(GROUP_POLL_S)


def _stop_group(proc: subprocess.Popen) -> None:
    """SIGTERM the job's whole process group, SIGKILL after the grace, and return only once
    the group is empty. Runs on EVERY exit path, so the lease is never released while a
    backgrounded worker of the job lives on. Further stop signals are ignored from here on:
    an interrupt inside the grace must not skip the SIGKILL and release early.
    (A job that calls setsid leaves the group; it still holds the passed lease fd.)
    """
    for sig in _STOP_SIGNALS:
        signal.signal(sig, signal.SIG_IGN)
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGTERM)
    if _wait_group(proc, KILL_GRACE_S):
        return
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGKILL)
    _wait_group(proc, float("inf"))


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

    # SIGHUP (closed terminal, dropped ssh) and SIGQUIT are catchable: unhandled they kill
    # this holder without stopping the job tree, which keeps the passed lease fd.
    saved = {sig: signal.getsignal(sig) for sig in _STOP_SIGNALS}
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):
        signal.signal(sig, _term)
    try:
        with gpu_lease(args.holder, args.need_gb, args.acquire_timeout) as grant:
            logger.info("gpu lease granted to %s: unloaded %s", grant.holder, grant.unloaded)
            # pass_fds: the job tree shares the locked open file description, so the lease
            # outlives this process if it is SIGKILLed while any job process still runs.
            pass_fds = (grant.fd,) if grant.fd >= 0 else ()
            proc = subprocess.Popen(
                cmd,
                start_new_session=True,
                preexec_fn=_pdeathsig_preexec(),
                pass_fds=pass_fds,
            )
            try:
                rc = proc.wait(timeout=max_hold)
            except subprocess.TimeoutExpired:
                logger.warning("gpu lease max-hold %.0fs reached: stopping %s", max_hold, cmd)
                rc = 124
            except KeyboardInterrupt:
                rc = 130
            _stop_group(proc)  # every path: no group member outlives the lease
            if rc != 0:
                raise _ChildFailedError(rc)  # release event records exit_ok=False
            return 0
    except _ChildFailedError as exc:
        return exc.rc
    except GpuLeaseError as exc:
        logger.error("%s", exc)
        return 75  # EX_TEMPFAIL
    finally:
        for sig, handler in saved.items():
            signal.signal(sig, handler)


class _ChildFailedError(Exception):
    def __init__(self, rc: int) -> None:
        super().__init__(rc)
        self.rc = rc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())
