"""Extract the global cipher (base-26 bijection) and solve ALL cryptarithm
problems end-to-end; measure exact-match coverage vs the answer key."""
import json, csv, sys, random
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
            q = ln.split(":", 1)[1].strip() if ":" in ln else None; continue
        if " = " in ln and "alice" not in low and "example" not in low:
            lhs, rhs = ln.split(" = ", 1); exs.append((lhs, rhs))
    return exs, q

def split5(e):
    return (e[:2], e[2], e[3:5]) if len(e) == 5 and e[2] in OPS else None

# gather +/- tuples to fit a base-26 bijection
addsub = []
allsyms = set()
for i, c in cat.items():
    if not c.startswith("cryptarithm") or i not in P:
        continue
    exs, q = parse_clean(P[i])
    rows = list(exs) + ([(q, A[i])] if q and i in A else [])
    for lhs, out in rows:
        sp = split5(lhs)
        if sp:
            allsyms.update(sp[0] + sp[2] + out)
            if sp[1] in "+-":
                addsub.append((sp[0], sp[1], sp[2], out))
syms = sorted(allsyms)
BASE = len(syms)  # 26 -> bijection digits 0..25
print(f"distinct symbols={len(syms)} -> BASE={BASE}")

random.Random(1).shuffle(addsub)
val = {s: Int(f"v{ord(s)}") for s in syms}
S = Solver()
for s in syms:
    S.add(val[s] >= 0, val[s] < BASE)
def expr(s):
    e = 0
    for ch in s: e = e * BASE + val[ch]
    return e
for Aa, op, Bb, out in addsub[:600]:
    S.add((expr(Aa) + expr(Bb) if op == "+" else expr(Aa) - expr(Bb)) == expr(out))
assert S.check() == sat, "no base solution"
m = S.model()
cipher = {s: m[val[s]].as_long() for s in syms}
print("cipher (symbol->digit):", {s: cipher[s] for s in syms})
# canonical digit->symbol from OUTPUT usage frequency (deterministic encoder)
from collections import Counter as _C, defaultdict as _D
out_use = _D(_C)
for i, c in cat.items():
    if not c.startswith("cryptarithm") or i not in A: continue
    for ch in A[i]:
        if ch in cipher: out_use[cipher[ch]][ch] += 1
inv = {}
ambiguous = 0
for d, ctr in out_use.items():
    inv[d] = ctr.most_common(1)[0][0]
    if len(ctr) > 1: ambiguous += 1
print(f"digits with >1 output symbol (ambiguous encode): {ambiguous}/{len(out_use)}")

def dec(s):
    v = 0
    for ch in s: v = v * BASE + cipher[ch]
    return v

def enc(n, width=None):
    if n < 0: return None
    digs = []
    if n == 0: digs = [0]
    while n: digs.append(n % BASE); n //= BASE
    digs = digs[::-1]
    if width: digs = [0] * (width - len(digs)) + digs
    return "".join(inv[d] for d in digs)

def solve_query(q):
    sp = split5(q)
    if not sp: return None
    Aa, op, Bb = sp
    a, b = dec(Aa), dec(Bb)
    if op == "+": r = a + b
    elif op == "-": r = a - b
    elif op == "*": r = a * b
    elif op == "/":
        if b == 0 or a % b: return None
        r = a // b
    else: return None
    return enc(r)

# measure exact-match over ALL cryptarithm problems, by category
from collections import Counter
res = Counter(); tot = Counter()
mism = []
for i, c in cat.items():
    if not c.startswith("cryptarithm") or i not in P or i not in A:
        continue
    _, q = parse_clean(P[i])
    if not q: continue
    tot[c] += 1
    pred = solve_query(q)
    if pred is not None and pred == A[i]:
        res[c] += 1
    elif len(mism) < 8:
        mism.append((c, q, pred, A[i]))
print("\n=== EXACT-MATCH coverage (global cipher solver) ===")
for c in sorted(tot):
    print(f"  {c}: {res[c]}/{tot[c]} ({100*res[c]/tot[c]:.1f}%)")
print("\nsample mismatches (cat, query, pred, answer):")
for x in mism: print("  ", x)
