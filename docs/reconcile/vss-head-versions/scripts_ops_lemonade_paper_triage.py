#!/usr/bin/env python3
"""Batch triage of arXiv abstracts on local silicon (:13305, $0), in parallel.

WHY TRIAGE RATHER THAN DEEP LANES. A batch of 9 papers at 3 deep lenses each is 27 local
calls; measured on this box, a 35B lane with max_tokens=5000 runs minutes, so that batch is
hours. Triage first, deep-dive only what earns it.

PARALLEL, capped at 2. Measured 2026-08-19: two harnesses written earlier that day ran lanes
sequentially and wasted 545s of wall-clock across lanes with no data dependency. But local
lanes SHARE the :13305 router, and this box has been hard-frozen once by over-subscription
(2026-08-15 OOM), so the cap stays low.

MODEL CHOICE: gpt-oss-20b, not the 35B. Triage is a short-answer task — what is it, does it
touch our surfaces, verdict. Per the standing routing rule, do not run a 1-sentence classify
on a 35B. A live probe returned PROBE_OK well inside the budget.

⚠ Even a small model can spend its budget reasoning and return finish_reason=length with ZERO
content. That is a budget fault, not a refusal, and is reported as TRUNCATED rather than
scored as a verdict.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from durable_swarm_output import DurableRun


LOCAL_URL = "http://localhost:13305/api/v1/chat/completions"
MODEL = "gpt-oss-20b"
MAX_CONCURRENCY = 1  # dropped from 2 after the 500s above, to rule out router contention

# What this system actually has, so the lane judges fit against reality rather than vibes.
SURFACES = """COHEZION'S ACTUAL SURFACES (judge fit against these, not against generalities):
- a SurrealDB knowledge graph (neuron/synapse) + GraphRAG that is hybrid: semantic-vector
  AND graph-ancestry
- a 32,008-note Obsidian vault; an 8,944-item work queue written by an autonomous research
  daemon polling arXiv/HF/Reddit/HN
- multi-agent lanes (adversarial review, cloud consultation) coordinated by a session bus with
  KNOWN identity/delivery defects
- local-first inference on :13305 (NPU->iGPU->CPU) at $0, escalating to cloud only on a
  quality-gate failure
- governance as markdown: harness.md + 24 always-loaded rule files
MEASURED DEFECTS 2026-08-19: no validation at the vault->graph write boundary (3,146 empty
schema fields, a float in a categorical field); governance claims that are 54% wrong (15 of 28
test-count assertions); no per-writer trust labels (4 of 14 review claims were false); learned
state that dies at process exit; reasoning_content discarded so lanes are judged on output
statistics only."""


def call(model: str, prompt: str, max_tokens: int, timeout: int = 600) -> tuple[str, str]:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
    ).encode()
    req = urllib.request.Request(
        LOCAL_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        d = json.loads(r.read())
    ch = d["choices"][0]
    txt = (ch["message"].get("content") or "").strip()
    for closer in (r"<\|?channel\|>", r"</think>"):
        parts = re.split(closer, txt)
        if len(parts) > 1:
            txt = parts[-1].strip()
    if not txt and ch.get("finish_reason") == "length":
        n = len(ch["message"].get("reasoning_content") or "")
        return "", f"TRUNCATED: budget spent reasoning ({n} chars), no content"
    return txt, ""


def triage(item: tuple[str, dict]) -> dict:
    pid, meta = item
    prompt = f"""Triage this arXiv paper for a specific engineering system. Be terse and concrete.

PAPER {pid}: {meta["title"]}
ABSTRACT: {meta["abs"]}

{SURFACES}

Answer in exactly these five lines, nothing else:
CLAIM: <the paper's central claim, one sentence, no restating the abstract>
EVIDENCE: <what they actually measured, with numbers if the abstract gives any; say
  "self-reported" or "external benchmark" where determinable>
TOUCHES: <which named Cohezion surface(s) above it bears on, or NONE>
CATCH: <the strongest reason this may NOT transfer here — required, do not skip>
VERDICT: SKIP or NOTE or PILOT"""
    t0 = time.time()
    try:
        # 6000, not 1800. MEASURED 2026-08-19: at 1800 this batch produced 2 HTTP 500s and a
        # truncation carrying 3,859 chars of reasoning with ZERO content — 1 of 8 lanes
        # parseable. The budget must cover the REASONING, not the output. A five-line answer
        # does not make a thinking model think less, and on this router truncation surfaces as
        # a 500 rather than a clean finish_reason.
        txt, err = call(MODEL, prompt, max_tokens=6000)
    except Exception as e:
        txt, err = "", f"{type(e).__name__}: {e}"[:180]
    m = re.findall(r"VERDICT:\s*(SKIP|NOTE|PILOT)", txt or "", re.I)
    return {
        "paper": pid,
        "title": meta["title"],
        "model": MODEL,
        "elapsed_s": round(time.time() - t0, 1),
        "chars": len(txt),
        "verdict": (m[-1].upper() if m else ("INSTRUMENT-FAILED" if err else "INCONCLUSIVE")),
        "error": err,
        "text": txt,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", default=os.environ.get("TMPDIR", "/tmp") + "/papers/all.json")
    args = ap.parse_args()

    papers = json.load(open(args.papers))
    run = DurableRun.attach("arxiv-batch-triage")
    print(f"durable run -> {run.dir}")
    print(f"{len(papers)} papers, model={MODEL}, concurrency={MAX_CONCURRENCY}\n", flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as ex:
        for r in ex.map(triage, papers.items()):
            run.record_lane(r)
            print(
                f"  {r['paper']}  {r['verdict']:18} {r['chars']:5}ch {r['elapsed_s']:6.1f}s  "
                f"{r['title'][:46]} {r['error']}",
                flush=True,
            )
    print(f"\nwall-clock {time.time() - t0:.0f}s")
    print("lanes persisted under", run.dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
