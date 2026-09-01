# ruff: noqa: I001 - import block is deliberately split by the sys.path setup below.
"""Quality-per-call roster recalibration under CONTROLLED apparatus (protocol 2026-09-01).

Why this exists: lemonade v11.8.0 flipped llama.cpp ``--parallel`` to 1 and changed
per-model arg precedence to REPLACE (not merge) — every quality-per-call ranking
measured before 11.8 ran under unequal effective configs and is untrustworthy
(research digest 20260901-roster-recal-and-prefix-cache-research). Rankings justify
routing, ctx lanes, and MTP decisions, so recalibration is a correctness audit, not
an enhancement (kimi council re-rank, position 0).

Controls held constant per the digest + house memories:
  * exclusive residency (drain before each model — 2026-08-16: +2x latency with peers)
  * ctx fixed (default 16384), never 0 (N3: ctx_size=0 mapped ~120GB GTT)
  * temperature 0 + fixed seed (accepting :13305 is not bit-reproducible)
  * max_tokens 1500 — the thinking-model empty-content trap fires below ~1024
    (memory: local-thinking-model-empty-content-is-instrument-bug)
  * cold trial (first scored call after load+warmup of a DIFFERENT prompt) recorded
    separately from warm trials — the prefix cache makes warm TTFT non-comparable
  * deterministic validators with word boundaries — never bare substring matching
    (metacognitive-calibration: substring passes hallucinate-then-hedge answers)

Usage (run at an IDLE window — this drains the fleet):
  .venv/bin/python scripts/experiments/roster_recalibration.py --reps 4
  .venv/bin/python scripts/experiments/roster_recalibration.py --models Gemma-4-E4B-it-GGUF --reps 2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "experiments"))

from durable_swarm_output import DurableRun  # noqa: E402
from roster_sweep import DEFAULT_ROSTER, _drain, _free_gb, _post, _psi  # noqa: E402

CHAT = "http://localhost:13305/v1/chat/completions"
SEED = 20260901
MAX_TOKENS = 1500


def _word(needle: str, hay: str) -> bool:
    """Word-boundary match, case-insensitive — the anti-substring-trap validator."""
    return re.search(rf"(?<![\w]){re.escape(needle)}(?![\w])", hay, re.IGNORECASE) is not None


def _v_paris(t: str) -> bool:
    return _word("paris", t) and not _word("not paris", t)


def _v_arith(t: str) -> bool:
    return _word("391", t)


def _v_json(t: str) -> bool:
    m = re.search(r"\{[^{}]*\}", t, re.DOTALL)
    if not m:
        return False
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return False
    return d.get("status") == "ok" and d.get("count") == 3


def _v_code(t: str) -> bool:
    m = re.search(r"```(?:python)?\n(.*?)```", t, re.DOTALL)
    src = m.group(1) if m else t
    ns: dict[str, object] = {}
    try:
        exec(compile(src, "<cand>", "exec"), {"__builtins__": __builtins__}, ns)  # noqa: S102
        fn = ns.get("second_largest")
        return callable(fn) and fn([3, 1, 4, 1, 5, 9, 2, 6]) == 6 and fn([7, 7, 3]) == 3
    except Exception:
        return False


def _v_reason(t: str) -> bool:
    return _word("24", t)


# (class, prompt, validator) — one battery, identical presentation for every model.
BATTERY: list[tuple[str, str, object]] = [
    ("categorical", "Answer with one word only. What is the capital of France?", _v_paris),
    ("short_answer", "Compute 17 * 23. Reply with the number only.", _v_arith),
    (
        "structured",
        'Return ONLY a JSON object (no prose, no code fences) with keys "status" set to'
        ' "ok" and "count" set to the number of vowels in the word "banana".',
        _v_json,
    ),
    (
        "code",
        "Write a Python function `second_largest(nums)` returning the second-largest"
        " DISTINCT value in a non-empty list (e.g. [7,7,3] -> 3). Reply with a single"
        " ```python code block and nothing else.",
        _v_code,
    ),
    (
        "reasoning",
        "A tank holds 120 liters. Pump A fills 8 L/min; leak B drains 3 L/min. Both run"
        " from empty. After how many minutes is the tank full? Give the number.",
        _v_reason,
    ),
]

WARMUP_PROMPT = "Reply with the single word: ready."


def _chat(model: str, prompt: str, timeout: int = 600) -> dict:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "seed": SEED,
            "max_tokens": MAX_TOKENS,
        }
    ).encode()
    req = urllib.request.Request(CHAT, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            d = json.load(r)
    except Exception as exc:  # a lane error is a RESULT, not a crash
        return {"error": f"{type(exc).__name__}: {exc}", "secs": time.time() - t0}
    text = (d.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    usage = d.get("usage") or {}
    return {
        "text": text,
        "secs": time.time() - t0,
        "gen_tokens": usage.get("completion_tokens", 0),
    }


async def recalibrate(models: list[str], reps: int, ctx: int, min_free: float) -> list[dict]:
    run = DurableRun(
        "roster-recalibration",
        meta={
            "models": models,
            "reps": reps,
            "ctx_size": ctx,
            "seed": SEED,
            "protocol": "20260901",
        },
    )
    rows: list[dict] = []
    print(f"{'model':<38} {'pass':>5} {'cold_s':>7} {'warm_p50':>8} {'tok_p50':>8}  by-class")
    print("-" * 100)
    for model in models:
        _drain()
        free, psi = _free_gb(), _psi()
        if free < min_free or psi > 10:
            note = f"SKIPPED free={free:.0f}G psi={psi:.1f}"
            rows.append({"model": model, "skipped": note})
            run.record_lane(rows[-1])
            print(f"{model:<38} {note}")
            continue
        res = _post("load", {"model_name": model, "ctx_size": ctx})
        if res.get("status") != "success":
            rows.append({"model": model, "load_error": str(res.get("error") or res)[:80]})
            run.record_lane(rows[-1])
            print(f"{model:<38} LOAD FAILED {rows[-1]['load_error'][:50]}")
            continue
        # Warm the graph on an UNSCORED prompt so cold trials measure the cache-cold
        # prefix path, not one-time graph compilation (18.1s vs 1.2s, 2026-08-16).
        _chat(model, WARMUP_PROMPT, timeout=300)

        per_class: dict[str, list[bool]] = {}
        cold_secs: list[float] = []
        warm_secs: list[float] = []
        toks: list[float] = []
        for cls, prompt, validator in BATTERY:
            for rep in range(reps):
                r = _chat(model, prompt)
                ok = bool(r.get("text")) and validator(r["text"])  # type: ignore[operator]
                per_class.setdefault(cls, []).append(ok)
                (cold_secs if rep == 0 else warm_secs).append(r.get("secs", 0.0))
                toks.append(r.get("gen_tokens", 0))
                run.record_lane(
                    {
                        "model": model,
                        "class": cls,
                        "rep": rep,
                        "cold": rep == 0,
                        "ok": ok,
                        "secs": round(r.get("secs", 0.0), 2),
                        "gen_tokens": r.get("gen_tokens", 0),
                        "error": r.get("error"),
                    }
                )
        total = sum(len(v) for v in per_class.values())
        passed = sum(sum(v) for v in per_class.values())
        by_class = " ".join(f"{c}={sum(v)}/{len(v)}" for c, v in per_class.items())
        row = {
            "model": model,
            "pass_rate": round(passed / total, 3) if total else 0.0,
            "cold_p50": round(statistics.median(cold_secs), 2) if cold_secs else None,
            "warm_p50": round(statistics.median(warm_secs), 2) if warm_secs else None,
            "tok_p50": round(statistics.median(toks), 0) if toks else None,
            "by_class": {c: f"{sum(v)}/{len(v)}" for c, v in per_class.items()},
        }
        rows.append(row)
        run.record_lane(row)
        print(
            f"{model:<38} {row['pass_rate']:>5.2f} {row['cold_p50']:>7} {row['warm_p50']:>8}"
            f" {row['tok_p50']:>8}  {by_class}",
            flush=True,
        )
    _drain()
    run.finalize({"reps": reps, "ctx_size": ctx})
    return rows


def report(rows: list[dict]) -> None:
    ok = [r for r in rows if "pass_rate" in r]
    if not ok:
        print("\nNo lane produced a measurement.")
        return
    print("\n=== quality-per-call at EQUAL config (pass rate desc, then warm p50) ===")
    for r in sorted(ok, key=lambda r: (-r["pass_rate"], r["warm_p50"] or 9e9)):
        print(f"  {r['model']:<38} {r['pass_rate']:.2f}  warm_p50={r['warm_p50']}s")
    print(
        "\nNext: feed per-class pass rates into the UCCI isotonic fit before updating any"
        " roster JSON; a model whose old rank shifts >2 positions gets an adversarial re-run."
    )


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="")
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--ctx-size", type=int, default=16384)
    ap.add_argument("--min-free-gb", type=float, default=40.0)
    args = ap.parse_args()
    models = [m.strip() for m in args.models.split(",") if m.strip()] or DEFAULT_ROSTER
    rows = await recalibrate(models, args.reps, args.ctx_size, args.min_free_gb)
    report(rows)


if __name__ == "__main__":
    asyncio.run(main())
