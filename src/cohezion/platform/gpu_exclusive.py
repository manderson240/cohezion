"""Exclusive iGPU for a critical job, using lemonade's OWN backend state as the mechanism.

    with gpu_exclusive("kaggle-train", need_gb=40):
        run_job()
    python -m cohezion.platform.gpu_exclusive --holder X --need-gb N [--max-hold 6h] -- cmd ...
    python -m cohezion.platform.gpu_exclusive --recover

No proxy or gate enforces anything (two such designs failed; memory
prefer-server-native-state-over-external-enforcement). Instead, while the job runs,
lemonade itself is told to put every new load on CPU, so displaced fleet work keeps
completing (slower), and GPU-resident models are unloaded through lemonade.

Steps: flock (serialises wrappers only) -> recover a crashed predecessor's state file ->
read ``GET /internal/config`` + ``GET /api/v1/system-info`` -> persist state (tmp+rename)
BEFORE any change -> ``POST /internal/set {"<section>": {"backend": "cpu"}}`` (the endpoint
``lemonade config set`` calls; lemond writes config.json on it, routes/internal/set.cpp) ->
per-model pins -> unload GPU residents until a fresh census is clean AND MemAvailable >=
need + 16 GiB -> run -> restore exactly -> verify -> release.

Backend resolution (lemonade source, router.cpp resolve_effective_options +
recipe_options.cpp is_empty_option): load request > per-model (recipe_options.json saved
layer, then user.* registry recipe_options) > global ``<section>.backend``. A per-model
``"auto"``/``""`` is EMPTY and falls through to the global key, so the tier-0 "auto"
recipes are covered by the global flip and are never touched. A CONCRETE per-model pin
(rocm/vulkan) wins, so for each downloaded model whose ``effective`` backend is still not
cpu after the flip we POST ``/v1/models/{id}/options {"<k>_backend": "cpu"}`` (merge
semantics), recording the exact saved value first; restore re-POSTs that value, or
``null`` when the key was absent (never DELETE: it would wipe the other saved options).

Pins are discovered over ``GET /api/v1/models?show_all=true`` (registry entries too: a
pinned model downloaded on demand mid-job would otherwise load on the GPU).

Sections: a load INSTALLS its resolved backend if missing (llamacpp_server.cpp:295,
sdcpp_server.cpp:207) and lemonade treats installed/update_available/update_required as
present (system_info.cpp:659), so any backend not ``unsupported`` is loadable. GUARDED: cpu
loadable -> flipped. UNGUARDED: a GPU backend loadable but no cpu one, or a config section
with no matching recipe in system-info (unknown -> fail closed). INERT: every backend
unsupported. Unguarded sections are REFUSED unless the caller passes ``allow_unguarded``
(``--allow-unguarded``): their loads would land on the iGPU. llamacpp must be guarded.

Busy residents (``is_busy``) are never force-unloaded (that would abort fleet requests);
they are skipped and retried each poll, and still-busy at ``DEADLINE_S`` refuses. The census
must stay clean for ``SETTLE_S`` (a load already in flight when the backend flipped resolved
its options earlier, router.cpp, and lands later). While the grant holds a WATCHER thread
re-censuses every ``WATCH_S``: it unloads late idle GPU residents, re-applies cpu to any
guarded section that reverted (a lemond restart after an unpersisted /internal/set - the
route logs and still answers 200), and tracks the minimum MemAvailable. The watcher is
stopped and joined BEFORE restore so it can never re-flip a restored setting.

Known limits (documented, not enforced): a ``/v1/load`` that passes ``llamacpp_backend``
explicitly outranks everything (lemonade_server_mcp.py, apply_lemonade_recipes.py).
MEMORY IS NOT RESERVED: ``need_gb`` is checked at grant time only. On unified RAM displaced
fleet models reload on CPU into the same pool; lemonade has no size cap (max_loaded_models
is a count) and the admission gate is out of scope. The watcher reports the minimum seen
(``min_mem_available_gb`` in the released event) and logs below the floor. A crash mid-job
leaves backend=cpu: the safe direction.
If the wrapper dies but its job (own session) survives, the state file records the job's
pgid and pid namespace; recovery REFUSES while that group is alive or when the namespace
differs (agent shells each get their own: liveness is then unknowable, so cpu mode stays).
``--recover --force`` is the explicit escape. Any exception during setup (including
SIGTERM/SIGHUP/Ctrl-C) restores before propagating.
"""

from __future__ import annotations

import argparse
import base64
import fcntl
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cohezion.inference import hotswap


logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / "dev" / "cohezion" / ".cache"
LOCK_PATH = CACHE_DIR / "gpu-exclusive.lock"
STATE_PATH = CACHE_DIR / "gpu-exclusive.state.json"
SURREAL_URL = "http://localhost:8001/sql"
EVENT_TYPES = (
    "gpu_exclusive_requested",
    "gpu_exclusive_granted",
    "gpu_exclusive_refused",
    "gpu_exclusive_released",
)
CPU = "cpu"
_LOADABLE = {"installed", "update_available", "update_required", "installable"}
DEADLINE_S = 180.0
POLL_S = 2.0
SETTLE_S = 20.0  # census must stay clean this long (in-flight loads land late)
WATCH_S = 5.0  # watcher period while the grant holds
_GPU_TOKENS = {"gpu", "igpu"}


class GpuExclusiveRefusedError(RuntimeError):
    """Exclusive GPU could not be established; lemonade settings were restored."""


def _lemonade(method: str, path: str, body: object = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(  # noqa: S310 - local lemonade base
        f"{hotswap.LEMONADE_BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - cold /models took 21s
        return json.loads(r.read() or b"{}")


def _options_path(model_id: str) -> str:
    return f"/api/v1/models/{urllib.parse.quote(model_id, safe='')}/options"


def emit(event_type: str, payload: dict) -> bool:
    """CREATE one data_product_event row; fail-open. True only on per-statement OK."""
    row = {
        "event_type": event_type,
        "source": "gpu_exclusive",
        "timestamp": time.time(),
        "payload": json.dumps(payload, sort_keys=True, default=str),
        "priority": 5 if event_type == "gpu_exclusive_refused" else 1,
    }
    req = urllib.request.Request(
        SURREAL_URL,
        data=f"CREATE data_product_event CONTENT {json.dumps(row)};".encode(),
        method="POST",
        headers={
            "Accept": "application/json",
            "surreal-ns": "cohezion",
            "surreal-db": "main",
            "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as r:  # noqa: S310
            body = json.loads(r.read())
    except Exception as exc:
        logger.debug("gpu_exclusive: emit %s failed: %s", event_type, exc)
        return False
    # SurrealDB answers HTTP 200 for statement errors; the status lives in the body.
    ok = isinstance(body, list) and bool(body) and all(s.get("status") == "OK" for s in body)
    ok = ok and bool(body[0].get("result"))
    if not ok:
        logger.warning("gpu_exclusive: event %s rejected: %s", event_type, str(body)[:200])
    return ok


def _write_state(path: Path, state: dict) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(state, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _gtt_used_gb() -> float | None:
    paths = list(Path("/sys/class/drm").glob("card*/device/mem_info_gtt_used"))
    try:
        return sum(int(p.read_text()) for p in paths) / 2**30 if paths else None
    except OSError:
        return None


def _restore(state: dict) -> None:
    """Put back exactly what the state file recorded, then verify through lemonade."""
    globals_ = state.get("globals", {})
    if globals_:
        _lemonade("POST", "/internal/set", {s: {"backend": v} for s, v in globals_.items()})
    for mid, keys in state.get("models", {}).items():
        body = {k: (e["value"] if e["had"] else None) for k, e in keys.items()}
        _lemonade("POST", _options_path(mid), body)
    cfg = _lemonade("GET", "/internal/config")
    bad = [s for s, v in globals_.items() if cfg.get(s, {}).get("backend") != v]
    for mid, keys in state.get("models", {}).items():
        saved = _lemonade("GET", _options_path(mid)).get("saved") or {}
        for k, e in keys.items():
            if (saved.get(k) != e["value"]) if e["had"] else (k in saved):
                bad.append(f"{mid}:{k}")
    if bad:
        raise RuntimeError(f"restore did not verify: {bad}")


def _restore_and_clear(state_path: Path, state: dict) -> bool:
    try:
        _restore(state)
    except Exception as exc:
        logger.error("gpu_exclusive: restore FAILED, state kept at %s: %s", state_path, exc)
        return False
    state_path.unlink(missing_ok=True)
    return True


def _apply_cpu_mode(state: dict, state_path: Path, allow_unguarded: bool) -> None:
    cfg = _lemonade("GET", "/internal/config")
    recipes = _lemonade("GET", "/api/v1/system-info").get("recipes", {})
    guarded, unguarded, cpu_recipes = {}, [], set()
    for section, val in cfg.items():
        if not (isinstance(val, dict) and "backend" in val):
            continue
        recipe = next((r for r in recipes if r.replace("-", "") == section), None)
        backends = recipes.get(recipe, {}).get("backends", {}) if recipe else {}
        loadable = {b for b, i in backends.items() if i.get("state") in _LOADABLE}
        if CPU in loadable:
            guarded[section] = val["backend"]
            cpu_recipes.add(recipe)
        elif loadable or recipe is None:  # GPU-only, or unknown to system-info
            unguarded.append(section)
    if "llamacpp" not in guarded:
        # Unexpected config shape or no installed cpu backend: a grant would let the fleet
        # reload onto the GPU mid-job, so fail closed before changing anything.
        raise GpuExclusiveRefusedError(
            f"llamacpp backend cannot be redirected to cpu: {cfg.get('llamacpp')!r}"
        )
    if unguarded and not allow_unguarded:
        raise GpuExclusiveRefusedError(
            f"sections {unguarded} have a GPU backend but no installed cpu backend; their "
            "loads would land on the iGPU. Install the cpu backend or pass allow_unguarded"
        )
    state.update(globals=guarded, unguarded=unguarded)
    _write_state(state_path, state)  # durable BEFORE the first mutation
    if guarded:
        _lemonade("POST", "/internal/set", {s: {"backend": CPU} for s in guarded})
    for m in _lemonade("GET", "/api/v1/models?show_all=true").get("data", []):
        if m.get("recipe") not in cpu_recipes:
            continue
        opts = _lemonade("GET", _options_path(m["id"]))
        saved = opts.get("saved") or {}
        for key, val in (opts.get("effective") or {}).items():
            if key.endswith("_backend") and val != CPU:
                entry = {"had": key in saved, "value": saved.get(key)}
                state["models"].setdefault(m["id"], {})[key] = entry
                _write_state(state_path, state)
                _lemonade("POST", _options_path(m["id"]), {key: CPU})


def _gpu_residents() -> list[dict] | None:
    """Residents holding the iGPU (hybrid 'gpu npu' included; FLM/NPU-only excluded)."""
    res = hotswap.resident_models_or_none()
    if res is None:
        return None
    return [
        m
        for m in res
        if m.get("recipe") != "flm" and set(str(m.get("device", "")).split()) & _GPU_TOKENS
    ]


def _unload_idle(res: list[dict]) -> int:
    """Unload non-busy residents; a busy one has live requests and is retried later."""
    idle = [m["model_name"] for m in res if not m.get("is_busy")]
    for mid in idle:
        hotswap.unload(mid)
    return len(idle)


def _clear_gpu(need_gb: float) -> int:
    """Unload GPU residents until the census stays clean for SETTLE_S and memory fits."""
    deadline, unloaded, clean_since = time.monotonic() + DEADLINE_S, 0, None
    while True:
        res, mem = _gpu_residents(), hotswap.free_gb_or_none()
        now = time.monotonic()
        if res == [] and mem is not None and mem >= need_gb + hotswap.RAM_FLOOR_GB:
            clean_since = now if clean_since is None else clean_since
            if now - clean_since >= SETTLE_S:
                return unloaded
        else:
            clean_since = None
        if now >= deadline:
            names = [(m["model_name"], "busy" if m.get("is_busy") else "idle") for m in res or []]
            raise GpuExclusiveRefusedError(
                f"GPU residents={names} MemAvailable={mem} GB, need {need_gb}+"
                f"{hotswap.RAM_FLOOR_GB} GB floor"
            )
        unloaded += _unload_idle(res or [])
        time.sleep(POLL_S)


def _watch(stop: threading.Event, guarded: list[str], stats: dict) -> None:
    """While the grant holds: re-assert cpu mode, evict late GPU loads, track memory."""
    while not stop.wait(WATCH_S):
        try:
            cfg = _lemonade("GET", "/internal/config")
            reverted = [s for s in guarded if cfg.get(s, {}).get("backend") != CPU]
            if reverted:
                logger.warning("gpu_exclusive: %s reverted from cpu; re-applying", reverted)
                _lemonade("POST", "/internal/set", {s: {"backend": CPU} for s in reverted})
                stats["reapplied"] += len(reverted)
            late = _gpu_residents() or []
            if late:
                logger.warning("gpu_exclusive: late GPU residents %s", late)
                stats["late_unloads"] += _unload_idle(late)
                stats["late_busy"] += sum(1 for m in late if m.get("is_busy"))
            mem = hotswap.free_gb_or_none()
            if mem is not None:
                cur = stats["min_mem_available_gb"]
                stats["min_mem_available_gb"] = mem if cur is None else min(cur, mem)
                if mem < hotswap.RAM_FLOOR_GB:
                    logger.warning("gpu_exclusive: MemAvailable %.1f GB below floor", mem)
        except Exception as exc:
            logger.warning("gpu_exclusive: watcher tick failed: %s", exc)


@contextmanager
def _flock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _pidns() -> str:
    try:
        return os.readlink("/proc/self/ns/pid")
    except OSError:
        return ""


def recover(state_path: Path, force: bool = False) -> bool:
    """Restore a crashed holder's settings. Caller must hold the flock."""
    if not state_path.exists():
        return True
    state = json.loads(state_path.read_text())
    pgid = state.get("child_pgid")
    if pgid and not force and (not state.get("pidns") or state.get("pidns") != _pidns()):
        # Another pid namespace: killpg cannot see the job, so liveness is UNKNOWN.
        logger.error(
            "gpu_exclusive: crashed holder's job %s ran in pid namespace %s (here %s); "
            "keeping cpu mode - use --recover --force once the job is known gone",
            pgid,
            state.get("pidns"),
            _pidns(),
        )
        return False
    if pgid and not force:
        try:
            os.killpg(int(pgid), 0)
        except ProcessLookupError:
            pass
        except PermissionError:
            logger.error("gpu_exclusive: crashed holder's job group %s still exists", pgid)
            return False
        else:
            # The wrapper died (SIGKILL/OOM) but its job still runs on the GPU: keep cpu mode.
            # Cannot see across pid namespaces; a job in another namespace reads as gone.
            logger.error("gpu_exclusive: crashed holder's job group %s still running", pgid)
            return False
    logger.warning("gpu_exclusive: restoring settings left by a crashed holder")
    return _restore_and_clear(state_path, state)


@contextmanager
def gpu_exclusive(holder: str, need_gb: float, allow_unguarded: bool = False) -> Iterator[dict]:
    lock_path, state_path = Path(LOCK_PATH), Path(STATE_PATH)
    base = {"holder": holder, "need_gb": need_gb, "pid": os.getpid()}
    emit("gpu_exclusive_requested", base)
    with _flock(lock_path):
        if not recover(state_path):
            emit("gpu_exclusive_refused", {**base, "reason": "crash recovery failed"})
            raise GpuExclusiveRefusedError(f"cannot restore prior state from {state_path}")
        state: dict = {**base, "started": time.time(), "globals": {}, "models": {}}
        gtt_before = _gtt_used_gb()
        try:
            _apply_cpu_mode(state, state_path, allow_unguarded)
            unloaded = _clear_gpu(need_gb)
        except BaseException as exc:  # SIGTERM/SIGHUP (SystemExit), Ctrl-C included
            restored = _restore_and_clear(state_path, state)
            emit("gpu_exclusive_refused", {**base, "reason": repr(exc), "restored": restored})
            if isinstance(exc, GpuExclusiveRefusedError) or not isinstance(exc, Exception):
                raise
            raise GpuExclusiveRefusedError(str(exc)) from exc
        info = {
            **base,
            "unloaded": unloaded,
            "unguarded": state.get("unguarded", []),
            "allow_unguarded": allow_unguarded,
            "memory_reserved": False,  # need_gb checked at grant only; see module doc
            "gtt_used_gb_before": gtt_before,
            "gtt_used_gb_after": _gtt_used_gb(),
        }

        def record_child(pgid: int) -> None:
            state.update(child_pgid=pgid, pidns=_pidns())
            _write_state(state_path, state)

        logger.info("gpu_exclusive: granted %s", info)
        emit("gpu_exclusive_granted", info)
        stop = threading.Event()
        stats = {"late_unloads": 0, "late_busy": 0, "reapplied": 0, "min_mem_available_gb": None}
        watcher = threading.Thread(
            target=_watch, args=(stop, list(state["globals"]), stats), daemon=True
        )
        watcher.start()
        try:
            yield {**info, "record_child": record_child, "watch": stats}
        finally:
            stop.set()
            watcher.join()  # never let a tick re-flip a setting after restore
            restored = _restore_and_clear(state_path, state)
            emit("gpu_exclusive_released", {**base, **stats, "restored": restored})


def parse_duration(text: str) -> float:
    units = {"s": 1, "m": 60, "h": 3600}
    if text[-1:] in units:
        return float(text[:-1]) * units[text[-1]]
    return float(text)


def _kill_group(proc: subprocess.Popen) -> None:
    for sig, wait in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
            proc.wait(timeout=wait)
            return
        except ProcessLookupError:
            return
        except subprocess.TimeoutExpired:
            continue


def _raise_exit(signum: int, _frame: object) -> None:
    raise SystemExit(128 + signum)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gpu_exclusive", description=__doc__.split("\n")[0])
    p.add_argument("--holder")
    p.add_argument("--need-gb", type=float)
    p.add_argument("--max-hold", default="6h")
    p.add_argument("--recover", action="store_true", help="only restore a crashed state")
    p.add_argument("--force", action="store_true", help="with --recover: ignore job liveness")
    p.add_argument("--allow-unguarded", action="store_true", help="grant despite GPU-only recipes")
    p.add_argument("cmd", nargs=argparse.REMAINDER)
    args = p.parse_args(argv)
    if args.recover:
        with _flock(Path(LOCK_PATH)):
            return 0 if recover(Path(STATE_PATH), force=args.force) else 1
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    if not (args.holder and args.need_gb is not None and cmd):
        p.error("--holder, --need-gb and a command after -- are required")
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, _raise_exit)
    try:
        with gpu_exclusive(args.holder, args.need_gb, args.allow_unguarded) as info:
            proc = subprocess.Popen(cmd, start_new_session=True, close_fds=True)
            info["record_child"](proc.pid)
            try:
                return proc.wait(timeout=parse_duration(args.max_hold))
            except subprocess.TimeoutExpired:
                logger.error("gpu_exclusive: --max-hold exceeded, killing job group")
                _kill_group(proc)
                return 124
            except BaseException:
                _kill_group(proc)
                raise
    except GpuExclusiveRefusedError as exc:
        print(f"gpu_exclusive: refused: {exc}", file=sys.stderr)
        return 75


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sys.exit(main())
