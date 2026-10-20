"""Autonomous 4-Hour Evolution Supervisor for Cohezion.

Orchestrates:
1. Lemonade Tier 1 Local Inference (port 13305, Bonsai-8B-gguf)
2. Ollama Cloud Tier 2 (port 11434, glm-5.3-flash, qwen3.5:397b-cloud)
3. Tripartite Goal Loops: Internal Codebase Sweeps, Frontier Research, Experiential Learning
4. AutoHarness AST bytecode verifiers (0ms) and ZK-FV Plonkish gates
5. Dual persistence into SurrealDB (http://localhost:8001) and Obsidian Vault (~/vaults/cohezion-vault/)
6. Inter-agent communication via EventBus and durable Kanban item tracking
"""

from __future__ import annotations

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
logger = logging.getLogger("autonomous_supervisor")

TOTAL_CYCLES = 8
CYCLE_DELAY_SECONDS = 20


async def run_autonomous_evolution_cycle(cycle_idx: int) -> bool:
    goal_id = f"mission_4h_cycle_{cycle_idx}_{int(time.time())}"
    logger.info(f"=== Starting Autonomous Evolution Cycle {cycle_idx}/{TOTAL_CYCLES}: {goal_id} ===")
    
    bus = EventBus()
    await bus.publish(
        Event.agent_complete(
            agent_name="autonomous_supervisor",
            duration_ms=5.0,
            result={"cycle": cycle_idx, "status": "cycle_started", "goal_id": goal_id},
        )
    )
    
    goal = GoalSpecification(
        goal_id=goal_id,
        title=f"Autonomous 4h Optimization Cycle {cycle_idx}: Recursive Cohezion Refinement",
        target_metric="sheaf_dirichlet_energy",
        target_threshold=0.10,
        max_iterations=3,
    )
    
    loop = TripartiteGoalLoop(max_depth=3)
    start_t = time.perf_counter()
    res = loop.run(goal)
    duration_ms = (time.perf_counter() - start_t) * 1000.0
    
    logger.info(
        f"Cycle {cycle_idx} Complete in {duration_ms:.2f}ms | "
        f"{'Converged: ' + str(res.converged) if res.steps_executed else 'NO STEP EXECUTED (nothing attempted)'} | "
        f"Reward: {(f'{res.final_reward:.4f}' if res.final_reward is not None else 'UNKNOWN')} | Notes Created: {len(res.vault_notes_created)}"
    )
    
    latest_strat = res.history[-1].strategy if res.history else "cellular_sheaf_diffusion"
    
    # Update Kanban Card
    persist_item({
        "id": f"kanban-{goal_id}",
        "title": f"Autonomous Cycle {cycle_idx}: {latest_strat}",
        "status": "done" if res.converged else "review",
        "priority": "normal",
        "source": "autonomous_supervisor",
        "category": "recursive_evolution",
        "description": f"{'Converged: ' + str(res.converged) if res.steps_executed else 'No step executed (nothing attempted)'}, Final Reward: {(f'{res.final_reward:.4f}' if res.final_reward is not None else 'UNKNOWN')}, Iterations: {res.iterations_run}",
    })
    
    await bus.publish(
        Event.agent_complete(
            agent_name="autonomous_supervisor",
            duration_ms=duration_ms,
            result={
                "cycle": cycle_idx,
                "status": "cycle_completed",
                "converged": res.converged,
                "steps_executed": res.steps_executed,
                "reward": res.final_reward,
                "vault_notes": res.vault_notes_created,
            },
        )
    )
    return res.converged


async def main() -> None:
    logger.info("Starting Cohezion Autonomous 4-Hour Evolution Supervisor...")
    start_time = time.time()
    successful_cycles = 0
    
    for cycle in range(1, TOTAL_CYCLES + 1):
        try:
            converged = await run_autonomous_evolution_cycle(cycle)
            if converged:
                successful_cycles += 1
        except Exception as e:
            logger.error(f"Error in cycle {cycle}: {e}", exc_info=True)
            
        logger.info(f"Cycle {cycle} complete. Sleeping {CYCLE_DELAY_SECONDS}s before next optimization cycle...")
        await asyncio.sleep(CYCLE_DELAY_SECONDS)
        
    total_duration = time.time() - start_time
    logger.info(f"Autonomous evolution supervisor finished {TOTAL_CYCLES} cycles ({successful_cycles} converged) in {total_duration:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
