#!/usr/bin/env python3
"""Work-queue actioner driver — one batch per invocation (cron/wakeup-friendly).

Drains APPLY items in reviewed/approved through a real CompoundExecutor cycle
on local inference and flips them to `actioned` via the work-queue API.
Design: vault research/2026-07-10-daemon-consumer-design-v2 (+3 corrections).

Usage:
    uv run python scripts/actioner.py                 # one batch of 50
    uv run python scripts/actioner.py --batch 5       # smaller batch
    uv run python scripts/actioner.py --dry-run       # triage report only, no writes
    uv run python scripts/actioner.py --model Gemma-4-E4B-it-GGUF

Scheduling (design §5): cron every 5 min → 12 runs/hr × 50 = 6,000/day capacity
vs ≤600/day inflow. Safe alongside the research daemon: the ONLY queue mutation
is the PATCH route (never the JSON file).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


class _NullMCP:
    """Minimal MCP stand-in: the actioner needs no vault MCP tools; executor
    vault logging is fail-open. Every attribute is a no-op callable."""

    def __getattr__(self, name: str):
        return lambda *a, **k: None


def main() -> int:
    ap = argparse.ArgumentParser(description="Drain APPLY work-queue items (one batch)")
    ap.add_argument("--batch", type=int, default=50, help="max items this run (default 50)")
    ap.add_argument("--api", default="http://localhost:8080", help="work-queue API base")
    ap.add_argument("--model", default="Gemma-4-E4B-it-GGUF", help="local model id (:13305)")
    ap.add_argument("--dry-run", action="store_true", help="triage + report only, no writes")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from cohezion.actioner.engine import WorkQueueAPI, default_chat_fn, run_batch
    from cohezion.compound import make_executor

    executor = make_executor(_NullMCP())
    summary = run_batch(
        executor,
        api=WorkQueueAPI(args.api),
        chat_fn=default_chat_fn(args.model),
        batch_size=args.batch,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, indent=2))
    # Honest exit code: failures present -> nonzero (cron surfaces it), but
    # partial progress is still recorded item-by-item.
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
