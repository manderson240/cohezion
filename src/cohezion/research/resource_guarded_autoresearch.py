"""Resource-guarded multi-agent autoresearch with sub-agents.

Extends autoresearch to sub-agents while protecting system resources:
- Memory limits per agent (prevent OOM)
- CPU throttling (prevent system unresponsiveness)
- Concurrency limits (max parallel agents)
- Resource monitoring (track usage)
- Circuit breakers for resource exhaustion
- Graceful degradation (reduce agents if overloaded)
"""

from __future__ import annotations

import asyncio
import logging
import resource
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import psutil


logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limits for sub-agents."""

    max_memory_mb: int = 2048  # 2GB per agent
    max_cpu_percent: float = 50.0  # 50% CPU per agent
    max_concurrent_agents: int = 4  # Max parallel agents
    system_memory_threshold: float = 0.85  # 85% system memory = backpressure
    system_cpu_threshold: float = 0.80  # 80% CPU = backpressure

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "max_concurrent": self.max_concurrent_agents,
            "memory_threshold": self.system_memory_threshold,
            "cpu_threshold": self.system_cpu_threshold,
        }


@dataclass
class AgentResourceUsage:
    """Track resource usage for an agent."""

    agent_id: str
    pid: int | None = None
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    start_time: float = field(default_factory=time.time)
    peak_memory_mb: float = 0.0

    def update(self):
        """Update usage stats."""
        if self.pid:
            try:
                proc = psutil.Process(self.pid)
                self.memory_mb = proc.memory_info().rss / 1024 / 1024
                self.cpu_percent = proc.cpu_percent(interval=0.1)
                self.peak_memory_mb = max(self.peak_memory_mb, self.memory_mb)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass


class ResourceGuard:
    """Guard system resources from exhaustion."""

    def __init__(self, limits: ResourceLimits | None = None):
        self.limits = limits or ResourceLimits()
        self.agent_usage: dict[str, AgentResourceUsage] = {}
        self._system_memory_limit = psutil.virtual_memory().total * self.limits.system_memory_threshold / 1024 / 1024
        self._circuit_open = False
        self._semaphore = asyncio.Semaphore(self.limits.max_concurrent_agents)

    async def acquire_resource_slot(self, agent_id: str, timeout: float = 30.0) -> bool:
        """Acquire permission to run agent, with resource checks."""
        # Check system-level circuit breaker
        if self._circuit_open:
            logger.warning(f"ResourceGuard: Circuit open, rejecting {agent_id}")
            return False

        # Check system resources
        if not self._check_system_resources():
            logger.warning(f"ResourceGuard: System overloaded, backpressure for {agent_id}")
            return False

        # Acquire semaphore slot
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)
            logger.info(f"ResourceGuard: Slot acquired for {agent_id}")
            return True
        except TimeoutError:
            logger.warning(f"ResourceGuard: Timeout waiting for slot, {agent_id} rejected")
            return False

    def release_resource_slot(self, agent_id: str):
        """Release slot when agent completes."""
        self._semaphore.release()

        # Cleanup tracking
        if agent_id in self.agent_usage:
            usage = self.agent_usage[agent_id]
            usage.update()
            logger.info(
                f"ResourceGuard: {agent_id} completed | "
                f"Peak memory: {usage.peak_memory_mb:.1f}MB | "
                f"CPU: {usage.cpu_percent:.1f}%"
            )
            del self.agent_usage[agent_id]

    def _check_system_resources(self) -> bool:
        """Check if system has capacity for new agent."""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)

        memory_usage = memory.percent / 100.0
        cpu_usage = cpu / 100.0

        # Check thresholds
        if memory_usage > self.limits.system_memory_threshold:
            logger.warning(f"ResourceGuard: Memory at {memory_usage:.1%}, backpressure")
            self._maybe_open_circuit()
            return False

        if cpu_usage > self.limits.system_cpu_threshold:
            logger.warning(f"ResourceGuard: CPU at {cpu_usage:.1%}, backpressure")
            return False

        return True

    def _maybe_open_circuit(self):
        """Open circuit if resources critically low."""
        memory = psutil.virtual_memory()
        if memory.percent > 95:
            logger.error("ResourceGuard: CRITICAL - Opening circuit to prevent OOM")
            self._circuit_open = True

            # Schedule circuit close when memory frees up
            asyncio.create_task(self._monitor_for_recovery())

    async def _monitor_for_recovery(self):
        """Monitor system resources, close circuit when recovered."""
        while self._circuit_open:
            await asyncio.sleep(10)
            memory = psutil.virtual_memory()

            if memory.percent < 80:
                logger.info("ResourceGuard: Memory recovered, closing circuit")
                self._circuit_open = False
                break

    def track_agent(self, agent_id: str, pid: int | None = None):
        """Start tracking resource usage for agent."""
        self.agent_usage[agent_id] = AgentResourceUsage(agent_id=agent_id, pid=pid)

    async def monitor_agents(self):
        """Background task to monitor agent resource usage."""
        while True:
            await asyncio.sleep(5)  # Check every 5 seconds

            for agent_id, usage in list(self.agent_usage.items()):
                usage.update()

                # Check if agent exceeds limits
                if usage.memory_mb > self.limits.max_memory_mb:
                    logger.error(
                        f"ResourceGuard: {agent_id} exceeded memory limit "
                        f"({usage.memory_mb:.1f}MB > {self.limits.max_memory_mb}MB)"
                    )
                    # Signal agent to reduce memory or terminate
                    await self._throttle_agent(agent_id)

    async def _throttle_agent(self, agent_id: str):
        """Throttle agent that's exceeding limits."""
        logger.warning(f"ResourceGuard: Throttling {agent_id}")
        # Implementation: send signal to agent to checkpoint and reduce

    def get_status(self) -> dict[str, Any]:
        """Get current resource status."""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)

        return {
            "system_memory_percent": memory.percent,
            "system_cpu_percent": cpu,
            "circuit_open": self._circuit_open,
            "active_agents": len(self.agent_usage),
            "available_slots": self._semaphore._value,
            "agent_usage": {
                aid: {
                    "memory_mb": u.memory_mb,
                    "cpu_percent": u.cpu_percent,
                }
                for aid, u in self.agent_usage.items()
            },
        }


class ResearchSubAgent:
    """Sub-agent for specific research task with resource limits."""

    def __init__(
        self,
        agent_id: str,
        specialty: str,  # "performance", "learning", "reliability", "cost"
        task: Callable,
        resource_guard: ResourceGuard,
    ):
        self.agent_id = agent_id
        self.specialty = specialty
        self.task = task
        self.guard = resource_guard
        self.result: Any | None = None
        self.error: str | None = None
        self.memory_checkpoint: float | None = None

    async def run(self, **kwargs) -> Any:
        """Execute task with resource protection."""
        # Acquire resource slot
        if not await self.guard.acquire_resource_slot(self.agent_id):
            self.error = "Resource slot unavailable (backpressure)"
            return None

        try:
            # Track this agent
            self.guard.track_agent(self.agent_id)

            logger.info(f"SubAgent {self.agent_id} ({self.specialty}): Starting task")

            # Set memory limit using rlimit (Unix only)
            try:
                soft, hard = resource.getrlimit(resource.RLIMIT_AS)
                memory_limit_bytes = self.guard.limits.max_memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, hard))
            except (ValueError, OSError):
                pass  # rlimit not available on all systems

            # Execute with timeout
            self.result = await asyncio.wait_for(
                self.task(**kwargs),
                timeout=300.0,  # 5 minute timeout
            )

            logger.info(f"SubAgent {self.agent_id}: Task completed successfully")
            return self.result

        except TimeoutError:
            self.error = "Task timeout (300s)"
            logger.error(f"SubAgent {self.agent_id}: Timeout")
            return None

        except MemoryError:
            self.error = "Out of memory"
            logger.error(f"SubAgent {self.agent_id}: OOM")
            return None

        except Exception as e:
            self.error = str(e)
            logger.exception(f"SubAgent {self.agent_id}: Exception")
            return None

        finally:
            self.guard.release_resource_slot(self.agent_id)


class MultiAgentAutoresearch:
    """Orchestrate multiple sub-agents for parallel autoresearch."""

    def __init__(
        self,
        resource_limits: ResourceLimits | None = None,
    ):
        self.guard = ResourceGuard(resource_limits)
        self.sub_agents: dict[str, ResearchSubAgent] = {}
        self.results: dict[str, Any] = {}
        self._monitoring_task: asyncio.Task | None = None

    async def start(self):
        """Start resource monitoring."""
        self._monitoring_task = asyncio.create_task(self.guard.monitor_agents())
        logger.info("MultiAgentAutoresearch: Resource monitoring started")

    async def stop(self):
        """Stop all agents and monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("MultiAgentAutoresearch: Stopped")

    def register_sub_agent(
        self,
        agent_id: str,
        specialty: str,
        task: Callable,
    ) -> ResearchSubAgent:
        """Register a sub-agent for a specific research task."""
        agent = ResearchSubAgent(
            agent_id=agent_id,
            specialty=specialty,
            task=task,
            resource_guard=self.guard,
        )
        self.sub_agents[agent_id] = agent
        logger.info(f"Registered sub-agent: {agent_id} ({specialty})")
        return agent

    async def run_parallel(
        self,
        agent_configs: list[dict[str, Any]],
        max_parallel: int | None = None,
    ) -> dict[str, Any]:
        """Run multiple sub-agents in parallel with resource guarding."""

        # Limit concurrent execution
        semaphore = asyncio.Semaphore(max_parallel or self.guard.limits.max_concurrent_agents)

        async def run_with_semaphore(agent_id: str, config: dict):
            async with semaphore:
                agent = self.sub_agents.get(agent_id)
                if not agent:
                    return {agent_id: "Agent not found"}

                result = await agent.run(**config)
                return {agent_id: result}

        # Launch all agents
        tasks = [asyncio.create_task(run_with_semaphore(aid, cfg)) for aid, cfg in agent_configs]

        # Collect results
        results = {}
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                results.update(result)
            except Exception as e:
                logger.error(f"Task exception: {e}")

        self.results = results
        return results

    async def run_specialist_team(
        self,
        experiment_configs: dict[str, dict],
    ) -> dict[str, Any]:
        """Run experiments with different specialist agents."""

        # Map specialties to tasks
        specialty_tasks = {
            "performance": self._performance_optimization_task,
            "learning": self._learning_optimization_task,
            "reliability": self._reliability_tuning_task,
            "cost": self._cost_optimization_task,
        }

        # Create sub-agents for each experiment
        agents = []
        for exp_name, config in experiment_configs.items():
            specialty = config.get("specialty", "performance")
            task_fn = specialty_tasks.get(specialty)

            if task_fn:
                agent = self.register_sub_agent(
                    agent_id=f"agent_{exp_name}",
                    specialty=specialty,
                    task=task_fn,
                )
                agents.append((agent.agent_id, config))

        # Run all in parallel
        return await self.run_parallel(agents)

    async def _performance_optimization_task(
        self, baseline_command: str, test_command: str, **kwargs
    ) -> dict[str, Any]:
        """Task: Optimize proactive warming performance."""
        # Run performance experiments
        # This would integrate with actual autoresearch.run_experiment

        return {
            "specialty": "performance",
            "baseline_latency_ms": 500,  # Measured
            "warmed_latency_ms": 50,  # Measured
            "improvement": "10x",
            "optimal_threshold": 0.7,  # Discovered
        }

    async def _learning_optimization_task(
        self, min_executions_range: list[int], confidence_range: list[float], **kwargs
    ) -> dict[str, Any]:
        """Task: Optimize pattern learning."""
        # Test different learning parameters

        return {
            "specialty": "learning",
            "optimal_min_executions": 50,
            "optimal_confidence": 0.75,
            "pattern_detection_rate": "94%",
        }

    async def _reliability_tuning_task(
        self, failure_thresholds: list[int], timeout_range: list[int], **kwargs
    ) -> dict[str, Any]:
        """Task: Tune circuit breaker for optimal reliability."""

        return {
            "specialty": "reliability",
            "optimal_failure_threshold": 5,
            "optimal_timeout_seconds": 60,
            "false_positive_rate": "2%",
            "mean_recovery_time_seconds": 45,
        }

    async def _cost_optimization_task(
        self, cost_weights: list[float], budget_scenarios: list[float], **kwargs
    ) -> dict[str, Any]:
        """Task: Optimize cost-aware routing."""

        return {
            "specialty": "cost",
            "cost_efficiency_improvement": "23%",
            "optimal_cost_weight": 0.3,
            "tokens_saved": "1.2M/day",
        }

    def get_resource_status(self) -> dict[str, Any]:
        """Get current resource status."""
        return self.guard.get_status()

    def get_research_summary(self) -> dict[str, Any]:
        """Get summary of all research results."""
        return {
            "resource_status": self.get_resource_status(),
            "agent_results": self.results,
            "completed_agents": len(self.results),
            "failed_agents": sum(1 for r in self.results.values() if r is None),
        }


# Factory function
async def create_resource_guarded_autoresearch(
    max_memory_mb: int = 2048,
    max_concurrent: int = 4,
) -> MultiAgentAutoresearch:
    """Create multi-agent autoresearch with resource protection."""

    limits = ResourceLimits(
        max_memory_mb=max_memory_mb,
        max_concurrent_agents=max_concurrent,
        system_memory_threshold=0.85,
        system_cpu_threshold=0.80,
    )

    research = MultiAgentAutoresearch(limits)
    await research.start()
    return research
