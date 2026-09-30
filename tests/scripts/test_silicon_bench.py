"""The bench must REFUSE (skip) where a load would be refused/evicting, and never persist options."""

import importlib.util
from pathlib import Path


_spec = importlib.util.spec_from_file_location(
    "silicon_bench", Path(__file__).resolve().parents[2] / "scripts/ops/silicon_bench.py"
)
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)


def _world(monkeypatch, *, size=17.3, resident=(), avail=40.0):
    models = {"data": [{"id": "M", "size": size}]}
    health = {"all_models_loaded": [{"model_name": n, "device": d} for n, d in resident]}
    monkeypatch.setattr(sb, "_get", lambda p: models if "models" in p else health)
    monkeypatch.setattr(sb, "avail_gb", lambda: avail)
    ran = []
    monkeypatch.setattr(
        sb.subprocess,
        "run",
        lambda cmd, **k: (
            ran.append(cmd) or type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        ),
    )
    return ran


def test_sb1_headroom_respects_the_admission_floor_plus_margin():
    assert sb.headroom_ok(40.0, 17.3)
    assert not sb.headroom_ok(33.0, 17.3)  # 15.7 left < 16 floor + 2 margin
    assert sb.headroom_ok(35.3, 17.3)  # exactly 18.0 left


def test_sb2_a_load_that_would_breach_the_floor_is_skipped_not_attempted(monkeypatch):
    ran = _world(monkeypatch, avail=20.0)
    row = sb.bench("M", "cpu", 8192, 12, 64, False)
    assert row["status"] == "skipped" and "headroom" in row["reason"] and ran == []


def test_sb3_a_resident_model_is_never_reloaded(monkeypatch):
    ran = _world(monkeypatch, resident=[("M", "gpu")])
    row = sb.bench("M", "cpu", 8192, None, 64, False)
    assert row["status"] == "skipped" and "resident" in row["reason"] and ran == []


def test_sb4_an_occupied_npu_blocks_an_npu_load_unless_explicitly_allowed(monkeypatch):
    ran = _world(monkeypatch, resident=[("other-FLM", "npu")])
    assert sb.bench("M", "npu", 8192, None, 64, False)["status"] == "skipped" and ran == []


def test_sb5_load_command_selects_the_lane_and_never_saves_options():
    cpu = sb.load_cmd("M", "cpu", 8192, 12)
    assert (
        cpu[:3] == ["lemonade", "load", "M"]
        and cpu[cpu.index("--llamacpp") : cpu.index("--llamacpp") + 2] == ["--llamacpp", "cpu"]
    )
    assert "-t 12" in cpu and "--save-options" not in cpu
    assert "vulkan" in sb.load_cmd("M", "igpu", 8192, None) and "--llamacpp" not in sb.load_cmd(
        "M", "npu", 8192, None
    )
    assert all(
        "--save-options" not in sb.load_cmd("M", lane, 1024, 4) for lane in ("cpu", "igpu", "npu")
    )


def test_sb6_speeds_prefers_llamacpp_timings_and_marks_the_wall_clock_fallback():
    t = {"timings": {"predicted_per_second": 31.5, "prompt_per_second": 220.0}}
    assert sb.speeds(t, 9.0) == {"decode_tps": 31.5, "prefill_tps": 220.0, "method": "timings"}
    w = sb.speeds({"usage": {"completion_tokens": 100}}, 4.0)
    assert w["decode_tps"] == 25.0 and w["method"] == "wall" and w["prefill_tps"] is None
    assert sb.speeds({}, 4.0)["decode_tps"] is None  # no data is None, never 0


def test_sb7_router_unreachable_is_a_skip_not_a_score(monkeypatch):
    def boom(_p):
        raise OSError("down")

    monkeypatch.setattr(sb, "_get", boom)
    assert sb.bench("M", "cpu", 8192, None, 64, False)["status"] == "skipped"
