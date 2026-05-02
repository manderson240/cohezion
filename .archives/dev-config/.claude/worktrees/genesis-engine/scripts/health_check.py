#!/usr/bin/env python3
"""
ASCENDED COHEZION - System Health Check
Called by cron every hour
"""

import sys
from datetime import datetime


# Add src to path
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")


def main():
    import psutil

    mem = psutil.virtual_memory()

    if mem.percent > 90:
        print(f"WARNING: High memory usage at {datetime.now()}: {mem.percent}%")
    else:
        print(f"Health check OK at {datetime.now()}: Memory {mem.percent}%")


if __name__ == "__main__":
    main()
