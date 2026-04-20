#!/usr/bin/env python3
"""Multi-Agent Parallel Execution Orchestrator for Luma Speedrun.

Divides the workload across specialist agents working simultaneously
on different kernels and optimization strategies.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class AgentConfig:
    name: str
    kernel: str  # gemm | mla | moe
    strategy: str
    worktree: str
    command: list[str]
    timeout_min: int = 30
    priority: int = 1


@dataclass
class AgentResult:
    agent: str
    kernel: str
    status: str  # success | fail | timeout
    runtime_sec: float
    best_latency: float | None = None
    submission_path: str | None = None
    error_log: str | None = None


# AGENT DEFINITIONS - Specialists working in parallel
AGENTS: list[AgentConfig] = [
    # Primary GEMM Agent (load_inline + MFMA)
    AgentConfig(
        name="claude-gemm-primary",
        kernel="gemm",
        strategy="load_inline_mfma",
        worktree=".worktrees/luma-breakthrough-sprint",
        command=[
            "python",
            "luma_speedrun/autoresearch/driver.py",
            "--kernel",
            "gemm",
            "--max-cycles",
            "20",
        ],
        priority=1,
        timeout_min=60,
    ),
    # Autoresearch GEMM Agent (K-Search exploration)
    AgentConfig(
        name="autoresearch-gemm",
        kernel="gemm",
        strategy="ksearch",
        worktree="research/challenges/luma_amd_speedrun",
        command=["python", "autokernel.py", "--kernel", "gemm", "--mode", "explore"],
        priority=2,
        timeout_min=45,
    ),
    # OpenCode/Kimi GEMM Agent (rocWMMA)
    AgentConfig(
        name="kimi-gemm-rocwmma",
        kernel="gemm",
        strategy="rocwmma",
        worktree="hip-kernels-kimi-k2-5",
        command=["python", "scripts/compile_and_test.py", "--kernel", "gemm_vmfma_tuned"],
        priority=2,
        timeout_min=45,
    ),
    # MLA Agent (SnapMLA optimization)
    AgentConfig(
        name="claude-mla",
        kernel="mla",
        strategy="snapmla",
        worktree=".worktrees/luma-breakthrough-sprint",
        command=[
            "python",
            "luma_speedrun/autoresearch/driver.py",
            "--kernel",
            "mla",
            "--max-cycles",
            "20",
        ],
        priority=1,
        timeout_min=60,
    ),
    # Autoresearch MLA Agent
    AgentConfig(
        name="autoresearch-mla",
        kernel="mla",
        strategy="direct_asm",
        worktree="research/challenges/luma_amd_speedrun",
        command=["python", "autokernel.py", "--kernel", "mla", "--mode", "optimize"],
        priority=2,
        timeout_min=45,
    ),
    # MoE Primary Agent
    AgentConfig(
        name="claude-moe",
        kernel="moe",
        strategy="lds_bridge",
        worktree=".worktrees/luma-breakthrough-sprint",
        command=[
            "python",
            "luma_speedrun/autoresearch/driver.py",
            "--kernel",
            "moe",
            "--max-cycles",
            "20",
        ],
        priority=1,
        timeout_min=60,
    ),
    # MoE Specialist (KSPLIT tuning)
    AgentConfig(
        name="moe-specialist",
        kernel="moe",
        strategy="ksplit_sweep",
        worktree="research/challenges/luma_amd_speedrun/kernels/moe-mxfp4",
        command=["python", "sweep_ksplit.py", "--shapes", "all"],
        priority=2,
        timeout_min=45,
    ),
]


class ParallelOrchestrator:
    """Orchestrates multiple agents in parallel with resource management."""

    def __init__(self, base_dir: Path, max_parallel: int = 4):
        self.base_dir = base_dir
        self.max_parallel = max_parallel
        self.results: list[AgentResult] = []
        self.log_dir = base_dir / "luma_speedrun" / "parallel_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    async def run_agent(self, agent: AgentConfig) -> AgentResult:
        """Run a single agent with timeout and logging."""
        start = datetime.now()
        log_file = self.log_dir / f"{agent.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        worktree_path = self.base_dir / agent.worktree

        try:
            # Run agent process
            proc = await asyncio.create_subprocess_exec(
                *agent.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=worktree_path,
            )

            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=agent.timeout_min * 60
                )

                # Save log
                log_file.write_text(f"STDOUT:\n{stdout.decode()}\n\nSTDERR:\n{stderr.decode()}")

                # Parse results
                runtime = (datetime.now() - start).total_seconds()

                if proc.returncode == 0:
                    # Try to extract latency from output
                    best_latency = self._extract_latency(stdout.decode())

                    return AgentResult(
                        agent=agent.name,
                        kernel=agent.kernel,
                        status="success",
                        runtime_sec=runtime,
                        best_latency=best_latency,
                        submission_path=str(worktree_path / "submission.py"),
                    )
                else:
                    return AgentResult(
                        agent=agent.name,
                        kernel=agent.kernel,
                        status="fail",
                        runtime_sec=runtime,
                        error_log=stderr.decode()[-500:],
                    )

            except asyncio.TimeoutError:
                proc.kill()
                runtime = (datetime.now() - start).total_seconds()
                return AgentResult(
                    agent=agent.name,
                    kernel=agent.kernel,
                    status="timeout",
                    runtime_sec=runtime,
                    error_log="Timeout exceeded",
                )

        except Exception as e:
            runtime = (datetime.now() - start).total_seconds()
            return AgentResult(
                agent=agent.name,
                kernel=agent.kernel,
                status="fail",
                runtime_sec=runtime,
                error_log=str(e),
            )

    def _extract_latency(self, output: str) -> float | None:
        """Extract best latency from agent output."""
        import re

        # Look for patterns like "Best: 12.3 µs" or "Latency: 4.5"
        patterns = [
            r"Best:\s*([\d.]+)\s*µs",
            r"latency:\s*([\d.]+)",
            r"time:\s*([\d.]+)",
        ]
        for pattern in patterns:
            if match := re.search(pattern, output, re.IGNORECASE):
                return float(match.group(1))
        return None

    async def run_parallel(self, agents: list[AgentConfig]) -> list[AgentResult]:
        """Run agents in parallel with semaphore limiting."""
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def run_with_limit(agent: AgentConfig) -> AgentResult:
            async with semaphore:
                print(f"[START] {agent.name} on {agent.kernel}")
                result = await self.run_agent(agent)
                status_emoji = "✅" if result.status == "success" else "❌"
                print(f"[{status_emoji}] {agent.name}: {result.status} ({result.runtime_sec:.1f}s)")
                return result

        # Run all agents
        tasks = [run_with_limit(agent) for agent in agents]
        self.results = await asyncio.gather(*tasks)
        return self.results

    def print_summary(self):
        """Print execution summary."""
        print("\n" + "=" * 70)
        print("PARALLEL EXECUTION SUMMARY")
        print("=" * 70)

        for kernel in ["gemm", "mla", "moe"]:
            print(f"\n{kernel.upper()} Agents:")
            kernel_results = [r for r in self.results if r.kernel == kernel]
            for r in kernel_results:
                status_emoji = (
                    "✅" if r.status == "success" else "⏱️" if r.status == "timeout" else "❌"
                )
                latency_str = f" ({r.best_latency:.2f}µs)" if r.best_latency else ""
                print(f"  {status_emoji} {r.agent}: {r.status}{latency_str}")

        print("\n" + "=" * 70)
        success_count = sum(1 for r in self.results if r.status == "success")
        print(f"Total: {success_count}/{len(self.results)} agents succeeded")

        # Find best results per kernel
        print("\nBest Results per Kernel:")
        for kernel in ["gemm", "mla", "moe"]:
            kernel_results = [r for r in self.results if r.kernel == kernel and r.best_latency]
            if kernel_results:
                best = min(kernel_results, key=lambda r: r.best_latency or float("inf"))
                print(f"  {kernel}: {best.best_latency:.2f}µs by {best.agent}")


def main():
    """Main entry point."""
    base_dir = Path("/home/mike-anderson/dev/cohezion")

    # Select which agents to run
    if len(sys.argv) > 1:
        kernel_filter = sys.argv[1]
        agents = [a for a in AGENTS if a.kernel == kernel_filter]
        print(f"Running {len(agents)} agents for kernel: {kernel_filter}")
    else:
        agents = AGENTS
        print(f"Running all {len(agents)} agents in parallel")

    # Run orchestration
    orchestrator = ParallelOrchestrator(base_dir, max_parallel=4)

    try:
        asyncio.run(orchestrator.run_parallel(agents))
        orchestrator.print_summary()

        # Save results
        results_file = base_dir / "luma_speedrun" / "parallel_results.json"
        results_data = [
            {
                "agent": r.agent,
                "kernel": r.kernel,
                "status": r.status,
                "runtime_sec": r.runtime_sec,
                "best_latency": r.best_latency,
            }
            for r in orchestrator.results
        ]
        results_file.write_text(json.dumps(results_data, indent=2))
        print(f"\nResults saved to: {results_file}")

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
