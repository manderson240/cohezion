#!/usr/bin/env python3
"""Idempotent vault -> SurrealDB research sync.

Scans the Obsidian vault's research/reviews/corpus notes and UPSERTs one
`research_finding` record per note (record id = slug of the filename), so it is
safe to run repeatedly: it doubles as a one-shot backfill AND the persistence
engine when wired to a trigger (SessionStart hook / cron / PostToolUse).

Zero LLM, deterministic, no external deps. SurrealDB via HTTP (root:root, localhost).
Usage:
    python3 vault_surreal_sync.py            # sync all research/reviews/corpus notes
    python3 vault_surreal_sync.py --since 2026-07-12   # only notes whose `date:` >= given
"""
from __future__ import annotations

import argparse
import base64
import re
import sys
import urllib.request
from pathlib import Path

VAULT = Path.home() / "vaults" / "cohezion-vault"
FOLDERS = ("research", "reviews", "corpus")
SURREAL_URL = "http://localhost:8001/sql"
NS, DB = "cohezion", "main"
VALID_TYPES = {"research", "review", "corpus"}


def parse_frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip().strip('"').strip("'")
    return fm


def slug(name: str) -> str:
    return "v_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


def build_query(since: str | None) -> tuple[str, int]:
    stmts: list[str] = []
    for folder in FOLDERS:
        d = VAULT / folder
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md")):
            fm = parse_frontmatter(f.read_text(encoding="utf-8", errors="ignore"))
            if fm.get("type") not in VALID_TYPES:
                continue
            if since and fm.get("date", "") < since:
                continue
            fields = {
                "source": fm.get("source", ""),
                "topic": fm.get("topic", fm.get("title", f.stem)),
                "verdict": fm.get("verdict", ""),
                "date": fm.get("date", ""),
                "status": fm.get("status", ""),
                "folder": folder,
                "vault_note": f"{folder}/{f.name}",
            }
            sets = ", ".join(f'{k} = "{esc(v)}"' for k, v in fields.items())
            stmts.append(f"UPSERT research_finding:{slug(f.stem)} SET {sets};")
    return "\n".join(stmts), len(stmts)


def main() -> int:
    ap = argparse.ArgumentParser(description="Idempotent vault -> SurrealDB research sync")
    ap.add_argument("--since", default=None, help="only notes with date: >= YYYY-MM-DD")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    query, n = build_query(args.since)
    if n == 0:
        print("vault_surreal_sync: 0 notes matched")
        return 0
    if args.dry_run:
        print(f"vault_surreal_sync: would upsert {n} research_finding records (dry-run)")
        return 0

    req = urllib.request.Request(  # noqa: S310 (localhost, trusted)
        SURREAL_URL,
        data=query.encode(),
        headers={
            "surreal-ns": NS,
            "surreal-db": DB,
            "Content-Type": "text/plain",
            "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
            body = r.read().decode()
    except Exception as exc:  # noqa: BLE001 - report and fail soft
        print(f"vault_surreal_sync: SurrealDB write FAILED: {exc}", file=sys.stderr)
        return 1
    ok = body.count('"status":"OK"')
    print(f"vault_surreal_sync: upserted {n} notes -> research_finding ({ok} statements OK)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
