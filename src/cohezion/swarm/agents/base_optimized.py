"""Optimized base agent using compound engineering infrastructure.

This version uses shared services from the infrastructure layer:
- TieredCacheManager for unified caching
- SecurityPipeline for shared security
- EventBus for decoupled logging
- TaskManager for background task tracking
- UnifiedRegistry for capability discovery
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx

from cohezion.core.credit_manager import get_credit_manager
from cohezion.core.time_keeper import get_time_keeper
from cohezion.db.surreal_client import SurrealClient
from cohezion.infrastructure import (
    Event,
    EventBus,
    FilterResult,
    SecurityPipeline,
    TaskManager,
    TieredCacheManager,
    UnifiedRegistry,
    get_cache_manager,
    get_event_bus,
    get_security_pipeline,
    get_task_manager,
    get_unified_registry,
)
from cohezion.reliability.monitor import get_resource_monitor
from cohezion.swarm.journey_narrator import JourneyNarrator
from cohezion.swarm.redundancy_suppression import RedundancyManager
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class AgentResponse(str):
    """Enhanced string response with native agentic metadata."""

    def __new__(cls, content, **kwargs):
        obj = super().__new__(cls, content)
        for key, value in kwargs.items():
            setattr(obj, key, value)
        return obj

    def __getattr__(self, name):
        return None


class BaseAgent(ABC):
    """Optimized abstract base class for Swarm agents.

    Key optimizations:
    - Shared infrastructure services (singleton pattern)
    - Tiered caching (Memory → Semantic → File)
    - Security pipeline (shared across agents)
    - Event-driven logging (decoupled from DB)
    - Tracked background tasks (no fire-and-forget)
    - Lazy initialization of heavy components
    """

    # Class-level shared resources (initialized once)
    _shared_client: httpx.AsyncClient | None = None
    _client_ref_count: int = 0
    _client_lock: asyncio.Lock | None = None

    def __init__(
        self,
        model_name: str,
        config: SwarmConfig | None = None,
        cache_dir: Path | None = None,
    ):
        self.model_name = model_name
        self._apply_local_routing(model_name)
        self.config = config or SwarmConfig()
        self.priority = self.config.priority

        # Infrastructure services (lazy-initialized)
        self._cache: TieredCacheManager | None = None
        self._security: SecurityPipeline | None = None
        self._event_bus: EventBus | None = None
        self._task_manager: TaskManager | None = None
        self._registry: UnifiedRegistry | None = None
        self._redundancy_mgr: RedundancyManager | None = None
        self._narrator: JourneyNarrator | None = None

        # Legacy compatibility
        self._encoder = None
        self._db = SurrealClient()
        self._query_history: dict[str, int] = {}
        self._credit_manager = get_credit_manager()

        # Metrics
        self._metrics: dict[str, Any] = {
            "total_calls": 0,
            "cache_hits": 0,
            "total_latency_ms": 0,
            "errors": 0,
        }

        # Initialize class-level lock if needed
        if BaseAgent._client_lock is None:
            BaseAgent._client_lock = asyncio.Lock()

    async def _init_infrastructure(self) -> None:
        """Lazy-initialize all infrastructure services."""
        if self._cache is None:
            self._cache = await get_cache_manager()
            # Add file backend if not present
            if len(self._cache._backends) == 0:
                from cohezion.infrastructure import FileBackend

                await self._cache.add_backend(FileBackend("cache/swarm"))

        if self._security is None:
            self._security = await get_security_pipeline()

        if self._event_bus is None:
            self._event_bus = await get_event_bus()

        if self._task_manager is None:
            self._task_manager = await get_task_manager()

        if self._registry is None:
            self._registry = await get_unified_registry()

        if self._redundancy_mgr is None:
            self._redundancy_mgr = RedundancyManager(agent_name=self.__class__.__name__)

        if self._narrator is None:
            self._narrator = JourneyNarrator()

    @property
    async def client(self) -> httpx.AsyncClient:
        """Get shared HTTP client with reference counting."""
        if BaseAgent._shared_client is None:
            async with BaseAgent._client_lock:
                if BaseAgent._shared_client is None:
                    BaseAgent._shared_client = httpx.AsyncClient(
                        base_url=self.config.ollama_base_url,
                        timeout=httpx.Timeout(300.0, connect=10.0),
                        limits=httpx.Limits(
                            max_connections=50, max_keepalive_connections=20
                        ),
                    )
        BaseAgent._client_ref_count += 1
        return BaseAgent._shared_client

    async def close(self) -> None:
        """Release resources with proper cleanup."""
        async with BaseAgent._client_lock:
            BaseAgent._client_ref_count -= 1
            if BaseAgent._client_ref_count <= 0 and BaseAgent._shared_client:
                await BaseAgent._shared_client.aclose()
                BaseAgent._shared_client = None
                BaseAgent._client_ref_count = 0

    async def _call_ollama(
        self,
        prompt: str,
        temperature: float = 0.7,
        images: list[str] | None = None,
        max_tokens: int = 2048,
        system_prompt: str | None = None,
        ignore_cache: bool = False,
        model: str | None = None,
    ) -> AgentResponse:
        """Call local Ollama instance with optimized caching and security."""
        start_time = time.perf_counter()

        # Ensure infrastructure is initialized
        await self._init_infrastructure()

        # Generate query hash
        import hashlib

        req_hash_content = f"{self.model_name}:{prompt}"
        if images:
            req_hash_content += ":" + ":".join(images[:3])
        query_hash = hashlib.sha256(req_hash_content.encode()).hexdigest()[:12]

        # Check redundancy
        suppression_level, effective_prompt = self._redundancy_mgr.check(prompt)
        if suppression_level > 0:
            await self._redundancy_mgr.apply_suppression(suppression_level, prompt)
            if suppression_level == 3:
                return AgentResponse(
                    "[Suppressed] Task suspended due to extreme redundancy.",
                    security_level="suppressed",
                )

        self._query_history[query_hash] = self._query_history.get(query_hash, 0) + 1
        freq = self._query_history[query_hash]

        # Check cache (unified tiered cache)
        if not ignore_cache:
            cached = await self._cache.get(self.model_name, prompt, images)
            if cached:
                self._metrics["cache_hits"] += 1

                # Publish cache hit event
                await self._event_bus.publish(
                    Event.cache_access(
                        agent_name=self.__class__.__name__,
                        hit=True,
                        tier="unknown",  # Could track which tier hit
                        model=self.model_name,
                    )
                )

                return AgentResponse(
                    cached.response,
                    embedding=cached.embedding,
                    persistence_id=cached.persistence_id,
                    frequency=freq,
                    phi_score=cached.phi_score,
                    confidence=cached.confidence,
                    alignment_score=cached.alignment_score,
                    security_level="safe",
                    narration=cached.narration,
                    cached=True,
                )

        # Security check
        security_result = await self._security.check_input(prompt)
        if not security_result.allowed:
            await self._event_bus.publish(
                Event(
                    type=EventType.SECURITY_VIOLATION,
                    source=self.__class__.__name__,
                    payload={"reason": security_result.reason, "input": prompt[:100]},
                )
            )
            return AgentResponse(
                f"[Blocked] {security_result.reason}",
                security_level="blocked",
            )

        # Token economics
        agent_id = self.__class__.__name__
        active_model = model or self.model_name

        if not self._credit_manager.can_afford(agent_id, active_model):
            active_model = self._credit_manager.get_best_affordable_model(
                agent_id, active_model
            )
            logger.warning(f"Agent {agent_id} downgraded to {active_model}")

        self._metrics["total_calls"] += 1
        monitor = get_resource_monitor()

        # Degraded mode handling
        current_prompt = effective_prompt
        effective_system = system_prompt
        if self.config.degraded_mode:
            current_prompt = prompt[:1024]
            if system_prompt:
                effective_system = system_prompt[:512]

        # Execute LLM call
        final_result = ""
        embedding = None
        phi_score, confidence, alignment_score = 0.5, 0.5, 1.0

        client = await self.client

        for round_idx in range(self.config.max_refinement_rounds):
            if monitor.resource_coordinator:
                await monitor.resource_coordinator.prepare_resources_for_priority(
                    self.priority
                )

            await monitor.wait_for_capacity()
            call_start = time.perf_counter()

            try:
                payload = {
                    "model": active_model,
                    "prompt": current_prompt,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                }
                if effective_system:
                    payload["system"] = effective_system
                if images:
                    payload["images"] = images

                response = await client.post("/api/generate", json=payload)
                response.raise_for_status()
                result = response.json().get("response", "")

                # Self-evaluation
                phi_score, confidence, audit_res = await self.self_evaluate(
                    result,
                    query=prompt,
                    metadata={
                        "agent": agent_id,
                        "model": active_model,
                        "round": round_idx,
                    },
                )
                alignment_score = audit_res.get("alignment_score", 1.0)

                # Publish LLM call event
                await self._event_bus.publish(
                    Event.llm_call(
                        agent_name=agent_id,
                        model=active_model,
                        prompt_tokens=len(result.split()),
                        phi_score=phi_score,
                        round=round_idx + 1,
                    )
                )

                if phi_score >= self.config.min_phi_threshold:
                    final_result = result
                    break

                if round_idx < self.config.max_refinement_rounds - 1:
                    current_prompt = (
                        f"{effective_prompt}\n\n"
                        f"PREVIOUS ATTEMPT: {result}\n\n"
                        f"CRITIQUE: Score was {phi_score:.2f} (Target: {self.config.min_phi_threshold}). "
                        "Please refine and deepen your response."
                    )
                else:
                    final_result = result

            except Exception as e:
                logger.error(f"Ollama call failed: {e}")
                self._metrics["errors"] += 1
                if round_idx == 0:
                    raise
                break
            finally:
                monitor.release_capacity()

        # Output filtering
        filter_result = await self._security.check_output(final_result)
        if filter_result.risk_score > 0.5:
            final_result = filter_result.content

        # Generate embedding
        try:
            if self._encoder is None:
                from cohezion.flume.autoencoder import FlumeConfig, FlumeEncoder

                self._encoder = FlumeEncoder(config=FlumeConfig())
            z = self._encoder.get_semantic_vector(final_result)
            embedding = z.tolist() if hasattr(z, "tolist") else list(z)
        except Exception:
            pass

        # Journey narration
        narration = self._narrator.generate_narration(
            agent_id, prompt[:100], final_result
        )
        await self._narrator.narrate(narration)

        # Cache result
        persistence_id = f"thought_{int(time.time() * 1000)}_{query_hash}"
        await self._cache.set(
            model=self.model_name,
            prompt=prompt,
            response=final_result,
            images=images,
            ttl_seconds=self.config.cache_ttl_seconds,
            embedding=embedding,
            persistence_id=persistence_id,
            phi_score=phi_score,
            confidence=confidence,
            alignment_score=alignment_score,
            narration=narration,
        )

        # Publish completion event
        latency = (time.perf_counter() - start_time) * 1000
        self._metrics["total_latency_ms"] += latency

        await self._event_bus.publish(
            Event.agent_complete(
                agent_name=agent_id,
                result=final_result[:200],  # Truncate for event size
                duration_ms=latency,
                phi_score=phi_score,
            )
        )

        return AgentResponse(
            final_result,
            embedding=embedding,
            persistence_id=persistence_id,
            frequency=freq,
            phi_score=phi_score,
            confidence=confidence,
            alignment_score=alignment_score,
            security_level="safe",
            narration=narration,
        )

    async def find_tools(self, query: str, top_k: int = 3) -> list:
        """Find relevant capabilities using unified registry."""
        await self._init_infrastructure()
        results = await self._registry.search(query, limit=top_k)
        return [cap for cap, _ in results]

    async def delegate_task(self, query: str, target_agent: str | None = None) -> Any:
        """Delegate task to peer agent with proper tracking."""
        await self._init_infrastructure()

        if not target_agent:
            matches = await self._registry.search(
                f"agent for {query}", limit=1, types=["agent"]
            )
            if not matches:
                logger.warning(f"No suitable agent found for: {query}")
                return None
            target_agent = matches[0][0].name

        logger.info(f"🤝 Delegating to {target_agent}: {query[:50]}...")

        try:
            await self._event_bus.publish(
                Event(
                    type=EventType.AGENT_START,
                    source=self.__class__.__name__,
                    payload={"action": "delegation", "target": target_agent},
                )
            )

            # Dynamic instantiation
            import importlib
            import re

            module_name = re.sub(r"(?<!^)(?=[A-Z])", "_", target_agent).lower()
            if module_name.endswith("_agent"):
                module_name = module_name.replace("_agent", "")

            try:
                module = importlib.import_module(f"cohezion.swarm.agents.{module_name}")
            except ImportError:
                module = importlib.import_module(
                    f"cohezion.swarm.agents.{module_name}_agent"
                )

            class_ = getattr(module, target_agent)
            peer = class_(config=self.config)

            # Execute with task tracking
            result = await peer.process(query)
            await peer.close()

            await self._event_bus.publish(
                Event(
                    type=EventType.AGENT_COMPLETE,
                    source=self.__class__.__name__,
                    payload={"action": "delegation_complete", "target": target_agent},
                )
            )

            return result

        except Exception as e:
            logger.error(f"Delegation failed: {e}")
            await self._event_bus.publish(
                Event(
                    type=EventType.AGENT_ERROR,
                    source=self.__class__.__name__,
                    payload={"action": "delegation_error", "error": str(e)},
                )
            )
            return None

    async def self_evaluate(
        self, response_text: str, query: str = "", metadata: dict | None = None
    ) -> tuple[float, float, dict]:
        """Evaluate response quality."""
        eval_model = "phi3:mini"
        phi, conf = 0.8, 0.8

        try:
            client = await self.client
            prompt = f"""Evaluate the response below.
1. Technical Accuracy (0.0-1.0)
2. Confidence & Certainty (0.0-1.0)

RESPONSE:
{response_text}

Output JSON: {{"phi_score": 0.85, "confidence": 0.90}}"""

            payload = {
                "model": eval_model,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.0},
            }
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            data = response.json().get("response", "{}")
            if isinstance(data, str):
                data = json.loads(data)
            phi = float(data.get("phi_score", 0.8))
            conf = float(data.get("confidence", 0.8))
        except Exception:
            pass

        audit_res = {
            "alignment_score": 1.0,
            "violations": [],
            "justification": "Audit skipped.",
        }
        if self.__class__.__name__ != "AlignmentAgent":
            try:
                from cohezion.swarm.agents.alignment_agent import AlignmentAgent

                auditor = AlignmentAgent(config=self.config)
                audit_res = await auditor.audit(query, response_text, metadata or {})
                await auditor.close()
            except Exception as e:
                logger.warning(f"Alignment audit failed: {e}")

        return phi, conf, audit_res

    @abstractmethod
    async def process(self, *args: Any, **kwargs: Any) -> Any:
        """Process input and return output. Implemented by subclasses."""
        pass

    def get_metrics(self) -> dict[str, Any]:
        """Return current metrics."""
        from cohezion.core.time_keeper import get_time_keeper

        total_calls = max(1, self._metrics["total_calls"])
        return {
            **self._metrics,
            "model": self.model_name,
            "cache_hit_rate": self._metrics["cache_hits"] / total_calls,
            "avg_latency_ms": self._metrics["total_latency_ms"] / total_calls,
            "timestamp": get_time_keeper().now_iso,
        }

    def _apply_local_routing(self, model_name: str) -> None:
        """Apply local routing policy."""
        config_path = Path("config/maintenance_config.json")
        if not config_path.exists():
            self.model_name = model_name
            return

        try:
            import json

            policy = json.loads(config_path.read_text())
            # Simplified - just use provided model for now
            self.model_name = model_name
        except Exception as e:
            logger.warning(f"Local routing failed: {e}")
            self.model_name = model_name

    async def _synchronize_mrp(self) -> None:
        """Execute Memory Recovery Protocol with task tracking."""
        await self._init_infrastructure()

        task_id = await self._task_manager.create_task(
            self._mrp_sync_impl(),
            name=f"mrp_sync_{self.__class__.__name__}",
        )
        logger.info(f"MRP sync scheduled: {task_id}")

    async def _mrp_sync_impl(self) -> None:
        """Actual MRP synchronization logic."""
        try:
            latest_pulse = await self._db.query(
                "SELECT * FROM mission_pulse ORDER BY timestamp DESC LIMIT 1"
            )
            if latest_pulse and isinstance(latest_pulse, list):
                data_list = (
                    latest_pulse[0].get("result", [])
                    if isinstance(latest_pulse[0], dict)
                    else latest_pulse
                )
                if data_list and len(data_list) > 0:
                    logger.info(f"MRP: Synced with pulse")

            # Start pulse loop as tracked task
            await self._task_manager.create_task(
                self._mrp_pulse_loop(),
                name=f"mrp_pulse_{self.__class__.__name__}",
            )
        except Exception as e:
            logger.error(f"MRP sync failed: {e}")

    async def _mrp_pulse_loop(self) -> None:
        """Background pulse loop (properly tracked)."""
        while True:
            await asyncio.sleep(self.config.mrp_pulse_interval_minutes * 60)
            try:
                from datetime import datetime

                pulse_payload = {
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat(),
                    "metrics": self.get_metrics(),
                }
                await self._db.create("mission_pulse", pulse_payload)
                logger.debug("MRP: Pulse emitted")
            except Exception as e:
                logger.error(f"MRP pulse failed: {e}")
