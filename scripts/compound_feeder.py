#!/usr/bin/env python3
"""Thin driver for the compound-task feeder (work item f803d5ae1202).

Run on a timer BEFORE the compound daemon's cycle so the daemon has pending work
instead of idling on an empty queue. See ``cohezion.compound.compound_feeder`` for the
suggested systemd unit + timer (installed by the lead/user, not from here).

    python scripts/compound_feeder.py --limit 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cohezion.compound.compound_feeder import feed_compound_tasks


def main() -> int:
    parser = argparse.ArgumentParser(description="Feed the compound daemon from the work-queue.")
    parser.add_argument("--limit", type=int, default=5, help="max NEW tasks to feed this run")
    args = parser.parse_args()
    result = feed_compound_tasks(limit=args.limit)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
