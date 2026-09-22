#!/usr/bin/env bash
set -euo pipefail

# 4-Hour Continuous Background Evolution Daemon for Cohezion
# Runs 120 cycles with 120s intervals = 4.0 hours total duration
# Uses unbuffered Python, logging to /tmp/cohezion_4h_evolution.log

LOG_FILE="/tmp/cohezion_4h_evolution.log"
PID_FILE="/tmp/cohezion_4h_evolution.pid"

echo "=== Starting Cohezion 4-Hour Autonomous Evolution Daemon ==="
echo "Timestamp: $(date -Iseconds)"

cat << 'PYEOF' > /tmp/cohezion_4h_runner.py
import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from cohezion.core.event_bus import Event, EventBus
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.flume.loop_goal_refactor_engine import GoalSpecification
from cohezion.recursive_trace.tripartite_goal_loop import TripartiteGoalLoop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] %(message)s",
)
logger = logging.getLogger("4h_daemon")

TOTAL_CYCLES = 120
INTERVAL_SECONDS = 120

async def main():
    logger.info(f"Starting 4-hour evolution loop: {TOTAL_CYCLES} cycles @ {INTERVAL_SECONDS}s interval")
    bus = EventBus()
    for cycle in range(1, TOTAL_CYCLES + 1):
        goal_id = f"daemon_4h_cycle_{cycle}_{int(time.time())}"
        logger.info(f"Cycle {cycle}/{TOTAL_CYCLES}: {goal_id}")
        goal = GoalSpecification(
            goal_id=goal_id,
            title=f"Autonomous 4h Optimization Cycle {cycle}: Cohezion Refinement",
            target_metric="sheaf_dirichlet_energy",
            target_threshold=0.10,
            max_iterations=3,
        )
        loop = TripartiteGoalLoop(max_depth=3)
        t0 = time.perf_counter()
        try:
            res = loop.run(goal)
            ms = (time.perf_counter() - t0) * 1000.0
            latest_strat = res.history[-1].strategy if res.history else "cellular_sheaf_diffusion"
            persist_item({
                "id": f"kanban-{goal_id}",
                "title": f"Daemon Cycle {cycle}: {latest_strat}",
                "status": "done" if res.converged else "review",
                "priority": "normal",
                "source": "4h_daemon",
                "category": "recursive_evolution",
                "description": f"Converged: {res.converged}, Reward: {(f'{res.final_reward:.4f}' if res.final_reward is not None else 'UNKNOWN')}, Iterations: {res.iterations_run}",
            })
            await bus.publish(
                Event.agent_complete(
                    agent_name="4h_daemon",
                    duration_ms=ms,
                    result={"cycle": cycle, "converged": res.converged, "reward": res.final_reward},
                )
            )
            logger.info(f"Cycle {cycle} succeeded: Converged={res.converged}, Reward={(f'{res.final_reward:.4f}' if res.final_reward is not None else 'UNKNOWN')}, Latency={ms:.2f}ms")
        except Exception as e:
            logger.error(f"Cycle {cycle} encountered error: {e}", exc_info=True)
            
        logger.info(f"Cycle {cycle} complete. Sleeping {INTERVAL_SECONDS}s...")
        await asyncio.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    asyncio.run(main())
PYEOF

PYTHONPATH=src uv run python -u /tmp/cohezion_4h_runner.py >> "$LOG_FILE" 2>&1 &
RUNNER_PID=$!
echo "$RUNNER_PID" > "$PID_FILE"
echo "Daemon launched in background with PID $RUNNER_PID. Logging to $LOG_FILE."
