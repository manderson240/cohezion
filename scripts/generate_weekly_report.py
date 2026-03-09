#!/usr/bin/env python3
"""
ASCENDED COHEZION - Weekly Evolution Report
Called by cron on Sundays at 5:00 AM
"""

import json
import sys
from datetime import datetime


# Add src to path
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")


def main():
    from cohezion.swarm.compound_evolution import CompoundEvolutionEngine

    engine = CompoundEvolutionEngine()
    summary = engine.get_evolution_summary()

    print(f"Weekly Evolution Report - {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 60)
    print(json.dumps(summary, indent=2))
    print("=" * 60)


if __name__ == "__main__":
    main()
