"""Integration adapters for Dynamic Compound System with Cohezion.

Wires new proactive/reactive system into existing infrastructure:
- Circuit breakers → ComputeBackendRouter
- Proactive warming → ModelPoolManager
- Adaptive routing → CostAwareRouter
- Events → Existing logging/monitoring
- Patterns → Vault MCP
"""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from cohezion.compound.proactive_reactive_engine import (
    ProactiveReactiveEngine,
    SystemEvent,
)
from cohezion.core.mcp_client import MCPClient
from cohezion.swarm.compute_backend_router import (
    BackendType,
    ComputeBackendRouter,
)
from cohezion.swarm.cost_aware_router import CostAwareRouter
from cohezion.swarm.model_pool_manager import ModelPoolManager, get_pool_manager


logger = logging.getLogger(__name__)


class CircuitBreakerRouterAdapter:
    """Adapts circuit breakers to ComputeBackendRouter.

    Ensures ComputeBackendRouter respects circuit breaker states
    when routing to backends.
    """

    def __init__(
        self,
        backend_router: ComputeBackendRouter,
        proactive_engine: ProactiveReactiveEngine,
    ):
        self.router = backend_router
        self.engine = proactive_engine
        self._backend_states: dict[BackendType, bool] = {}

        # Wire events
        self._setup_circuit_events()

    def _setup_circuit_events(self):
        """Wire circuit breaker events to router updates."""
        self.engine.register_event_handler(
            SystemEvent.CIRCUIT_OPENED,
            self._on_circuit_opened,
        )
        self.engine.register_event_handler(
            SystemEvent.CIRCUIT_CLOSED,
            self._on_circuit_closed,
        )

    async def _on_circuit_opened(self, event: SystemEvent, data: dict):
        """When circuit opens, mark backend unavailable in router."""
        backend = data.get("backend")
        if backend and isinstance(backend, BackendType):
            logger.warning(f"CIRCUIT_OPENED: Marking {backend} unavailable")
            self._backend_states[backend] = False

            # Update router's view of this backend
            status = self.router.get_backend_status(backend)
            if status:
                status.available = False
                status.last_updated = datetime.now()

    async def _on_circuit_closed(self, event: SystemEvent, data: dict):
        """When circuit closes, restore backend availability."""
        backend = data.get("backend")
        if backend and isinstance(backend, BackendType):
            logger.info(f"CIRCUIT_CLOSED: Marking {backend} available")
            self._backend_states[backend] = True

            # Update router's view
            status = self.router.get_backend_status(backend)
            if status:
                status.available = True
                status.last_updated = datetime.now()

    def is_backend_available(self, backend: BackendType) -> bool:
        """Check if backend is available (respects circuit breaker)."""
        # First check circuit breaker
        breaker = self.engine.get_circuit_breaker(backend)
        if not breaker.can_execute():
            return False

        # Also check our tracked state
        if backend in self._backend_states:
            return self._backend_states[backend]

        # Fall back to router's view
        return self.router.is_backend_available(backend)

    def get_available_backends(self) -> list[BackendType]:
        """Get list of available backends respecting circuit breakers."""
        all_backends = [b for b in BackendType]
        return [b for b in all_backends if self.is_backend_available(b)]


class ProactivePoolAdapter:
    """Adapts proactive warming to ModelPoolManager."""

    def __init__(
        self,
        pool_manager: ModelPoolManager,
        proactive_engine: ProactiveReactiveEngine,
    ):
        self.pool = pool_manager
        self.engine = proactive_engine

        # Register proactive handlers
        self._register_proactive_handlers()

    def _register_proactive_handlers(self):
        """Wire proactive actions to pool warming."""
        # Hook into proactive trigger loop
        original_evaluate = self.engine._evaluate_proactive_triggers

        async def wrapped_evaluate():
            await original_evaluate()
            # After proactive evaluation, warm any needed models
            await self._sync_warming_state()

        self.engine._evaluate_proactive_triggers = wrapped_evaluate

        self.engine.register_event_handler(SystemEvent.PATTERN_MATCHED, self._on_pattern_matched)

    async def _on_pattern_matched(self, event: SystemEvent, data: dict):
        """Warm models when a workload pattern is matched."""
        pattern = data.get("pattern")
        if pattern and hasattr(pattern, "preferred_agents"):
            await self.warm_for_pattern(pattern)

    async def _sync_warming_state(self):
        """Sync warming state with pool manager."""
        # Get warmed agents from proactive engine
        warmed_agents = self._get_warmed_agents()

        for agent in warmed_agents:
            model = self._agent_to_model(agent)
            if model:
                await self.warm_model(model, priority=1.0)

    def _get_warmed_agents(self) -> list[str]:
        """Get list of agents that should be warmed."""
        # Check proactive actions for warming
        warmed = []
        for action in self.engine._proactive_actions:
            if action.action_type in ["warm_code_agents", "warm_reasoning_agents", "warm_pattern"]:
                warmed.extend(action.agents_warmed)
        return list(set(warmed))  # Deduplicate

    async def warm_model(self, model_name: str, priority: float = 0.5):
        """Pre-warm model into pool."""
        try:
            logger.info(f"Proactive warming: {model_name} (priority={priority})")
            # Actual loading deferred to pool manager's next cycle
        except Exception as e:
            logger.warning(f"PROACTIVE_WARM_FAILED: {model_name} - {e}")

    async def warm_for_pattern(self, pattern: Any):
        """Warm models based on predicted pattern."""
        logger.info(f"PROACTIVE_PATTERN: Warming for pattern at {pattern.hour}:00")

        for agent in pattern.preferred_agents:
            model = self._agent_to_model(agent)
            if model:
                await self.warm_model(model, priority=1.0)

    def _agent_to_model(self, agent_name: str) -> str | None:
        """Map agent name to Lemonade model name for pool."""
        mapping = {
            "CodeSpecialist": "CodeLlama-7b-Instruct-hf-Hybrid",
            "ReasoningSpecialist": "Qwen3-8B-Hybrid",
            "NovelSpecialist": "Phi-4-mini-instruct-Hybrid",
            "VisionSpecialist": "Gemma-4-E4B-it-GGUF",
        }
        return mapping.get(agent_name)


class AdaptiveCostAdapter:
    """Adapts adaptive routing to consider cost."""

    def __init__(self, cost_router: CostAwareRouter):
        self.cost_router = cost_router
        self._cost_cache: dict[str, float] = {}

    async def score_with_cost(
        self,
        agent_scores: dict[str, float],
        budget_remaining: float,
        tokens_estimate: int = 1000,
    ) -> dict[str, float]:
        """Adjust scores based on cost constraints."""
        adjusted_scores = {}

        for agent, score in agent_scores.items():
            # Get cost estimate
            cost = await self._get_cost_estimate(agent, tokens_estimate)

            # Apply cost weighting
            if budget_remaining <= 0:
                # No budget - only allow free options
                if cost > 0:
                    adjusted_scores[agent] = 0  # Disallow
                else:
                    adjusted_scores[agent] = score
            elif cost <= budget_remaining:
                # Within budget - slight preference for cheaper
                cost_efficiency = 1 - (cost / max(budget_remaining, 0.01))
                adjusted_scores[agent] = score * (0.8 + 0.2 * cost_efficiency)
            else:
                # Over budget - penalize
                adjusted_scores[agent] = score * 0.5

        return adjusted_scores

    async def _get_cost_estimate(self, agent_name: str, tokens: int) -> float:
        """Estimate cost for agent execution."""
        # Check cache
        if agent_name in self._cost_cache:
            base_cost = self._cost_cache[agent_name]
        else:
            # Get from cost router
            base_cost = self._lookup_cost(agent_name)
            self._cost_cache[agent_name] = base_cost

        # Scale by tokens
        return base_cost * (tokens / 1000)

    def _lookup_cost(self, agent_name: str) -> float:
        """Lookup base cost for agent (Lemonade-first architecture)."""
        costs = {
            "CodeSpecialist": 0.0,  # Lemonade NPU - free
            "ReasoningSpecialist": 0.0,  # Lemonade Hybrid - free
            "CloudAgent": 0.0,  # Ollama Pro - subscription, not per-token
            "VisionSpecialist": 0.0,  # Lemonade GPU - free
        }
        return costs.get(agent_name, 0.0)


class EventLoggingAdapter:
    """Adapts event system to existing logging/monitoring."""

    def __init__(self, proactive_engine: ProactiveReactiveEngine):
        self.engine = proactive_engine
        self._custom_handlers: list[Callable] = []
        self._register_handlers()

    def _register_handlers(self):
        """Wire events to existing logging."""
        self.engine.register_event_handler(
            SystemEvent.CIRCUIT_OPENED,
            self._log_circuit_event,
        )
        self.engine.register_event_handler(
            SystemEvent.CIRCUIT_CLOSED,
            self._log_circuit_event,
        )
        self.engine.register_event_handler(
            SystemEvent.PATTERN_MATCHED,
            self._log_pattern_event,
        )
        self.engine.register_event_handler(
            SystemEvent.AGENT_PERFORMANCE_DEGRADED,
            self._log_degradation,
        )
        self.engine.register_event_handler(
            SystemEvent.WORKLOAD_SPIKE_DETECTED,
            self._log_spike,
        )

    def add_custom_handler(self, event_type: SystemEvent, handler: Callable):
        """Add user-defined handler for events."""
        self.engine.register_event_handler(event_type, handler)

    async def _log_circuit_event(self, event: SystemEvent, data: dict):
        """Log circuit breaker events."""
        backend = data.get("backend", "unknown")
        failures = data.get("failures", "N/A")

        if event == SystemEvent.CIRCUIT_OPENED:
            logger.warning(
                f"🚨 CIRCUIT_OPENED | backend={backend} | "
                f"failures={failures} | routing_around_failure"
            )
        elif event == SystemEvent.CIRCUIT_CLOSED:
            logger.info(f"✅ CIRCUIT_CLOSED | backend={backend} | recovered, restoring_traffic")

    async def _log_pattern_event(self, event: SystemEvent, data: dict):
        """Log pattern detection events."""
        pattern_type = data.get("type", "unknown")
        confidence = data.get("confidence", 0.0)
        hour = data.get("hour", "N/A")

        logger.info(
            f"🧠 PATTERN_DETECTED | type={pattern_type} | "
            f"hour={hour}:00 | confidence={confidence:.0%} | "
            f"will_proactively_warm"
        )

    async def _log_degradation(self, event: SystemEvent, data: dict):
        """Log performance degradation events."""
        agent = data.get("agent", "unknown")
        success_rate = data.get("success_rate", 0.0)
        latency = data.get("avg_latency", 0)

        logger.error(
            f"⚠️ DEGRADATION | agent={agent} | "
            f"success_rate={success_rate:.1%} | latency={latency:.0f}ms | "
            f"consider_alternative_fallback"
        )

    async def _log_spike(self, event: SystemEvent, data: dict):
        """Log workload spike events."""
        severity = data.get("severity", "unknown")
        current_load = data.get("current_load", 0)

        logger.warning(
            f"📈 WORKLOAD_SPIKE | severity={severity} | load={current_load} | scaling_up"
        )


class VaultPatternAdapter:
    """Adapts pattern learning to Vault MCP persistence."""

    def __init__(
        self,
        mcp_client: MCPClient,
        proactive_engine: ProactiveReactiveEngine,
    ):
        self.mcp = mcp_client
        self.engine = proactive_engine

    async def persist_patterns(self):
        """Persist detected patterns to vault."""
        patterns = self.engine._detected_patterns

        if not patterns:
            return

        logger.info(f"VAULT_PERSIST: Saving {len(patterns)} patterns")

        for pattern in patterns:
            try:
                record = {
                    "type": "workload_pattern",
                    "timestamp": datetime.now().isoformat(),
                    "hour": pattern.hour,
                    "day_of_week": pattern.day_of_week,
                    "task_types": pattern.task_types,
                    "preferred_agents": pattern.preferred_agents,
                    "confidence": pattern.confidence,
                    "avg_requests": pattern.avg_requests_per_hour,
                }

                # Write to vault if available
                if hasattr(self.mcp, "write_to_vault"):
                    await self.mcp.write_to_vault(
                        record,
                        tags=["workload_pattern", "dynamic_system"],
                    )
                    logger.debug(f"  → Persisted pattern for hour {pattern.hour}:00")
                else:
                    # Fall back to file persistence when MCP is not available
                    import json
                    from pathlib import Path

                    pattern_file = Path.home() / ".claude" / "anthropic-intel" / "patterns.jsonl"
                    pattern_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(pattern_file, "a") as f:
                        f.write(json.dumps(record, default=str) + "\n")
                    logger.debug(f"  → File-persisted pattern for hour {pattern.hour}:00")

            except Exception as e:
                logger.warning(f"VAULT_PERSIST_FAILED: {e}")

    async def load_patterns(self) -> list[Any]:
        """Load previous patterns from vault."""
        try:
            if not hasattr(self.mcp, "find_relevant_context"):
                # Fall back to file persistence when MCP is not available
                import json
                from pathlib import Path

                pattern_file = Path.home() / ".claude" / "anthropic-intel" / "patterns.jsonl"
                if pattern_file.exists():
                    patterns = []
                    for line in pattern_file.read_text().splitlines():
                        if line.strip():
                            patterns.append(json.loads(line))
                    logger.info(f"  → Loaded {len(patterns)} patterns from file")
                    return patterns
                return []

            logger.info("VAULT_LOAD: Loading historical patterns")

            # Query vault for patterns
            results = await self.mcp.find_relevant_context(
                query="workload patterns",
                limit=50,
                tags=["workload_pattern"],
            )

            # Deserialize patterns
            patterns = self._deserialize_patterns(results)

            logger.info(f"  → Loaded {len(patterns)} patterns from vault")
            return patterns

        except Exception as e:
            logger.warning(f"VAULT_LOAD_FAILED: {e}")
            return []

    def _deserialize_patterns(self, records: list[dict]) -> list[Any]:
        """Convert vault records back to pattern objects."""
        from cohezion.compound.proactive_reactive_engine import WorkloadPattern

        patterns = []
        for record in records:
            try:
                pattern = WorkloadPattern(
                    hour=record.get("hour", 0),
                    day_of_week=record.get("day_of_week", 0),
                    task_types=record.get("task_types", []),
                    avg_requests_per_hour=record.get("avg_requests", 0),
                    preferred_agents=record.get("preferred_agents", []),
                    confidence=record.get("confidence", 0.0),
                )
                patterns.append(pattern)
            except Exception as e:
                logger.debug(f"Failed to deserialize pattern: {e}")

        return patterns

    async def persist_execution_outcome(
        self,
        task: str,
        agent: str,
        backend: str,
        success: bool,
        latency_ms: float,
    ):
        """Persist execution outcome for learning."""
        try:
            record = {
                "type": "execution_outcome",
                "timestamp": datetime.now().isoformat(),
                "task_preview": task[:200],
                "agent": agent,
                "backend": backend,
                "success": success,
                "latency_ms": latency_ms,
            }

            if hasattr(self.mcp, "write_to_vault"):
                await self.mcp.write_to_vault(
                    record,
                    tags=["execution", agent, backend],
                )
        except Exception as e:
            logger.debug(f"VAULT_PERSIST_EXECUTION_FAILED: {e}")


class DynamicSystemCoordinator:
    """Central coordinator that wires all adapters together."""

    def __init__(
        self,
        mcp_client: MCPClient,
        backend_router: ComputeBackendRouter | None = None,
        pool_manager: ModelPoolManager | None = None,
        cost_router: CostAwareRouter | None = None,
    ):
        self.mcp = mcp_client

        # Create or get components
        self.backend_router = backend_router or ComputeBackendRouter.get_default()
        self.pool_manager = pool_manager or get_pool_manager()
        self.cost_router = cost_router or CostAwareRouter()

        # These will be set in initialize()
        self.proactive_engine: ProactiveReactiveEngine | None = None
        self.adapters: dict[str, Any] = {}

    async def initialize(self, enable_proactive: bool = True, enable_reactive: bool = True):
        """Initialize dynamic system with all adapters."""
        from cohezion.swarm import get_orchestrator

        orchestrator = await get_orchestrator()

        self.proactive_engine = ProactiveReactiveEngine(
            mcp_client=self.mcp,
            orchestrator=orchestrator,
            enable_proactive=enable_proactive,
            enable_reactive=enable_reactive,
            enable_learning=True,
        )

        await self.proactive_engine.start()

        # Wire all adapters
        self.adapters = {
            "circuit": CircuitBreakerRouterAdapter(
                self.backend_router,
                self.proactive_engine,
            ),
            "pool": ProactivePoolAdapter(
                self.pool_manager,
                self.proactive_engine,
            ),
            "cost": AdaptiveCostAdapter(self.cost_router),
            "logging": EventLoggingAdapter(self.proactive_engine),
            "vault": VaultPatternAdapter(
                self.mcp,
                self.proactive_engine,
            ),
        }

        # Load previous patterns
        await self._load_historical_patterns()

        logger.info("✅ DynamicSystemCoordinator initialized with all adapters")

    async def _load_historical_patterns(self):
        """Load patterns from previous sessions."""
        vault_adapter = self.adapters.get("vault")
        if vault_adapter:
            patterns = await vault_adapter.load_patterns()
            if patterns:
                logger.info(f"🧠 Loaded {len(patterns)} historical patterns from vault")
                # Apply to engine
                self.proactive_engine._detected_patterns.extend(patterns)

    async def execute(self, task: str, context: dict | None = None, **kwargs) -> Any:
        """Execute task with full dynamic system."""
        if not self.proactive_engine:
            raise RuntimeError("Coordinator not initialized. Call initialize() first.")

        # Route execution through orchestrator (which uses all adapters)
        from cohezion.swarm import get_orchestrator

        orch = await get_orchestrator()

        result = await orch.execute(task, context, **kwargs)

        # Persist outcome to vault
        vault_adapter = self.adapters.get("vault")
        if vault_adapter:
            await vault_adapter.persist_execution_outcome(
                task=task,
                agent=result.agent_name,
                backend=result.backend,
                success=result.success,
                latency_ms=result.latency_ms,
            )

        return result

    def get_available_backends(self) -> list[BackendType]:
        """Get backends respecting circuit breakers."""
        circuit_adapter = self.adapters.get("circuit")
        if circuit_adapter:
            return circuit_adapter.get_available_backends()
        return [b for b in BackendType]

    def add_event_handler(self, event: SystemEvent, handler: Callable):
        """Add custom event handler."""
        logging_adapter = self.adapters.get("logging")
        if logging_adapter:
            logging_adapter.add_custom_handler(event, handler)

    async def shutdown(self):
        """Graceful shutdown."""
        if self.proactive_engine:
            # Persist final patterns
            vault_adapter = self.adapters.get("vault")
            if vault_adapter:
                await vault_adapter.persist_patterns()

            await self.proactive_engine.stop()

        logger.info("✅ DynamicSystemCoordinator shutdown complete")


class LemonadeAdapter:
    """Adapts proactive engine to Lemonade 3-slot model hotswapping.

    Slots: NPU (fast/small), GPU (quality/large), CPU (background)
    Each slot maps to a Lemonade backend with hardware affinity.

    Hotswap flow:
        1. Unload current model from slot (POST /api/unload)
        2. Load new model into slot (POST /api/load)
        3. Update internal state

    The Lemonade unified router at localhost:13305 uses OpenAI-compatible API.
    Router dispatches to the appropriate backend (NPU / iGPU / CPU) on demand.
    """

    # Slot → backend mapping for Lemonade server
    SLOT_BACKENDS = {
        "npu": "hybrid",  # RyzenAI 1.7 NPU+CPU
        "gpu": "rocm",  # ROCm llamacpp (RDNA 3.5 iGPU)
        "cpu": "onnx",  # ONNX int4 (CPU only)
    }

    def __init__(self, lemonade_base_url: str = "http://localhost:13305"):  # router-centric (Phase 2)
        self.base_url = lemonade_base_url.rstrip("/")
        self._loaded_models: dict[str, str] = {"npu": "", "gpu": "", "cpu": ""}

    async def hotswap(self, slot: str, model_name: str) -> bool:
        """Hotswap a model in the specified slot (npu/gpu/cpu).

        Calls Lemonade API to unload old model and load new one.
        Falls back to state-only tracking if API is unavailable.
        """
        if slot not in self._loaded_models:
            logger.error(f"Invalid slot: {slot}")
            return False

        old_model = self._loaded_models[slot]
        if old_model == model_name:
            return True  # Already loaded

        backend = self.SLOT_BACKENDS.get(slot, "hybrid")
        logger.info(f"Hotswap {slot} ({backend}): {old_model or '(empty)'} → {model_name}")

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Unload current model if one is loaded
                if old_model:
                    resp = await client.post(
                        f"{self.base_url}/api/unload",
                        json={"model": old_model},
                    )
                    if resp.status_code not in (200, 404):
                        logger.warning(f"Unload {old_model} returned {resp.status_code}")

                # Load new model with backend affinity
                resp = await client.post(
                    f"{self.base_url}/api/load",
                    json={"model": model_name, "backend": backend},
                )
                if resp.status_code == 200:
                    self._loaded_models[slot] = model_name
                    logger.info(f"Hotswap complete: {slot} → {model_name}")
                    return True
                else:
                    logger.warning(f"Load {model_name} returned {resp.status_code}")
                    return False
        except ImportError:
            logger.debug("httpx not available, tracking state only")
            self._loaded_models[slot] = model_name
            return True
        except Exception as e:
            logger.warning(f"Lemonade API unavailable ({e}), tracking state only")
            self._loaded_models[slot] = model_name
            return True

    async def get_server_models(self) -> list[str]:
        """Query Lemonade server for available models."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/v1/models")
                if resp.status_code == 200:
                    data = resp.json()
                    return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            logger.debug(f"Failed to query Lemonade models: {e}")
        return []

    def get_loaded_models(self) -> dict[str, str]:
        """Return current model loaded in each slot."""
        return dict(self._loaded_models)

    def select_slot_for_task(self, task_type: str) -> str:
        """Select best slot for a given task type."""
        task_slot_map = {
            "coding": "npu",  # Fast, CodeLlama-7b
            "reasoning": "gpu",  # Quality, Qwen3-14B
            "vision": "gpu",  # Gemma-4-31B mmproj
            "embedding": "gpu",  # nomic-embed-text-v2
            "background": "cpu",  # DeepSeek-R1-CPU, no GPU contention
        }
        return task_slot_map.get(task_type, "npu")


# Convenience factory
async def create_integrated_dynamic_system(
    mcp_client: MCPClient,
    **kwargs,
) -> DynamicSystemCoordinator:
    """Factory for creating fully integrated system.

    Args:
        mcp_client: Connected MCP client
        **kwargs: Passed to coordinator

    Returns:
        Initialized DynamicSystemCoordinator with all adapters wired
    """
    coordinator = DynamicSystemCoordinator(mcp_client, **kwargs)
    await coordinator.initialize()
    return coordinator
