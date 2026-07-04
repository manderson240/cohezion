"""Test whether cryptarithm operators have GLOBAL consistent behavior.

Pool every (A, op, B, output) tuple across all cryptarithm problems:
 - each example equation 'AB op CD = OUT' in the prompt
 - each query 'AB op CD' paired with its train.csv answer (OUT = answer)
Group by operator; for each, find which DSL transform fits the most tuples.
If one transform dominates per operator => global rule exists => crackable.
"""
import json, csv, sys, re
from collections import defaultdict, Counter
csv.field_size_limit(sys.maxsize)

REPO = "/home/mike-anderson/dev/cohezion/.tmp_kaggle/nemo-win"
cat = {}
for line in open(f"{REPO}/problems.jsonl"):
    o = json.loads(line); cat[o["id"]] = o["category"]
prompts, answers = {}, {}
for row in csv.DictReader(open(f"{REPO}/train.csv")):
    prompts[row["id"]] = row["prompt"]; answers[row["id"]] = row["answer"]

OPS = set("*+-/")

def parse(prompt):
    exs, q = [], None
    for l in prompt.splitlines():
        m = re.search(r"determine the result for[: ]+(.+?)\s*\.?\s*$", l, re.I)
        if m:
            q = m.group(1).strip().strip("`"); continue
        if " = " in l and "example" not in l.lower():
            lhs, rhs = l.split(" = ", 1)
            exs.append((lhs.strip().strip("`"), rhs.strip().strip("`")))
    return exs, q

def split5(e):
    if len(e) == 5 and e[2] in OPS:
        return e[:2], e[2], e[3:5]
    return None

# DSL: name -> f(A,B)->out  (A,B are 2-char strings)
FNS = {
    "concat": lambda A, B: A + B,
    "rconcat": lambda A, B: B + A,
    "left": lambda A, B: A,
    "right": lambda A, B: B,
    "interAB": lambda A, B: A[0] + B[0] + A[1] + B[1],
    "interBA": lambda A, B: B[0] + A[0] + B[1] + A[1],
    "rev": lambda A, B: (A + B)[::-1],
    "rrev": lambda A, B: (B + A)[::-1],
    "outer": lambda A, B: A[0] + B[1],
    "inner": lambda A, B: A[1] + B[0],
    "innerR": lambda A, B: B[0] + A[1],
    "outerR": lambda A, B: B[1] + A[0],
    "A0B": lambda A, B: A[0] + B,
    "AB1": lambda A, B: A + B[1],
    "A": lambda A, B: A,
}

tuples_by_op = defaultdict(list)  # op -> list of (A,B,out)
for i, c in cat.items():
    if not c.startswith("cryptarithm") or i not in prompts:
        continue
    exs, q = parse(prompts[i])
    for lhs, out in exs:
        sp = split5(lhs)
        if sp:
            tuples_by_op[sp[1]].append((sp[0], sp[2], out))
    if q and i in answers:
        sp = split5(q)
        if sp:
            tuples_by_op[sp[1]].append((sp[0], sp[2], answers[i]))

print("Per-operator GLOBAL transform fit (over all pooled tuples):")
for op in sorted(tuples_by_op):
    tl = tuples_by_op[op]
    n = len(tl)
    fits = Counter()
    for name, f in FNS.items():
        c = 0
        for A, B, out in tl:
            try:
                if f(A, B) == out:
                    c += 1
            except Exception:
                pass
        fits[name] = c
    top = fits.most_common(4)
    best = top[0]
    print(f"  op {op!r}: n={n:5d}  best={best[0]}={100*best[1]/n:5.1f}%  "
          f"runners={[(k, f'{100*v/n:.0f}%') for k, v in top[1:]]}")

# output-length distribution per op (reveals non-2/4-char ops = value transforms)
print("\nOutput length distribution per operator:")
for op in sorted(tuples_by_op):
    lens = Counter(len(out) for _, _, out in tuples_by_op[op])
    print(f"  op {op!r}: {dict(sorted(lens.items()))}")
