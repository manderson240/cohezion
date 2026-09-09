"""Measure LANE TERMINATION: does a model emit a usable structured answer, or ruminate forever?

Complements scripts/experiments/review_lane_benchmark.py, which measures whether a lane's
VERDICT is correct (balanced accuracy on planted defects, executed ground truth). That axis says
nothing about whether an answer comes out AT ALL -- a lane scoring 1.00 accuracy is useless in a
swarm if it never emits a parseable answer. The existing table hints at this in exactly one
footnote: "Gemma-4-31B-it 0.85 PARTIAL (15/24 parsed)".

Measured 2026-08-15/16, the cost of not having this number: six prompt iterations were spent
treating a MODEL-selection problem as a prompt-engineering problem. Gemma-4-26B-A4B produced
14,000-17,500 raw characters and never emitted the marker on evaluative prompts; swapping to
Gemma-4-E4B collapsed output to 2,000-3,100 chars and 10-24s with the SAME prompt. Raising
max_tokens did not help, because the budget was never the binding constraint.

Metrics per model:
  termination_rate  fraction of reps that emitted the marker AND the required fields.
                    This is the headline: a lane below ~0.8 is unusable for swarm work.
  raw_chars         median total generated output -- the DIRECT cost measure, spanning 85x
                    across the roster (205 to 17,400). Reported because overhead_ratio is
                    computed against text AFTER the last marker, so a model that places its
                    reasoning after the verdict would score as low-overhead without ruminating
                    any less. That confound was tested across 21 reps and REFUTED (answer_chars
                    is near-constant at 188-472, making overhead monotone in raw_chars), but
                    raw_chars needs no such argument.
  overhead_ratio    (raw_chars - answer_chars) / raw_chars -- how much of the output is
                    reasoning the caller must discard. High overhead with high termination is
                    merely expensive; high overhead with LOW termination is the failure mode.
  ceiling_rate      fraction of reps within 10% of the character ceiling implied by max_tokens.
                    A lane at the ceiling did not finish thinking; it was cut off.
  p50_secs          median latency.

Deliberately uses an EVALUATIVE prompt. Termination failures observed this session clustered on
judgement about contested material, not on concrete technical questions -- a benchmark using an
easy factual prompt would report every lane as fine and measure nothing.

Usage:
  .venv/bin/python scripts/experiments/lane_termination_benchmark.py --reps 3
  .venv/bin/python scripts/experiments/lane_termination_benchmark.py --models gpt-oss-20b,...
"""

# ruff: noqa: I001 - the import block is deliberately split by the sys.path.insert calls below;
# sorting it hoists `durable_swarm_output` above the path setup that makes it importable.
from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from durable_swarm_output import DurableRun  # noqa: E402

from cohezion.inference.gaia_adapter import build_gaia_llm_tier  # noqa: E402

MARKER = "===FINAL==="
FIELDS = ("VERDICT:", "REASON:")

# Evaluative, contested, and short enough that no lane can blame the input length.
PROMPT = """A team proposes replacing a well-tested 200-line module with a 40-line rewrite that
passes the same test suite. The tests were written against the OLD module's behaviour.

Is passing the existing suite sufficient evidence that the rewrite is safe? Argue one side.

OUTPUT CONTRACT (mandatory): think briefly, then emit the line
===FINAL===
and AFTER it write exactly these two labelled lines:
VERDICT: <sufficient|insufficient>
REASON: <one sentence>
The marker is NOT the end of your response. Never stop immediately after the marker.
"""


def classify(raw: str, max_tokens: int) -> dict:
    ceiling_chars = max_tokens * 4  # ~4 chars/token, the empirical ratio on this fleet
    at_ceiling = len(raw) >= 0.9 * ceiling_chars
    if MARKER not in raw:
        return {"terminated": False, "why": "no-marker", "answer_chars": 0,
                "at_ceiling": at_ceiling}
    answer = raw.rsplit(MARKER, 1)[1].strip()
    missing = [f for f in FIELDS if f.lower() not in answer.lower()]
    if missing:
        return {"terminated": False, "why": f"missing{missing}", "answer_chars": len(answer),
                "at_ceiling": at_ceiling}
    return {"terminated": True, "why": "", "answer_chars": len(answer), "at_ceiling": at_ceiling}


async def one_rep(model: str, max_tokens: int) -> dict:
    t0 = time.time()
    try:
        tier = build_gaia_llm_tier(model, max_tokens=max_tokens, temperature=0.3)
        res = await tier.run(PROMPT)
        raw = getattr(res, "text", None) or getattr(res, "output", None) or str(res)
        gen_tokens = int(getattr(res, "gen_tokens", 0) or 0)
        dropped = int(getattr(res, "dropped_reasoning_chars", 0) or 0)
    except Exception as exc:  # a dead lane is a RESULT to record, not an abort of the survey
        return {"model": model, "secs": round(time.time() - t0, 1), "raw_chars": 0,
                "terminated": False, "why": f"{type(exc).__name__}", "answer_chars": 0,
                "at_ceiling": False, "gen_tokens": 0, "dropped_reasoning_chars": 0}
    out = classify(raw or "", max_tokens)
    out.update({"model": model, "secs": round(time.time() - t0, 1), "raw_chars": len(raw or ""),
                "gen_tokens": gen_tokens, "dropped_reasoning_chars": dropped})
    return out


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=4000)
    args = ap.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if not models:
        print("--models is required (comma-separated). Only benchmark RESIDENT models: loading "
              "evicts other sessions' work and this box hard-hung twice on 2026-08-15.",
              file=sys.stderr)
        raise SystemExit(2)

    run = DurableRun("lane-termination-benchmark", meta={"models": models, "reps": args.reps})
    print(f"{'model':<34} {'term':>5} {'GEN_TOK':>8} {'rawch':>7} {'ovhd':>6} {'ceil':>5} "
          f"{'p50s':>7}  notes")
    print("-" * 100)
    stripped: list[tuple[str, int]] = []

    for model in models:
        reps = []
        for _ in range(args.reps):
            r = await one_rep(model, args.max_tokens)
            reps.append(r)
            run.record_lane(r)  # durable per rep: a crash costs one rep, not the run
        term = sum(1 for r in reps if r["terminated"]) / len(reps)
        ceil_rate = sum(1 for r in reps if r["at_ceiling"]) / len(reps)
        ovhd = [
            (r["raw_chars"] - r["answer_chars"]) / r["raw_chars"]
            for r in reps if r["raw_chars"] > 0
        ]
        p50 = statistics.median(r["secs"] for r in reps)
        raw_med = statistics.median(r["raw_chars"] for r in reps)
        gen_med = statistics.median(r.get("gen_tokens", 0) for r in reps)
        drop_med = statistics.median(r.get("dropped_reasoning_chars", 0) for r in reps)
        if drop_med > 0:
            stripped.append((model, int(drop_med)))
        whys = {r["why"] for r in reps if r["why"]}
        print(f"{model:<34} {term:>5.2f} {gen_med:>8.0f} {raw_med:>7.0f} "
              f"{statistics.mean(ovhd) if ovhd else 0:>6.2f} "
              f"{ceil_rate:>5.2f} {p50:>7.1f}  {','.join(sorted(whys)) or 'ok'}", flush=True)

    run.finalize({"reps": args.reps, "max_tokens": args.max_tokens})

    # Self-report invalidity rather than printing clean-looking incomparable numbers. On
    # 2026-08-16 this table ranked lanes by rawch and got the order backwards, because the two
    # lanes it called cheapest were the two whose reasoning the adapter had stripped.
    if stripped:
        print("\n!! rawch/ovhd measure what the CALLER RECEIVES, not what was generated. These")
        print("   lanes had reasoning removed before measurement -- either dropped from the")
        print("   reasoning_content channel, or stripped inline by gaia_adapter._answer_only:")
        for m, n in stripped:
            print(f"     {m}: ~{n} chars removed per call")
        print("   Rank by GEN_TOK, which the provider counts over every generated token.")
    elif any(True for _ in models):
        print("\nrawch comparable across this run: no lane had reasoning removed.")
    print(f"\n[durable] {run.dir}")


if __name__ == "__main__":
    asyncio.run(main())
