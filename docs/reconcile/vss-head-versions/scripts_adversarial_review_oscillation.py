"""Multiperspective adversarial review of the oscillation detector.

Two tiers, distinct lenses, and a POSITIVE marker contract.

WHY THE MARKER CONTRACT: a lane that returns nothing must not read as approval. The known
hazard (`silent-lens-counts-as-approval`) is a review harness that treats "no findings" as
PASS. Here a lane is INCONCLUSIVE unless it emits `VERDICT: <token>`, and INCONCLUSIVE is
reported separately from PASS. A zero-finding lane is treated as suspect, not as a clean bill.

Lanes never share a lens. Redundancy finds the same thing N times; diversity is what catches
failure modes a single lens is blind to.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

from durable_swarm_output import DurableRun
from untrusted_content import wrap_untrusted


# Both are loopback. S310's concern is user-supplied schemes; these are fixed literals.
LOCAL_URL = "http://localhost:13305/api/v1/chat/completions"
CLOUD_URL = "http://localhost:11434/api/chat"

# Family-specific reasoning delimiters. rsplit on the LAST one — a model can emit several.
_THINK_PATTERNS = [
    (r"<\|channel\|?>?thought", r"<\|?channel\|>"),
    (r"<think>", r"</think>"),
]


def strip_reasoning(text: str) -> str:
    for _, close in _THINK_PATTERNS:
        parts = re.split(close, text)
        if len(parts) > 1:
            text = parts[-1]
    return text.strip()


def call_local(model: str, prompt: str, timeout: int = 900) -> tuple[str, str]:
    """Call a local lane, budgeting for reasoning.

    MEASURED 2026-08-19: at max_tokens=2000, Qwen3.6-35B-A3B-MTP returned
    finish_reason='length', 6,449 chars of reasoning_content, and **0 chars of content** —
    completion_tokens hit the cap exactly. The budget was consumed thinking. This is NOT a
    context-window problem: the prompt was 2,437 tokens against a ~8,192-token slot
    (ctx_size 16384 / -np 2), leaving 5,755 free. Raising the cap is the correct fix here;
    raising it ABOVE the slot would not be (see thinking-model-token-budget-gate-trap).

    Truncation is reported distinctly from silence. A model that ran out of budget has not
    declined to answer, and conflating the two would let an apparatus fault read as a verdict.
    """
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 5000,
            "temperature": 0.3,
        }
    ).encode()
    req = urllib.request.Request(LOCAL_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    choice = d["choices"][0]
    msg = choice["message"]
    content = strip_reasoning(msg.get("content") or "")
    if not content and choice.get("finish_reason") == "length":
        reasoning = len(msg.get("reasoning_content") or "")
        return "", f"TRUNCATED: budget exhausted in reasoning ({reasoning} chars), no content"
    return content, ""


def call_cloud(model: str, prompt: str, timeout: int = 900) -> tuple[str, str]:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.3},
        }
    ).encode()
    req = urllib.request.Request(CLOUD_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    if "error" in d:
        raise RuntimeError(str(d["error"])[:200])
    return strip_reasoning(d.get("message", {}).get("content") or ""), ""


# DO NOT "fix" this with constrained decoding. It looks like the obvious upgrade and it is a
# regression here. Measured 2026-08-19: :13305 does honour `response_format: json_schema` —
# Qwen3-8B returned bare prose without it and exactly `{"verdict": "FLAWED"}` with it. But a
# grammar guarantees FORM, not CONTENT: in that probe the question was nonsense and the model
# answered FLAWED anyway, because the grammar left it no other move.
#
# The three local lanes that fail here surface as INCONCLUSIVE — visibly broken, excluded from
# the tally, and that visibility is what prompted the diagnosis that found a real budget defect.
# Under a schema they would have returned three well-formed verdicts backed by nothing,
# indistinguishable from real votes. That converts a visible failure into an invisible one.
#
# Rule: constrain EXTRACTION output (a parse failure is pure loss); never constrain JUDGMENT
# output, because the absence of an answer is itself information and a grammar destroys it.
VERDICT_RE = re.compile(r"VERDICT:\s*(SOUND|FLAWED|UNSAFE-TO-PROMOTE)", re.I)


def extract_verdict(text: str) -> str:
    """Positive contract. No marker anywhere => INCONCLUSIVE, never PASS.

    Not `^`-anchored: models indent, bullet, and bold their markers.
    """
    hits = VERDICT_RE.findall(text or "")
    return hits[-1].upper() if hits else "INCONCLUSIVE"


def degenerate(text: str) -> bool:
    """Tail-window repetition check — local models degenerate at the END, not the start.

    MEASURED FAILURE 2026-08-19: the first version used a unique-WORD ratio and passed a
    Qwen3-8B lane that had collapsed into repeating one sentence with cosmetic renumbering.
    Its tail held 50 unique words out of 91 — healthy by that measure — while a single 6-gram
    ("with hidden drift in band is") appeared 4 times. Vocabulary diversity does not detect
    PHRASE repetition, so the gate was measuring the wrong thing entirely.

    n-gram repetition is the right instrument. Real prose does not repeat a 6-word phrase
    three times inside 600 characters; a degenerating model does little else.
    """
    if len(text) < 200:
        return True
    words = text[-600:].split()
    if len(words) < 12:
        return True
    grams = [" ".join(words[i : i + 6]) for i in range(len(words) - 5)]
    return max(grams.count(g) for g in set(grams)) >= 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lanes", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        ok = True
        cases = [
            ("no marker at all", "This looks fine to me.", "INCONCLUSIVE"),
            ("indented marker", "  - **VERDICT: FLAWED** because...", "FLAWED"),
            ("last marker wins", "VERDICT: SOUND\nOn reflection VERDICT: FLAWED", "FLAWED"),
            ("empty", "", "INCONCLUSIVE"),
        ]
        for name, text, want in cases:
            got = extract_verdict(text)
            flag = "ok " if got == want else "FAIL"
            ok &= got == want
            print(f"  [{flag}] {name}: {got}")
        # The 4th case is the REGRESSION case: it is the real Qwen3-8B tail that the
        # unique-word version of this gate scored as healthy. If it ever passes again the
        # gate has regressed to measuring vocabulary instead of repetition.
        _qwen_tail = (
            "**Input:** A list with hidden drift in band is not hidden thrash. "
            "**Actual Input:** A list with hidden drift in band is not hidden thrash. "
            "**Consequence:** The function incorrectly flags a list with hidden drift in "
            "band is not hidden thrash. I could not break the function with any valid input "
            "with hidden drift in band is not hidden thrash."
        )
        for name, text, want in [
            ("empty is degenerate", "", True),
            ("word-level repetition is degenerate", "the the the " * 90, True),
            (
                "real prose is not",
                "The threshold at 0.6 sits mid-gap between two synthetic clusters, which is "
                "defensible only while those clusters remain the whole evidence base. A "
                "distribution-relative bound would adapt as production series accumulate, "
                "though it needs a warm-up period before its variance estimate stabilises. "
                "Meanwhile the minimum sample floor interacts badly with short windows, "
                "since a degenerate candidate range collapses to one testable lag.",
                False,
            ),
            ("REGRESSION: real Qwen3-8B collapsed tail", _qwen_tail, True),
        ]:
            got = degenerate(text)
            flag = "ok " if got == want else "FAIL"
            ok &= got == want
            print(f"  [{flag}] {name}: {got}")
        print("SELF-TEST", "PASS" if ok else "FAIL")
        return 0 if ok else 1

    # Source under review is UNTRUSTED input: measured 2026-08-07, a reviewed file's embedded
    # prompt-template string literals captured 2 of 3 reviewer models. Fence it.
    src = wrap_untrusted(
        Path("src/cohezion/compound/oscillation_detector.py").read_text(), "SOURCE"
    )
    wiring = Path("src/cohezion/compound/degradation_detector.py").read_text()
    m = re.search(r"    def _refresh_oscillation.*?\n    def compute_friction", wiring, re.S)
    wiring_excerpt = wrap_untrusted(m.group(0) if m else "(wiring not found)", "SOURCE")
    tests = wrap_untrusted(
        Path("tests/compound/test_oscillation_detector.py").read_text(), "TESTS"
    )

    LENSES = {
        "threshold-calibration": (
            "The threshold OSCILLATION_THRESHOLD = 0.6 was chosen from SEVEN synthetic cases "
            "(non-thrash scored <=0.206, thrash 1.000) and has NEVER fired on real data. "
            "Attack the threshold specifically. Is 0.6 defensible, arbitrary, or actively "
            "misleading? What would a principled derivation look like? Is a fixed scalar even "
            "the right shape here, versus a distribution-relative bound?"
        ),
        "false-negative-hunt": (
            "Find real oscillation this scorer MISSES. The sign-flip requirement (autocorr "
            "positive at lag k, negative near k/2) is restrictive. Construct concrete series "
            "that a practitioner would call thrash but that score below 0.6: amplitude-"
            "modulated cycles, period drift, oscillation buried in trend, duty cycles that "
            "are not 50/50, three-state rotations A->B->C->A. Give numbers, not adjectives."
        ),
        "false-positive-hunt": (
            "Find series that are NOT thrash but score above 0.6. The authors rejected raw "
            "autocorrelation because it fired on Brownian drift at 0.821 — did the fix fully "
            "close that, or just the one seed they tested? Consider mean-reverting processes, "
            "AR(1) with negative coefficient, sawtooth recovery after alerts, and a metric "
            "that legitimately alternates because the SYSTEM alternates by design."
        ),
        "boundary-and-window": (
            "Attack MIN_SAMPLES = 8 and the n=20 window. The loop runs k in range(4, n//2+1), "
            "so at n=8 only k=4 is tested and neg uses lag max(2, 2)=2. Is that a real test or "
            "a degenerate one? What happens at n=8,9,10 exactly? Is the period-2 special case "
            "(lag1 < -0.5) consistent with the general branch, or a second, differently-"
            "calibrated detector bolted on? Could the two disagree?"
        ),
        "coupling-to-cc1": (
            "Attack is_hidden_thrash's hard-coded band [1.3, 1.7]. It duplicates the CC1 "
            "constant rather than importing it, so the two can silently drift apart. Also: is "
            "gating the composite on FD correct at all, or does it throw away true positives "
            "whose FD sits just outside the band? What is the failure mode if CC1 is ever "
            "recalibrated?"
        ),
        "honesty-audit": (
            "The authors claim OBSERVE-ONLY status and admit real-data validation was "
            "INCONCLUSIVE (326 series, max score 0.139, 98% near-degenerate). Audit that "
            "honesty. Is the admission accurate, or does it understate/overstate? Given a "
            "detector that has never fired on real data, is shipping it observe-only the right "
            "call, or is it dormant code that will rot? What single piece of evidence would "
            "most change your mind?"
        ),
    }

    LANE_SPECS = [
        ("local", "Qwen3.6-35B-A3B-MTP-GGUF", "threshold-calibration"),
        ("local", "gpt-oss-20b", "boundary-and-window"),
        ("local", "Qwen3-8B-GGUF", "false-positive-hunt"),
        ("cloud", "deepseek-v4-pro:cloud", "false-negative-hunt"),
        ("cloud", "qwen3.5:397b-cloud", "coupling-to-cc1"),
        ("cloud", "nemotron-3-ultra:cloud", "honesty-audit"),
    ]
    if args.lanes:
        want = set(args.lanes.split(","))
        LANE_SPECS = [s for s in LANE_SPECS if s[1] in want or s[2] in want]

    run = DurableRun.attach("oscillation-adversarial-review")
    print(f"durable run -> {run.dir}\n")

    for tier, model, lens in LANE_SPECS:
        prompt = f"""You are an adversarial reviewer. ASSUME THIS CODE IS BROKEN and find how.

Your assigned lens — stay in it, do not review the whole file generically:
{LENSES[lens]}

A review that finds nothing is a FAILED review. If you genuinely cannot break it under your
lens, say so explicitly and explain what you tried.

=== oscillation_detector.py ===
{src}

=== how it is wired into DegradationDetector ===
{wiring_excerpt}

=== the tests that currently pass ===
{tests}

Respond with:
1. FINDINGS — numbered. For each: the concrete failure, a specific input that triggers it
   (actual numbers), and the consequence. No vague concerns.
2. WHAT I COULD NOT BREAK — be specific about what you tried.
3. A final line, exactly: VERDICT: SOUND or VERDICT: FLAWED or VERDICT: UNSAFE-TO-PROMOTE
"""
        t0 = time.time()
        print(f"[{tier:5}] {model} / {lens} ...", flush=True)
        try:
            fn = call_local if tier == "local" else call_cloud
            text, err = fn(model, prompt)
        except Exception as e:
            text, err = "", f"{type(e).__name__}: {e}"[:300]

        result = {
            "tier": tier,
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
            f"        -> {result['verdict']:18} {result['chars']:6}ch "
            f"{result['elapsed_s']:6.1f}s {err}",
            flush=True,
        )

    print("\nlanes persisted under", run.dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
