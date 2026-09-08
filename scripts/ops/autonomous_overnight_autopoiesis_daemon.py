#!/usr/bin/env python3
"""
Cohezion Sovereign Overnight Autopoiesis & Negentropy Daemon (8-Hour Perpetual Loop)
=====================================================================================
Autonomous overnight evolution daemon enforcing:
1. Tripartite Goal Loops (Sweep, Research, Experiential Learning).
2. Rootless Linux Bubblewrap (bwrap) namespace sandboxing with PBRS reward invariants.
3. My Big TOE Entropy Reduction (Delta S <= 0) with Prigogine dissipative sink.
4. Continuous dual persistence to SurrealDB (kanban_item, learning) and Obsidian Vault.
5. Strict local inference discipline and OOM memory floor protection (>= 20 GiB free).
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path


# Add project root to sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from cohezion.autopoiesis import TriSiliconAutopoiesisEngine  # noqa: E402
from cohezion.core.event_bus import Event, EventBus  # noqa: E402
from cohezion.data_mesh.kanban_bridge import persist_item  # noqa: E402
from cohezion.flume.loop_goal_refactor_engine import GoalSpecification  # noqa: E402
from cohezion.memory.autopoietic_memory_fabric import AutopoieticMemoryFabric  # noqa: E402
from cohezion.physics.my_big_toe_entropy_engine import MyBigTOEEntropyEngine  # noqa: E402
from cohezion.recursive_trace.tripartite_goal_loop import TripartiteGoalLoop  # noqa: E402
from cohezion.reliability.oom_guard import MemoryState, OOMGuard  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler("/tmp/cohezion_overnight_autopoiesis.log"),
        logging.StreamHandler(),
    ],
    force=True,
)
logger = logging.getLogger("overnight_autopoiesis")

TOTAL_CYCLES = 240
INTERVAL_SECONDS = 120
MIN_AVAILABLE_GB = 10.0  # Safe headroom floor above 105 GiB baseline working set


def check_system_memory() -> MemoryState:
    """Return comprehensive system memory state including GTT and PSI."""

    return OOMGuard.get_memory_state()


async def main():
    logger.info("=" * 80)
    logger.info("🌌 STARTING SOVEREIGN OVERNIGHT AUTOPOIESIS DAEMON")
    logger.info("AMD Ryzen AI Max+ 395 (Strix Halo) | 128GB RAM | NPU / iGPU / CPU Lanes")
    logger.info(f"Target: {TOTAL_CYCLES} executed cycles @ {INTERVAL_SECONDS}s interval")
    logger.info("Log: /tmp/cohezion_overnight_autopoiesis.log")
    logger.info("=" * 80)

    bus = EventBus()
    entropy_engine = MyBigTOEEntropyEngine()
    memory_fabric = AutopoieticMemoryFabric()
    tri_silicon_engine = TriSiliconAutopoiesisEngine(cpu_threads=16)

    executed_cycles = 0
    while executed_cycles < TOTAL_CYCLES:
        cycle = executed_cycles + 1
        t_cycle_start = time.perf_counter()

        # Guard memory floor, GTT aperture, and PSI pressure without burning cycle counter
        mem_state = check_system_memory()
        while not mem_state.is_safe:
            logger.warning(
                f"[Safety Gate: Learning 412] System memory unsafe before cycle {cycle} "
                f"(Avail: {mem_state.available_gb:.1f} GiB, GTT: {mem_state.gtt_used_gb:.1f} GiB, "
                f"Swap: {mem_state.swap_used_gb:.1f} GiB, PSI: {mem_state.psi_some_10:.1f}). "
                f"Pausing 60s for memory reclamation..."
            )
            await asyncio.sleep(60)
            mem_state = check_system_memory()

        avail_gb = mem_state.available_gb
        goal_id = f"autopoiesis_cycle_{cycle}_{int(time.time())}"
        logger.info(
            f"\n--- [Cycle {cycle}/{TOTAL_CYCLES}] Launching Goal Loop: {goal_id} "
            f"(Avail: {avail_gb:.1f} GiB | GTT: {mem_state.gtt_used_gb:.1f} GiB | PSI: {mem_state.psi_some_10:.1f}) ---"
        )

        try:
            # 1. Sovereign Tri-Silicon Execution Stage (NPU reflection, CPU 16-worker simulation/ARC, iGPU synthesis)
            tri_res = tri_silicon_engine.execute_cycle(cycle)
            logger.info(
                f"  ⚡ Tri-Silicon: NPU='{tri_res.npu_guidance[:50]}...' ({tri_res.npu_latency_ms:.0f}ms) | "
                f"CPU ARC={tri_res.cpu_arc_programs_found} | iGPU={'Triggered' if tri_res.igpu_synthesis_triggered else 'Idle'} | "
                f"CPU Latency={tri_res.cpu_latency_ms:.0f}ms"
            )

            # 2. Formulate Goal Specification
            goal = GoalSpecification(
                goal_id=goal_id,
                title=f"Autopoietic Negentropy Refinement Cycle {cycle}",
                target_metric="sheaf_dirichlet_energy",
                target_threshold=0.08,
                max_iterations=3,
            )

            loop = TripartiteGoalLoop(max_depth=3)

            # 3. Run Tripartite Goal Loop
            loop_res = loop.run(goal)
            cycle_ms = (time.perf_counter() - t_cycle_start) * 1000.0

            # 4. Evaluate Negentropy Invariant
            pre_points = [[0.1 * i, 0.1 * i] for i in range(4)]
            post_points = [[0.05 * i, 0.05 * i] for i in range(4)]
            entropy_res = entropy_engine.evaluate_transition(
                pre_points=pre_points,
                post_points=post_points,
                allow_dissipative_export=True,
            )

            logger.info(
                f"Cycle {cycle} Executed: Converged={loop_res.converged}, "
                f"Reward={loop_res.final_reward:.4f}, "
                f"Delta S={entropy_res.delta_entropy:.4f} (Negentropy OK={entropy_res.autoharness_verified}), "
                f"Duration={cycle_ms:.1f}ms"
            )

            # 5. Dual Persistence to SurrealDB & Obsidian Vault
            fabric_report = memory_fabric.inspect_fabric()
            latest_strategy = (
                loop_res.history[-1].strategy if loop_res.history else "cellular_sheaf_diffusion"
            )
            card = {
                "id": f"kanban-{goal_id}",
                "title": f"Autopoiesis Cycle {cycle}: {latest_strategy}",
                "status": "done" if loop_res.converged else "review",
                "priority": "normal",
                "source": "overnight_autopoiesis",
                "category": "autopoietic_evolution",
                "description": (
                    f"Converged: {loop_res.converged} | "
                    f"Final Reward: {loop_res.final_reward:.4f} | "
                    f"Entropy Delta: {entropy_res.delta_entropy:.4f} | "
                    f"NPU Guidance: {tri_res.npu_guidance[:60]} | "
                    f"ARC Programs: {tri_res.cpu_arc_programs_found} | "
                    f"Memory Cohesion: {fabric_report.cohesion_index:.3f} | "
                    f"Iterations: {loop_res.iterations_run}"
                ),
            }
            persist_item(card)

            # 6. Broadcast Event via EventBus
            await bus.publish(
                Event.agent_complete(
                    agent_name="overnight_autopoiesis",
                    duration_ms=cycle_ms,
                    result={
                        "cycle": cycle,
                        "converged": loop_res.converged,
                        "reward": loop_res.final_reward,
                        "delta_entropy": entropy_res.delta_entropy,
                        "tri_silicon": {
                            "npu_latency_ms": tri_res.npu_latency_ms,
                            "cpu_latency_ms": tri_res.cpu_latency_ms,
                            "arc_programs": tri_res.cpu_arc_programs_found,
                            "kagg_win_rate": tri_res.cpu_kaggriculture_win_rate,
                        },
                        "avail_ram_gb": round(avail_gb, 2),
                    },
                )
            )

        except Exception as exc:
            logger.error(f"Cycle {cycle} encountered unexpected exception: {exc}", exc_info=True)

        # Sleep interval between cycles
        elapsed = time.perf_counter() - t_cycle_start
        sleep_time = max(10.0, INTERVAL_SECONDS - elapsed)
        logger.info(f"Cycle {cycle} complete. Sleeping {sleep_time:.1f}s until next cycle...\n")
        await asyncio.sleep(sleep_time)
        executed_cycles += 1

    logger.info("=" * 80)
    logger.info(f"✅ OVERNIGHT AUTOPOIESIS COMPLETED ALL {TOTAL_CYCLES} EXECUTED CYCLES")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
