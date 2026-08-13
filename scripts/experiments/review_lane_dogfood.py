"""Dogfood the review benchmark: REAL Cohezion code, REAL defects we actually shipped.

WHY THIS EXISTS. The toy-snippet benchmark (review_lane_benchmark.py) is SATURATED at the
top: three models scored balanced accuracy 1.00, so it cannot rank them. A saturated
instrument cannot answer "which lane should we route to", which was the whole question.

It also leaves a validity gap. Toy snippets are 5-line functions with textbook defects.
Cohezion code is longer, has real names, real docstrings, and defects that survived review
by a competent engineer -- because every defect below is one I SHIPPED THIS SESSION and
later found. That is the ground truth: not invented bugs, but the actual ones.

    engine_for_ignores_escalation   ME1 mutation -- reports the entry tier, so the learner
                                    is fed 'npu' for work that escalated to CPU
    idle_counted_as_failure         H3 mutation -- conflates a STARVED daemon with a FAILING
                                    one, which sends the responder to the wrong process
    gate_only_checks_all_zero       the real S4 defect an adversarial lane found on
                                    2026-08-12: the comment claims it proves the projection
                                    "mixes dimensions", the check only rejects all-zero
    heartbeat_unqueryable           the real defect found by READING THE BUS: event_type is
                                    "CUSTOM" while the payload's own kind says
                                    daemon_heartbeat, so the obvious query returns nothing
    auroc_drops_tie_correction      ties collapsed to ordinal rank, which silently inflates
                                    AUROC whenever scores repeat

Clean controls are REAL repo functions, unmodified.

SAME PROTOCOL as the toy benchmark, deliberately: identical prompt, parser, metric and
gates, so the two corpora are directly comparable. The interesting comparison is not the
absolute score but whether the RANKING is preserved. If it is, the cheap toy benchmark is a
valid proxy. If it is not, toy benchmarks are misleading -- which is a finding about
benchmarking, not about any model.

Ground truth is EXECUTED here too (gate S1): every defective variant must provably diverge
from the real implementation on probe inputs.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from review_lane_benchmark import (  # noqa: E402
    MODELS,
    ask,
    balanced_accuracy,
    gate_s2,
    parse,
)

CKPT = Path("/tmp/claude-1000/review_dogfood_ckpt.json")
RESULT = Path("/tmp/claude-1000/review_dogfood_result.json")

# ---------------------------------------------------------------- real corpus
TASKS: list[dict] = [
    {
        "name": "engine_for_ignores_escalation",
        "buggy": True,
        "keywords": ["escalat", "ignore", "unused", "min_tier", "not used", "add", "entry", "index"],
        "reference": (
            '_OMNI_TIERS = ("npu", "igpu", "cpu")\n\n'
            "def engine_for(min_tier_index, escalation_count, is_cloud):\n"
            '    if is_cloud:\n        return "cloud"\n'
            "    idx = min(max(0, int(min_tier_index) + int(escalation_count)), len(_OMNI_TIERS) - 1)\n"
            "    return _OMNI_TIERS[idx]\n"
        ),
        "source": (
            '_OMNI_TIERS = ("npu", "igpu", "cpu")\n\n'
            "def engine_for(min_tier_index, escalation_count, is_cloud):\n"
            '    """Which compute engine the cascade landed on. Cloud short-circuits;\n'
            '    otherwise NPU(0) -> iGPU(1) -> CPU(2) by (entry + escalations)."""\n'
            "    if is_cloud:\n        return \"cloud\"\n"
            "    idx = min(max(0, int(min_tier_index)), len(_OMNI_TIERS) - 1)\n"
            "    return _OMNI_TIERS[idx]\n"
        ),
        "entry": "engine_for",
        "probes": [[0, 1, False], [0, 2, False], [1, 1, False]],
    },
    {
        "name": "idle_counted_as_failure",
        "buggy": True,
        "keywords": ["idle", "failure", "conflat", "should not", "distinct", "increment", "separate"],
        "reference": (
            "class Health:\n"
            "    def __init__(self):\n        self.attempts = 0\n        self.failures = 0\n        self.idle = 0\n"
            "    def record_failure(self):\n        self.attempts += 1\n        self.failures += 1\n"
            "    def record_idle(self):\n        self.idle += 1\n"
            "    def failure_rate(self):\n"
            "        return 0.0 if self.attempts == 0 else self.failures / self.attempts\n\n"
            "def probe(n_idle):\n    h = Health()\n"
            "    for _ in range(n_idle):\n        h.record_idle()\n    return h.failure_rate()\n"
        ),
        "source": (
            "class Health:\n"
            '    """Tracks daemon health. IDLE (no work available) is a different condition\n'
            '    from FAILURE (work attempted and failed) and must not be conflated."""\n'
            "    def __init__(self):\n        self.attempts = 0\n        self.failures = 0\n        self.idle = 0\n"
            "    def record_failure(self):\n        self.attempts += 1\n        self.failures += 1\n"
            "    def record_idle(self):\n        self.idle += 1\n        self.attempts += 1\n        self.failures += 1\n"
            "    def failure_rate(self):\n"
            "        return 0.0 if self.attempts == 0 else self.failures / self.attempts\n\n"
            "def probe(n_idle):\n    h = Health()\n"
            "    for _ in range(n_idle):\n        h.record_idle()\n    return h.failure_rate()\n"
        ),
        "entry": "probe",
        "probes": [[3], [1], [10]],
    },
    {
        "name": "gate_only_checks_all_zero",
        "buggy": True,
        "keywords": ["all-zero", "all zero", "mix", "only", "does not", "concentrat", "one dimension", "weaker", "insufficient"],
        "reference": (
            "def projection_is_sane(matrix, probe):\n"
            "    out = [sum(w * v for w, v in zip(row, probe)) for row in matrix]\n"
            "    if max(abs(x) for x in out) < 1e-9:\n        return False\n"
            "    peak = max(abs(x) for x in out) or 1e-12\n"
            "    live = sum(1 for x in out if abs(x) > 0.01 * peak)\n"
            "    return live >= len(out) // 2\n"
        ),
        "source": (
            "def projection_is_sane(matrix, probe):\n"
            '    """Verify a random projection actually MIXES dimensions, rather than\n'
            '    ignoring them or funnelling everything into a single output dimension."""\n'
            "    out = [sum(w * v for w, v in zip(row, probe)) for row in matrix]\n"
            "    if max(abs(x) for x in out) < 1e-9:\n        return False\n"
            "    return True\n"
        ),
        "entry": "projection_is_sane",
        # A funnel matrix: output dim 0 alive, all others dead. Passes the buggy check.
        "probes": [
            [[[1.0, 1.0, 1.0, 1.0]] + [[0.0] * 4 for _ in range(3)], [1.0, 2.0, 3.0, 4.0]],
            [[[2.0, 0.0, 0.0, 0.0]] + [[0.0] * 4 for _ in range(3)], [1.0, 1.0, 1.0, 1.0]],
        ],
    },
    {
        "name": "heartbeat_unqueryable",
        "buggy": True,
        "keywords": ["custom", "event_type", "mismatch", "kind", "docstring", "contradict", "query", "select", "daemon_heartbeat"],
        "reference": (
            "def build_event(payload):\n"
            '    return {"event_type": payload["kind"], "source": "daemon:" + payload["daemon"],\n'
            '            "payload": payload}\n'
        ),
        "source": (
            "def build_event(payload):\n"
            '    """Publish a heartbeat. The event_type column is what consumers select on,\n'
            '    so it must match the payload kind (daemon_heartbeat)."""\n'
            '    return {"event_type": "CUSTOM", "source": "daemon:" + payload["daemon"],\n'
            '            "payload": payload}\n'
        ),
        "entry": "build_event",
        "probes": [
            [{"kind": "daemon_heartbeat", "daemon": "research_daemon"}],
            [{"kind": "daemon_heartbeat", "daemon": "compound_daemon"}],
        ],
        "probe_is_single_arg": True,
    },
    {
        "name": "auroc_drops_tie_correction",
        "buggy": True,
        "keywords": ["tie", "equal", "duplicate", "average rank", "same score", "midrank", "inflat"],
        "reference": (
            "def auroc(pos, neg):\n"
            "    scored = [(s, 1) for s in pos] + [(s, 0) for s in neg]\n"
            "    scored.sort(key=lambda t: t[0])\n"
            "    ranks = {}\n    i = 0\n"
            "    while i < len(scored):\n        j = i\n"
            "        while j + 1 < len(scored) and scored[j + 1][0] == scored[i][0]:\n            j += 1\n"
            "        avg = (i + j) / 2 + 1\n"
            "        for k in range(i, j + 1):\n            ranks[k] = avg\n"
            "        i = j + 1\n"
            "    rs = sum(ranks[k] for k, (_, lab) in enumerate(scored) if lab == 1)\n"
            "    return (rs - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))\n"
        ),
        "source": (
            "def auroc(pos, neg):\n"
            '    """Rank-based AUROC. Tied scores must receive the AVERAGE of the ranks they\n'
            '    span, otherwise the result depends on sort order."""\n'
            "    scored = [(s, 1) for s in pos] + [(s, 0) for s in neg]\n"
            "    scored.sort(key=lambda t: t[0])\n"
            "    rs = sum(k + 1 for k, (_, lab) in enumerate(scored) if lab == 1)\n"
            "    return (rs - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))\n"
        ),
        "entry": "auroc",
        "probes": [[[1.0, 1.0], [1.0, 1.0]], [[2.0, 2.0, 2.0], [2.0, 2.0]]],
    },
    # ---- CLEAN CONTROLS: real repo functions, unmodified ----
    {
        "name": "clean_feynman_path_weight",
        "buggy": False,
        "keywords": [],
        "reference": (
            "import math\n\ndef feynman_path_weight(quality, cost_usd, lam=100.0):\n"
            "    return quality * math.exp(-lam * max(0.0, cost_usd))\n"
        ),
        "source": (
            "import math\n\ndef feynman_path_weight(quality, cost_usd, lam=100.0):\n"
            '    """Path weight: quality damped exponentially by metered cost."""\n'
            "    return quality * math.exp(-lam * max(0.0, cost_usd))\n"
        ),
        "entry": "feynman_path_weight",
        "probes": [[0.5, 0.0], [1.0, 0.01], [0.8, 0.005]],
    },
    {
        "name": "clean_balanced_accuracy",
        "buggy": False,
        "keywords": [],
        "reference": (
            "def balanced_accuracy(tp, fn, tn, fp):\n"
            "    sens = tp / (tp + fn) if (tp + fn) else 0.0\n"
            "    spec = tn / (tn + fp) if (tn + fp) else 0.0\n"
            "    return (sens + spec) / 2\n"
        ),
        "source": (
            "def balanced_accuracy(tp, fn, tn, fp):\n"
            '    """Mean of sensitivity and specificity, so an always-positive predictor\n'
            '    scores 0.5 rather than 1.0."""\n'
            "    sens = tp / (tp + fn) if (tp + fn) else 0.0\n"
            "    spec = tn / (tn + fp) if (tn + fp) else 0.0\n"
            "    return (sens + spec) / 2\n"
        ),
        "entry": "balanced_accuracy",
        "probes": [[5, 5, 5, 5], [10, 0, 0, 10], [3, 1, 4, 2]],
    },
    {
        "name": "clean_lennard_jones",
        "buggy": False,
        "keywords": [],
        "reference": (
            "def lennard_jones(r, sigma, epsilon):\n"
            "    sr6 = (sigma / r) ** 6\n    sr12 = sr6 * sr6\n"
            "    return 4.0 * epsilon * (sr12 - sr6)\n"
        ),
        "source": (
            "def lennard_jones(r, sigma, epsilon):\n"
            '    """Lennard-Jones 12-6 potential."""\n'
            "    sr6 = (sigma / r) ** 6\n    sr12 = sr6 * sr6\n"
            "    return 4.0 * epsilon * (sr12 - sr6)\n"
        ),
        "entry": "lennard_jones",
        "probes": [[1.0, 1.0, 1.0], [2.0, 1.0, 1.0], [1.5, 1.2, 0.8]],
    },
]


def _call(src: str, entry: str, args: list, single: bool):
    ns: dict = {}
    exec(compile(src, "<task>", "exec"), ns)  # noqa: S102 - fixtures authored here
    try:
        return ns[entry](*(args[0],)) if single else ns[entry](*args)
    except Exception as exc:
        return f"RAISED:{type(exc).__name__}"


def gate_s1() -> list[str]:
    fails = []
    for t in TASKS:
        single = bool(t.get("probe_is_single_arg"))
        differs = any(
            _call(t["source"], t["entry"], p, single) != _call(t["reference"], t["entry"], p, single)
            for p in t["probes"]
        )
        if t["buggy"] and not differs:
            fails.append(f"S1 '{t['name']}' labelled buggy but matches reference on all probes")
        if not t["buggy"] and differs:
            fails.append(f"S1 '{t['name']}' labelled clean but diverges from reference")
    return fails


def gate_c1_c2() -> list[str]:
    fails = []
    for label, always in (("C1 ALWAYS-BUG", "BUG"), ("C2 ALWAYS-CLEAN", "CLEAN")):
        rows = [{"buggy": t["buggy"], "verdict": always} for t in TASKS]
        _, _, bal = balanced_accuracy(rows)
        if not 0.40 <= bal <= 0.60:
            fails.append(f"{label} scores {bal:.2f}, expected ~0.5 -- metric is degenerate")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--max-hours", type=float, default=8.0)
    args = ap.parse_args()

    print("=" * 78)
    print("V-MODEL GATES — real code, real defects")
    print("=" * 78)
    for label, fn in (("S1 executable ground truth", gate_s1), ("S2 parser", gate_s2), ("C1/C2 degenerate", gate_c1_c2)):
        fails = fn()
        for f in fails:
            print("  FAIL:", f)
        if fails:
            return 2
        print(f"  {label} PASS")
    print(f"\ncorpus: {sum(t['buggy'] for t in TASKS)} real defects + {sum(not t['buggy'] for t in TASKS)} clean real functions")
    print(f"fleet: {len(MODELS)} models x {len(TASKS)} tasks x {args.reps} reps\n")

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
                hit = bool(verdict == "BUG" and t["keywords"]
                           and any(k.lower() in reason.lower() for k in t["keywords"]))
                state["rows"].append({
                    "model": model, "task": t["name"], "rep": rep, "buggy": t["buggy"],
                    "verdict": verdict, "reason": reason[:220], "named_defect": hit,
                    "elapsed": round(elapsed, 1), "finish": finish,
                })
                CKPT.write_text(json.dumps(state))
        rows = [r for r in state["rows"] if r["model"] == model and r["verdict"]]
        if rows:
            sens, spec, bal = balanced_accuracy(rows)
            nb = [r for r in rows if r["buggy"]]
            print(f"  {model:<40} bal={bal:.2f} sens={sens:.2f} spec={spec:.2f} "
                  f"named={sum(r['named_defect'] for r in nb)}/{len(nb)}", flush=True)
        else:
            print(f"  {model:<40} NO PARSEABLE OUTPUT", flush=True)

    print("\n" + "=" * 78)
    print(f"{'model':<40} {'bal':>5} {'sens':>5} {'spec':>5} {'named':>7}")
    print("-" * 78)
    summary = []
    for model in MODELS:
        rows = [r for r in state["rows"] if r["model"] == model and r["verdict"]]
        if not rows:
            print(f"{model:<40} {'—':>5} {'—':>5} {'—':>5} {'—':>7}")
            summary.append({"model": model, "usable": False})
            continue
        sens, spec, bal = balanced_accuracy(rows)
        nb = [r for r in rows if r["buggy"]]
        named = sum(r["named_defect"] for r in nb)
        print(f"{model:<40} {bal:>5.2f} {sens:>5.2f} {spec:>5.2f} {named:>3}/{len(nb):<3}")
        summary.append({"model": model, "usable": True, "balanced_accuracy": round(bal, 3),
                        "sensitivity": round(sens, 3), "specificity": round(spec, 3),
                        "named_defect": named, "n_buggy": len(nb)})
    print("=" * 78)
    RESULT.write_text(json.dumps({"summary": summary, "rows": state["rows"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
