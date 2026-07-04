"""FINAL diagnostic: is there a NON-DEGENERATE global cipher? Force a bijection
(Distinct rules out the all-zeros cheat), search bases, verify on held-out +
multiplication. SAT+generalizes => global rule. All fail => per-problem => dead."""
import json, csv, sys, random
csv.field_size_limit(sys.maxsize)
from z3 import Int, Solver, sat, Distinct  # type: ignore

REPO = "/home/mike-anderson/dev/cohezion/.tmp_kaggle/nemo-win"
cat = {}
for line in open(f"{REPO}/problems.jsonl"):
    o = json.loads(line); cat[o["id"]] = o["category"]
P, A = {}, {}
for row in csv.DictReader(open(f"{REPO}/train.csv")):
    P[row["id"]] = row["prompt"]; A[row["id"]] = row["answer"]
OPS = set("*+-/")

def parse_clean(prompt):
    exs, q = [], None
    for ln in prompt.splitlines():
        low = ln.lower()
        if "determine the result" in low:
            q = ln.split(":", 1)[1].strip() if ":" in ln else None; continue
        if " = " in ln and "alice" not in low and "example" not in low:
            lhs, rhs = ln.split(" = ", 1); exs.append((lhs, rhs))
    return exs, q

def split5(e):
    return (e[:2], e[2], e[3:5]) if len(e) == 5 and e[2] in OPS else None

addsub, mul, allsyms = [], [], set()
for i, c in cat.items():
    if not c.startswith("cryptarithm") or i not in P: continue
    exs, q = parse_clean(P[i])
    for lhs, out in list(exs) + ([(q, A[i])] if q and i in A else []):
        sp = split5(lhs)
        if sp:
            allsyms.update(sp[0] + sp[2] + out)
            (addsub if sp[1] in "+-" else (mul if sp[1] == "*" else [])).append((sp[0], sp[1], sp[2], out))
syms = sorted(allsyms)
random.Random(7).shuffle(addsub)
fit, hold = addsub[:250], addsub[250:700]

def intval(s, sol, base):
    v = 0
    for ch in s: v = v * base + sol[ch]
    return v

print(f"symbols={len(syms)}  fit={len(fit)} hold={len(hold)} mul={len(mul)}")
for base in [26, 28, 30, 32, 36, 40, 50, 64, 90]:
    val = {s: Int(f"v{ord(s)}") for s in syms}
    S = Solver(); S.set("timeout", 20000)
    for s in syms: S.add(val[s] >= 0, val[s] < base)
    S.add(Distinct(*val.values()))
    def e(s):
        x = 0
        for ch in s: x = x * base + val[ch]
        return x
    for Aa, op, Bb, out in fit:
        S.add((e(Aa) + e(Bb) if op == "+" else e(Aa) - e(Bb)) == e(out))
    r = S.check()
    if r != sat:
        print(f"base={base}: {r}")
        continue
    m = S.model(); sol = {s: m[val[s]].as_long() for s in syms}
    def ver(ts):
        ok = 0
        for Aa, op, Bb, out in ts:
            lv, rv, ov = intval(Aa, sol, base), intval(Bb, sol, base), intval(out, sol, base)
            rr = lv + rv if op == "+" else (lv - rv if op == "-" else lv * rv)
            ok += (rr == ov)
        return ok
    print(f"base={base}: SAT  held-out +/- {ver(hold)}/{len(hold)} ({100*ver(hold)/max(1,len(hold)):.0f}%)  "
          f"* {ver(mul)}/{len(mul)} ({100*ver(mul)/max(1,len(mul)):.0f}%)")
