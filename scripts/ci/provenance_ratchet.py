#!/usr/bin/env python3
"""Goal-provenance coverage ratchet: coverage may rise, never fall.

Measured 2026-09-21: **1 of 6,169 goals carries `origin_trace_ids` (0.02%)**. Demanding
100% today would fail every build and be switched off within a week, which is how the
ruff backlog got to 896. So this gates the DERIVATIVE, not the level: a change may not
make provenance worse. That is the same shape as ``ruff_ratchet.py``, deliberately.

This script is also the production CONSUMER of
``cohezion.traceability.loop_goal_graph`` -- it calls both the producer
(``coverage_certificate``) and the INDEPENDENT checker (``verify_coverage``), so the
witness is re-validated by code that shares nothing with the code that produced it. A
module with no caller is dormant no matter how well tested; this is the caller.

## Exit codes -- three outcomes, never two

    0  measured, coverage >= baseline
    1  measured, coverage REGRESSED below baseline
    2  COULD NOT MEASURE

Code 2 exists because of the defect fixed in this repo on 2026-09-20: ``ruff_ratchet``
parsed an empty stdout as ``[]`` and reported **0 violations -- a PASS -- from a run that
never happened**. The lesson generalises past ruff: a measurement tool must never let
"I could not look" collapse into "I looked and it was fine". An unreachable database is
UNKNOWN, and UNKNOWN is not success.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from cohezion.traceability.loop_goal_graph import (  # noqa: E402
    coverage_certificate,
    verify_coverage,
)


BASELINE_PATH = REPO / "scripts" / "ci" / "provenance_baseline.json"
SURREAL_URL = "http://localhost:8001/sql"
# Same provenance discipline as ruff_ratchet: a baseline that was typed rather than
# measured is a number with no evidence behind it.
_PROVENANCE = "measured-by: provenance_ratchet.py --update"


class CouldNotMeasureError(RuntimeError):
    """Raised when the live graph cannot be read. Never downgraded to a count."""


def fetch_goal_graph() -> tuple[list[str], list[tuple[str, str]]]:
    """Read goals and their provenance. Raises CouldNotMeasureError, never returns 0."""
    body = b"SELECT id, origin_trace_ids FROM goal;"
    req = urllib.request.Request(
        SURREAL_URL,
        data=body,
        headers={
            "surreal-ns": "cohezion",
            "surreal-db": "main",
            "Content-Type": "text/plain",
            "Accept": "application/json",
            "Authorization": "Basic cm9vdDpyb290",
        },
    )
    try:
        # never caller-supplied, so the file:/custom-scheme risk S310 guards cannot arise.
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise CouldNotMeasureError(f"SurrealDB unreachable at {SURREAL_URL}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CouldNotMeasureError(f"SurrealDB returned unparseable JSON: {exc}") from exc

    if not payload or not isinstance(payload, list):
        raise CouldNotMeasureError("SurrealDB returned an empty envelope")
    first = payload[0]
    # A statement error arrives as HTTP 200 with status != OK -- the documented
    # surrealdb-http-200-with-statement-error trap. Reading `result` regardless would
    # turn a failed query into "no goals", i.e. 100% coverage of nothing.
    if first.get("status") != "OK":
        raise CouldNotMeasureError(f"SurrealDB statement error: {first.get('result')}")
    rows = first.get("result")
    if not isinstance(rows, list):
        raise CouldNotMeasureError(f"unexpected result shape: {type(rows).__name__}")

    goal_ids: list[str] = []
    edges: list[tuple[str, str]] = []
    for row in rows:
        gid = f"goal:{row.get('id')}"
        goal_ids.append(gid)
        for trace in row.get("origin_trace_ids") or []:
            edges.append((f"trace:{trace}", gid))
    return goal_ids, edges


def read_baseline() -> tuple[int, float, bool]:
    """Return (covered_count, coverage_pct, was_measured). Missing baseline reads as 0."""
    if not BASELINE_PATH.exists():
        return 0, 0.0, False
    data = json.loads(BASELINE_PATH.read_text())
    return (
        int(data.get("covered", 0)),
        float(data.get("coverage_pct", 0.0)),
        _PROVENANCE in data.get("note", ""),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--update", action="store_true", help="rewrite baseline to measured")
    args = ap.parse_args()

    try:
        goal_ids, edges = fetch_goal_graph()
    except CouldNotMeasureError as exc:
        print(f"provenance_ratchet: COULD NOT MEASURE -- {exc}", file=sys.stderr)
        print(
            "  Refusing to report a coverage number from a measurement that did not "
            "happen (exit 2 is not a pass).",
            file=sys.stderr,
        )
        return 2

    cert = coverage_certificate(goal_ids, edges)
    # Independent re-check of the producer's witness before anything is decided on it.
    if not verify_coverage(goal_ids, edges, cert.witness):
        print(
            "provenance_ratchet: the coverage witness FAILED independent verification",
            file=sys.stderr,
        )
        return 2

    total = len(goal_ids)
    covered = total - len(cert.witness)
    pct = (covered / total * 100.0) if total else 100.0

    if args.update:
        BASELINE_PATH.write_text(
            json.dumps(
                {
                    "coverage_pct": round(pct, 4),
                    "covered": covered,
                    "total": total,
                    "note": _PROVENANCE,
                },
                indent=2,
            )
            + "\n"
        )
        print(f"provenance_ratchet: baseline updated to {pct:.4f}% ({covered}/{total})")
        return 0

    baseline_covered, _baseline_pct, measured = read_baseline()
    if not measured and BASELINE_PATH.exists():
        print(
            "provenance_ratchet: baseline carries no measured-by stamp -- it was typed, "
            "not measured. Re-run with --update.",
            file=sys.stderr,
        )
        return 2

    # Gate on the COUNT of provenanced goals, not the rate.
    #
    # The rate's denominator is adversarial: `goal` is a shared table and other
    # subsystems (Tri-Silicon Refinement Cycle, Autopoietic Negentropy, ...) append
    # un-provenanced rows continuously -- measured 6,169 -> 6,182 within minutes of each
    # other. A rate ratchet would therefore fire on unrelated writes while nothing about
    # provenance had worsened, and a gate that cries wolf gets switched off. The count is
    # monotone under other writers: it falls only if provenance we already had was LOST,
    # which is the regression actually worth blocking. The rate stays as reporting.
    if covered < baseline_covered:
        print(
            f"provenance_ratchet: REGRESSION -- {covered} provenanced goals < baseline "
            f"{baseline_covered}. Provenance that existed has been lost.",
            file=sys.stderr,
        )
        print(f"  {len(cert.witness)} orphans, e.g. {cert.witness[:3]}", file=sys.stderr)
        return 1

    verdict = "improved" if covered > baseline_covered else "held"
    print(
        f"provenance_ratchet: OK -- {covered} provenanced goals {verdict} vs baseline "
        f"{baseline_covered} ({pct:.4f}% of {total}; rate is reported, not gated)"
    )
    if covered > baseline_covered:
        print("  Lock it in: python scripts/ci/provenance_ratchet.py --update")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
