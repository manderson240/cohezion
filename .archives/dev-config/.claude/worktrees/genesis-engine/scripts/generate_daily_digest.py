#!/usr/bin/env python3
"""
ASCENDED COHEZION - Daily Digest Generator
Called by cron at 4:00 PM daily
"""

import asyncio
import sys
from datetime import datetime


# Add src to path
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")


async def main():
    from cohezion.swarm.autonomous_universe_mission import get_mission_orchestrator
    from cohezion.swarm.milestone_alerts import NotificationManager

    orchestrator = get_mission_orchestrator("manderson240@gmail.com")
    status = orchestrator.get_all_missions()

    notifier = NotificationManager("manderson240@gmail.com")

    today = datetime.now().strftime("%Y-%m-%d")

    await notifier.send_daily_digest(today, status.get("active", []), {})

    print(f"Daily digest sent for {today}")


if __name__ == "__main__":
    asyncio.run(main())
