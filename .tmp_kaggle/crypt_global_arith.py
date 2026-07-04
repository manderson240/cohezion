"""DECISIVE DIAGNOSTIC: is there ONE global (base, symbol->digit) mapping that
makes the cryptarithm arithmetic work across ALL problems?

Strategy: use +/- equations (linear in val given fixed base) to solve the global
mapping with Z3 for candidate bases; then VERIFY the solution reproduces held-out
+/- AND * equations. Generalization => global rule (learnable). No fit => per-problem.
"""
import json, csv, sys
csv.field_size_limit(sys.maxsize)
from z3 import Int, Solver, sat  # type: ignore

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
            q = ln.split(":", 1)[1].strip() if ":" in ln else None
            continue
        if " = " in ln and "alice" not in low and "example" not in low:
            lhs, rhs = ln.split(" = ", 1)
            exs.append((lhs, rhs))
    return exs, q

def split5(e):
    return (e[:2], e[2], e[3:5]) if len(e) == 5 and e[2] in OPS else None

tuples = []  # (Astr, op, Bstr, outstr)
for i, c in cat.items():
    if not c.startswith("cryptarithm") or i not in P:
        continue
    exs, q = parse_clean(P[i])
    rows = list(exs)
    if q and i in A:
        rows.append((q, A[i]))
    for lhs, out in rows:
        sp = split5(lhs)
        if sp and all(ch not in OPS or True for ch in out):  # keep all
            tuples.append((sp[0], sp[1], sp[2], out))

syms = sorted({ch for A_, op, B_, out in tuples for ch in (A_ + B_ + out)})
print(f"tuples={len(tuples)}  distinct symbols={len(syms)}")

addsub = [t for t in tuples if t[1] in "+-"]
mul = [t for t in tuples if t[1] == "*"]
print(f"+/- tuples={len(addsub)}  * tuples={len(mul)}")

def intval_expr(s, val, base):
    e = 0
    for ch in s:
        e = e * base + val[ch]
    return e

def intval(s, sol, base):
    v = 0
    for ch in s:
        v = v * base + sol[ch]
    return v

import random
rng = random.Random(0)
fit_tuples = addsub[:]
rng.shuffle(fit_tuples)
train_set = fit_tuples[:400]
hold_set = fit_tuples[400:900]

for base in [16, 18, 20, 22, 24, 26]:
    val = {s: Int(f"v_{ord(s)}") for s in syms}
    S = Solver()
    for s in syms:
        S.add(val[s] >= 0, val[s] < base)
    for A_, op, B_, out in train_set:
        lhs = intval_expr(A_, val, base)
        rhs = intval_expr(B_, val, base)
        o = intval_expr(out, val, base)
        if op == "+":
            S.add(lhs + rhs == o)
        else:
            S.add(lhs - rhs == o)
    res = S.check()
    if res != sat:
        print(f"base={base}: UNSAT on {len(train_set)} +/- eqns")
        continue
    m = S.model()
    sol = {s: m[val[s]].as_long() for s in syms}
    # verify on held-out +/- and on *
    def verify(ts):
        ok = 0
        for A_, op, B_, out in ts:
            lv, rv, ov = intval(A_, sol, base), intval(B_, sol, base), intval(out, sol, base)
            r = lv + rv if op == "+" else (lv - rv if op == "-" else lv * rv)
            if r == ov:
                ok += 1
        return ok
    h_ok = verify(hold_set)
    m_ok = verify(mul)
    print(f"base={base}: SAT. held-out +/- {h_ok}/{len(hold_set)} ({100*h_ok/max(1,len(hold_set)):.1f}%)  "
          f"* {m_ok}/{len(mul)} ({100*m_ok/max(1,len(mul)):.1f}%)")
