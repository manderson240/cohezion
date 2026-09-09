#!/usr/bin/env python3
"""Continuous Overnight Kaggle Worker Service."""
import asyncio
import time
from launch_kaggle_overnight_leaderboard_engine import execute_overnight_cycle

async def run_overnight_service():
    cycle = 2
    while True:
        try:
            await execute_overnight_cycle(cycle)
            cycle += 1
            # Sleep 180 seconds between autonomous optimization rounds
            await asyncio.sleep(180.0)
        except Exception as e:
            print(f"Cycle {cycle} exception: {e}")
            await asyncio.sleep(60.0)

if __name__ == "__main__":
    asyncio.run(run_overnight_service())
