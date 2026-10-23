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

Known limits (documented, not enforced): a ``/v1/load`` that passes ``llamacpp_backend``
explicitly outranks everything (lemonade_server_mcp.py, apply_lemonade_recipes.py; the
latter's ``save_options`` also replaces the saved entry). Recipes with no INSTALLED cpu
backend (vllm, acestep, ...) cannot be redirected; they are reported as ``unguarded``.
On-disk persistence of /internal/set is from source; lemond's config dir is not readable
here, so the state-file restore at the next start is what covers a restart. A crash
mid-job leaves backend=cpu: the safe direction.
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
DEADLINE_S = 180.0
POLL_S = 2.0
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
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
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


def _apply_cpu_mode(state: dict, state_path: Path) -> None:
    cfg = _lemonade("GET", "/internal/config")
    recipes = _lemonade("GET", "/api/v1/system-info").get("recipes", {})
    guarded, unguarded, cpu_recipes = {}, [], set()
    for section, val in cfg.items():
        if not (isinstance(val, dict) and "backend" in val):
            continue
        recipe = next((r for r in recipes if r.replace("-", "") == section), section)
        cpu = recipes.get(recipe, {}).get("backends", {}).get(CPU, {})
        if cpu.get("state") == "installed":
            guarded[section] = val["backend"]
            cpu_recipes.add(recipe)
        else:
            unguarded.append(section)
    state.update(globals=guarded, unguarded=unguarded)
    _write_state(state_path, state)  # durable BEFORE the first mutation
    if guarded:
        _lemonade("POST", "/internal/set", {s: {"backend": CPU} for s in guarded})
    for m in _lemonade("GET", "/api/v1/models").get("data", []):
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


def _gpu_residents() -> list[str] | None:
    res = hotswap.resident_models_or_none()
    if res is None:
        return None
    out = []
    for m in res:
        tokens = set(str(m.get("device", "")).split())
        if m.get("recipe") != "flm" and "npu" not in tokens and tokens & _GPU_TOKENS:
            out.append(m["model_name"])
    return out


def _clear_gpu(need_gb: float) -> int:
    """Unload GPU residents until census is clean and memory fits; returns unload count."""
    deadline, unloaded = time.monotonic() + DEADLINE_S, 0
    while True:
        res, mem = _gpu_residents(), hotswap.free_gb_or_none()
        if res == [] and mem is not None and mem >= need_gb + hotswap.RAM_FLOOR_GB:
            return unloaded
        if time.monotonic() >= deadline:
            raise GpuExclusiveRefusedError(
                f"GPU residents={res} MemAvailable={mem} GB, need {need_gb}+"
                f"{hotswap.RAM_FLOOR_GB} GB floor"
            )
        for mid in res or []:
            hotswap.unload(mid)
            unloaded += 1
        time.sleep(POLL_S)


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


def recover(state_path: Path) -> bool:
    """Restore a crashed holder's settings. Caller must hold the flock."""
    if not state_path.exists():
        return True
    logger.warning("gpu_exclusive: restoring settings left by a crashed holder")
    return _restore_and_clear(state_path, json.loads(state_path.read_text()))


@contextmanager
def gpu_exclusive(holder: str, need_gb: float) -> Iterator[dict]:
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
            _apply_cpu_mode(state, state_path)
            unloaded = _clear_gpu(need_gb)
        except Exception as exc:
            restored = _restore_and_clear(state_path, state)
            emit("gpu_exclusive_refused", {**base, "reason": str(exc), "restored": restored})
            if isinstance(exc, GpuExclusiveRefusedError):
                raise
            raise GpuExclusiveRefusedError(str(exc)) from exc
        info = {
            **base,
            "unloaded": unloaded,
            "unguarded": state.get("unguarded", []),
            "gtt_used_gb_before": gtt_before,
            "gtt_used_gb_after": _gtt_used_gb(),
        }
        logger.info("gpu_exclusive: granted %s", info)
        emit("gpu_exclusive_granted", info)
        try:
            yield info
        finally:
            restored = _restore_and_clear(state_path, state)
            emit("gpu_exclusive_released", {**base, "restored": restored})


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
    p.add_argument("cmd", nargs=argparse.REMAINDER)
    args = p.parse_args(argv)
    if args.recover:
        with _flock(Path(LOCK_PATH)):
            return 0 if recover(Path(STATE_PATH)) else 1
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    if not (args.holder and args.need_gb is not None and cmd):
        p.error("--holder, --need-gb and a command after -- are required")
    signal.signal(signal.SIGTERM, _raise_exit)
    try:
        with gpu_exclusive(args.holder, args.need_gb):
            proc = subprocess.Popen(cmd, start_new_session=True, close_fds=True)
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
