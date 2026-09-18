#!/usr/bin/env python3
"""Loop docs' `mirror:` claims must resolve to live SurrealDB rows.

Motivation (2026-09-04 index): loop docs carried `mirror: SurrealDB ns cohezion db main --
tables X_loop, X_goal` frontmatter for tables that did not exist (0 nodes). A mirror line was a
CLAIM, never a row. Fourth sibling of dormancy_scan / doc_code_consistency / phantom_attr_scan:
"does the graph the doc points at actually contain the thing?".

For every doc with a `mirror:` line this resolves each cited table (in the cited db,
default `main`) -- scoped by `domain='X'` when the line names one -- to a live row count and FAILS
on zero or a missing table. `mirror: none ...` is an honest non-claim and is skipped.

ABSENT vs UNKNOWN: if SurrealDB is unreachable the check reports UNKNOWN and exits 0 (so CI
runners without the DB do not turn a dead instrument into a red/green claim); `--require-live`
makes UNKNOWN a failure. Doc roots default to the vault + repo docs/ and are skipped when absent.

    python scripts/ci/loop_doc_mirror_check.py [--docs DIR ...] [--require-live]
    python scripts/ci/loop_doc_mirror_check.py --self-test   # plants a phantom: RED, then GREEN
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
DEFAULT_DOC_ROOTS = (
    Path.home() / "vaults" / "cohezion-vault" / "references",
    Path.home() / "vaults" / "cohezion-vault" / "reports",
    REPO / "docs",
)

# Mirror claims measured PHANTOM on 2026-09-18 (docs cite tables that do not exist). Named, not
# counted, and a RATCHET: entries may only be removed. A grandfathered claim that starts holding
# rows fails the gate until its entry is deleted, so this list cannot silently rot.
# Fix = write the rows (or correct the doc), then delete the entry.
GRANDFATHERED = frozenset(
    {
        ("20260904-admission-proxy-loops-and-goals.md", "main.admission_proxy_loop"),
        ("20260904-admission-proxy-loops-and-goals.md", "main.admission_proxy_goal"),
    }
)

_NEGATED_DB = re.compile(r"\(?\s*NOT\s+db\s+\S+[^)—-]*\)?", re.I)
_MIRROR_LINE = re.compile(r"^mirror:\s*(?P<body>.+)$", re.M)
_DB = re.compile(r"\bdb\s+\**(?P<db>[a-z_][a-z0-9_]*)\**", re.I)
_DOMAIN = re.compile(r"domain\s*=\s*['\"](?P<domain>[^'\"]+)['\"]")
# Table-shaped identifiers only: a doc's prose words must not become "tables".
_TABLE = re.compile(
    r"\b(?P<t>[a-z][a-z0-9]*(?:_[a-z0-9]+)*_(?:loop|goal|node|edge)|goal_graph|event_log|goal|loop)\b"
)


@dataclass(frozen=True)
class Claim:
    doc: str
    db: str
    table: str
    domain: str | None


def parse_claims(doc: str, text: str) -> list[Claim]:
    claims: list[Claim] = []
    for m in _MIRROR_LINE.finditer(text):
        body = _NEGATED_DB.sub(" ", m["body"].strip().strip("\"'"))  # "db main (NOT db vault ...)"
        if body.lower().startswith("none"):
            continue
        # Split into per-database segments: "db main -- table goal, db vault -- table event_log".
        marks = list(_DB.finditer(body))
        segments = (
            [(mk["db"].lower(), body[mk.end() : marks[i + 1].start() if i + 1 < len(marks) else None])
             for i, mk in enumerate(marks)]
            if marks
            else [("main", body)]
        )  # fmt: skip
        for db, seg in segments:
            dom = _DOMAIN.search(seg)
            for t in dict.fromkeys(x["t"] for x in _TABLE.finditer(seg)):
                claims.append(Claim(doc, db, t, dom["domain"] if dom else None))
    return claims


def check(
    claims: list[Claim], count: Callable[[str, str, str | None], int | None]
) -> tuple[list[str], list[str]]:
    """(failures, unknowns). count() -> row count, or None for UNKNOWN (instrument down)."""
    failures: list[str] = []
    unknowns: list[str] = []
    for c in claims:
        n = count(c.db, c.table, c.domain)
        scope = f" WHERE domain='{c.domain}'" if c.domain else ""
        known = (Path(c.doc).name, f"{c.db}.{c.table}") in GRANDFATHERED
        if n is None:
            unknowns.append(f"{c.doc}: {c.db}.{c.table}{scope}")
        elif n == 0 and not known:  # THE guard: a claim about a graph that holds nothing is phantom
            failures.append(f"{c.doc}: mirror claims {c.db}.{c.table}{scope} but it has 0 rows")
        elif n > 0 and known:
            failures.append(
                f"{c.doc}: {c.db}.{c.table} now has rows -- delete its GRANDFATHERED entry"
            )
    return failures, unknowns


def live_count(db: str, table: str, domain: str | None) -> int | None:
    sys.path.insert(0, str(REPO / "src"))
    from cohezion.flume.trace_goal_sources import sql

    where = f" WHERE domain = '{domain}'" if domain else ""
    try:
        rows = sql(f"SELECT count() AS n FROM {table}{where} GROUP ALL;", db)
    except RuntimeError as exc:
        return 0 if "does not exist" in str(exc) else None  # missing table = ABSENT
    except OSError:
        return None  # unreachable = UNKNOWN
    return rows[0]["n"] if rows else 0


def scan_docs(roots: list[Path]) -> list[Claim]:
    claims: list[Claim] = []
    for root in roots:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*.md")):
            claims.extend(parse_claims(str(p), p.read_text(errors="replace")[:4000]))
    return claims


def self_test() -> int:
    """Plant a phantom mirror -> RED; a real one -> GREEN; a `none` non-claim -> silent."""
    world = {("main", "twin_loop", None): 7}

    def fake(db: str, table: str, domain: str | None) -> int | None:
        return world.get((db, table, domain), 0)

    with tempfile.TemporaryDirectory() as d:
        real = Path(d, "real.md")
        real.write_text(
            "---\nmirror: SurrealDB ns cohezion db **main** — tables twin_loop (L1–L6)\n---\n"
        )
        phantom = Path(d, "phantom.md")
        phantom.write_text(
            "---\nmirror: SurrealDB ns cohezion db main — table nonexistent_loop\n---\n"
        )
        none = Path(d, "none.md")
        none.write_text("---\nmirror: none yet — candidate for goal tables\n---\n")

        red, _ = check(scan_docs([Path(d)]), fake)
        if not any("nonexistent_loop" in f for f in red) or any("twin_loop" in f for f in red):
            print(f"SELF-TEST BROKEN: expected RED on ONLY the phantom, got {red}")
            return 1
        phantom.unlink()
        green, _ = check(scan_docs([Path(d)]), fake)
        if green:
            print(f"SELF-TEST BROKEN: expected GREEN after removing the phantom, got {green}")
            return 1
    print("SELF-TEST OK: phantom mirror -> RED, real + `none` -> GREEN.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--docs", nargs="*", type=Path, help="doc roots (default: vault + repo docs)")
    ap.add_argument("--require-live", action="store_true", help="UNKNOWN (DB down) is a failure")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    claims = scan_docs(args.docs or list(DEFAULT_DOC_ROOTS))
    failures, unknowns = check(claims, live_count)
    print(f"{len(claims)} mirror claim(s) checked")
    for u in unknowns:
        print(f"  UNKNOWN (instrument unreachable): {u}")
    for f in failures:
        print(f"  RED: {f}")
    if failures or (unknowns and args.require_live):
        return 1
    print("OK" if claims else "OK (no mirror claims found)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
