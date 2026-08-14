"""Publish measured review capability into `model_performance` as role="review".

This is the wiring step. Until now the benchmark was a vault note and a bus event -- true,
and read by nothing. `fleet_roster.select(role)` is Cohezion's single source of truth for
"which model should role X use right now", and it consumes measured quality from
`model_performance` keyed by (model, role). Writing there makes the measurement a code path
the daemons already read, rather than knowledge that rots.

CHANCE CORRECTION, and it is not cosmetic. The roster ranks in three tiers:

    measured > 0   -> proven-good, dominates priors
    no measurement -> unknown, priors only
    measured == 0  -> proven-bad, BELOW unknown

Balanced accuracy has its floor at 0.50, not 0.0 -- an always-BUG model scores 0.50 and is
worthless. Writing raw balanced accuracy would put a CHANCE-LEVEL model in the proven-good
tier, ranking it above an untried one. So the stored score is

    quality = max(0.0, 2 * (balanced_accuracy - 0.5))

which sends chance to exactly 0.0 -- the roster's "evidence of failure" tier, which is what
chance-level review capability actually is. 1.00 -> 1.00, 0.83 -> 0.66, 0.50 -> 0.0.

SOURCE IS THE REAL-CODE CORPUS, not the toy one. Toy rated Qwen3-Coder-30B a perfect 1.00
while it fabricates on real clean code; the corpora disagree (Spearman 0.664) and the
real-code measurement is the one that predicted an observed production failure.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

CKPT = Path("/tmp/claude-1000/review_dogfood_ckpt.json")
SQL = "http://localhost:8001/sql"
HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
    "Accept": "application/json",
    "Authorization": "Basic cm9vdDpyb290",
}


def run(stmt: str) -> list:
    req = urllib.request.Request(SQL, data=stmt.encode(), headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        parsed = json.loads(r.read().decode())
    for st in parsed:
        if st.get("status") != "OK":
            raise RuntimeError(f"statement FAILED inside HTTP 200: {st.get('result')}")
    return parsed


def main() -> int:
    if not CKPT.exists():
        print("no benchmark data")
        return 2
    rows = json.loads(CKPT.read_text())["rows"]

    by = defaultdict(list)
    for r in rows:
        by[r["model"]].append(r)

    records: list[tuple[str, float, float, float]] = []
    for model, rs in by.items():
        ok = [r for r in rs if r["verdict"]]
        if not ok:
            # Attempted and never produced a parseable verdict. That IS a measurement of
            # unusability -- distinct from never having been run, which writes nothing.
            records.append((model, 0.0, 0.0, 0.0))
            continue
        buggy = [r for r in ok if r["buggy"]]
        clean = [r for r in ok if not r["buggy"]]
        if not buggy or not clean:
            continue
        sens = sum(r["verdict"] == "BUG" for r in buggy) / len(buggy)
        spec = sum(r["verdict"] == "CLEAN" for r in clean) / len(clean)
        bal = (sens + spec) / 2
        records.append((model, bal, spec, max(0.0, 2.0 * (bal - 0.5))))

    print(f"{'model':<40} {'bal':>5} {'spec':>5} {'stored':>7}")
    print("-" * 62)
    for model, bal, spec, q in sorted(records, key=lambda t: -t[3]):
        note = "  <- chance or worse => proven-bad tier" if q == 0.0 else ""
        print(f"{model:<40} {bal:>5.2f} {spec:>5.2f} {q:>7.2f}{note}")

    # Replace rather than append: re-running must not skew the mean with stale rows.
    run('DELETE model_performance WHERE role = "review" AND task = "review_lane_benchmark";')
    # `ts` is TYPE none|string in this schema, not a datetime -- time::now() fails
    # coercion inside an HTTP 200. Existing rows store a plain ISO string.
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    for model, _bal, _spec, q in records:
        run(
            "CREATE model_performance SET "
            f"model = {json.dumps(model)}, role = \"review\", "
            f"quality_score = {q!r}, task = \"review_lane_benchmark\", "
            f"lap = 1, tps = 0.0, ts = {json.dumps(stamp)};"
        )

    check = run(
        'SELECT model, math::mean(quality_score) AS q FROM model_performance '
        'WHERE role = "review" GROUP BY model;'
    )[0]["result"]
    print(f"\nverified in model_performance: {len(check)} models under role='review'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
