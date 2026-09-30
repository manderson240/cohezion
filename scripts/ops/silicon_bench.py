"""Measure decode/prefill speed of ONE model on ONE Lemonade lane (npu / igpu / cpu) — safely.

Why it exists: lane speeds were quoted from vendor pages measured on other hardware, or from
bandwidth arithmetic. This loads a model on a chosen backend with the first-party ``lemonade load``
options, times a fixed prompt, and records the row. It REFUSES to run (status "skipped") rather than
score a refusal as a slow result, in exactly the cases that burned this fleet before:
  * free RAM would drop below the 16 GB admission floor (+ margin) — a load would be refused/evicting;
  * the model is already resident (never reload or re-backend someone else's model);
  * an NPU load while another FLM model is resident (the NPU is single-slot: a swap stalls the router).
It never passes --save-options, so a benchmark cannot change how a model loads for anyone else.

Usage: python scripts/ops/silicon_bench.py MODEL --lane cpu [--threads 12] [--ctx 8192] [--allow-npu-swap]
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROUTER = "http://localhost:13305"
FLOOR_GB, MARGIN_GB = 16.0, 2.0
OUT = Path(__file__).resolve().parents[2] / ".cache" / "silicon_bench.jsonl"
PROMPT = (
    "List the planets of the solar system in order from the sun, one per line, with one fact each."
)


def avail_gb() -> float:
    line = next(
        ln for ln in Path("/proc/meminfo").read_text().splitlines() if ln.startswith("MemAvailable")
    )
    return int(line.split()[1]) / 2**20


def headroom_ok(
    avail: float, size_gb: float, floor: float = FLOOR_GB, margin: float = MARGIN_GB
) -> bool:
    """True iff loading ``size_gb`` still leaves the admission floor plus a margin free."""
    return avail - size_gb >= floor + margin - 1e-9  # epsilon: 35.3 - 17.3 != 18.0 in floats


def load_cmd(model: str, lane: str, ctx: int, threads: int | None) -> list[str]:
    """First-party ``lemonade load`` command for a lane. Never includes --save-options."""
    cmd = ["lemonade", "load", model, "--ctx-size", str(ctx)]
    if lane == "cpu":
        cmd += ["--llamacpp", "cpu"] + (["--llamacpp-args", f"-t {threads}"] if threads else [])
    elif lane == "igpu":
        cmd += ["--llamacpp", "vulkan"]
    return cmd  # lane == "npu": FLM models are NPU by recipe; nothing to select


def speeds(resp: dict, wall_s: float) -> dict:
    """decode/prefill tok/s from a chat completion. llama.cpp reports ``timings``; FLM does not, so
    fall back to wall-clock over completion tokens (marked method='wall', decode-inclusive)."""
    t = resp.get("timings")
    if t and t.get("predicted_per_second"):
        return {
            "decode_tps": t["predicted_per_second"],
            "prefill_tps": t.get("prompt_per_second"),
            "method": "timings",
        }
    n = (resp.get("usage") or {}).get("completion_tokens") or 0
    return {
        "decode_tps": n / wall_s if wall_s and n else None,
        "prefill_tps": None,
        "method": "wall",
    }


def _get(path: str) -> dict:
    with urllib.request.urlopen(ROUTER + path, timeout=15) as r:  # noqa: S310 - fixed localhost router
        return json.load(r)


def _chat(model: str, n_predict: int) -> tuple[dict, float]:
    body = {
        "model": model, "temperature": 0, "max_tokens": n_predict, "messages": [{"role": "user", "content": PROMPT}],
        "chat_template_kwargs": {"enable_thinking": False},
    }  # fmt: skip
    req = urllib.request.Request(  # noqa: S310
        ROUTER + "/v1/chat/completions",
        json.dumps(body).encode(),
        {"Content-Type": "application/json"},
    )
    t = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:  # noqa: S310
        return json.load(r), time.time() - t


def bench(
    model: str, lane: str, ctx: int, threads: int | None, n_predict: int, allow_npu_swap: bool
) -> dict:
    row = {
        "ts": time.strftime("%FT%T"),
        "model": model,
        "lane": lane,
        "ctx": ctx,
        "threads": threads,
    }
    try:
        size = next(
            m["size"] for m in _get("/api/v1/models?show_all=true")["data"] if m["id"] == model
        )
        resident = {m["model_name"]: m for m in _get("/api/v1/health")["all_models_loaded"]}
    except Exception as exc:
        return {**row, "status": "skipped", "reason": f"router unreachable: {type(exc).__name__}"}
    if model in resident:
        return {
            **row,
            "status": "skipped",
            "reason": "already resident (not reloading another session's model)",
        }
    if (
        lane == "npu"
        and any(m["device"] == "npu" for m in resident.values())
        and not allow_npu_swap
    ):
        return {
            **row,
            "status": "skipped",
            "reason": "NPU is single-slot and occupied; pass --allow-npu-swap",
        }
    a = avail_gb()
    if not headroom_ok(a, size):
        return {
            **row,
            "status": "skipped",
            "reason": f"headroom: {a:.1f} GB free, need {size:.1f}+{FLOOR_GB + MARGIN_GB:.0f}",
        }
    t = time.time()
    p = subprocess.run(
        load_cmd(model, lane, ctx, threads), capture_output=True, text=True, timeout=900
    )
    if p.returncode:
        return {**row, "status": "load_failed", "detail": (p.stdout + p.stderr)[-200:]}
    row.update(
        load_s=round(time.time() - t),
        avail_before_gb=round(a, 1),
        avail_after_gb=round(avail_gb(), 1),
    )
    try:
        _chat(model, 16)  # warm-up (kernel compile / cache fill) — never scored
        runs = [speeds(*_chat(model, n_predict)) for _ in range(3)]
        dec = [r["decode_tps"] for r in runs if r["decode_tps"]]
        pre = [r["prefill_tps"] for r in runs if r["prefill_tps"]]
        row.update(status="ok", method=runs[0]["method"], decode_tps=round(statistics.median(dec), 2) if dec else None,
                   prefill_tps=round(statistics.median(pre), 1) if pre else None, n_runs=len(dec))  # fmt: skip
    finally:
        subprocess.run(["lemonade", "unload", model], capture_output=True, timeout=120)
    return row


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("model")
    ap.add_argument("--lane", choices=("npu", "igpu", "cpu"), required=True)
    ap.add_argument("--ctx", type=int, default=8192)
    ap.add_argument("--threads", type=int)
    ap.add_argument("--n-predict", type=int, default=128)
    ap.add_argument("--allow-npu-swap", action="store_true")
    a = ap.parse_args(argv)
    row = bench(a.model, a.lane, a.ctx, a.threads, a.n_predict, a.allow_npu_swap)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(json.dumps(row))
    return 0 if row["status"] in ("ok", "skipped") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
