#!/usr/bin/env python3
"""Local-inference research on 'Physics of Agents' (arXiv 2608.16578), run in the foreground.

THREE CORRECTIONS FROM FAILURES EARLIER THE SAME EVENING, all measured:

1. BUDGET COVERS REASONING, NOT OUTPUT. A triage batch at max_tokens=1800 returned 2 HTTP 500s
   and a truncation carrying 3,859 chars of reasoning with ZERO content — 1 of 8 lanes usable.
   A five-line answer does not make a thinking model think less. 6000 here.

2. gpt-oss-20b FABRICATES ON LONG MULTI-CONSTRAINT PROMPTS. Given abstract + a 15-line surfaces
   block + a 5-line output format, it described GRIP (a RAG paper) as "a benchmark for RL agents
   in cooking scenarios" — a DIFFERENT paper in the same batch — and invented `TOUCHES` values
   never supplied. Context bleed was tested and REFUTED (a short focused prompt returns GRIP
   correctly), so this is a capability limit at prompt complexity. Hence: 35B, and short prompts
   with ONE question each.

3. `cmd &` INSIDE A NORMAL BASH CALL GETS REAPED. A prior run logged its header and produced no
   lanes in 15 minutes while the router answered in 1ms and the same 35B returned in 2.6s on a
   small prompt. The model was never the problem; the process was killed when the tool call
   returned. Run in the foreground.

Local concurrency stays at 2 — the lanes share :13305 and this box has been hard-frozen once by
over-subscription (2026-08-15 OOM).
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from durable_swarm_output import DurableRun  # noqa: E402

LOCAL_URL = "http://localhost:13305/api/v1/chat/completions"
MODEL = "Qwen3.6-35B-A3B-MTP-GGUF"

ABSTRACT = """"Physics of Agents: Statistical Mechanics Predicts Collective Behavior of AI Agents"
(El, Paeng, Dinc, Su, Erdogan, Pappu, Ye, Zhao, Ganguli, Zou — arXiv:2608.16578, 2026-08-17).

ABSTRACT (verbatim): AI agents increasingly operate as part of interacting systems rather than in
isolation. As agents exchange information and jointly make decisions, their interactions can
improve collective reasoning but may also produce herding, polarization, or amplify shared
biases. Here, we study over 10,000 communities of language-model agents that repeatedly exchange
messages and revise their opinions across objective mathematics questions and subjective
political statements. Despite substantial diversity in possible behavior, the individual and
group dynamics can be represented by three characteristic regimes: indifference, polarization,
and consensus. AI agents start indifferent and build conviction as they interact. On objective
questions, communication improves collective accuracy, while on subjective questions it often
drifts group opinions toward the right in the political spectrum. We explain these observations
with a statistical-mechanics formalism in which agents stochastically favor lower social
pressure. Given only initial opinions, our model predicts individual trajectories, outperforms
all standard baselines, generalizes to unseen community graphs, and reproduces the observed group
archetype distributions. Our fitted model parameters reveal: i) communities operate below the
critical social temperature, which explains conviction buildup; ii) attractive ties outweigh
repulsive ones, which favors consensus; and iii) agents holding the correct answer exert the
strongest pull, which drives truth-seeking."""

# Deliberately SHORT and SINGLE-QUESTION per lane. See correction 2 above.
LANES = [
    (
        "design",
        """Our multi-agent reviews use ISOLATED lanes: each lane gets its own prompt and its own
angle, and lanes never see each other's output. A 6-lane adversarial review and a 4-lane
consultation both ran that way today.

Question: does this paper support or undermine that isolation choice? Reason from findings (i)
'communities operate below the critical social temperature, which explains conviction buildup'
and (ii) 'attractive ties outweigh repulsive ones, which favors consensus'. Be concrete about
when communication between lanes would HELP and when it would herd. One page maximum.""",
    ),
    (
        "rigor",
        """This codebase contains seven 'physics bridges' that all share one literal expression,
4*x*(1-x), documented as a 'Universal HIHO Theorem'. Returning 1.0 at x=0.5 is a property of that
formula. There are no fitted parameters and no out-of-sample prediction.

Question: contrast that with what this paper actually does — >10,000 measured communities, fitted
parameters, prediction of held-out trajectories, generalisation to unseen graphs. What specific
methodological steps separate a statistical-mechanics MODEL from statistical-mechanics NOTATION?
List the steps. Do not be polite about the gap. One page maximum.""",
    ),
]


def call(prompt: str, timeout: int = 900) -> tuple[str, str]:
    body = json.dumps(
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 6000,
            "temperature": 0.3,
        }
    ).encode()
    req = urllib.request.Request(  # noqa: S310 — fixed loopback literal
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
        return "", f"TRUNCATED: budget spent reasoning ({n} chars)"
    return txt, ""


def run_lane(spec: tuple[str, str]) -> dict:
    name, question = spec
    t0 = time.time()
    try:
        txt, err = call(f"{ABSTRACT}\n\n{question}")
    except Exception as e:
        txt, err = "", f"{type(e).__name__}: {e}"[:180]
    return {
        "lane": name,
        "model": MODEL,
        "elapsed_s": round(time.time() - t0, 1),
        "chars": len(txt),
        "error": err,
        "text": txt,
    }


def main() -> int:
    run = DurableRun.attach("physics-of-agents-research")
    print(f"durable run -> {run.dir}\n", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=2) as ex:
        for r in ex.map(run_lane, LANES):
            run.record_lane(r)
            print(f"  {r['lane']:8} {r['chars']:6}ch {r['elapsed_s']:6.1f}s {r['error']}", flush=True)
    print(f"\nwall-clock {time.time() - t0:.0f}s -> {run.dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
