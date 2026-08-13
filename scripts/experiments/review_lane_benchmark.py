"""Which local models can actually review code? Overnight fleet benchmark.

THE QUESTION, stated so it can come back "none of them":

    Cohezion routes adversarial code review to local lanes. On 2026-08-12 one lane produced
    9 findings of which 2 were valid -- 78% fabrication, including three arithmetic errors
    on numbers supplied in its own prompt. Nobody has measured which models can do this job,
    so every routing decision is a guess.

WHY MUTATION TESTING IS THE RIGHT INSTRUMENT: a planted defect has EXACT ground truth. No
LLM judge, no rubric, no "who reviews the reviewer" regress. Either the model found the bug
that is provably there, or it did not.

THE CLEAN CONTROLS ARE THE POINT. Half the failure mode is a model that says "yes there is a
bug" to everything -- which scores 100% detection and is worthless. Clean tasks measure
that directly: a BUG verdict on correct code is a fabrication, full stop. The headline
metric is therefore balanced accuracy, not detection rate.

GROUND TRUTH IS EXECUTED, NOT ASSERTED (gate S1). Every buggy variant is RUN against inputs
where it must disagree with the reference, and every clean variant is RUN where it must
agree. A "buggy" function that happens to be correct would silently poison every score
derived from it, and asserting the defect in a comment cannot catch that.

V-MODEL GATES, each aborts rather than reporting a number:
  S1  executable ground truth: buggy variants MUST differ from reference, clean MUST match
  S2  the marker contract must be extractable from a synthetic reply (the parser is an
      instrument too, and an unvalidated parser scores everything as unparseable)
  C1  a degenerate ALWAYS-BUG strategy must score ~0.5 balanced accuracy. If it scores well,
      the metric rewards the exact pathology being measured and every result is void.
  C2  a degenerate ALWAYS-CLEAN strategy must likewise score ~0.5.

Sequential by construction: llm headroom on this host is 0 (3 of 3 slots), and running
lanes concurrently produced empty replies and HTTP 500s on 2026-08-12.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

try:
    from cohezion.data_mesh.daemon_health import DaemonHealth, make_bus_publisher
except Exception:  # pragma: no cover - benchmark must run without the bus
    DaemonHealth = None  # type: ignore[assignment]
    make_bus_publisher = None  # type: ignore[assignment]

ENDPOINT = "http://localhost:13305/api/v1/chat/completions"
CKPT = Path("/tmp/claude-1000/review_bench_ckpt.json")
RESULT = Path("/tmp/claude-1000/review_bench_result.json")

MODELS = [
    "lfm2.5-230m-code-exp-GGUF-F16",
    "llama3.2-3b-FLM",
    "qwen3-4b-FLM",
    "SmolLM3-3B-IQ4_XS-GGUF-IQ4_XS",
    "Qwen3-8B-GGUF",
    "deepseek-r1-0528-8b-FLM",
    "gpt-oss-20b",
    "Gemma-4-26B-A4B-it-GGUF",
    "Nemotron-3-Nano-30B-A3B-GGUF",
    "Qwen3-Coder-30B-A3B-Instruct-GGUF",
    "Gemma-4-31B-it-GGUF",
    "Qwen3.6-35B-A3B-GGUF",
]

# ---------------------------------------------------------------- the corpus
# Each task: (name, source, is_buggy, defect_keywords, probe_inputs)
# `reference` is the CORRECT implementation; buggy variants must diverge on probe inputs.

TASKS: list[dict] = [
    {
        "name": "offbyone_last_element",
        "buggy": True,
        "keywords": ["off-by-one", "off by one", "range", "last", "len(", "n - 1", "n-1", "misses", "skip"],
        "reference": "def total(xs):\n    s = 0\n    for i in range(len(xs)):\n        s += xs[i]\n    return s\n",
        "source": "def total(xs):\n    s = 0\n    for i in range(len(xs) - 1):\n        s += xs[i]\n    return s\n",
        "probes": [[[1, 2, 3]], [[5]], [[4, 4, 4, 4]]],
        "probe_is_single_arg": True,
    },
    {
        "name": "inverted_comparison",
        "buggy": True,
        "keywords": ["invert", "reversed", "backwards", "<", ">", "comparison", "wrong direction", "should be"],
        "reference": "def largest(xs):\n    best = xs[0]\n    for x in xs:\n        if x > best:\n            best = x\n    return best\n",
        "source": "def largest(xs):\n    best = xs[0]\n    for x in xs:\n        if x < best:\n            best = x\n    return best\n",
        "probes": [[[1, 9, 3]], [[-4, -1]], [[2, 2, 7]]],
        "probe_is_single_arg": True,
    },
    {
        "name": "swapped_arguments",
        "buggy": True,
        "keywords": ["swap", "order", "argument", "reversed", "backwards", "wrong order", "numerator", "denominator"],
        "reference": "def ratio(a, b):\n    if b == 0:\n        return 0.0\n    return a / b\n\ndef pct(part, whole):\n    return ratio(part, whole) * 100\n",
        "source": "def ratio(a, b):\n    if b == 0:\n        return 0.0\n    return a / b\n\ndef pct(part, whole):\n    return ratio(whole, part) * 100\n",
        "probes": [[1, 4], [3, 6], [2, 8]],
    },
    {
        "name": "wrong_variable",
        "buggy": True,
        "keywords": ["wrong variable", "should be", "hi", "lo", "typo", "uses", "instead of", "mid"],
        "reference": "def midpoint(lo, hi):\n    return (lo + hi) / 2\n\ndef clamp_mid(lo, hi, v):\n    m = midpoint(lo, hi)\n    return m if v > m else v\n",
        "source": "def midpoint(lo, hi):\n    return (lo + hi) / 2\n\ndef clamp_mid(lo, hi, v):\n    m = midpoint(lo, lo)\n    return m if v > m else v\n",
        "probes": [[0, 10, 8], [2, 6, 5], [1, 3, 9]],
    },
    {
        "name": "missing_zero_guard",
        "buggy": True,
        "keywords": ["zero", "division", "divide", "guard", "empty", "ZeroDivision", "len(", "crash"],
        "reference": "def mean(xs):\n    if not xs:\n        return 0.0\n    return sum(xs) / len(xs)\n",
        "source": "def mean(xs):\n    return sum(xs) / len(xs)\n",
        "probes": [[[]], [[1, 2]], [[3]]],
        "probe_is_single_arg": True,
    },
    # ---- CLEAN CONTROLS: correct code. A BUG verdict here is a fabrication. ----
    {
        "name": "clean_running_max",
        "buggy": False,
        "keywords": [],
        "reference": "def running_max(xs):\n    out = []\n    best = None\n    for x in xs:\n        best = x if best is None or x > best else best\n        out.append(best)\n    return out\n",
        "source": "def running_max(xs):\n    out = []\n    best = None\n    for x in xs:\n        best = x if best is None or x > best else best\n        out.append(best)\n    return out\n",
        "probes": [[[1, 3, 2]], [[5, 4]], [[]]],
        "probe_is_single_arg": True,
    },
    {
        "name": "clean_normalise",
        "buggy": False,
        "keywords": [],
        "reference": "def normalise(xs):\n    total = sum(xs)\n    if total == 0:\n        return [0.0 for _ in xs]\n    return [x / total for x in xs]\n",
        "source": "def normalise(xs):\n    total = sum(xs)\n    if total == 0:\n        return [0.0 for _ in xs]\n    return [x / total for x in xs]\n",
        "probes": [[[1, 1, 2]], [[0, 0]], [[5]]],
        "probe_is_single_arg": True,
    },
    {
        "name": "clean_dedupe_stable",
        "buggy": False,
        "keywords": [],
        "reference": "def dedupe(xs):\n    seen = set()\n    out = []\n    for x in xs:\n        if x not in seen:\n            seen.add(x)\n            out.append(x)\n    return out\n",
        "source": "def dedupe(xs):\n    seen = set()\n    out = []\n    for x in xs:\n        if x not in seen:\n            seen.add(x)\n            out.append(x)\n    return out\n",
        "probes": [[[1, 1, 2]], [[3, 2, 3]], [[]]],
        "probe_is_single_arg": True,
    },
]

PROMPT = """You are reviewing a short Python snippet for correctness defects.

Some snippets are CORRECT. Saying a correct snippet is buggy is as wrong as missing a real bug.

Answer in EXACTLY this format, nothing else:
VERDICT: BUG
REASON: <one sentence naming the specific defect>

or:
VERDICT: CLEAN
REASON: <one sentence>

Snippet:
```python
{code}
```
"""

VERDICT_RE = re.compile(r"VERDICT:\s*(BUG|CLEAN)", re.I)
REASON_RE = re.compile(r"REASON:\s*(.+)", re.I)


def parse(text: str) -> tuple[str | None, str]:
    v = VERDICT_RE.search(text or "")
    r = REASON_RE.search(text or "")
    return (v.group(1).upper() if v else None), (r.group(1).strip() if r else "")


# ---------------------------------------------------------------- V-model gates
def _call_fn(src: str, name: str, args: list, single: bool):
    ns: dict = {}
    exec(compile(src, "<task>", "exec"), ns)  # noqa: S102 - fixture code authored here
    fn = ns[name]
    try:
        return fn(*(args[0],)) if single else fn(*args)
    except Exception as exc:  # a crash IS a behavioural difference
        return f"RAISED:{type(exc).__name__}"


def gate_s1() -> list[str]:
    """Executable ground truth. A 'buggy' variant that behaves correctly poisons every score."""
    fails = []
    for t in TASKS:
        # Entry point = the LAST function defined; probes target it.
        entry = re.findall(r"^def (\w+)", t["source"], re.M)[-1]
        single = bool(t.get("probe_is_single_arg"))
        differs = False
        for probe in t["probes"]:
            got = _call_fn(t["source"], entry, probe, single)
            want = _call_fn(t["reference"], entry, probe, single)
            if got != want:
                differs = True
        if t["buggy"] and not differs:
            fails.append(f"S1 '{t['name']}' is labelled buggy but matches reference on all probes")
        if not t["buggy"] and differs:
            fails.append(f"S1 '{t['name']}' is labelled clean but diverges from reference")
    return fails


def gate_s2() -> list[str]:
    """The parser is an instrument. An unvalidated one scores everything unparseable."""
    fails = []
    v, r = parse("VERDICT: BUG\nREASON: off-by-one in the range call")
    if v != "BUG" or "off-by-one" not in r:
        fails.append(f"S2 parser failed on a well-formed BUG reply: {v!r} {r!r}")
    v2, _ = parse("verdict: clean\nreason: looks fine")
    if v2 != "CLEAN":
        fails.append("S2 parser is case-sensitive")
    v3, _ = parse("I think there may be an issue here somewhere.")
    if v3 is not None:
        fails.append("S2 parser invented a verdict from unstructured prose")
    return fails


def balanced_accuracy(rows: list[dict]) -> tuple[float, float, float]:
    buggy = [r for r in rows if r["buggy"]]
    clean = [r for r in rows if not r["buggy"]]
    sens = sum(r["verdict"] == "BUG" for r in buggy) / len(buggy) if buggy else float("nan")
    spec = sum(r["verdict"] == "CLEAN" for r in clean) / len(clean) if clean else float("nan")
    return sens, spec, (sens + spec) / 2


def gate_c1_c2() -> list[str]:
    """Degenerate strategies must score ~0.5, or the metric rewards the pathology."""
    fails = []
    for label, always in (("C1 ALWAYS-BUG", "BUG"), ("C2 ALWAYS-CLEAN", "CLEAN")):
        rows = [{"buggy": t["buggy"], "verdict": always} for t in TASKS]
        _, _, bal = balanced_accuracy(rows)
        if not 0.40 <= bal <= 0.60:
            fails.append(f"{label} scores {bal:.2f}, expected ~0.5 -- metric is degenerate")
    return fails


# ---------------------------------------------------------------- runner
def ask(model: str, code: str, timeout: int) -> tuple[str, float, str]:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": PROMPT.format(code=code)}],
            "max_tokens": 12000,  # thinking models spend most of this before speaking
            "seed": 7,
        }
    ).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
        ch = d["choices"][0]
        return ch["message"]["content"] or "", time.time() - t0, str(ch.get("finish_reason"))
    except (urllib.error.URLError, OSError, KeyError, ValueError, TimeoutError) as exc:
        return "", time.time() - t0, f"ERROR:{type(exc).__name__}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--max-hours", type=float, default=8.0)
    args = ap.parse_args()

    health = None
    if DaemonHealth is not None and make_bus_publisher is not None:
        health = DaemonHealth(
            "review_lane_benchmark", publish_fn=make_bus_publisher(), watch_artifact=CKPT,
            stale_after_s=1800,
        )

    print("=" * 78)
    print("V-MODEL GATES — abort rather than report a number")
    print("=" * 78)
    for label, fn in (("S1 executable ground truth", gate_s1), ("S2 parser", gate_s2), ("C1/C2 degenerate strategies", gate_c1_c2)):
        fails = fn()
        for f in fails:
            print("  FAIL:", f)
        if fails:
            if health:
                health.record_failure(label)
                health.heartbeat()
            return 2
        print(f"  {label} PASS")
    print(f"\ncorpus: {sum(t['buggy'] for t in TASKS)} buggy + {sum(not t['buggy'] for t in TASKS)} clean")
    print(f"fleet: {len(MODELS)} models x {len(TASKS)} tasks x {args.reps} reps "
          f"= {len(MODELS) * len(TASKS) * args.reps} calls\n")

    state: dict = {"rows": []}
    if CKPT.exists():
        try:
            state = json.loads(CKPT.read_text())
            print(f"resumed with {len(state['rows'])} rows\n")
        except (OSError, ValueError):
            pass
    done = {(r["model"], r["task"], r["rep"]) for r in state["rows"]}

    t0 = time.time()
    for model in MODELS:
        if time.time() - t0 > args.max_hours * 3600:
            print("time budget reached — stopping cleanly")
            break
        for rep in range(args.reps):
            for t in TASKS:
                if (model, t["name"], rep) in done:
                    continue
                text, elapsed, finish = ask(model, t["source"], args.timeout)
                verdict, reason = parse(text)
                hit = bool(verdict == "BUG" and t["keywords"] and
                           any(k.lower() in reason.lower() for k in t["keywords"]))
                state["rows"].append({
                    "model": model, "task": t["name"], "rep": rep, "buggy": t["buggy"],
                    "verdict": verdict, "reason": reason[:220], "named_defect": hit,
                    "elapsed": round(elapsed, 1), "finish": finish,
                })
                if health:
                    health.record_success() if verdict else health.record_failure(f"{model}: {finish}")
                CKPT.write_text(json.dumps(state))
        rows = [r for r in state["rows"] if r["model"] == model and r["verdict"]]
        if rows:
            sens, spec, bal = balanced_accuracy(rows)
            named = sum(r["named_defect"] for r in rows if r["buggy"])
            nb = sum(r["buggy"] for r in rows)
            print(f"  {model:<40} bal={bal:.2f} sens={sens:.2f} spec={spec:.2f} "
                  f"named={named}/{nb} parsed={len(rows)}/{len(TASKS)*args.reps}", flush=True)
        else:
            print(f"  {model:<40} NO PARSEABLE OUTPUT — lane unusable", flush=True)
        if health:
            health.heartbeat()

    print("\n" + "=" * 78)
    print(f"{'model':<40} {'bal':>5} {'sens':>5} {'spec':>5} {'named':>7} {'parsed':>7}")
    print("-" * 78)
    summary = []
    for model in MODELS:
        rows = [r for r in state["rows"] if r["model"] == model and r["verdict"]]
        attempted = len([r for r in state["rows"] if r["model"] == model])
        if not rows:
            print(f"{model:<40} {'—':>5} {'—':>5} {'—':>5} {'—':>7} {0:>3}/{attempted:<3}")
            summary.append({"model": model, "usable": False})
            continue
        sens, spec, bal = balanced_accuracy(rows)
        nb = [r for r in rows if r["buggy"]]
        named = sum(r["named_defect"] for r in nb)
        print(f"{model:<40} {bal:>5.2f} {sens:>5.2f} {spec:>5.2f} "
              f"{named:>3}/{len(nb):<3} {len(rows):>3}/{attempted:<3}")
        summary.append({"model": model, "usable": True, "balanced_accuracy": round(bal, 3),
                        "sensitivity": round(sens, 3), "specificity": round(spec, 3),
                        "named_defect": named, "n_buggy": len(nb), "parsed": len(rows),
                        "attempted": attempted})
    print("=" * 78)
    print("bal = balanced accuracy ((sens+spec)/2). 0.50 = chance. A model that always says")
    print("BUG scores sens=1.00 spec=0.00 bal=0.50 -- which is why bal is the headline.")
    RESULT.write_text(json.dumps({"summary": summary, "rows": state["rows"]}, indent=1))
    if health:
        health.heartbeat()
    return 0


if __name__ == "__main__":
    sys.exit(main())
