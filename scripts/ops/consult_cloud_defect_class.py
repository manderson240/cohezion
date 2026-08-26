#!/usr/bin/env python3
"""Consult Ollama Cloud models on ONE question: why does this system keep shipping
declared-but-never-delivered capability, and which proposed fix actually addresses it?

Six instances were verified in a single day (2026-08-19), across three different substrates.
That is not a bug; it is a production rate. The question is what stops it.

Distinct lens per lane — redundancy finds the same answer N times, diversity finds what one
lens cannot. Positive VERDICT marker required: a silent lane is INCONCLUSIVE, never assent.

⚠ Cloud lanes cost real balance. Small run, call count reported. NEVER kimi-k3:cloud (HTTP 402).
⚠ Use the HTTP API. `ollama run` timed out and returned empty for cloud models on 2026-08-19
  while the API answered instantly — a broken instrument, not a dead service.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from durable_swarm_output import DurableRun


CLOUD_URL = "http://localhost:11434/api/chat"

EVIDENCE = """
Six VERIFIED instances of one defect class, all measured on 2026-08-19 in one codebase/vault.
Every number was executed, not estimated.

1. PHANTOM HARNESS INVARIANTS (x5). `harness.md` documented capabilities that never existed.
   One (MB1) carried a verification command that was real, green, and measuring something
   unrelated — 6 tests that never referenced the field it claimed to verify. Undetected ~8 weeks.

2. SELF-HEALING THAT NEVER HEALED. `SelfHealingSystem.heal()` has ZERO callers in any revision
   (`git log -S 'healer.heal(' --all` => 0 commits; control returns 3). Its only other entry
   point calls `heal_manifold`, a method never defined in ANY revision
   (`git log -S 'def heal_manifold' --all` => 0). The call raised AttributeError past an
   `except ImportError` guard into a bus-level `except Exception`. Silent.

3. SATURATED SENSOR DRIVING A LIVE PIPELINE. `journey_point.coherence` = variance over four
   HARDCODED constants (0.7/0.75/0.8/0.65). `1 - min(var*4,1) == 0.9875` EXACTLY = the corpus
   mode, 81,469 of 278,741 rows. The four "evaluator" modules that produce it are keyword stubs;
   the 827-line file has ZERO inference calls. Consumers read 0.5-as-healthy while producers
   write 1.0-as-good, so 99.79% of events crossed the drift threshold.

4. UNPERSISTED LEARNED STATE. `DegradationDetector` CB7 persistence has 27 test references and
   NO production caller. Every learned baseline dies at process exit.

5. VAULT AT SCALE. 11,013 notes (34% of 32,008) all carry a status. Of 1,575 marked "actioned",
   17 (1.1%) exceed 2000 bytes. => 1,558 notes claim work that produced no output.

6. THE RULES THEMSELVES. A governing rule file states "Resolved 2026-08-02: the project copy was
   reduced to a pointer stub". The project copy is the full 5,549-byte document, unchanged. The
   resolution was documented and never performed.

WHAT ALREADY EXISTS (so do not propose these as new):
- `dormancy_scan.py` — curated guard: named capability + regex for its CONSUMPTION site. Catches
  re-dormancy of KNOWN capabilities. Cannot discover new ones.
- `narrow_guard_scan.py` — AST scan for try-blocks whose handler cannot catch what the body
  raises. Built today; caught instance 2's shape. 63 hits, report-only.
- `verification-depth.md` — consumption invariants, discriminating tests, adversarial second pass.
- ~6,133 tests, all green throughout. Every instance above passed every existing check.

PROPOSALS CURRENTLY ON THE TABLE:
A. Seeded-defect benchmark measuring RECALL of the review harness (we currently measure only
   precision; a 6-lane review verified 14 claims and MISSED the most consequential bug).
B. A status gate: the vault actioner may not write "actioned" without a deliverable.
C. Executable procedural practices instead of markdown ones (markdown does not fail when the
   code moves; executable checks do).
D. Load-responsive maintenance: measure per-capability invocation on real traffic rather than
   binary has-a-consumer.
"""

LENSES = {
    "root-cause": (
        "Do not propose a fix yet. Diagnose. Six instances, three substrates (source code, "
        "persisted data, governing documentation), one day. What is the SHARED generative "
        "mechanism? Argue for one specific cause and name what evidence would falsify it. "
        "Reject the easy answers ('insufficient testing', 'move fast') unless you can show they "
        "explain why the checks that DID run all passed."
    ),
    "proposal-triage": (
        "Four proposals (A-D) are on the table. Rank them by how much of the SIX instances each "
        "would actually have caught, instance by instance. Be specific: for each proposal name "
        "which numbered instances it catches and which it structurally cannot. A proposal that "
        "catches nothing on this list is a distraction regardless of how good it sounds. Then say "
        "which ONE to build first and what it costs."
    ),
    "adversary": (
        "Assume the six instances are NOT a coherent class and that grouping them is a "
        "storytelling error. Argue that case as strongly as you can. Are these six unrelated bugs "
        "that pattern-matching has bundled? If the grouping IS sound, say what would distinguish "
        "a real defect class from an appealing narrative — and apply that test."
    ),
    "incentive": (
        "Ignore the technical layer. Every one of these six was produced by an automated or "
        "semi-automated process that had NO INCENTIVE to verify its own output, and every one "
        "produced a artifact that LOOKS like success. What is the minimal change to what gets "
        "REWARDED or RECORDED that would make the defect unprofitable to produce? Concrete "
        "mechanisms only, not culture advice."
    ),
}

MODELS = [
    ("deepseek-v4-pro:cloud", "root-cause"),
    ("qwen3.5:397b-cloud", "proposal-triage"),
    ("nemotron-3-ultra:cloud", "adversary"),
    ("glm-5.2:cloud", "incentive"),
]

VERDICT_RE = re.compile(r"VERDICT:\s*([A-Z][A-Z-]{2,30})", re.I)


def extract_verdict(text: str) -> str:
    hits = VERDICT_RE.findall(text or "")
    return hits[-1].upper() if hits else "INCONCLUSIVE"


def degenerate(text: str) -> bool:
    if len(text) < 200:
        return True
    words = text[-600:].split()
    if len(words) < 12:
        return True
    grams = [" ".join(words[i : i + 6]) for i in range(len(words) - 5)]
    return max(grams.count(g) for g in set(grams)) >= 3


def call_cloud(model: str, prompt: str, timeout: int = 900) -> str:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.3},
        }
    ).encode()
    req = urllib.request.Request(
        CLOUD_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        d = json.loads(r.read())
    if "error" in d:
        raise RuntimeError(str(d["error"])[:200])
    return (d.get("message", {}).get("content") or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--lanes", default="")
    args = ap.parse_args()

    if args.self_test:
        ok = True
        for name, text, want in [
            ("no marker", "Looks fine.", "INCONCLUSIVE"),
            ("last wins", "VERDICT: A\nActually VERDICT: B-C", "B-C"),
            ("empty", "", "INCONCLUSIVE"),
        ]:
            got = extract_verdict(text)
            ok &= got == want
            print(f"  [{'ok  ' if got == want else 'FAIL'}] {name}: {got}")
        print("SELF-TEST", "PASS" if ok else "FAIL")
        return 0 if ok else 1

    specs = MODELS
    if args.lanes:
        want = set(args.lanes.split(","))
        specs = [s for s in specs if s[0] in want or s[1] in want]

    run = DurableRun.attach("cloud-defect-class-consult")
    print(f"durable run -> {run.dir}\n")
    calls = 0

    for model, lens in specs:
        prompt = f"""You are consulted as an outside view on a live engineering question.

{EVIDENCE}

YOUR ASSIGNED LENS — stay in it, do not answer the other lenses' questions:
{LENSES[lens]}

Rules:
- Be concrete. Reference the numbered instances by number.
- Do NOT restate the evidence back. It is the input, not the deliverable.
- If you cannot answer within your lens, say so and say why — that is a real result.
- End with one line: VERDICT: <one hyphenated token summarising your position>
"""
        t0 = time.time()
        print(f"[{model} / {lens}] ...", flush=True)
        try:
            text = call_cloud(model, prompt)
            err = ""
            calls += 1
        except Exception as e:
            text, err = "", f"{type(e).__name__}: {e}"[:200]

        result = {
            "model": model,
            "lens": lens,
            "elapsed_s": round(time.time() - t0, 1),
            "chars": len(text),
            "verdict": extract_verdict(text) if not err else "INSTRUMENT-FAILED",
            "degenerate": degenerate(text) if text else None,
            "error": err,
            "text": text,
        }
        run.record_lane(result)
        print(
            f"    -> {result['verdict']:24} {result['chars']:6}ch "
            f"{result['elapsed_s']:6.1f}s {err}",
            flush=True,
        )

    print(f"\ncloud calls made: {calls}")
    print("lanes persisted under", run.dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
