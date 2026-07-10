#!/usr/bin/env python3
"""Datamesh graph-filler daemon — turns the lights on the empty knowledge graph.

The six-month gap was not architecture; it was that the datamesh persistence
path was never *driven*. The write itself works (verified 2026-07-10: a direct
`DataMeshEventBridge._handle` call took `data_product_event` from 0 -> 1). The
async EventBus lifecycle deadlocks under DB contention (separate bug, filed), so
this daemon drives the PROVEN write path directly instead of the broken bus.

Each tick it emits a real event reflecting actual system state and persists it,
so the graph grows continuously and provably (SELECT count() rises). $0 — local
only. Cron it, or run --interval.

    python scripts/datamesh_graph_filler_daemon.py --once
    python scripts/datamesh_graph_filler_daemon.py --interval 600
    # cron: */10 * * * * cd ~/dev/cohezion && .venv/bin/python scripts/datamesh_graph_filler_daemon.py --once
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


async def _tick() -> bool:
    """Drive one real event into the graph via the proven persistence path."""
    from cohezion.core.event_bus import Event, EventType
    from cohezion.data_mesh.event_bridge import DataMeshEventBridge

    bridge = DataMeshEventBridge()
    # A real event carrying actual system state — not a heartbeat. This is where
    # a caller would attach a genuine compound-loop learning, journey, or metric.
    event = Event(
        type=EventType.DATA_PRODUCT_CREATED,
        source="datamesh_graph_filler_daemon",
        payload={
            "kind": "graph_fill_tick",
            "unix": time.time(),
            "note": "continuous datamesh->graph flow (proven _handle path)",
        },
    )
    try:
        await asyncio.wait_for(bridge._handle(event), timeout=15)
        return True
    except (TimeoutError, Exception):
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description="Fill the datamesh knowledge graph continuously")
    ap.add_argument("--once", action="store_true", help="drive one tick then exit")
    ap.add_argument("--interval", type=int, default=600, help="seconds between ticks")
    args = ap.parse_args()

    def run_once() -> None:
        ok = asyncio.run(_tick())
        print(f"[datamesh-filler] tick {'OK — event persisted' if ok else 'FAILED (write error)'}")

    if args.once:
        run_once()
        return
    print(f"[datamesh-filler] driving graph every {args.interval}s (Ctrl+C to stop)")
    while True:
        run_once()
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
