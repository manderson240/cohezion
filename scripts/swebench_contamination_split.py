#!/usr/bin/env -S uv run python
"""Rigorous contamination check: does RECOGNITION predict better DISCRIMINATION?

The loose version of this check measured only a recognition rate (57% for Gemma-4-E4B) and then
argued from aggregates that recognition was not converting into discrimination. That is an
inference, not a measurement. This script does the real test.

Per instance it runs THREE probes and joins them:
  1. recognition — "which project is this from?" on the bare hunk
  2. defect detection on the DEFECTIVE half (issue-grounded, the fair task)
  3. defect detection on the FIXED half

Then it computes MCC separately over the RECOGNISED and UNRECOGNISED subsets.

READING THE RESULT:
  MCC(recognised) >> MCC(unrecognised)  -> contamination is inflating the headline number.
  MCC(recognised) ~= MCC(unrecognised)  -> the model knows the codebase but is REASONING about
                                           the defect, not recalling it. Familiarity with
                                           popular repos (django, astropy, sympy) is expected
                                           of any GitHub-trained model and is NOT by itself
                                           benchmark contamination.

Caveat that survives any result: subset sizes are small, so treat a difference as directional
unless it is large. Report both subset n values, never just the deltas.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

RECOGNISE_PROMPT = (
    "Which open-source Python project is this code from?\n"
    "Answer with ONLY the project name (e.g. django, numpy, flask), or UNKNOWN if unsure.\n\n"
    "```python\n{code}\n```"
)


def _mcc(tp: int, tn: int, fp: int, fn: int) -> float:
    d = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return (tp * tn - fp * fn) / d if d else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Gemma-4-E4B-it-GGUF")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--max-tokens", type=int, default=3072)
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    from swebench_defect_bench import PROMPT_CTX, _verdict, build_cases

    from cohezion.inference.gaia_adapter import build_gaia_llm_tier

    chat = build_gaia_llm_tier(args.model, max_tokens=args.max_tokens).agent.prompt

    cases = build_cases(args.limit)
    by_iid: dict[str, dict] = {}
    for iid, code, defective, issue in cases:
        key = iid.replace("__fixed", "")
        by_iid.setdefault(key, {"issue": issue})
        by_iid[key]["bug" if defective else "fixed"] = code

    rows = []
    for i, (iid, d) in enumerate(by_iid.items(), 1):
        if "bug" not in d or "fixed" not in d:
            continue
        true_repo = iid.split("__")[0].lower()
        try:
            rec_reply = (chat(RECOGNISE_PROMPT.format(code=d["bug"])) or "").lower()
            recognised = true_repo in re.sub(r"[^a-z0-9 _-]", " ", rec_reply)[-260:]
            v_bug = _verdict(chat(PROMPT_CTX.format(issue=d["issue"], code=d["bug"])) or "")
            v_fix = _verdict(chat(PROMPT_CTX.format(issue=d["issue"], code=d["fixed"])) or "")
        except Exception as exc:
            print(f"  [{i:2d}] {true_repo} ERROR {exc}", flush=True)
            continue

        rows.append({"iid": iid, "recognised": recognised, "v_bug": v_bug, "v_fix": v_fix})
        print(
            f"  [{i:2d}] {true_repo:12s} recognised={'Y' if recognised else 'n'} "
            f"bug->{v_bug} fixed->{v_fix}",
            flush=True,
        )

    def score(subset):
        tp = sum(1 for r in subset if r["v_bug"] is True)
        fn = sum(1 for r in subset if r["v_bug"] is False)
        fp = sum(1 for r in subset if r["v_fix"] is True)
        tn = sum(1 for r in subset if r["v_fix"] is False)
        return tp, tn, fp, fn, _mcc(tp, tn, fp, fn)

    rec = [r for r in rows if r["recognised"]]
    unrec = [r for r in rows if not r["recognised"]]
    print(f"\n{'subset':14s} {'instances':>9s} {'tp':>3s} {'tn':>3s} {'fp':>3s} {'fn':>3s} {'MCC':>6s}")
    out = {}
    for label, subset in (("RECOGNISED", rec), ("unrecognised", unrec), ("ALL", rows)):
        tp, tn, fp, fn, m = score(subset)
        print(f"{label:14s} {len(subset):>9d} {tp:>3d} {tn:>3d} {fp:>3d} {fn:>3d} {m:>6.2f}")
        out[label] = {"n": len(subset), "tp": tp, "tn": tn, "fp": fp, "fn": fn, "mcc": m}

    if rec and unrec:
        delta = out["RECOGNISED"]["mcc"] - out["unrecognised"]["mcc"]
        print(f"\nMCC(recognised) - MCC(unrecognised) = {delta:+.2f}")
        print(
            "LARGE POSITIVE -> contamination inflates the headline.\n"
            "NEAR ZERO or NEGATIVE -> codebase familiarity WITHOUT benchmark memorisation;\n"
            "the model is reasoning about the defect, not recalling the patch."
        )
        print(f"\nSubset sizes are {len(rec)} vs {len(unrec)} — treat as DIRECTIONAL, not precise.")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps({"summary": out, "rows": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
