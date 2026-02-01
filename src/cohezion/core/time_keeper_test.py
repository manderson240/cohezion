"""
Verification script for Gateway 11 (Temporal Mastery) foundation.
Tests TimeKeeper event logging and velocity calculation.
"""

import asyncio
import logging

from cohezion.core.time_keeper import get_time_keeper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_velocity_tracking():
    print("--- Testing TimeKeeper ---")
    tk = get_time_keeper()

    # 1. Check ISO Time
    now = tk.now_iso
    print(f"Current Time (ISO): {now}")
    assert "T" in now and "+" in now, "Invalid ISO format"

    # 2. Log Events (Simulate Task Completion)
    print("Logging 5 task completion events...")
    for i in range(5):
        await tk.log_event(
            agent_name="TestAgent",
            event_type="TASK_COMPLETE",
            details={"task_id": i},
            duration_ms=100.0,
        )

    # Allow DB async write to settle (if necessary)
    await asyncio.sleep(1)

    # Debug: Check raw query response
    try:
        # Check Total Count
        raw_res = await tk.db.query("SELECT count() FROM velocity_events GROUP ALL")
        print(f"DEBUG Total Count: {raw_res}")

        # Check Server Time (RETURN syntax)

        # Check Recent Events Raw
        recent_res = await tk.db.query(
            "SELECT timestamp, <datetime>timestamp as dt FROM velocity_events ORDER BY timestamp DESC LIMIT 5"
        )
        print(f"DEBUG Last 5 Timestamps: {recent_res}")

        # Check Velocity Query Manually
        vel_query = "SELECT count() as count FROM velocity_events WHERE type = 'TASK_COMPLETE' AND <datetime>timestamp > time::now() - 5m GROUP ALL"
        vel_res = await tk.db.query(vel_query)
        print(f"DEBUG Velocity Query Result: {vel_res}")

    except Exception as e:
        print(f"DEBUG Query Failed: {e}")

    # 3. Calculate Velocity
    velocity = await tk.calculate_velocity(window_minutes=5)
    print(f"Calculated Velocity (Tasks/Hour): {velocity}")

    # Since we strictly count events in the window, if we just did 5 events,
    # the velocity query (count) should return 5.
    # Note: calculate_velocity implementation currently returns COUNT,
    # implying raw throughput in the window.
    # If we want "Tasks Per Hour" rate, we'd extrapolate, but the
    # current implementation just counts events in window.

    if velocity >= 5:
        print("✅ SUCCESS: Velocity tracking working.")
    else:
        print(f"❌ FAILURE: Expected >= 5 events, got {velocity}")


if __name__ == "__main__":
    asyncio.run(test_velocity_tracking())
