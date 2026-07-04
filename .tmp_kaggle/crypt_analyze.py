"""Spike: understand the symbol-arithmetic cryptarithm structure exactly."""
import json, csv, sys, re
csv.field_size_limit(sys.maxsize)

REPO = "/home/mike-anderson/dev/cohezion/.tmp_kaggle/nemo-win"
cat, status = {}, {}
for line in open(f"{REPO}/problems.jsonl"):
    o = json.loads(line); cat[o["id"]] = o["category"]; status[o["id"]] = o.get("status", "?")
prompts, answers = {}, {}
for row in csv.DictReader(open(f"{REPO}/train.csv")):
    prompts[row["id"]] = row["prompt"]; answers[row["id"]] = row["answer"]

OPS = set("*-+/")

def parse_problem(prompt):
    """Extract example equations 'LHS = RHS' and the query 'determine the result for: X'."""
    lines = [l.strip() for l in prompt.splitlines() if l.strip()]
    examples = []
    query = None
    for l in lines:
        m = re.match(r".*determine the result for[: ]+(.+?)\.?$", l, re.I)
        if m:
            query = m.group(1).strip().strip("`")
            continue
        if " = " in l:
            lhs, rhs = l.split(" = ", 1)
            lhs = lhs.strip().strip("`"); rhs = rhs.strip().strip("`")
            # skip the intro line
            if any(ch in OPS for ch in lhs) or len(lhs) <= 8:
                examples.append((lhs, rhs))
    return examples, query

ids = [i for i in cat if cat[i] == "cryptarithm_deduce" and i in prompts]
print(f"cryptarithm_deduce with prompt: {len(ids)}")
for i in ids[:3]:
    print("=" * 60)
    print("id", i, "status", status[i], "answer", repr(answers[i]))
    print("RAW PROMPT repr:")
    print(repr(prompts[i])[:700])
    ex, q = parse_problem(prompts[i])
    print(f"parsed {len(ex)} examples, query={q!r}")
    for lhs, rhs in ex:
        print(f"   LHS={lhs!r}  RHS={rhs!r}")
    # distinct symbols (non-operator, non-space)
    allsym = set()
    for lhs, rhs in ex:
        for ch in lhs + rhs:
            if ch not in OPS and not ch.isspace():
                allsym.add(ch)
    print(f"   distinct non-op symbols: {len(allsym)} -> {sorted(allsym)}")
