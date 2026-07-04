"""Clean-parse diagnostic: read raw train.csv, do NOT strip backticks, verify
5-char AB-op-CD structure exactly, then re-run global per-operator fit."""
import json, csv, sys
from collections import defaultdict, Counter
csv.field_size_limit(sys.maxsize)

REPO = "/home/mike-anderson/dev/cohezion/.tmp_kaggle/nemo-win"
cat = {}
for line in open(f"{REPO}/problems.jsonl"):
    o = json.loads(line); cat[o["id"]] = o["category"]
P, A = {}, {}
for row in csv.DictReader(open(f"{REPO}/train.csv")):
    P[row["id"]] = row["prompt"]; A[row["id"]] = row["answer"]
OPS = set("*+-/")

# 1) Hand-inspect raw char structure of equation lines (NO stripping)
print("=== RAW char structure (first cryptarithm_deduce problem) ===")
for i, c in cat.items():
    if c == "cryptarithm_deduce" and i in P:
        for ln in P[i].splitlines():
            if " = " in ln and "example" not in ln.lower():
                lhs, rhs = ln.split(" = ", 1)
                print(f"  LHS={list(lhs)!r} (len {len(lhs)})  RHS={list(rhs)!r} (len {len(rhs)})")
        # query line
        for ln in P[i].splitlines():
            if "determine the result" in ln.lower():
                q = ln.split(":", 1)[1].strip()
                print(f"  QUERY raw={list(q)!r} (len {len(q)}) answer={list(A[i])!r}")
        break

def parse_clean(prompt):
    """No backtick stripping. Equation line = 'LHS = RHS'. Query after colon."""
    exs, q = [], None
    for ln in prompt.splitlines():
        low = ln.lower()
        if "determine the result" in low:
            q = ln.split(":", 1)[1].strip() if ":" in ln else None
            continue
        if " = " in ln and "example" not in low and "alice" not in low:
            lhs, rhs = ln.split(" = ", 1)
            exs.append((lhs, rhs))
    return exs, q

def split5(e):
    return (e[:2], e[2], e[3:5]) if len(e) == 5 and e[2] in OPS else None

def _try(f, a, b):
    try:
        return f(a, b)
    except Exception:
        return None

# 2) Re-run GLOBAL per-operator fit on cleanly-parsed tuples
FNS = {
    "concat": lambda A, B: A + B,
    "rconcat": lambda A, B: B + A,
    "interAB": lambda A, B: A[0] + B[0] + A[1] + B[1],
    "interBA": lambda A, B: B[0] + A[0] + B[1] + A[1],
    "rev": lambda A, B: (A + B)[::-1],
    "rrev": lambda A, B: (B + A)[::-1],
}
tup = defaultdict(list)
n_eq = n_5 = 0
for i, c in cat.items():
    if not c.startswith("cryptarithm") or i not in P:
        continue
    exs, q = parse_clean(P[i])
    rows = list(exs)
    if q and i in A:
        rows.append((q, A[i]))
    for lhs, out in rows:
        n_eq += 1
        sp = split5(lhs)
        if sp:
            n_5 += 1
            tup[sp[1]].append((sp[0], sp[2], out))

print(f"\n=== clean parse: {n_eq} equations, {n_5} fit 5-char AB-op-CD ({100*n_5/max(1,n_eq):.1f}%) ===")
print("Per-operator GLOBAL transform fit (clean tuples):")
for op in sorted(tup):
    tl = tup[op]; n = len(tl)
    fits = Counter()
    for name, f in FNS.items():
        fits[name] = sum(1 for a, b, o in tl if _try(f, a, b) == o)
    top = fits.most_common(3)
    print(f"  op {op!r}: n={n:5d}  " + "  ".join(f"{k}={100*v/n:.0f}%" for k, v in top))
    lens = Counter(len(o) for _, _, o in tl)
    print(f"        out-lens={dict(sorted(lens.items()))}")


def _try(f, a, b):
    try:
        return f(a, b)
    except Exception:
        return None
