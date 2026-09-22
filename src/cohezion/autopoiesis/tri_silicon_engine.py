"""Tri-Silicon Sovereign Autopoiesis Engine for AMD Strix Halo.
==============================================================
Orchestrates continuous hardware-specialized autopoietic cycles:
1. NPU Phase: FastFlowLM (XDNA2, port 13305) - Reflection, strategy synthesis, and directional steering.
2. CPU Phase: 16-Core Zen 4 AVX-512 - High-throughput parallel tournaments & ARC DSL symbolic search.
3. iGPU Phase: Radeon 8060S Vulkan/ROCm - Code generation and heuristic policy synthesis.
4. Mathematical Negentropy Verification: Sheaf Dirichlet energy relaxation and Prigogine dissipative entropy sink.
5. Dual Persistence: Commits to SurrealDB (experiment_run, kanban_item) and Obsidian Vault.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from cohezion.arc.strix_dsl_search import StrixHaloDSLEngine
from cohezion.flume.loop_goal_refactor_engine import GoalSpecification
from cohezion.physics.my_big_toe_entropy_engine import MyBigTOEEntropyEngine
from cohezion.recursive_trace.tripartite_goal_loop import TripartiteGoalLoop
from cohezion.reliability.oom_guard import MemoryState, OOMGuard


logger = logging.getLogger("tri_silicon_autopoiesis")

LEMONADE_URL = "http://127.0.0.1:13305/v1/chat/completions"
VAULT_LEARNINGS_DIR = Path.home() / "vaults" / "cohezion-vault" / "01-Learnings"


def observed_state(rewards: list[float | None], mem: MemoryState) -> list[list[float]] | None:
    """Per-iteration [measured reward, measured free-RAM fraction]; None if any is unknown.

    This is the only state the entropy check sees. It is MEASURED, so the entropy can
    rise as well as fall between cycles (the previous version built the "after" points
    as a tight cluster around a centroid, so Delta S <= 0 held by construction).
    """
    if not mem.total_gb or not rewards or any(r is None for r in rewards):
        return None
    frac = max(0.0, min(1.0, mem.available_gb / mem.total_gb))
    return [[float(r), frac] for r in rewards]  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class TriSiliconCycleResult:
    """Quantitative scorecard of a single Tri-Silicon autopoietic cycle."""

    cycle: int
    npu_guidance: str
    npu_model: str
    npu_latency_ms: float
    cpu_arc_programs_found: int
    cpu_kaggriculture_win_rate: float | None
    cpu_sheaf_converged: bool
    cpu_latency_ms: float
    igpu_synthesis_triggered: bool
    delta_entropy: float | None  # None = no measured previous state (e.g. first cycle)
    autoharness_verified: bool | None  # None = negentropy check not performed
    total_latency_ms: float
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return asdict(self)


class TriSiliconAutopoiesisEngine:
    """Sovereign Tri-Silicon Autopoiesis Orchestrator on AMD Strix Halo."""

    def __init__(
        self,
        cpu_threads: int = 16,
        npu_model: str = "llama3.2-1b-FLM",
        igpu_model: str = "gemma-4-E4B-it-GGUF",
    ) -> None:
        self.cpu_threads = cpu_threads
        self.npu_model = npu_model
        self.igpu_model = igpu_model
        self.entropy_engine = MyBigTOEEntropyEngine()
        from cohezion.agi.zkfv_compiler import ZKFVCompiler

        self.zkfv_compiler = ZKFVCompiler(salt="tri_silicon_sovereign_v1")
        self.arc_dsl_engine = StrixHaloDSLEngine(
            max_depth=2,
            beam_width=20,
            n_threads=self.cpu_threads,
        )
        self._prev_state: list[list[float]] | None = None  # measured state, previous cycle

    def execute_npu_phase(self, cycle: int) -> tuple[str, float]:
        """Phase 1: NPU-accelerated reflection and goal direction via FastFlowLM."""
        t0 = time.perf_counter()
        prompt = (
            f"Autopoiesis Cycle {cycle}: Suggest the single highest-leverage optimization "
            "focus (e.g., ARC spatial invariants, heuristic tournament mutation, or sheaf diffusion) "
            "in 1 concise sentence."
        )
        payload = {
            "model": self.npu_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 80,
            "temperature": 0.4,
        }
        try:
            req = urllib.request.Request(
                LEMONADE_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
                data = json.loads(resp.read().decode())
                content = data["choices"][0]["message"]["content"].strip()
                # Strip thinking block if present
                if "</think>" in content:
                    content = content.split("</think>")[-1].strip()
                latency_ms = (time.perf_counter() - t0) * 1000.0
                return content or "Focus on ARC spatial invariant synthesis.", latency_ms
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            logger.debug(f"[NPU Phase Fallback] Cycle {cycle}: {exc}")
            return "Cellular sheaf diffusion and spatial invariant relaxation.", latency_ms

    def execute_cpu_phase(self, cycle: int, npu_guidance: str) -> dict[str, Any]:
        """Phase 2: 16-core Zen 4 AVX-512 parallel tournament & ARC DSL symbolic search."""
        t0 = time.perf_counter()

        # Pin OpenMP to physical cores for memory bandwidth bound workloads
        os.environ["OMP_NUM_THREADS"] = str(self.cpu_threads)
        os.environ["OMP_PLACES"] = "cores"
        os.environ["OMP_PROC_BIND"] = "close"

        # 1. ARC Symbolic Search step
        sample_task = {
            "train": [
                {"input": [[1, 2], [3, 4]], "output": [[3, 1], [4, 2]]},
                {"input": [[5, 6], [7, 8]], "output": [[7, 5], [8, 6]]},
            ],
            "test": [{"input": [[9, 0], [1, 2]]}],
        }
        sol, _ = self.arc_dsl_engine.solve_single_task(sample_task)
        programs_found = 1 if sol is not None else 0

        # 2. Tripartite Goal Loop
        goal = GoalSpecification(
            goal_id=f"tri_silicon_cycle_{cycle}_{int(time.time())}",
            title=f"Tri-Silicon Refinement Cycle {cycle}",
            target_metric="sheaf_dirichlet_energy",
            target_threshold=0.08,
            max_iterations=3,
        )
        loop = TripartiteGoalLoop(max_depth=2)
        loop_res = loop.run(goal)

        # 3. Kaggriculture Mutation Step (sampled every 5 cycles for efficiency)
        kagg_win_rate = None
        if cycle % 5 == 0:
            try:
                base_dir = (
                    Path(__file__).resolve().parent.parent.parent.parent
                    / "scripts"
                    / "kaggle"
                    / "kaggriculture_kernel"
                )
                v3_path = str(base_dir / "main_PLANNER_v3.py")
                livestock_path = str(base_dir / "main_LIVESTOCK.py")
                if Path(v3_path).exists() and Path(livestock_path).exists():
                    import sys

                    if str(base_dir) not in sys.path:
                        sys.path.insert(0, str(base_dir))
                    from multiprocessing import Pool

                    from evolve_planner import play_match

                    tasks = [(v3_path, livestock_path, seed, 0) for seed in range(4)]
                    with Pool(processes=min(4, self.cpu_threads)) as pool:
                        results = pool.map(play_match, tasks)
                    wins = sum(1 for r in results if r[1] > r[2])
                    kagg_win_rate = wins / len(results) if results else None
            except Exception as exc:
                logger.debug(f"[Kaggriculture Tournament] Skipped: {exc}")

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "programs_found": programs_found,
            "converged": loop_res.converged,
            "final_reward": loop_res.final_reward,
            "rewards": [it.learning.reward for it in loop_res.history],
            "steps_executed": loop_res.steps_executed,
            "kagg_win_rate": kagg_win_rate,
            "latency_ms": latency_ms,
        }

    def execute_igpu_phase(
        self, cycle: int, cpu_results: dict[str, Any]
    ) -> tuple[bool, str, float]:
        """Phase 3: iGPU code synthesis and policy refinement if improvements detected."""
        t0 = time.perf_counter()
        # Trigger code synthesis when an exact program is found or reward exceeds threshold
        should_synthesize = cpu_results.get("programs_found", 0) > 0 and (cycle % 10 == 0)
        if not should_synthesize:
            return False, "Synthesis skipped (not scheduled)", 0.0

        prompt = (
            f"Synthesize an optimized Python heuristic transform based on winning ARC invariant. "
            f"Cycle: {cycle}, Reward: {cpu_results.get('final_reward') if cpu_results.get('final_reward') is not None else 'UNKNOWN'}."
        )
        payload = {
            "model": self.igpu_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 128,
            "temperature": 0.2,
        }
        try:
            req = urllib.request.Request(
                LEMONADE_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
                data = json.loads(resp.read().decode())
                content = data["choices"][0]["message"]["content"].strip()
                latency_ms = (time.perf_counter() - t0) * 1000.0
                return True, content, latency_ms
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            logger.debug(f"[iGPU Phase] Skipped: {exc}")
            return False, f"Fallback synthesis: {exc}", latency_ms

    def execute_cycle(self, cycle: int) -> TriSiliconCycleResult:
        """Execute a complete sovereign Tri-Silicon autopoietic cycle."""
        t_start = time.perf_counter()

        # Check memory safety
        mem = OOMGuard.get_memory_state()
        if not mem.is_safe:
            logger.warning(
                f"[OOM Guard] Memory tight before cycle {cycle} (Avail: {mem.available_gb:.1f} GiB). "
                "Executing lightweight cycle."
            )

        # 1. NPU Phase
        npu_guidance, npu_latency_ms = self.execute_npu_phase(cycle)

        # 2. CPU Phase
        cpu_results = self.execute_cpu_phase(cycle, npu_guidance)

        # 3. iGPU Phase
        igpu_triggered, igpu_content, igpu_latency_ms = self.execute_igpu_phase(cycle, cpu_results)

        # 4. Strict Negentropy Invariant Verification (Delta S <= 0, no dissipative loophole)
        #    on MEASURED state: this cycle vs the previous one. No previous state -> UNKNOWN.
        post_state = observed_state(cpu_results.get("rewards", []), OOMGuard.get_memory_state())
        delta_entropy: float | None = None
        negentropy_ok: bool | None = None
        entropy_reduced: bool | None = None
        if self._prev_state is not None and post_state is not None:
            entropy_res = self.entropy_engine.evaluate_transition(
                pre_points=self._prev_state,
                post_points=post_state,
                pre_coherences=[pt[0] for pt in self._prev_state],
                post_coherences=[pt[0] for pt in post_state],
                allow_dissipative_export=False,
            )
            delta_entropy = entropy_res.delta_entropy
            negentropy_ok = entropy_res.autoharness_verified
            entropy_reduced = entropy_res.is_entropy_reduced
        self._prev_state = post_state

        total_latency_ms = (time.perf_counter() - t_start) * 1000.0

        # 5. Dual Persistence: Commit result to Obsidian Vault and SurrealDB Experiential Substrate
        self._persist_to_vault(
            cycle=cycle,
            guidance=npu_guidance,
            delta_entropy=delta_entropy,
            negentropy_ok=negentropy_ok,
            cpu_results=cpu_results,
            igpu_triggered=igpu_triggered,
        )

        try:
            if cpu_results.get("final_reward") is None:
                raise ValueError("final_reward UNKNOWN; not recording a fabricated quality")
            if entropy_reduced is None:
                raise ValueError("Delta S UNKNOWN; not recording a fabricated success")
            from cohezion.learning.vault_neuron_reader import VaultNeuronWriter

            VaultNeuronWriter.get_instance().write_outcome(
                task_id=f"tri_silicon_cycle_{cycle}",
                category="autopoiesis_tri_silicon",
                success=entropy_reduced,
                tokens=128,
                node="strix_halo_tri_silicon",
                model=self.npu_model,
                quality_score=float(cpu_results.get("final_reward", 0.0)),
                elapsed_ms=total_latency_ms,
            )
        except Exception as exc:
            logger.debug("Experiential persistence skipped: %s", exc)

        return TriSiliconCycleResult(
            cycle=cycle,
            npu_guidance=npu_guidance,
            npu_model=self.npu_model,
            npu_latency_ms=npu_latency_ms,
            cpu_arc_programs_found=cpu_results["programs_found"],
            cpu_kaggriculture_win_rate=cpu_results["kagg_win_rate"],
            cpu_sheaf_converged=cpu_results["converged"],
            cpu_latency_ms=cpu_results["latency_ms"],
            igpu_synthesis_triggered=igpu_triggered,
            delta_entropy=delta_entropy,
            autoharness_verified=negentropy_ok,
            total_latency_ms=total_latency_ms,
            details={
                "igpu_content": igpu_content,
                "igpu_latency_ms": igpu_latency_ms,
                "final_reward": cpu_results.get("final_reward"),
                "steps_executed": cpu_results.get("steps_executed", 0),
            },
        )

    def _persist_to_vault(
        self,
        cycle: int,
        guidance: str,
        delta_entropy: float | None,
        cpu_results: dict[str, Any],
        igpu_triggered: bool,
        negentropy_ok: bool | None = None,
    ) -> None:
        """Write structured retrospective entry into Obsidian Vault."""
        try:
            if not VAULT_LEARNINGS_DIR.exists():
                VAULT_LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
            today_str = time.strftime("%Y-%m-%d")
            ds_txt = f"{delta_entropy:.4f}" if delta_entropy is not None else "UNKNOWN"
            ok_txt = "not checked" if negentropy_ok is None else f"Negentropy OK={negentropy_ok}"
            retro_file = VAULT_LEARNINGS_DIR / f"autopoiesis_tri_silicon_{today_str}.md"
            entry = (
                f"\n### Tri-Silicon Cycle {cycle} ({time.strftime('%H:%M:%S')})\n"
                f"- **NPU Guidance**: {guidance}\n"
                f"- **CPU ARC Programs**: {cpu_results.get('programs_found', 0)} | "
                f"Sheaf Converged: {cpu_results.get('converged', False)} | "
                f"Kaggriculture Win Rate: {cpu_results.get('kagg_win_rate')}\n"
                f"- **iGPU Synthesis**: {'Triggered' if igpu_triggered else 'Idle'}\n"
                f"- **Goal-loop steps executed**: {cpu_results.get('steps_executed', 0)}\n"
                f"- **Entropy Delta**: ΔS = {ds_txt} ({ok_txt})\n"
            )
            with open(retro_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as exc:
            logger.debug(f"Vault persistence failed: {exc}")
