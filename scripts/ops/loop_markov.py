#!/usr/bin/env python3
"""Absorbing Markov chain over the autopoietic loop, estimated from loop_branching_ratio.compute().

States (item lifecycle, linear): CREATED -> DECIDED -> TASK -> ACT_PROSE -> ACT_DIFF -> CLOSED,
every transient state also exits to STUCK ("no transition observed within the window").
Row p(s->next) = item-level count at next / item-level count at s, from the SAME attributed
counts as the sigma report. A row whose count is UNKNOWN (unreadable source) is UNKNOWN and so is
every number reachable through it -- never 0. A row with 0 parents was never observed: it goes to
STUCK with p=1 in the MEASURED chain, and to its successor with p=1 in the OPTIMISTIC chain (the
upper bound that makes sensitivity non-degenerate). The CREATED self-loop models actioner rescans
with p = 1 - 1/amplification; it cannot change absorption probabilities, only expected steps,
so steps are reported both as lifecycle stages (no self-loop) and as actioner visits.
"""

from __future__ import annotations

import argparse
import datetime as dt
import functools
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
import loop_branching_ratio as lbr


T = ["CREATED", "DECIDED", "TASK", "ACT_PROSE", "ACT_DIFF"]  # transient, in lifecycle order
NXT = dict(zip(T, [*T[1:], "CLOSED"], strict=True))
U = "UNKNOWN"


def item_counts(r):
    """Item-level count reaching each stage (None = UNKNOWN), from a compute() result."""
    c, nt = r["counts"], r["notes"]
    return {"CREATED": c["SENSE"], "DECIDED": nt.get("decided_items"), "TASK": nt.get("task_items"),
            "ACT_PROSE": nt.get("act_prose_items"), "ACT_DIFF": c["ACT_diff"], "CLOSED": c["CLOSE"]}  # fmt: skip


def build(n, optimistic=False, strict=True):  # strict=False: planted UNKNOWN->0 bug
    """{state: {succ: p}} or {state: UNKNOWN}. Fan-out >1 is capped at 1 (report() lists it)."""
    P = {}
    for s in T:
        a, b = n[s], n[NXT[s]]
        if not strict:
            a, b = a or 0, b or 0
        if a is None or b is None:
            P[s] = U
        elif a == 0:
            P[s] = {NXT[s]: 1.0} if optimistic else {"STUCK": 1.0}
        else:
            p = min(1.0, b / a)
            P[s] = {NXT[s]: p, "STUCK": 1.0 - p}
    return P


def _inv(M):
    k = len(M)
    A = [[*row, *(float(i == j) for j in range(k))] for i, row in enumerate(M)]
    for c in range(k):
        piv = max(range(c, k), key=lambda r: abs(A[r][c]))
        if abs(A[piv][c]) < 1e-15:
            raise ZeroDivisionError("I-Q singular: a transient state never exits")
        A[c], A[piv] = A[piv], A[c]
        A[c] = [x / A[c][c] for x in A[c]]
        for r in range(k):
            if r != c and A[r][c]:
                A[r] = [x - A[r][c] * y for x, y in zip(A[r], A[c], strict=True)]
    return [row[k:] for row in A]


def solve(P, start="CREATED"):
    """Absorption probabilities B[start], expected steps, visit probabilities h[state]."""
    tr = [s for s in P if isinstance(P[s], dict) or P[s] == U]
    reach, todo = set(), [start]
    while todo:
        s = todo.pop()
        if s in reach or s not in P:
            continue
        reach.add(s)
        if P[s] == U:
            return None
        todo += list(P[s])
    tr = [s for s in tr if s in reach]
    N = _inv([[float(i == j) - P[i].get(j, 0.0) for j in tr] for i in tr])
    i0, absorb = tr.index(start), sorted({t for s in tr for t in P[s] if t not in tr})
    B = {a: sum(N[i0][j] * P[s].get(a, 0.0) for j, s in enumerate(tr)) for a in absorb}
    h = {s: N[i0][j] / N[j][j] for j, s in enumerate(tr)} | B
    return {"absorb": B, "steps": sum(N[i0]), "visit": h}


def perturb(P, s, t, eps=0.05, renorm=True):  # renorm=False is the planted bug
    row = dict(P[s])
    row[t] = row.get(t, 0.0) + eps
    z = sum(row.values()) if renorm else 1.0
    return {**P, s: {k: v / z for k, v in row.items()}}


def sensitivity(P, target="CLOSED", renorm=True):
    base = solve(P)
    if base is None:
        return U
    b0, out = base["absorb"].get(target, 0.0), []
    for s in T:
        if isinstance(P[s], dict):
            for t in {NXT[s], s}:  # forward progress, or an extra rescan
                r = solve(perturb(P, s, t, renorm=renorm))
                out.append((f"{s}->{t}", round(r["absorb"].get(target, 0.0) - b0, 6)))
    return sorted(out, key=lambda x: -x[1])


def with_rescan(P, amp):
    if not isinstance(amp, (int, float)) or amp < 1 or not isinstance(P["CREATED"], dict):
        return U
    p = 1 - 1 / amp
    return {**P, "CREATED": {"CREATED": p, **{k: v * (1 - p) for k, v in P["CREATED"].items()}}}


def report(r):
    n = item_counts(r)
    P, Po = build(n), build(n, optimistic=True)
    s, so = solve(P), solve(Po)
    vis = solve(v) if (v := with_rescan(P, r["rescan"].get("amplification"))) != U else None
    capped = [
        s for s in T if n[s] and n[NXT[s]] is not None and n[NXT[s]] > n[s]
    ]  # fan-out >1 made p=1
    return {"item_counts": n, "fanout_capped": capped, "chain": P, "P_close": s["absorb"].get("CLOSED", 0.0) if s else U,
            "P_close_optimistic": so["absorb"].get("CLOSED", 0.0) if so else U,
            "steps_lifecycle": round(s["steps"], 4) if s else U,
            "steps_actioner_visits": round(vis["steps"], 1) if vis else U, "rescan_status": r["rescan"]["status"],
            "sensitivity_measured": sensitivity(P), "sensitivity_optimistic": sensitivity(Po)}  # fmt: skip


def backtest(src, days, now):
    mid = now - dt.timedelta(days=days / 2)

    def half(keep):  # same sources, queue restricted to one half of the window by created_at
        return {**src, "queue": lambda: [i for i in src["queue"]() if (t := lbr._ts(i.get("created_at"))) and keep(t)]}  # fmt: skip

    fit = solve(build(item_counts(lbr.compute(half(lambda t: t < mid), days, now))))
    obs = item_counts(lbr.compute(half(lambda t: t >= mid), days, now))
    if fit is None or obs["CREATED"] in (None, 0):
        return U
    rows = {st: (round(fit["visit"].get(st, 0.0), 5), round(obs[st] / obs["CREATED"], 5) if obs[st] is not None else U)
            for st in [*T[1:], "CLOSED"]}  # fmt: skip
    return {"mid": mid.isoformat(), "second_half_items": obs["CREATED"],
            "state": {k: {"pred": p, "obs": o, "abs_err": U if o == U else round(abs(p - o), 5)} for k, (p, o) in rows.items()}}  # fmt: skip


def self_test(renorm=True, unknown_as_zero=False):
    hand = {
        "A": {"A": 0.5, "B": 0.25, "X": 0.25},
        "B": {"C": 0.4, "X": 0.6},
    }  # P(C|A)=0.2, steps 2.5
    r = solve(hand, "A")
    q = perturb(hand, "A", "B", renorm=renorm)  # A: .5/1.05 .3/1.05 .25/1.05 -> P(C)=.3/.55*.4
    n = {"CREATED": 10, "DECIDED": 5, "TASK": 2, "ACT_PROSE": 1, "ACT_DIFF": 0, "CLOSED": 0}
    unk = {**n, "TASK": None}
    opt, meas, full = build(n, optimistic=True), build(n), build({**n, "ACT_DIFF": 1, "CLOSED": 1})
    cases = [("hand P(C|A)", round(r["absorb"]["C"], 9), 0.2), ("hand steps", round(r["steps"], 9), 2.5),
             ("hand visit B", round(r["visit"]["B"], 9), 0.5),
             ("perturbed P(C|A) renormalized", round(solve(q, "A")["absorb"]["C"], 9), round(0.3 / 0.55 * 0.4, 9)),
             ("measured 0 blocks optimistic too", solve(opt)["absorb"].get("CLOSED", 0.0), 0.0),
             ("measured chain: every lever dead", sensitivity(meas)[0][1], 0.0),
             ("optimistic lever = the measured-0 cut", sensitivity(opt)[0], ("ACT_PROSE->ACT_DIFF", round(0.1 * 0.05 / 1.05, 6))),
             ("P(CLOSE) = .5*.4*.5", round(solve(full)["absorb"]["CLOSED"], 9), 0.1),
             ("self-loop leaves P unchanged", round(solve(with_rescan(full, 4.0))["absorb"]["CLOSED"], 9), 0.1),
             ("lifecycle steps 1+.5+.2+.1+.1", round(solve(full)["steps"], 9), 1.9),
             ("rescan visits: 4 + .9", round(solve(with_rescan(full, 4.0))["steps"], 9), 4.9),
             ("UNKNOWN row -> P UNKNOWN", solve(build(unk, strict=not unknown_as_zero)), None)]  # fmt: skip
    fails = [f"{lbl}: got {g!r} want {w!r}" for lbl, g, w in cases if g != w]
    print("SELF-TEST", "PASS" if not fails else "FAIL", *fails, sep="\n  ")
    return not fails


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument(
        "--mutant-no-renorm", action="store_true", help="planted bug: self-test must FAIL"
    )
    ap.add_argument("--mutant-unknown-as-zero", action="store_true", help="planted bug: must FAIL")
    a = ap.parse_args()
    if a.self_test:
        return 0 if self_test(not a.mutant_no_renorm, a.mutant_unknown_as_zero) else 1
    src = {k: functools.cache(f) for k, f in lbr.LIVE.items()}  # every source read once
    now = dt.datetime.now(dt.UTC)
    r = lbr.compute(src, a.window_days, now)
    out = {"window_days": a.window_days, **report(r), "backtest": backtest(src, a.window_days, now)}
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
