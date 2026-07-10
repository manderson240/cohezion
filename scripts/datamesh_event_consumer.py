#!/usr/bin/env python3
"""Datamesh event-consumer driver — one drain pass per invocation (timer-friendly).

Closes the EventBus dead-end: DataMeshEventBridge persists events to SurrealDB
``data_product_event``; this consumer claims them idempotently (SCP1 array::add)
and turns actionable ones into work-queue items with local-inference summaries.
LIVE queries are unsupported on this deployment (versioned SurrealKV), so this
polls — pair with a systemd timer like the actioner.

Usage:
    uv run python scripts/datamesh_event_consumer.py            # one batch of 25
    uv run python scripts/datamesh_event_consumer.py --batch 5
    uv run python scripts/datamesh_event_consumer.py --consumer-id my-consumer
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Drain datamesh events (one pass)")
    ap.add_argument("--batch", type=int, default=25)
    ap.add_argument("--consumer-id", default="datamesh-event-consumer")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from cohezion.data_mesh.event_consumer import EventConsumer

    summary = EventConsumer(args.consumer_id).run_once(batch=args.batch)
    print(json.dumps(summary, indent=2))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
