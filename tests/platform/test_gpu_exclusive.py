"""Tests for cohezion.platform.gpu_exclusive.

Everything runs against a recording FAKE lemonade (+ fake SurrealDB /sql) bound to
127.0.0.1 on an ephemeral port. No test touches the live lemond, :13305 or :13315.
The fake implements lemonade's documented option resolution: a concrete per-model
``*_backend`` (saved layer, then registry layer) wins over the global ``<section>.backend``;
``"auto"``/``""`` fall through to the global key.
"""

from __future__ import annotations

import copy
import fcntl
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

import pytest

from cohezion.inference import hotswap
from cohezion.platform import gpu_exclusive as gx


SECTION_OF = {"llamacpp": "llamacpp", "sd-cpp": "sdcpp", "whispercpp": "whispercpp", "vllm": "vllm"}


class FakeLemonade:
    def __init__(self) -> None:
        self.config = {
            "port": 13315,
            "llamacpp": {"backend": "vulkan", "args": ""},
            "sdcpp": {"backend": "auto", "steps": 20},
            "whispercpp": {"backend": "auto"},
            "vllm": {"backend": "auto"},
        }
        self.sysinfo = {
            "recipes": {
                "llamacpp": {
                    "backends": {"cpu": {"state": "installed"}, "vulkan": {"state": "installed"}}
                },
                "sd-cpp": {
                    "backends": {
                        "cpu": {"state": "update_required"},
                        "vulkan": {"state": "installed"},
                    }
                },
                "whispercpp": {
                    "backends": {"cpu": {"state": "installed"}, "vulkan": {"state": "installed"}}
                },
                "vllm": {"backends": {"rocm": {"state": "installed"}}},
                "flm": {"backends": {"npu": {"state": "installed"}}},
            }
        }
        # model -> recipe; registry-layer options; saved (recipe_options.json) layer
        self.models = {
            "Bonsai-8B-gguf": "llamacpp",
            "Gemma-4-E2B-it-GGUF": "llamacpp",
            "Tier0-GGUF": "llamacpp",
            "user.Coder": "llamacpp",
            "whisper-v3": "whispercpp",
            "qwen3-1.7b-FLM": "flm",
        }
        self.registry = {"user.Coder": {"llamacpp_backend": "rocm"}}
        self.saved = {
            "Gemma-4-E2B-it-GGUF": {"llamacpp_backend": "rocm", "ctx_size": 8192},
            "Tier0-GGUF": {"llamacpp_backend": "auto", "ctx_size": 4096},
        }
        self.loaded = [
            {"model_name": "Bonsai-8B-gguf", "recipe": "llamacpp", "device": "gpu", "loaded": True},
            {"model_name": "whisper-v3", "recipe": "whispercpp", "device": "igpu", "loaded": True},
            {"model_name": "qwen3-1.7b-FLM", "recipe": "flm", "device": "npu", "loaded": True},
            {"model_name": "cpu-model", "recipe": "llamacpp", "device": "cpu", "loaded": True},
        ]
        self.sticky: dict[str, int] = {}  # model -> number of unloads it ignores
        self.sql_response: list = [{"status": "OK", "result": [{"id": "data_product_event:1"}]}]
        self.requests: list[tuple[str, str, object]] = []
        self.fail_set = False

    # -- lemonade resolution ------------------------------------------------
    def effective(self, mid: str) -> dict:
        recipe = self.models[mid]
        key = f"{recipe.replace('-', '')}_backend"
        section = SECTION_OF.get(recipe, recipe)
        val = None
        for layer in (self.saved.get(mid, {}), self.registry.get(mid, {})):
            v = layer.get(key)
            if v not in (None, "", "auto"):
                val = v
                break
        if val is None:
            val = self.config.get(section, {}).get("backend", "")
        return {key: val, "model_name": mid}

    def handle(self, method: str, path: str, body):
        self.requests.append((method, path, body))
        if path == "/internal/config":
            return 200, copy.deepcopy(self.config)
        if path == "/internal/set":
            if self.fail_set:
                return 500, {"error": "boom"}
            for section, vals in body.items():
                if "backend" in vals and vals["backend"] == "cpu":
                    recipe = next(r for r, s in SECTION_OF.items() if s == section)
                    if "cpu" not in self.sysinfo["recipes"][recipe]["backends"]:
                        return 400, {"error": f"{section}.backend must be one of auto,..."}
            for section, vals in body.items():
                self.config.setdefault(section, {}).update(vals)
            return 200, {"status": "success", "updated": body}
        if path == "/api/v1/system-info":
            return 200, self.sysinfo
        if path == "/api/v1/models":
            return 200, {"data": [{"id": m, "recipe": r} for m, r in self.models.items()]}
        if path.startswith("/api/v1/models/") and path.endswith("/options"):
            mid = unquote(path[len("/api/v1/models/") : -len("/options")])
            if method == "POST":
                entry = self.saved.setdefault(mid, {})
                for k, v in body.items():
                    if v is None:
                        entry.pop(k, None)
                    else:
                        entry[k] = v
            return 200, {
                "model_name": mid,
                "saved": copy.deepcopy(self.saved.get(mid, {})),
                "effective": self.effective(mid),
            }
        if path == "/api/v1/health":
            return 200, {"status": "ok", "all_models_loaded": copy.deepcopy(self.loaded)}
        if path == "/api/v1/unload":
            mid = body["model_name"]
            if self.sticky.get(mid, 0) > 0:
                self.sticky[mid] -= 1
                return 200, {"status": "success"}
            self.loaded = [m for m in self.loaded if m["model_name"] != mid]
            return 200, {"status": "success"}
        if path == "/sql":
            return 200, self.sql_response
        return 404, {"error": "not found"}


@pytest.fixture
def fake(tmp_path, monkeypatch):
    lem = FakeLemonade()

    class Handler(BaseHTTPRequestHandler):
        def _do(self, method):
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b""
            body = raw.decode() if self.path == "/sql" else (json.loads(raw) if raw else None)
            status, out = lem.handle(method, self.path, body)
            data = json.dumps(out).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._do("GET")

        def do_POST(self):
            self._do("POST")

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    monkeypatch.setattr(hotswap, "LEMONADE_BASE", base)
    monkeypatch.setattr(gx, "SURREAL_URL", f"{base}/sql")
    monkeypatch.setattr(gx, "LOCK_PATH", tmp_path / "gpu-exclusive.lock")
    monkeypatch.setattr(gx, "STATE_PATH", tmp_path / "gpu-exclusive.state.json")
    monkeypatch.setattr(hotswap, "free_gb_or_none", lambda: 64.0)
    monkeypatch.setattr(gx, "POLL_S", 0.01)
    yield lem
    srv.shutdown()


def _nonempty(saved: dict) -> dict:
    # Removing a key with null may leave an empty entry; that is equivalent to no entry.
    return {k: v for k, v in saved.items() if v}


def _baseline(lem: FakeLemonade):
    return copy.deepcopy(lem.config), copy.deepcopy(lem.saved)


def test_settings_saved_before_change_and_restored_exactly(fake):
    cfg0, saved0 = _baseline(fake)
    seen_state = {}
    with gx.gpu_exclusive("test", need_gb=8) as info:
        # During the job: every cpu-capable recipe defaults to cpu ...
        assert fake.config["llamacpp"]["backend"] == "cpu"
        assert fake.config["whispercpp"]["backend"] == "cpu"
        # ... recipes with no INSTALLED cpu backend are left alone and reported
        assert fake.config["sdcpp"]["backend"] == "auto"
        assert fake.config["vllm"]["backend"] == "auto"
        assert set(info["unguarded"]) == {"sdcpp", "vllm"}
        # ... and every downloaded cpu-capable model now resolves to cpu
        for mid, recipe in fake.models.items():
            if recipe in ("llamacpp", "whispercpp"):
                assert next(iter(fake.effective(mid).values())) == "cpu", mid
        seen_state = json.loads(gx.STATE_PATH.read_text())
    assert seen_state["globals"]["llamacpp"] == "vulkan"
    # state was durable BEFORE the first mutating call
    first_set = next(i for i, r in enumerate(fake.requests) if r[1] == "/internal/set")
    assert first_set > 0
    assert fake.config == cfg0
    assert _nonempty(fake.saved) == saved0
    assert not gx.STATE_PATH.exists()


def test_state_file_written_before_any_mutation(fake, monkeypatch):
    real_write = gx._write_state
    mutations_before_write: list[int] = []

    def spy(path, state):
        mutations_before_write.append(
            sum(1 for m, p, _ in fake.requests if m == "POST" and p != "/sql")
        )
        real_write(path, state)

    monkeypatch.setattr(gx, "_write_state", spy)
    with gx.gpu_exclusive("test", need_gb=1):
        pass
    assert mutations_before_write[0] == 0


def test_per_model_pins_auto_untouched_concrete_pinned_and_restored(fake):
    saved0 = copy.deepcopy(fake.saved)
    with gx.gpu_exclusive("test", need_gb=1):
        # "auto" defers to the global key -> never touched
        assert fake.saved["Tier0-GGUF"] == {"llamacpp_backend": "auto", "ctx_size": 4096}
        # concrete saved pin overridden in the saved layer, other options preserved
        assert fake.saved["Gemma-4-E2B-it-GGUF"] == {"llamacpp_backend": "cpu", "ctx_size": 8192}
        # registry-layer pin overridden by a saved-layer entry
        assert fake.saved["user.Coder"] == {"llamacpp_backend": "cpu"}
    assert fake.saved["Gemma-4-E2B-it-GGUF"] == {"llamacpp_backend": "rocm", "ctx_size": 8192}
    # key was ABSENT in the saved layer -> removed again (null), not set to a value
    assert "llamacpp_backend" not in fake.saved.get("user.Coder", {})
    assert _nonempty(fake.saved) == saved0
    assert not any(m == "DELETE" for m, _, _ in fake.requests)


def test_crash_recovery_restores_from_state_file_before_new_baseline(fake):
    # A previous wrapper crashed mid-job: lemonade is left at cpu, state file holds truth.
    fake.config["llamacpp"]["backend"] = "cpu"
    fake.saved["Gemma-4-E2B-it-GGUF"]["llamacpp_backend"] = "cpu"
    gx.STATE_PATH.write_text(
        json.dumps(
            {
                "holder": "crashed",
                "globals": {"llamacpp": "vulkan"},
                "models": {
                    "Gemma-4-E2B-it-GGUF": {"llamacpp_backend": {"had": True, "value": "rocm"}}
                },
            }
        )
    )
    with gx.gpu_exclusive("test", need_gb=1):
        state = json.loads(gx.STATE_PATH.read_text())
        # the new baseline is the RESTORED value, not the crashed job's cpu
        assert state["globals"]["llamacpp"] == "vulkan"
        assert state["models"]["Gemma-4-E2B-it-GGUF"]["llamacpp_backend"]["value"] == "rocm"
    assert fake.config["llamacpp"]["backend"] == "vulkan"
    assert fake.saved["Gemma-4-E2B-it-GGUF"]["llamacpp_backend"] == "rocm"
    assert not gx.STATE_PATH.exists()


def test_recover_cli_restores_without_running_a_job(fake):
    fake.config["llamacpp"]["backend"] = "cpu"
    gx.STATE_PATH.write_text(json.dumps({"globals": {"llamacpp": "vulkan"}, "models": {}}))
    assert gx.main(["--recover"]) == 0
    assert fake.config["llamacpp"]["backend"] == "vulkan"
    assert not gx.STATE_PATH.exists()


def test_unload_loop_retries_until_census_clean(fake):
    fake.sticky["Bonsai-8B-gguf"] = 2  # ignores two unloads (phantom 200s)
    with gx.gpu_exclusive("test", need_gb=1) as info:
        names = {m["model_name"] for m in fake.loaded}
        assert "Bonsai-8B-gguf" not in names and "whisper-v3" not in names
        # NPU/FLM and CPU residents are never unloaded
        assert {"qwen3-1.7b-FLM", "cpu-model"} <= names
        assert info["unloaded"] >= 2
    unloads = [b["model_name"] for m, p, b in fake.requests if p == "/api/v1/unload"]
    assert unloads.count("Bonsai-8B-gguf") == 3
    assert "qwen3-1.7b-FLM" not in unloads


def test_refusal_restores_settings_when_census_never_clears(fake, monkeypatch):
    monkeypatch.setattr(gx, "DEADLINE_S", 0.2)
    fake.sticky["Bonsai-8B-gguf"] = 10**6
    cfg0, saved0 = _baseline(fake)
    ran = False
    with pytest.raises(gx.GpuExclusiveRefusedError), gx.gpu_exclusive("test", need_gb=1):
        ran = True
    assert not ran
    assert fake.config == cfg0 and _nonempty(fake.saved) == saved0
    assert not gx.STATE_PATH.exists()
    events = [b for m, p, b in fake.requests if p == "/sql"]
    assert any("gpu_exclusive_refused" in e for e in events)


def test_refusal_when_memory_below_need_plus_floor(fake, monkeypatch):
    monkeypatch.setattr(gx, "DEADLINE_S", 0.1)
    monkeypatch.setattr(hotswap, "free_gb_or_none", lambda: 20.0)  # need 8 + 16 floor = 24
    cfg0, _ = _baseline(fake)
    with (
        pytest.raises(gx.GpuExclusiveRefusedError, match="MemAvailable"),
        gx.gpu_exclusive("test", need_gb=8),
    ):
        pass
    assert fake.config == cfg0


def test_lock_not_inherited_by_child_and_released(fake, tmp_path):
    pidfile = tmp_path / "grandchild.pid"
    # The command exits at once but leaves a grandchild running in its process group.
    rc = gx.main(
        ["--holder", "t", "--need-gb", "1", "--", "sh", "-c", f"sleep 30 & echo $! > {pidfile}"]
    )
    assert rc == 0
    gpid = int(pidfile.read_text())
    try:
        os.kill(gpid, 0)  # still alive
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                "import fcntl,os,sys;fd=os.open(sys.argv[1],os.O_RDWR);"
                "fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);print('ok')",
                str(gx.LOCK_PATH),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert probe.stdout.strip() == "ok", probe.stderr
    finally:
        os.kill(gpid, 9)


def test_lock_released_with_lock_un_before_close(fake, monkeypatch):
    calls: list[str] = []
    real_flock, real_close = fcntl.flock, os.close
    lock_fd = {}

    def flock(fd, op):
        lock_fd["fd"] = fd
        calls.append("UN" if op == fcntl.LOCK_UN else "EX")
        return real_flock(fd, op)

    def close(fd):
        if fd == lock_fd.get("fd"):
            calls.append("close")
        return real_close(fd)

    monkeypatch.setattr(gx.fcntl, "flock", flock)
    monkeypatch.setattr(gx.os, "close", close)
    with gx.gpu_exclusive("test", need_gb=1):
        pass
    assert calls == ["EX", "UN", "close"]


def test_max_hold_kills_process_group_then_restores(fake, monkeypatch):
    cfg0, _ = _baseline(fake)
    t0 = time.monotonic()
    rc = gx.main(["--holder", "t", "--need-gb", "1", "--max-hold", "1s", "--", "sleep", "30"])
    assert rc == 124
    assert time.monotonic() - t0 < 20
    assert fake.config == cfg0


def test_child_exit_code_propagates_and_events_emitted(fake):
    rc = gx.main(["--holder", "t", "--need-gb", "1", "--", "sh", "-c", "exit 3"])
    assert rc == 3
    sql = [b for m, p, b in fake.requests if p == "/sql"]
    kinds = [k for k in gx.EVENT_TYPES for s in sql if f'"{k}"' in s]
    assert kinds == ["gpu_exclusive_requested", "gpu_exclusive_granted", "gpu_exclusive_released"]
    assert all("CREATE data_product_event CONTENT" in s for s in sql)


def test_emit_counts_statement_error_with_http_200_as_failure(fake):
    fake.sql_response = [{"status": "ERR", "result": "Couldn't coerce value for field `timestamp`"}]
    assert gx.emit("gpu_exclusive_requested", {"holder": "t"}) is False
    fake.sql_response = [{"status": "OK", "result": [{"id": "x"}]}]
    assert gx.emit("gpu_exclusive_requested", {"holder": "t"}) is True


def test_emit_fails_open_when_surreal_unreachable(monkeypatch):
    monkeypatch.setattr(gx, "SURREAL_URL", "http://127.0.0.1:9/sql")
    assert gx.emit("gpu_exclusive_requested", {}) is False


def test_restore_failure_keeps_state_file_for_next_start(fake):
    with gx.gpu_exclusive("test", need_gb=1):
        fake.fail_set = True
    assert gx.STATE_PATH.exists()  # crash-safe: next wrapper restores from it
    fake.fail_set = False
    assert gx.main(["--recover"]) == 0
    assert fake.config["llamacpp"]["backend"] == "vulkan"


def test_parse_duration():
    assert gx.parse_duration("6h") == 21600
    assert gx.parse_duration("90m") == 5400
    assert gx.parse_duration("45") == 45
    assert gx.parse_duration("2s") == 2


def test_no_live_endpoint_in_defaults_used_by_tests(fake):
    assert ":13305" not in hotswap.LEMONADE_BASE and ":13315" not in hotswap.LEMONADE_BASE
    assert Path(gx.LOCK_PATH).parent != Path.home() / "dev" / "cohezion" / ".cache"


def test_child_does_not_receive_the_lock_fd(fake, tmp_path):
    # LOCK_UN releases the open file description even if a child held a dup, so the
    # release test alone cannot see inheritance; inspect the child's fd table directly.
    out = tmp_path / "fds.txt"
    script = f"for f in /proc/self/fd/*; do readlink $f; done > {out}; true"
    assert gx.main(["--holder", "t", "--need-gb", "1", "--", "sh", "-c", script]) == 0
    assert str(gx.LOCK_PATH) not in out.read_text()


def test_refuses_when_llamacpp_cannot_be_redirected(fake):
    # If the main LLM recipe is not guardable (no installed cpu backend, or an unexpected
    # config shape), a grant would let the fleet reload onto the GPU mid-job: fail closed.
    fake.sysinfo["recipes"]["llamacpp"]["backends"].pop("cpu")
    cfg0, _ = _baseline(fake)
    with pytest.raises(gx.GpuExclusiveRefusedError, match="llamacpp"), gx.gpu_exclusive("t", 1):
        pass
    assert fake.config == cfg0
    assert not any(p == "/api/v1/unload" for _, p, _ in fake.requests)


def test_recovery_refuses_while_crashed_holders_job_is_still_running(fake):
    # Wrapper SIGKILLed: lock released, but its job (own session) still runs on the GPU.
    job = subprocess.Popen(["sleep", "30"], start_new_session=True)
    try:
        fake.config["llamacpp"]["backend"] = "cpu"
        gx.STATE_PATH.write_text(
            json.dumps({"globals": {"llamacpp": "vulkan"}, "models": {}, "child_pgid": job.pid})
        )
        with pytest.raises(gx.GpuExclusiveRefusedError), gx.gpu_exclusive("t", 1):
            pass
        assert fake.config["llamacpp"]["backend"] == "cpu"  # NOT restored under a live job
        assert gx.STATE_PATH.exists()
        assert gx.main(["--recover"]) == 1
    finally:
        job.kill()
        job.wait()
    assert gx.main(["--recover"]) == 0  # job gone -> restore proceeds
    assert fake.config["llamacpp"]["backend"] == "vulkan"


def test_cli_records_child_pgid_in_state_during_the_job(fake, tmp_path):
    out = tmp_path / "state.json"
    rc = gx.main(
        ["--holder", "t", "--need-gb", "1", "--", "sh", "-c", f"cat {gx.STATE_PATH} > {out}"]
    )
    assert rc == 0
    assert isinstance(json.loads(out.read_text()).get("child_pgid"), int)
