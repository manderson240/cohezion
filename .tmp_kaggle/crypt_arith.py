"""Confirm the arithmetic-cryptarithm hypothesis and find the base."""
import json, csv, sys, re
from collections import Counter
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

tuples = []  # (A, op, B, out)
symbols = Counter()
for i, c in cat.items():
    if not c.startswith("cryptarithm") or i not in prompts:
        continue
    exs, q = parse(prompts[i])
    rows = list(exs)
    if q and i in answers:
        rows.append((q, answers[i]))
    for lhs, out in rows:
        sp = split5(lhs)
        if sp:
            tuples.append((sp[0], sp[1], sp[2], out))
            for ch in sp[0] + sp[2] + out:
                symbols[ch] += 1

print(f"total tuples: {len(tuples)}")
print(f"distinct symbols: {len(symbols)}")
print("symbols by frequency:", "".join(s for s, _ in symbols.most_common()))

# Test: for '-' with 1-char output, are the high digits equal (A[0]==B[0])?
minus1 = [(A, B, out) for A, op, B, out in tuples if op == "-" and len(out) == 1]
eq_hi = sum(1 for A, B, out in minus1 if A[0] == B[0])
print(f"\n'-' 1-char-output tuples: {len(minus1)}; A[0]==B[0]: {eq_hi} ({100*eq_hi/max(1,len(minus1)):.1f}%)")

# For those, out = val(A[1]) - val(B[1]); collect (A1,B1,out) to deduce ordering deltas
print("sample '-' 1-char (A,B,out):", minus1[:12])

# '+' 2-char output with no carry: out[0] from val(A0)+val(B0), out[1] from val(A1)+val(B1)
plus2 = [(A, B, out) for A, op, B, out in tuples if op == "+" and len(out) == 2]
print(f"\n'+' 2-char-output tuples: {len(plus2)}; sample:", plus2[:10])

# Check '*' outputs that ARE concat (digit*? ) vs not
star = [(A, B, out) for A, op, B, out in tuples if op == "*"]
print(f"\n'*' tuples: {len(star)}; sample:", star[:8])
