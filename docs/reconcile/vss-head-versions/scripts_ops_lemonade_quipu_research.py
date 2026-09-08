#!/usr/bin/env python3
"""Local-inference deep research on Quipu (arXiv 2608.16813), run in PARALLEL.

Three lanes, distinct angles, all on the :13305 OmniRouter at $0.

PARALLEL ON PURPOSE. Measured 2026-08-19 across two harnesses written earlier the same
day: 9 lanes took 729s sequentially against a 283s parallel floor, and 4 lanes took 184s
against 85s — 545s of pure wall-clock waste across lanes with no data dependency between
them. Each lane here gets its own prompt, model and angle and reads nothing from the others,
so the loop was the only reason to wait.

⚠ Local lanes SHARE the :13305 router, so concurrency is capped at 2. The fleet has been
crashed once by over-subscription (2026-08-15 OOM: pinning MLOCKed weights, GTT/TTM
overcommit, hard freeze). Cloud endpoints could go wider; local cannot.

⚠ Thinking models spend their budget reasoning: max_tokens must be generous (~5000) or the
lane returns finish_reason=length with ZERO content. That is a budget fault, not a refusal.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from durable_swarm_output import DurableRun


LOCAL_URL = "http://localhost:13305/api/v1/chat/completions"
MAX_LOCAL_CONCURRENCY = 2

ABSTRACT = """Quipu: A Governed Bitemporal Knowledge Graph Store (Steve Brown, arXiv:2608.16813,
cs.AI/cs.DB, submitted 2026-08-17).

ABSTRACT (verbatim): Agents now write knowledge graphs, but knowledge-graph stores still carry
defaults set when humans curated them: accept writes now and clean later, keep one time axis or
none, treat every writer's facts as equally trustworthy, and leave governance to dashboards and
middleware. These four defaults are individually convenient and jointly untenable under agent
workloads. We present Quipu, an embeddable store that inverts all four: no fact enters except
through a gate whose predicates evaluate the pending post-state; data, trust labels, verdicts,
and the rules themselves are bitemporal; named graphs are the unit of authority and trust,
composed under a lattice whose one invariant is that composition never widens; and the
governance specification Sigma, the trace, and signed verdicts are facts in the store they
govern, making the audit T |= Sigma a query. We evaluate with Census, a deterministic
multi-writer lifecycle whose single seeded run scores every research question against planted
ground truth: the gated store ends with 0 of 6 planted defects versus 6 of 6 ungated; all 7
composition probes uphold the lattice contract; 50 of 50 satisfied verdicts re-derive faithfully
as of their instant while all 50 would be misreported under a latest-only rule set; and the SARC
reference checker agrees with the in-store audit verdict-for-verdict, differing only on coverage
semantics. A recorded trace from a governed writer surfaces a live enforcement gap the audit
names with its remediation. On DEMM-Bench, an external decision-evidence sufficiency benchmark, a
content-only reading of the exported records answers all 512 property-level governance questions
correctly with zero overclaim under all eight degradation conditions, while container-presence
baselines overclaim on up to 87.5% of them."""

MEASURED = """MEASURED IN THIS SYSTEM ON 2026-08-19 (every number executed, not estimated).
Quipu's four "untenable defaults" map onto these one-for-one:

DEFAULT 1 "accept writes now and clean later":
  - vault: `relevance:` field has MONITOR 4,534 / APPLY 3,182 / EMPTY 3,146 / SKIP 35 /
    actionable 22 / REVIEW 15. 3,146 notes declare the field and leave it blank.
  - the upstream work-queue (8,944 items) has `relevance: 0.9` — a FLOAT in a categorical
    field — in 10 items. Corruption originates at the writer, not the export.
  - there is NO validation at the vault -> SurrealDB boundary, though CLAUDE.md mandates
    "Validation: Pydantic at boundaries".

DEFAULT 2 "one time axis or none":
  - a landed fix (550e44925, geodesic integration) was silently REVERTED by a later feature
    commit (b840a19e6, -219 lines) while the doc still asserted it was correct.
  - a governing rule states "Resolved 2026-08-02: the project copy was reduced to a pointer
    stub". The project copy is the full 5,549-byte document, unchanged.
  - a phantom invariant (MB1) survived ~8 weeks with a verification command that ran, passed,
    and measured unrelated code.

DEFAULT 3 "every writer equally trustworthy":
  - a 6-lane adversarial review produced 14 verifiable claims; 4 were REFUTED on execution.
  - three separate models produced confident, specific, WRONG numbers by reasoning instead of
    running.
  - a degenerate lane emitted a well-formed VERDICT marker attached to repeated nonsense.
  - there are NO per-writer trust labels anywhere.

DEFAULT 4 "governance to dashboards and middleware":
  - governance here is markdown: harness.md + 24 always-loaded rule files (~45,423 tokens).
  - of 28 "-> N passed" verification claims in harness.md, 15 do NOT match the test files
    (scripts/ci/pass_count_check.py, built today). 54% wrong.
  - 11,013 vault notes carry a status; of 1,575 marked "actioned", 17 (1.1%) have any output."""

LENSES = {
    "mechanism": (
        "Explain Quipu's four inversions CONCRETELY, as a database engineer would. In "
        "particular: (a) what does 'a gate whose predicates evaluate the pending POST-state' "
        "mean operationally, and how does it differ from an ordinary constraint or trigger? "
        "(b) what is bitemporality here, and why does making the RULES themselves bitemporal "
        "matter more than making the data bitemporal? (c) what is the lattice invariant "
        "'composition never widens' protecting against? Do not restate the abstract."
    ),
    "fit": (
        "Map each of Quipu's four inverted defaults onto the MEASURED findings supplied. For "
        "each: would Quipu's inversion have PREVENTED that specific defect, or is it "
        "orthogonal? Be willing to answer 'orthogonal' — several may be. Then state which ONE "
        "inversion is worth adopting first for a system that already has a SurrealDB graph, a "
        "32,008-note vault, and markdown governance, and say what it would cost."
    ),
    "skeptic": (
        "Attack the evaluation. The headline results come from 'Census, a deterministic "
        "multi-writer lifecycle whose SINGLE SEEDED RUN scores every research question against "
        "planted ground truth'. A single seeded run, with defects planted by the authors, "
        "evaluating the authors' own system. What can and cannot be concluded from '0 of 6 "
        "planted defects versus 6 of 6 ungated'? Is DEMM-Bench (external) stronger evidence, "
        "and what does 'container-presence baselines overclaim on up to 87.5%' actually compare? "
        "Name the specific experiment that would change your confidence."
    ),
}

MODELS = [
    ("Qwen3.6-35B-A3B-MTP-GGUF", "mechanism"),
    ("Qwen3.6-35B-A3B-MTP-GGUF", "fit"),
    ("gpt-oss-20b", "skeptic"),
]

_THINK_CLOSERS = [r"<\|?channel\|>", r"</think>"]


def strip_reasoning(text: str) -> str:
    for closer in _THINK_CLOSERS:
        parts = re.split(closer, text)
        if len(parts) > 1:
            text = parts[-1]
    return text.strip()


def call_local(model: str, prompt: str, timeout: int = 900) -> tuple[str, str]:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 5000,
            "temperature": 0.3,
        }
    ).encode()
    req = urllib.request.Request(
        LOCAL_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        d = json.loads(r.read())
    choice = d["choices"][0]
    content = strip_reasoning(choice["message"].get("content") or "")
    if not content and choice.get("finish_reason") == "length":
        n = len(choice["message"].get("reasoning_content") or "")
        return "", f"TRUNCATED: budget spent in reasoning ({n} chars), no content"
    return content, ""


def run_lane(spec: tuple[str, str]) -> dict:
    model, lens = spec
    prompt = f"""{ABSTRACT}

{MEASURED}

YOUR ASSIGNED ANGLE — stay in it:
{LENSES[lens]}

Rules: be concrete and reference the measured findings by their DEFAULT number where relevant.
Do NOT restate the abstract back. If you cannot answer within your angle, say so and say why.
End with one line: VERDICT: <one hyphenated token>"""
    t0 = time.time()
    try:
        text, err = call_local(model, prompt)
    except Exception as e:
        text, err = "", f"{type(e).__name__}: {e}"[:200]
    m = re.findall(r"VERDICT:\s*([A-Za-z][A-Za-z-]{2,40})", text or "")
    return {
        "model": model,
        "lens": lens,
        "elapsed_s": round(time.time() - t0, 1),
        "chars": len(text),
        "verdict": (m[-1].upper() if m else ("INSTRUMENT-FAILED" if err else "INCONCLUSIVE")),
        "error": err,
        "text": text,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lanes", default="")
    args = ap.parse_args()
    specs = MODELS
    if args.lanes:
        want = set(args.lanes.split(","))
        specs = [s for s in specs if s[1] in want or s[0] in want]

    run = DurableRun.attach("quipu-local-research")
    print(f"durable run -> {run.dir}")
    print(f"lanes: {len(specs)}, local concurrency cap: {MAX_LOCAL_CONCURRENCY}\n", flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=MAX_LOCAL_CONCURRENCY) as ex:
        for result in ex.map(run_lane, specs):
            run.record_lane(result)
            print(
                f"  {result['model'][:26]:28} {result['lens']:10} "
                f"-> {result['verdict']:22} {result['chars']:6}ch "
                f"{result['elapsed_s']:6.1f}s {result['error']}",
                flush=True,
            )
    wall = time.time() - t0
    seq = sum(r["elapsed_s"] for r in run._lanes) if hasattr(run, "_lanes") else 0
    print(f"\nwall-clock {wall:.0f}s (sequential would have been ~{seq:.0f}s)")
    print("lanes persisted under", run.dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
