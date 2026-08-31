#!/usr/bin/env -S uv run python
"""Contamination probe for the SWE-bench-derived defect benchmark.

THE THREAT. SWE-bench_Lite is public and plausibly in these models' training data. If a model
memorised the gold patches it would recognise the fixed form directly, and every MCC we report
would be inflated by recall rather than reasoning.

THE TEST — recognition split. For each instance, show the BARE hunk (no issue text) and ask
which open-source project it comes from. Then compare defect-detection performance on the
instances a model can identify versus those it cannot. If contamination is driving the score,
performance should be markedly HIGHER on recognised instances.

WHAT A POSITIVE RECOGNITION DOES AND DOES NOT MEAN. Naming `astropy` from an astropy hunk only
proves the model saw the CODEBASE — nearly certain for any popular Python repo, and not by
itself SWE-bench contamination. It becomes evidence of benchmark contamination only if it also
predicts better defect discrimination on those same instances.

PRIOR EVIDENCE AGAINST HEAVY CONTAMINATION (stated up front so this probe is not over-read):
a memorised benchmark yields near-ceiling scores. Measured MCC is 0.25-0.31, far from ceiling.
This probe tests whether the residual signal is recall-driven, not whether any exposure exists.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

RECOGNISE_PROMPT = (
    "Which open-source Python project is this code from?\n"
    "Answer with ONLY the project name (e.g. django, numpy, flask), or UNKNOWN if unsure.\n\n"
    "```python\n{code}\n```"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Gemma-4-E4B-it-GGUF")
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--max-tokens", type=int, default=1024)
    args = ap.parse_args()

    sys.path.insert(0, str(REPO / "scripts"))
    from swebench_defect_bench import build_cases

    from cohezion.inference.gaia_adapter import build_gaia_llm_tier

    chat = build_gaia_llm_tier(args.model, max_tokens=args.max_tokens).agent.prompt

    # Defective halves only — one probe per instance, not per case.
    cases = [c for c in build_cases(args.limit) if c[2]]
    hits = 0
    print(f"probing {len(cases)} instances with {args.model}\n", flush=True)

    for i, (iid, code, _d, _issue) in enumerate(cases, 1):
        true_repo = iid.split("__")[0].lower()
        try:
            reply = (chat(RECOGNISE_PROMPT.format(code=code)) or "").lower()
        except Exception as exc:
            print(f"  [{i:2d}] {true_repo:14s} ERROR {exc}", flush=True)
            continue
        # Take the LAST tokens: thinking models reason first, answer last.
        tail = re.sub(r"[^a-z0-9 _-]", " ", reply)[-260:]
        got = true_repo in tail
        hits += got
        print(
            f"  [{i:2d}] true={true_repo:14s} recognised={'YES' if got else 'no ':3s} "
            f"running={hits}/{i} ({hits / i:.0%})",
            flush=True,
        )

    print(f"\nrecognition rate: {hits}/{len(cases)} = {hits / max(1, len(cases)):.0%}")
    print(
        "\nINTERPRETATION: a HIGH rate proves codebase familiarity, not benchmark memorisation.\n"
        "It only indicts the MCC if defect discrimination is also markedly better on the\n"
        "recognised subset. A LOW rate is straightforward evidence against contamination."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
