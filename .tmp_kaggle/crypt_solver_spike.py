"""Verifiable solver spike for cryptarithm categories.

Form: AB [op] CD = OUT, op in {*,+,-,/}. Each operator's meaning is induced
per-problem from the examples. We try a DSL of string transforms; for each
operator keep transforms consistent with ALL its examples; if the query's
operator resolves to a unique output, predict it. Measure exact-match vs
ground truth (train.csv answers) => real coverage number.
"""
import json, csv, sys, re
from collections import defaultdict
csv.field_size_limit(sys.maxsize)

REPO = "/home/mike-anderson/dev/cohezion/.tmp_kaggle/nemo-win"
cat, status = {}, {}
for line in open(f"{REPO}/problems.jsonl"):
    o = json.loads(line); cat[o["id"]] = o["category"]; status[o["id"]] = o.get("status", "?")
prompts, answers = {}, {}
for row in csv.DictReader(open(f"{REPO}/train.csv")):
    prompts[row["id"]] = row["prompt"]; answers[row["id"]] = row["answer"]

OPS = set("*+-/")

def parse(prompt):
    """Return (examples=[(expr5, out)], query5) or None."""
    lines = [l.rstrip() for l in prompt.splitlines()]
    exs, q = [], None
    for l in lines:
        m = re.search(r"determine the result for[: ]+(.+?)\s*\.?\s*$", l, re.I)
        if m:
            q = m.group(1).strip().strip("`")
            continue
        if " = " in l and "example" not in l.lower():
            lhs, rhs = l.split(" = ", 1)
            lhs = lhs.strip().strip("`"); rhs = rhs.strip().strip("`")
            exs.append((lhs, rhs))
    return exs, q

def split5(expr):
    """AB op CD -> (A=expr[:2], op=expr[2], B=expr[3:5]) if len 5 & expr[2] in OPS."""
    if len(expr) != 5 or expr[2] not in OPS:
        return None
    return expr[:2], expr[2], expr[3:5]

# DSL of candidate transforms: f(A,B) -> output string. A,B are 2-char strings.
def dsl():
    fns = {}
    fns["concat"] = lambda A, B: A + B
    fns["rconcat"] = lambda A, B: B + A
    fns["left"] = lambda A, B: A
    fns["right"] = lambda A, B: B
    fns["interleave_AB"] = lambda A, B: A[0] + B[0] + A[1] + B[1]
    fns["interleave_BA"] = lambda A, B: B[0] + A[0] + B[1] + A[1]
    fns["rev_concat"] = lambda A, B: (A + B)[::-1]
    fns["A0B"] = lambda A, B: A[0] + B
    fns["AB0"] = lambda A, B: A + B[0]
    fns["outer"] = lambda A, B: A[0] + B[1]
    fns["inner"] = lambda A, B: A[1] + B[0]
    fns["A1B"] = lambda A, B: A[1] + B
    fns["AB1"] = lambda A, B: A + B[1]
    fns["A0B0"] = lambda A, B: A[0] + B[0]
    fns["A1B1"] = lambda A, B: A[1] + B[1]
    fns["B0A"] = lambda A, B: B[0] + A
    fns["BA0"] = lambda A, B: B + A[0]
    return fns

FNS = dsl()

def solve(prompt):
    exs, q = parse(prompt)
    if q is None:
        return None
    qp = split5(q)
    if qp is None:
        return None
    qA, qop, qB = qp
    # gather example transforms by operator
    by_op = defaultdict(list)
    for lhs, out in exs:
        sp = split5(lhs)
        if sp is None:
            continue
        A, op, B = sp
        by_op[op].append((A, B, out))
    # find candidate fns consistent with ALL examples of the query operator
    cand = []
    samples = by_op.get(qop, [])
    if not samples:
        return None
    for name, f in FNS.items():
        ok = True
        for A, B, out in samples:
            try:
                if f(A, B) != out:
                    ok = False; break
            except Exception:
                ok = False; break
        if ok:
            cand.append(name)
    # require all surviving candidates to agree on the query output (unique prediction)
    preds = set()
    for name in cand:
        try:
            preds.add(FNS[name](qA, qB))
        except Exception:
            pass
    if len(preds) == 1:
        return next(iter(preds))
    return None

for category in ["cryptarithm_deduce", "cryptarithm_guess"]:
    ids = [i for i in cat if cat[i] == category and i in prompts and i in answers]
    solved = attempted = correct = 0
    for i in ids:
        pred = solve(prompts[i])
        if pred is not None:
            attempted += 1
            if pred == answers[i]:
                correct += 1
    n = len(ids)
    print(f"{category}: n={n}  predicted={attempted} ({100*attempted/n:.1f}%)  "
          f"exact_correct={correct} ({100*correct/n:.1f}% of all, "
          f"{100*correct/max(1,attempted):.1f}% of predicted)")
