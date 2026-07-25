#!/usr/bin/env python3
"""N-run RELIABILITY harness — measures prompt variance under non-determinism.

Closes the one genuine gap found by the 2026-07-24 AI-code-quality gap-check: we tested
CORRECTNESS (does it pass once?) and cross-model agreement, but never the VARIANCE of a single
prompt across repeated runs. Three separate times in one session a single sample lied:
  - a single-seed ablation reported 42%; the 5-seed mean was 25% (true chance level)
  - a 70-pair cache-threshold run produced a spurious optimum refuted by a 501-pair run
  - a 0.965 mean hid the weakest audio clip until the per-clip table was printed

Reuses the EXISTING deterministic validator (`prompt_version_registry._validate`) — no
LLM-as-judge, no parallel validation logic.

Usage:
    uv run scripts/ci/prompt_reliability.py --fixtures fixtures.json [-n 10] [--model M]
    uv run scripts/ci/prompt_reliability.py --self-test

fixtures.json: [{"prompt": "...", "expected": "...", "validator_type": "contains|exact|regex",
                 "critical": true}]

Exit 0 if every fixture's pass-rate >= --threshold (default 1.0 for critical, 0.8 others).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from cohezion.compound.prompt_version_registry import _validate  # noqa: E402

ROUTER = "http://localhost:13305/v1/chat/completions"
DEFAULT_MODEL = "Gemma-4-E4B-it-GGUF"


def run_local(prompt: str, model: str, max_tokens: int = 200, temperature: float = 0.7) -> str:
    """One completion from the local fleet. Temperature > 0 on purpose: we are MEASURING variance."""
    body = json.dumps({"model": model, "max_tokens": max_tokens, "temperature": temperature,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(ROUTER, data=body,  # noqa: S310
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:  # noqa: S310
        msg = json.loads(r.read())["choices"][0]["message"]
    return (msg.get("content") or msg.get("reasoning_content") or "").strip()


def reliability(fixture: dict, n: int, model: str, run_fn=run_local) -> dict:
    """Run the SAME prompt n times; return pass-rate and the observed outputs' spread."""
    passes, lengths, errors = 0, [], 0
    for _ in range(n):
        try:
            out = run_fn(fixture["prompt"], model)
        except Exception:
            errors += 1
            continue
        lengths.append(len(out))
        if _validate(out, fixture.get("expected", ""), fixture.get("validator_type", "contains")):
            passes += 1
    scored = n - errors
    return {
        "prompt": fixture["prompt"][:70],
        "critical": bool(fixture.get("critical")),
        "runs": n, "errors": errors, "passes": passes,
        "pass_rate": (passes / scored) if scored else 0.0,
        "len_mean": round(statistics.mean(lengths), 1) if lengths else 0,
        "len_stdev": round(statistics.pstdev(lengths), 1) if len(lengths) > 1 else 0.0,
    }


def _self_test() -> int:
    """Discriminating self-test: a DETERMINISTIC stub must score 1.0, a FLAKY stub must not."""
    fx = {"prompt": "p", "expected": "yes", "validator_type": "contains", "critical": True}
    steady = reliability(fx, 10, "stub", run_fn=lambda p, m: "yes")
    flaky_seq = iter(["yes", "no"] * 5)
    flaky = reliability(fx, 10, "stub", run_fn=lambda p, m: next(flaky_seq))
    ok = steady["pass_rate"] == 1.0 and abs(flaky["pass_rate"] - 0.5) < 1e-9
    print(f"  steady stub pass_rate={steady['pass_rate']:.2f} (expect 1.00)")
    print(f"  flaky  stub pass_rate={flaky['pass_rate']:.2f} (expect 0.50)")
    print(f"[self-test] {'PASS' if ok else 'FAIL'} — harness distinguishes stable from flaky")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", type=Path)
    ap.add_argument("-n", "--runs", type=int, default=10)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--threshold", type=float, default=0.8, help="min pass-rate for non-critical")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return _self_test()
    if not a.fixtures:
        ap.error("--fixtures required (or --self-test)")

    fixtures = json.loads(a.fixtures.read_text())
    print(f"reliability: {len(fixtures)} fixtures x {a.runs} runs on {a.model}\n")
    failed = 0
    for fx in fixtures:
        r = reliability(fx, a.runs, a.model)
        need = 1.0 if r["critical"] else a.threshold
        bad = r["pass_rate"] < need
        failed += bad
        flag = "BRITTLE" if bad else "stable "
        print(f"  {flag} pass={r['pass_rate']:>5.0%} ({r['passes']}/{r['runs']})  "
              f"len μ={r['len_mean']} σ={r['len_stdev']}  err={r['errors']}  "
              f"{'[CRITICAL] ' if r['critical'] else ''}{r['prompt']}")
    print(f"\n{'FAIL' if failed else 'PASS'}: {failed} brittle of {len(fixtures)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
