#!/usr/bin/env python3
"""Machine-lane multiperspective adversarial diff review (local-first, $0-first).

Battle-tested in the 2026-08-13 landing campaign (v1.3.0/v1.4.0): the cloud lane
found a real stored-XSS the other lanes missed; divergence between lanes IS the
signal, and a lane with zero findings across many diffs is a broken lane.

Lanes:
  local : Qwen3-Coder-30B-A3B-Instruct-GGUF via lemonade :13305 (correctness) — $0
  cloud : deepseek-v4-flash:0731-cloud via ollama :11434 (adversarial/security)

Encoded traps (each cost real debugging time):
  - Thinking models park the answer in ``reasoning_content`` (lemonade) or
    ``reasoning`` (ollama) — an empty ``content`` is NOT an empty review.
  - A frugal max_tokens starves reasoning before the verdict line; the cloud
    lane needs ~8000. Verdict-missing at suspicious speed = truncation, not
    a clean diff.
  - Lanes run in parallel with EACH OTHER but branches serially WITHIN a lane
    (concurrent iGPU calls wreck generation throughput).
  - Sampling params are omitted for lemonade (the model-card sampling wins).

Contract: each review must end with ``VERDICT: LAND`` or ``VERDICT: HOLD <reason>``
(positive MARKER contract — absence means the lane failed, never that the diff
passed). Reviews land in ``$MPR_OUT_DIR`` (default: ./mpr-reviews).

Usage:
  LANES=local,cloud python scripts/ops/multiperspective_diff_review.py <branch>...
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# MEASURED 2026-08-07: reviewing a file whose source contains LLM prompt templates as string
# literals, 2 of 3 reviewer models obeyed the EMBEDDED prompt instead of the review task. A diff is
# exactly that hazard, so its payload is fenced before it reaches the model.
from finding_grounding import grounding
from untrusted_content import wrap_untrusted


REPO = os.environ.get("MPR_REPO", "/home/mike-anderson/dev/cohezion")
OUT = Path(os.environ.get("MPR_OUT_DIR", "./mpr-reviews"))
BASE = os.environ.get("MPR_BASE", "main")

PROMPT = """You are an ADVERSARIAL code reviewer for the Cohezion repo (Python 3.13, \
compound-AI orchestration). Assume this change is broken until proven otherwise. \
Perspective: {perspective}.

Review the unified diff below (branch -> {base} merge candidate). Find: real bugs, \
silent data loss, broken invariants, security issues, tests that can't fail, dead \
wiring (producer with no consumer). Ignore style. Cite file:line from the diff for \
every finding. If you cannot find a genuine defect, say so plainly — do not invent \
findings.

End your reply with exactly one line:
VERDICT: LAND
or
VERDICT: HOLD <one-line reason>

DIFF:
{diff}
"""


def chat(url: str, model: str, prompt: str, max_tokens: int, extra: dict) -> str:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        **extra,
    }
    req = urllib.request.Request(  # noqa: S310 — fixed localhost inference URLs
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as r:  # noqa: S310
        d = json.loads(r.read().decode())
    msg = d["choices"][0]["message"]
    text = (msg.get("content") or "").strip()
    if not text:  # thinking-model empty-content trap
        text = (msg.get("reasoning_content") or msg.get("reasoning") or "").strip()
    return text


def get_diff(branch: str, limit: int) -> str:
    diff = subprocess.run(
        ["git", "-C", REPO, "diff", f"{BASE}...{branch}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    if len(diff) > limit:
        diff = diff[:limit] + f"\n\n[TRUNCATED: diff is {len(diff)} chars total]"
    return diff


def run_lane(
    branches: list[str],
    lane: str,
    url: str,
    model: str,
    perspective: str,
    limit: int,
    max_tokens: int,
    extra: dict,
) -> None:
    for branch in branches:
        slug = branch.replace("/", "__")
        out = OUT / f"{slug}.{lane}.md"
        if out.exists() and "VERDICT:" in out.read_text():
            print(f"[{lane}] {branch}: cached, skip", flush=True)
            continue
        t0 = time.time()
        # Bound BEFORE the try: get_diff() can raise, and the except-path below still reaches the
        # grounding check. Leaving it unbound would turn a survivable per-branch failure into a
        # NameError that kills the lane.
        diff = ""
        try:
            diff = get_diff(branch, limit)
            text = chat(
                url,
                model,
                PROMPT.format(
                    perspective=perspective,
                    diff=wrap_untrusted(diff, "DIFF"),
                    base=BASE,
                ),
                max_tokens,
                extra,
            )
        except Exception as e:  # lane must survive per-branch failure
            text = f"LANE_ERROR: {e}\nVERDICT: HOLD lane error"
        dt = time.time() - t0
        # GROUNDING, at the point of write. Measured 2026-08-20: two lanes AGREED on a blocking
        # defect and both FABRICATED it (an INSERT INTO absent from the diff). Agreement carried no
        # information — same model, shared blind spot — so provenance is checked here rather than
        # by adding more voters. Grounding is NECESSARY, not sufficient: a grounded finding can
        # still draw a wrong conclusion, so this annotates, it does not auto-reject.
        g = grounding(text, diff)
        stamp = (
            f"<!-- grounding: spans={g['spans']} matched={g['grounded_spans']} "
            f"ratio={g['ratio']} -->\n"
        )
        warn = (
            ""
            if g["grounded"]
            else "> ⚠ **UNGROUNDED** — no quoted span in this review occurs in the reviewed diff. "
            "Treat every finding as unsourced until each is checked against the source.\n\n"
        )
        out.write_text(f"# {branch} — {lane} ({model}, {dt:.0f}s)\n\n{stamp}{warn}{text}\n")
        has_verdict = "VERDICT:" in text
        print(
            f"[{lane}] {branch}: {dt:.0f}s verdict={'OK' if has_verdict else 'MISSING'} "
            f"grounding={g['grounded_spans']}/{g['spans']}"
            f"{' UNGROUNDED' if not g['grounded'] else ''}",
            flush=True,
        )


def main() -> int:
    branches = sys.argv[1:]
    if not branches:
        print("usage: multiperspective_diff_review.py <branch>...", file=sys.stderr)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    all_lanes = {
        "local": (
            "local-coder",
            "http://localhost:13305/v1/chat/completions",
            "Qwen3-Coder-30B-A3B-Instruct-GGUF",
            "correctness, control flow, data integrity",
            20000,
            2500,
            {},
        ),
        "cloud": (
            "cloud-deepseek",
            "http://localhost:11434/v1/chat/completions",
            "deepseek-v4-flash:0731-cloud",
            "adversarial security, injection, silent failure modes, race conditions",
            50000,
            8000,
            {"temperature": 0.2},
        ),
    }
    selected = os.environ.get("LANES", "local,cloud").split(",")
    lanes = [all_lanes[k] for k in selected if k in all_lanes]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(run_lane, branches, *lane) for lane in lanes]
        for f in futs:
            f.result()
    print("ALL LANES COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
