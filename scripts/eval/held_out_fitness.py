#!/usr/bin/env python3
"""Held-out real-task fitness — the compound loop's external true-north.

The self-improvement loop was optimizing INTERNAL, self-referential metrics
(coherence / compound_score) — and this session found that fitness signal was
inverted across 5 sites with nothing catching it, because a loop graded by its own
number cannot notice the number is lying (decisions/2026-07-12-cohezion-true-north-reflection.md).

This harness gives the loop a fitness it CANNOT fake: the pass-rate over the
held-out `golden_fixture` set (fixed input -> expected_output ground truth), scored
DETERMINISTICALLY (all significant expected words present, word-boundary,
case-insensitive — no LLM judge, no answer leakage), run on LOCAL inference ($0).

Run repeatedly to track compounding: does pass-rate rise after a refinement cycle?
    python3 scripts/eval/held_out_fitness.py                 # baseline now
    python3 scripts/eval/held_out_fitness.py --json          # machine-readable

v1 scope (honest): runs each fixture input through the base local model with a
generic assistant prompt (NOT yet the per-skill PRIME prompt). It is a real, external,
deterministic system-fitness baseline. NEXT iteration: prepend each fixture's skill
PRIME prompt so skill-refinement can measurably move this number (the compounding proof).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

SURREAL_URL = "http://localhost:8001/sql"
LEMONADE_URL = "http://localhost:13305/api/v1/chat/completions"
MODEL = os.environ.get("HELD_OUT_MODEL", "Bonsai-8B-gguf")
_STOP = {"the", "a", "an", "of", "to", "in", "for", "and", "or", "with", "3d", "2d"}
SKILLS_DIR = Path(__file__).resolve().parents[2] / "src" / "cohezion" / "skills"


def _load_skill_prompt(skill_name: str) -> str:
    """Load a skill's PRIME prompt (capped), so skill-refinement can measurably move the
    fitness. Falls back to a generic prompt when the skill file is absent."""
    stem = skill_name.replace("-", "_")
    for cand in (SKILLS_DIR / f"{stem.upper()}.md", SKILLS_DIR / f"{stem}.md", SKILLS_DIR / f"{skill_name}.md"):
        if cand.exists():
            txt = cand.read_text(encoding="utf-8", errors="ignore")
            return f"You are the '{skill_name}' skill. Apply it precisely and answer concisely.\n\n{txt[:3000]}"
    return "You are a concise expert engineering assistant."


def _surreal(query: str) -> list:
    req = urllib.request.Request(  # noqa: S310
        SURREAL_URL, data=query.encode(),
        headers={"surreal-ns": "cohezion", "surreal-db": "main", "Content-Type": "text/plain",
                 "Authorization": "Basic " + base64.b64encode(b"root:root").decode()})
    with urllib.request.urlopen(req, timeout=15) as r:  # noqa: S310
        return json.load(r)[0].get("result", [])


def _infer(prompt: str, system_prompt: str, timeout: int = 90) -> str:
    body = {"model": MODEL, "temperature": 0.0, "max_tokens": 512,
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": prompt}]}
    req = urllib.request.Request(  # noqa: S310
        LEMONADE_URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            d = json.load(r)
        return (d["choices"][0]["message"].get("content") or "")
    except Exception as exc:  # noqa: BLE001
        return f"[infer-error:{str(exc)[:60]}]"


def _passes(expected: str, output: str) -> bool:
    """Deterministic: every significant word of expected appears (word-boundary) in output."""
    out = output.lower()
    words = [w for w in re.findall(r"[a-z0-9]+", expected.lower()) if len(w) > 2 and w not in _STOP]
    if not words:
        return expected.lower() in out
    return all(re.search(rf"\b{re.escape(w)}\b", out) for w in words)


def main() -> int:
    ap = argparse.ArgumentParser(description="Held-out golden_fixture pass-rate (loop true-north)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    fixtures = _surreal(f"SELECT skill_name, input, expected_output FROM golden_fixture LIMIT {args.limit};")
    if not fixtures:
        print("held_out_fitness: no golden_fixtures found (populate the held-out set first)", file=sys.stderr)
        return 2

    results = []
    for fx in fixtures:
        inp, exp = fx.get("input", ""), fx.get("expected_output", "")
        out = _infer(inp, _load_skill_prompt(fx.get("skill_name", "")))
        ok = _passes(exp, out)
        results.append({"skill": fx.get("skill_name", "?"), "expected": exp, "passed": ok})

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    rate = passed / total if total else 0.0
    payload = {"model": MODEL, "total": total, "passed": passed, "pass_rate": round(rate, 4),
               "results": results}
    if args.json:
        print(json.dumps(payload))
    else:
        print(f"=== held-out fitness (golden_fixture) — model {MODEL} ===")
        for r in results:
            print(f"  {'✓' if r['passed'] else '✗'} [{r['skill']:24}] expects: {r['expected'][:40]}")
        print(f"\nPASS-RATE: {passed}/{total} = {rate:.1%}   (the loop's external true-north)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
