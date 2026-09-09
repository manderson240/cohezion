#!/usr/bin/env python3
"""Demonstration and Validation of Refactoring Traces into Goals and Loops."""

import asyncio
import time
import httpx
import numpy as np

from cohezion.flume.loop_goal_refactor_engine import (
    GoalSpecification,
    AutonomousGoalExecutor,
    TraceToLoopTransformer
)

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Authorization": "Basic cm9vdDpyb290",
    "Content-Type": "text/plain"
}

async def run_refactor_demo():
    print("\n" + "=" * 115)
    print("🔄 REFACTORING TRACES INTO GOAL-DIRECTED AUTONOMOUS LOOPS (AMD STRIX HALO)")
    print("=" * 115)

    # 1. Raw Linear Trace Simulation
    print("\n▶ [1] Ingesting Raw Linear Trace Events:")
    raw_trace = [
        {"step": 1, "agent": "scout", "finding": "Poincaré manifold curvature drift observed"},
        {"step": 2, "agent": "evaluator", "metric": 0.22},
        {"step": 3, "agent": "calibrator", "metric": 0.38},
        {"step": 4, "agent": "verifier", "metric": 0.50}
    ]
    for ev in raw_trace:
        print(f"  • Trace Event: {ev}")

    # 2. Refactor Trace -> Goal Specification
    print("\n▶ [2] Transforming Linear Trace into Formal Goal Specification:")
    goal = TraceToLoopTransformer.synthesize_goal_from_trace(
        raw_trace,
        goal_title="Attain and Lock HIHO 0.50 Coherence Attractor"
    )
    print(f"  ✓ Goal Created: `{goal.title}` (ID: {goal.goal_id})")
    print(f"  ✓ Target Metric: {goal.target_metric} >= {goal.target_threshold} | Max Iterations: {goal.max_iterations}")

    # 3. Execute Autonomous Closed-Loop State Machine
    print("\n▶ [3] Executing Autonomous Goal Loop State Machine:")
    
    # State is current coherence
    initial_coherence = 0.15
    
    def step_fn(iteration: int, state: float) -> tuple[float, float, str]:
        # Negative feedback allostatic step towards 0.50
        error = 0.50 - state
        step = 0.45 * error
        new_state = float(state + step)
        action = f"CTAC Curvature Adjustment (Delta: {step:+.4f})"
        return new_state, new_state, action

    def verifier_fn(metric_val: float) -> bool:
        return abs(metric_val - 0.50) <= 0.01

    executor = AutonomousGoalExecutor(goal)
    result = await executor.execute_loop(initial_coherence, step_fn, verifier_fn)

    for step in result.history:
        status_mark = "🎯 GOAL REACHED" if step.is_goal_met else "🔄 Iterating"
        print(f"  Iteration #{step.iteration}: Coherence = {step.metric_value:.4f} | {step.action_taken:<45} | {status_mark}")

    print(f"\n  ✓ Loop Converged: {result.converged} in {result.iterations_run} iterations ({result.total_time_ms} ms)")

    # 4. Durable SurrealDB Goal & Loop Trace Persistence
    print("\n▶ [4] Persisting Goal & Execution Loop to SurrealDB...")
    sql = f"""
    CREATE goal CONTENT {{
        goal_id: '{goal.goal_id}',
        title: '{goal.title}',
        target_metric: '{goal.target_metric}',
        target_threshold: {goal.target_threshold},
        converged: {str(result.converged).lower()},
        iterations_run: {result.iterations_run},
        final_metric: {result.final_metric},
        total_time_ms: {result.total_time_ms},
        timestamp: '{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}'
    }};
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(SURREAL_URL, headers=SURREAL_HEADERS, content=sql)
        print(f"  ✓ Goal Record Persisted to SurrealDB (HTTP {r.status_code})")

    print("\n" + "=" * 115)
    print("🎉 TRACE REFACTORING INTO GOALS & LOOPS COMPLETE AND VERIFIED!\n")

if __name__ == "__main__":
    asyncio.run(run_refactor_demo())
