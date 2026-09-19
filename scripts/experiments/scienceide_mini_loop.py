"""ScienceIDE loop in miniature, on local silicon, from parts Cohezion already has.

ScienceIDE (aitofound, arXiv 2609.19134): pinned code + ONE injected defect + an instruction that
states only the observed symptom; a verifier RE-EXECUTES and compares to reference; reward is
execution-based, not diff-based; tasks are discarded unless the nominal passes AND the variant
fails (their "two-solve self-validation"). Same loop here:

  defect injector  = cohezion.testing.mutation_tester.MutationTestingEngine (AST cmp/binop)
  agent lane       = cohezion.inference.gaia_adapter.build_gaia_llm_tier (:13305, $0)
  verifier/oracle  = cohezion.compound.sandboxed_exec.run_untrusted (out of process; H5)

Usage:
  PYTHONPATH=src python3 scripts/experiments/scienceide_mini_loop.py --models Gemma-4-E4B-it-GGUF \
      [--limit N] [--out results.jsonl]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time

from cohezion.compound.sandboxed_exec import run_untrusted
from cohezion.inference.gaia_adapter import build_gaia_llm_tier
from cohezion.testing.mutation_tester import MutationTestingEngine


# name -> (source, tests). Tests are plain asserts run in the SAME sandbox namespace.
TASKS: dict[str, tuple[str, str]] = {
    "binary_search": (
        "def binary_search(a, x):\n    lo, hi = 0, len(a) - 1\n    while lo <= hi:\n"
        "        mid = (lo + hi) // 2\n        if a[mid] == x:\n            return mid\n"
        "        if a[mid] < x:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n"
        "    return -1\n",
        "assert binary_search([1,3,5,7,9], 7) == 3\nassert binary_search([1,3,5,7,9], 1) == 0\n"
        "assert binary_search([1,3,5,7,9], 9) == 4\nassert binary_search([1,3,5,7,9], 4) == -1\n"
        "assert binary_search([], 1) == -1\n",
    ),
    "gcd": (
        "def gcd(a, b):\n    while b != 0:\n        a, b = b, a % b\n    return a\n",
        "assert gcd(48, 18) == 6\nassert gcd(17, 5) == 1\nassert gcd(0, 9) == 9\nassert gcd(20, 100) == 20\n",
    ),
    "is_prime": (
        "def is_prime(n):\n    if n < 2:\n        return False\n    i = 2\n"
        "    while i * i <= n:\n        if n % i == 0:\n            return False\n        i += 1\n"
        "    return True\n",
        "assert is_prime(2) and is_prime(13) and is_prime(97)\n"
        "assert not is_prime(1) and not is_prime(9) and not is_prime(49) and not is_prime(0)\n",
    ),
    "kadane": (
        "def max_subarray(a):\n    best = cur = a[0]\n    for v in a[1:]:\n"
        "        cur = max(v, cur + v)\n        best = max(best, cur)\n    return best\n",
        "assert max_subarray([-2,1,-3,4,-1,2,1,-5,4]) == 6\nassert max_subarray([-3,-1,-2]) == -1\n"
        "assert max_subarray([5]) == 5\nassert max_subarray([1,2,3]) == 6\n",
    ),
    "merge_intervals": (
        "def merge(iv):\n    iv = sorted(iv)\n    out = []\n    for s, e in iv:\n"
        "        if out and s <= out[-1][1]:\n            out[-1][1] = max(out[-1][1], e)\n"
        "        else:\n            out.append([s, e])\n    return out\n",
        "assert merge([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]\n"
        "assert merge([[1,4],[4,5]]) == [[1,5]]\nassert merge([[3,4],[1,2]]) == [[1,2],[3,4]]\n",
    ),
    "balanced": (
        "def balanced(s):\n    depth = 0\n    for c in s:\n        if c == '(':\n            depth += 1\n"
        "        elif c == ')':\n            depth -= 1\n            if depth < 0:\n                return False\n"
        "    return depth == 0\n",
        "assert balanced('(()())') and balanced('') and not balanced('(()') and not balanced(')(')\n",
    ),
    "running_mean": (
        "def running_mean(xs, k):\n    out = []\n    s = 0.0\n    for i, v in enumerate(xs):\n"
        "        s += v\n        if i >= k:\n            s -= xs[i - k]\n"
        "        if i >= k - 1:\n            out.append(s / k)\n    return out\n",
        "assert running_mean([1,2,3,4,5], 2) == [1.5,2.5,3.5,4.5]\n"
        "assert running_mean([2,4,6], 3) == [4.0]\nassert running_mean([1,2], 3) == []\n",
    ),
    "clamp_grid": (
        "def clamp_grid(g, lo, hi):\n    return [[min(max(v, lo), hi) for v in row] for row in g]\n",
        "assert clamp_grid([[-1,5,12]], 0, 9) == [[0,5,9]]\nassert clamp_grid([[3]], 3, 3) == [[3]]\n",
    ),
    "lcs_len": (
        "def lcs(a, b):\n    m = [[0]*(len(b)+1) for _ in range(len(a)+1)]\n"
        "    for i in range(1, len(a)+1):\n        for j in range(1, len(b)+1):\n"
        "            if a[i-1] == b[j-1]:\n                m[i][j] = m[i-1][j-1] + 1\n"
        "            else:\n                m[i][j] = max(m[i-1][j], m[i][j-1])\n    return m[-1][-1]\n",
        "assert lcs('abcde','ace') == 3\nassert lcs('abc','def') == 0\nassert lcs('aaaa','aa') == 2\n",
    ),
    "roman": (
        "def roman(n):\n    vals = [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),"
        "(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]\n    out = ''\n"
        "    for v, s in vals:\n        while n >= v:\n            out += s\n            n -= v\n    return out\n",
        "assert roman(1994) == 'MCMXCIV'\nassert roman(58) == 'LVIII'\nassert roman(4) == 'IV'\nassert roman(3999) == 'MMMCMXCIX'\n",
    ),
}

INSTRUCTION = """Find and repair exactly one localized source defect in the Python function below.
Root cause and location are yours to determine. The verifier re-executes the function against
hidden tests; only a numerically/semantically correct result is rewarded.

## Observed symptom
{symptom}

## Defective source
```python
{source}```

Return ONLY the complete corrected source in a single ```python block. No explanation."""


def verify(source: str, tests: str) -> tuple[bool, str]:
    r = run_untrusted(source + "\n" + tests + "\nverdict_ok = True\n", collect=True, timeout_s=20)
    if r.ok and isinstance(r.value, dict) and r.value.get("verdict_ok") is True:
        return True, ""
    return False, (r.error or "no result")[:200]


def extract(text: str) -> str | None:
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return m.group(1) if m else None


def build_bank(limit: int | None) -> list[dict]:
    bank = []
    for name, (src, tests) in TASKS.items():
        ok, err = verify(src, tests)
        if not ok:
            print(f"SKIP {name}: nominal fails its own tests: {err}", file=sys.stderr)
            continue
        n = MutationTestingEngine.count_mutation_sites(src)
        for site in sorted({0, n - 1}) if n else []:
            mutated, mutant = MutationTestingEngine.generate_mutant(src, site)
            if mutant is None:
                continue
            fails, symptom = verify(mutated, tests)
            if fails:  # equivalent mutant: nominal AND variant pass -> discarded (two-solve rule)
                continue
            bank.append(
                {
                    "task": name,
                    "site": site,
                    "mutant": mutant.description,
                    "lineno": mutant.lineno,
                    "source": mutated,
                    "tests": tests,
                    "symptom": symptom,
                }
            )
        if limit and len(bank) >= limit:
            break
    return bank[:limit] if limit else bank


async def solve(lane, item: dict) -> dict:
    prompt = INSTRUCTION.format(symptom=item["symptom"], source=item["source"])
    t0 = time.perf_counter()
    res = await lane.run(prompt)
    dt = time.perf_counter() - t0
    cand = extract(res.text or "")
    if res.error or cand is None:
        return {"reward": 0, "why": f"lane: {res.error or 'no code block'}", "s": round(dt, 1)}
    ok, err = verify(cand, item["tests"])
    return {
        "reward": int(ok),
        "why": "" if ok else err,
        "s": round(dt, 1),
        "chars": len(res.text or ""),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-tokens", type=int, default=1500)
    args = ap.parse_args()

    bank = build_bank(args.limit)
    print(f"bank: {len(bank)} (nominal passes, mutant fails) tasks", file=sys.stderr)
    out = open(args.out, "a") if args.out else None  # noqa: SIM115 -- closed in finally below
    summary = {}
    for model in args.models:
        lane = build_gaia_llm_tier(model_id=model, max_tokens=args.max_tokens)
        wins = 0
        for item in bank:
            r = asyncio.run(solve(lane, item))
            wins += r["reward"]
            row = {"model": model, **{k: item[k] for k in ("task", "site", "mutant")}, **r}
            print(json.dumps(row), file=out or sys.stdout, flush=True)
        summary[model] = (wins, len(bank))
    if out:
        out.close()
    for m, (w, n) in summary.items():
        print(f"{m}: {w}/{n} = {w / n:.2f}" if n else f"{m}: no tasks", file=sys.stderr)


if __name__ == "__main__":
    main()
