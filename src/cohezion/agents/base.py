"""Base agent class for all SLM Swarm agents."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.flume.autoencoder import FlumeEncoder
    from cohezion.swarm.swarm_types import SwarmConfig

import httpx

from cohezion.compound.exp_persistence.accumulator import get_accumulator
from cohezion.core.compound.engine import CompoundLogicEngine
from cohezion.core.credit_manager import get_credit_manager
from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.core.time_keeper import get_time_keeper
from cohezion.reliability import get_circuit
from cohezion.reliability.batch_manager import BatchManager
from cohezion.reliability.context_harness import ContextHarness
from cohezion.reliability.monitor import get_resource_monitor
from cohezion.reliability.offload_manager import OffloadManager
from cohezion.reliability.pool import get_pool
from cohezion.reliability.semantic_cache import SemanticCache
from cohezion.rewards.system import RewardSystem
from cohezion.security.output_filter import OutputFilter
from cohezion.security.prompt_guard import PromptGuard, ThreatLevel
from cohezion.universe.engine import UniverseSimulationEngine


logger = logging.getLogger(__name__)


class AgentResponse(str):
    """
    Enhanced string response with native agentic metadata.
    """

    def __new__(cls, content, **kwargs):
        obj = super().__new__(cls, content)
        for key, value in kwargs.items():
            setattr(obj, key, value)
        return obj

    def __getattr__(self, name):
        return None


class BaseAgent(ABC):
    """
    Abstract base class for Swarm agents.

    Provides common functionality:
    - Ollama HTTP client management
    - Response caching with LRU eviction
    - Timeout handling and retries
    - Logging and metrics
    """

    def __init__(
        self,
        model_name: str,
        config: SwarmConfig | None = None,
        cache_dir: Path | None = None,
    ):
        from cohezion.registry.capability_registry import CapabilityRegistry
        from cohezion.swarm.journey_narrator import JourneyNarrator
        from cohezion.swarm.redundancy_suppression import RedundancyManager
        from cohezion.swarm.swarm_types import SwarmConfig

        self.registry = CapabilityRegistry()  # Auto-discovery enabled
        self.model_name = model_name
        self._apply_local_routing(model_name)
        self.config = config or SwarmConfig()
        self.priority = self.config.priority
        self.cache_dir = cache_dir or Path("cache/swarm")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._client: httpx.AsyncClient | None = None
        self._metrics: dict[str, Any] = {
            "total_calls": 0,
            "cache_hits": 0,
            "total_latency_ms": 0,
            "errors": 0,
        }

        # Native Intelligence & Persistence
        self._encoder: FlumeEncoder | None = None
        self._db: SurrealClient = SurrealClient()
        self._query_history: dict[str, int] = {}  # query_hash -> count
        self._credit_manager = get_credit_manager()

        # Phase 4: Adversarial Robustness
        self._security_guard = PromptGuard(strict_mode=self.config.strict_security)
        self._output_filter = OutputFilter(redact_pii=True)

        # Gateway 32: Redundancy Suppression
        self._redundancy_mgr = RedundancyManager(agent_name=self.__class__.__name__)

        # Gateway 32: Journey Narration
        self._narrator = JourneyNarrator()

        # Universe Simulation Engine - 12D/512D manifold tracking
        self._universe = UniverseSimulationEngine()
        self._current_journey = None

        # Reward System - XP, achievements, streaks
        self._rewards = RewardSystem()

        # Gateway 44: Local Offload & Context Harness
        self._offload_mgr = OffloadManager()
        self._harness = ContextHarness()
        self._batch_mgr = BatchManager()
        self._semantic_cache = SemanticCache(
            cache_dir=str(self.cache_dir / "semantic"),
            threshold=self.config.semantic_cache_threshold,
        )

        # Gateway 12: Memory Recovery Protocol (MRP)
        self._compound_engine = CompoundLogicEngine(registry=self.registry)
        self._background_tasks: set[asyncio.Task] = set()
        if self.config.mrp_sync:
            _task = asyncio.create_task(self._synchronize_mrp())
            self._background_tasks.add(_task)
            _task.add_done_callback(self._background_tasks.discard)

    @property
    def client(self) -> Any:
        """Get the shared connection pool for Ollama."""
        return get_pool(
            name="ollama",
            base_url=self.config.ollama_base_url,
            timeout=300.0,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _cache_key(self, prompt: str, images: list[str] | None = None) -> str:
        """Generate a stable cache key."""
        content = f"{self.model_name}:{prompt}"
        if images:
            content += ":" + ":".join(images[:3])  # Use first 3 images for keying
        return hashlib.sha256(content.encode()).hexdigest()

    async def _get_cached(
        self, prompt: str, images: list[str] | None = None
    ) -> dict[str, Any] | None:
        """Retrieve a cached response if available and not expired."""
        key = self._cache_key(prompt, images)
        cache_file = self.cache_dir / f"{key}.json"

        if not cache_file.exists():
            pass

        try:
            data = json.loads(cache_file.read_text())
            age = time.time() - data.get("timestamp", 0)
            if age < self.config.cache_ttl_seconds:
                return data
        except Exception as e:
            logger.debug("Cache read failed for %s: %s", cache_file, e)

        # Phase 4: Semantic Fallback
        if not images and self._encoder:
            # Only semantic search for text-only prompts
            query_vec = self._encoder.encode(prompt)
            if hasattr(query_vec, "cpu"):
                query_vec = query_vec.cpu().numpy()
            semantic_hit = await self._semantic_cache.search(query_vec, query_text=prompt)
            if semantic_hit:
                logger.info(f"✨ Semantic Cache Hit (score: {semantic_hit['semantic_score']:.2f})")
                self._metrics["cache_hits"] += 1
                return semantic_hit

        return None

    async def _set_cached(
        self,
        prompt: str,
        response: str,
        embedding: list[float] | None = None,
        persistence_id: str | None = None,
        phi_score: float = 0.0,
        confidence: float = 1.0,
        alignment_score: float = 1.0,
        images: list[str] | None = None,
        narration: str | None = None,
    ) -> None:
        """Cache a response with its intelligence metadata."""
        key = self._cache_key(prompt, images)
        cache_file = self.cache_dir / f"{key}.json"

        data = {
            "model": self.model_name,
            "prompt": prompt[:500],
            "response": response,
            "embedding": embedding.tolist() if hasattr(embedding, "tolist") else embedding,
            "persistence_id": persistence_id,
            "phi_score": phi_score,
            "confidence": confidence,
            "alignment_score": alignment_score,
            "narration": narration,
            "images_hash": hashlib.sha256(":".join(images).encode()).hexdigest()
            if images
            else None,
            "timestamp": time.time(),
        }
        cache_file.write_text(json.dumps(data, ensure_ascii=False))

        # Phase 4: Semantic Projection (only for text-only)
        if not images and self._encoder:
            query_vec = self._encoder.encode(prompt)
            if hasattr(query_vec, "cpu"):
                query_vec = query_vec.cpu().numpy()
            await self._semantic_cache.add(
                vector=query_vec,
                response=response,
                metadata={
                    "prompt": prompt[:500],
                    "phi_score": phi_score,
                    "confidence": confidence,
                    "agent": self.__class__.__name__,
                },
                query_text=prompt,
            )

    async def enqueue_batch_task(self, query: str, context: str | None = None) -> str:
        """Enqueue a task for later batch processing."""
        # Security: Use UUID instead of MD5 for task identifiers
        # MD5 is cryptographically weak and should not be used even for non-security identifiers
        task_id = uuid.uuid4().hex[:8]
        self._batch_mgr.enqueue(task_id, query, context)
        logger.info(f"📥 Task {task_id} enqueued for batch processing.")
        return task_id

    async def _compound_discovery(self, query: str) -> None:
        """
        Discover existing capabilities that can accelerate the current task.
        """
        compounds = self._compound_engine.analyze_task_for_compounding(query)
        if compounds:
            # Inject compound wisdom into the narrator or logs
            summary = ", ".join([f"{c['name']} ({len(c['hooks'])} hooks)" for c in compounds])
            logger.info(f"🧩 [COMPOUND] Leveraging existing patterns: {summary}")
            # Potentially update system prompt for the next call
            self._compound_wisdom = compounds
        else:
            self._compound_wisdom = []

    async def process_batch(self, model: str | None = None) -> dict[str, str]:
        """Process all enqueued tasks in a single local SLM call."""
        batch = self._batch_mgr.get_batch()
        if not batch:
            return {}

        logger.info(f"🚀 Processing batch of {batch['count']} tasks...")

        # Apply Context Harness to the consolidated prompt
        harness = ContextHarness(target_model=model or self.model_name)
        payload = harness.harness_prompt(batch["prompt"])

        # Call Ollama (ignore cache for batches as they are dynamic)
        response = await self._call_ollama(
            prompt=payload["prompt"],
            system_prompt=payload["system"],
            model=model or self.model_name,
            ignore_cache=True,
        )

        # Parse results
        results = self._batch_mgr.parse_batch_response(str(response))
        logger.info(
            f"✅ Batch processing complete. {len(results)}/{batch['count']} results parsed."
        )

        return results

    async def _call_ollama(
        self,
        prompt: str,
        temperature: float = 0.7,
        images: list[str] | None = None,
        max_tokens: int = 2048,
        system_prompt: str | None = None,
        ignore_cache: bool = False,
        model: str | None = None,
        task_type: str | None = None,
    ) -> AgentResponse:
        """
        Call local Ollama instance with optional image support and manifold projection.
        """
        start_time = time.perf_counter()
        tk = get_time_keeper()

        # 0. Compound Discovery (The Reckoning)
        if hasattr(self, "_compound_engine"):
            await self._compound_discovery(prompt)

        # 0. Check Frequency, Redundancy, & Cache
        req_hash_content = f"{self.model_name}:{prompt}"
        if images:
            req_hash_content += ":" + ":".join(images[:3])
        query_hash = hashlib.sha256(req_hash_content.encode()).hexdigest()[:12]

        # Gateway 32: Autonomic Redundancy Suppression
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

        if freq >= 5 and suppression_level == 0:  # Legacy check as fallback
            logger.warning(f"Task repeated {freq} times! Flagged for Skill Extraction.")
            await tk.log_event(
                agent_name=self.__class__.__name__,
                event_type="REPETITIVE_TASK_DETECTED",
                details={"query_hash": query_hash, "count": freq},
            )

        # Check cache first
        cached_data = await self._get_cached(prompt, images) if not ignore_cache else None
        if cached_data:
            # Log cache hit event
            await tk.log_event(
                agent_name=self.__class__.__name__,
                event_type="CACHE_HIT",
                details={"model": self.model_name},
                duration_ms=0,
            )
            # Return enriched response from cache
            return AgentResponse(
                cached_data["response"],
                embedding=cached_data["embedding"],
                persistence_id=cached_data["persistence_id"],
                frequency=freq,
                phi_score=cached_data.get("phi_score", 0.0),
                confidence=cached_data.get("confidence", 1.0),
                alignment_score=cached_data.get("alignment_score", 1.0),
                security_level="safe",  # Cached responses are assumed safe
                narration=cached_data.get("narration"),
            )

        # 1. Input Security Check (LLM01, LLM07)
        security_analysis = self._security_guard.analyze(prompt)
        if security_analysis.threat_level == ThreatLevel.MALICIOUS:
            logger.error(
                f"⚠️ SECURITY BLOCK: Malicious input detected: {security_analysis.matched_patterns}"
            )
            await tk.log_event(
                agent_name=self.__class__.__name__,
                event_type="SECURITY_BLOCK",
                details={
                    "patterns": security_analysis.matched_patterns,
                    "input": prompt[:100],
                },
            )
            return AgentResponse(
                f"[Blocked] Malicious input detected: {security_analysis.matched_patterns}",
                security_level="malicious",
            )

        # Phase 5: Token Economics check
        agent_id = self.__class__.__name__
        active_model = model or self.model_name

        if not self._credit_manager.can_afford(agent_id, active_model):
            active_model = self._credit_manager.get_best_affordable_model(agent_id, active_model)
            logger.warning(
                f"Agent {agent_id} cannot afford {self.model_name}. Downgraded to {active_model}."
            )

        self._metrics["total_calls"] += 1
        monitor = get_resource_monitor()

        # Phase 9: Degraded Mode prompt pruning
        effective_system = system_prompt
        if self.config.degraded_mode:
            # Simple heuristic: truncate to 1024 chars to save SLM resources
            current_prompt = prompt[:1024]
            if system_prompt:
                effective_system = system_prompt[:512]
            logger.info("Degraded mode active: Pruning prompts for efficiency.")
        else:
            current_prompt = effective_prompt

        final_result = ""
        embedding = None
        phi_score, confidence, alignment_score = 0.5, 0.5, 1.0

        # --- AUTONOMIC REFINEMENT LOOP (Gateway 11 & Law of Recurrence) ---
        for round_idx in range(self.config.max_refinement_rounds):
            # Proactive resource preparation for priority tasks
            if monitor.resource_coordinator:
                await monitor.resource_coordinator.prepare_resources_for_priority(self.priority)

            await monitor.wait_for_capacity()
            call_start = time.perf_counter()
            try:
                # Use Ascended Local Router if pointing to a known local model
                from cohezion.core.routing.router import LOCAL_ROUTER

                # Dynamic task detection if not specified
                effective_task_type = task_type
                if not effective_task_type:
                    effective_task_type = "general"
                    if current_prompt:
                        if "def " in current_prompt or "class " in current_prompt:
                            effective_task_type = "coding"
                        elif "reason" in current_prompt.lower() or "why" in current_prompt.lower():
                            effective_task_type = "reasoning"

                result = await LOCAL_ROUTER.route_task(
                    task_type=effective_task_type,
                    prompt=current_prompt or "",
                    context={
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        },
                        "system": effective_system,
                    },
                )

                # Evaluation (Phi-Score & Alignment)
                phi_score, confidence, audit_res = await self.self_evaluate(
                    result,
                    query=prompt,
                    metadata={
                        "agent": self.__class__.__name__,
                        "model": active_model,
                        "round": round_idx,
                    },
                )
                alignment_score = audit_res.get("alignment_score", 1.0)

                # Log successful LLM call
                await tk.log_event(
                    agent_name=self.__class__.__name__,
                    event_type="LLM_CALL",
                    details={
                        "model": active_model,
                        "tokens": len(result.split()),
                        "phi": phi_score,
                        "round": round_idx + 1,
                    },
                    duration_ms=(time.perf_counter() - call_start) * 1000,
                )

                # Check for stability well breakthrough
                if phi_score >= self.config.min_phi_threshold:
                    final_result = result
                    logger.info(
                        f"✨ Stability Well reached in round {round_idx + 1} (Phi: {phi_score:.2f})"
                    )
                    break

                # Prepare refinement or exit
                if round_idx < self.config.max_refinement_rounds - 1:
                    logger.info(
                        f"🔄 Low coherence ({phi_score:.2f}). Triggering refinement round "
                        f"{round_idx + 2}..."
                    )
                    current_prompt = (
                        f"{effective_prompt}\n\n"
                        f"PREVIOUS ATTEMPT: {result}\n\n"
                        f"CRITIQUE: The previous output score was {phi_score:.2f}"
                        f" (Target: {self.config.min_phi_threshold}). "
                        "Please refine and deepen your response specifically"
                        " addressing any missing technical logic or ethical"
                        " nuance."
                    )
                else:
                    final_result = result
            except Exception as e:
                logger.error(f"Ollama call failed in round {round_idx + 1}: {e}")
                get_circuit("ollama").record_failure()
                self._metrics["errors"] += 1
                await tk.log_event(
                    agent_name=self.__class__.__name__,
                    event_type="LLM_ERROR",
                    details={"error": str(e), "round": round_idx + 1},
                    duration_ms=(time.perf_counter() - call_start) * 1000,
                )
                if round_idx == 0:
                    raise
                break
            finally:
                monitor.release_capacity()

        # Final Post-Processing
        final_result = self._output_filter.filter(final_result).content

        # 2. FLUME Encoding
        try:
            if self._encoder is None:
                from cohezion.flume.autoencoder import FlumeConfig, FlumeEncoder

                self._encoder = FlumeEncoder(config=FlumeConfig())
            z = self._encoder.get_semantic_vector(final_result)
            embedding = z.tolist() if hasattr(z, "tolist") else list(z)
        except (ImportError, RuntimeError, OSError) as e:
            logger.debug(f"FLUME encoding unavailable, skipping: {e}")

        # 2.5 Journey Narration
        narration = self._narrator.generate_narration(
            self.__class__.__name__, prompt[:100], final_result
        )
        await self._narrator.narrate(narration)

        # Persistence & Cache
        persistence_id = f"thought_{int(time.time() * 1000)}_{query_hash}"
        await self._set_cached(
            prompt,
            final_result,
            embedding=embedding,
            persistence_id=persistence_id,
            phi_score=phi_score,
            confidence=confidence,
            alignment_score=alignment_score,
            images=images,
            narration=narration,
        )

        # Autonomic Experience Persistence
        try:
            accumulator = get_accumulator()

            # Refined Novelty Score (Threshold-based importance sampling)
            novelty = 1.0
            if embedding and self._db:
                try:
                    similar_nodes = await self._db.query_similar(embedding, limit=1)
                    if similar_nodes:
                        similarity = similar_nodes[0].get("score", 0.0)
                        novelty = max(0.01, 1.0 - similarity)
                except Exception as e:
                    logger.debug(f"Novelty detection failed, defaulting to 1.0: {e}")

            experience_data = {
                "mission_id": persistence_id,
                "agent": self.__class__.__name__,
                "model": active_model,
                "prompt": prompt,
                "response": final_result,
                "phi_score": phi_score,
                "confidence": confidence,
                "embedding": embedding,
                "timestamp": time.time(),
                "novelty": novelty,
                "decisions": [],
            }
            _task = asyncio.create_task(accumulator.add_experience(experience_data))
            self._background_tasks.add(_task)
            _task.add_done_callback(self._background_tasks.discard)
        except Exception as e:
            logger.warning(f"Persistence hook failed: {e}")

        latency = (time.perf_counter() - start_time) * 1000
        self._metrics["total_latency_ms"] += latency

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

    async def delegate_task(self, query: str, target_agent: str | None = None) -> Any:
        """
        Delegate a task to a peer agent within the swarm.

        Args:
            query: The task/query to delegate
            target_agent: Optional name/type of agent to target.
                         If None, uses registry for discovery.
        """
        from cohezion.core.time_keeper import get_time_keeper

        tk = get_time_keeper()

        # 1. Discovery
        if not target_agent:
            matches = self.registry.find(f"agent for {query}", top_k=1)
            if not matches or matches[0].type != "agent":
                logger.warning(f"No suitable peer agent found for: {query}")
                return None
            target_agent = matches[0].name

        logger.info(f"🤝 Delegating task to {target_agent}: {query[:50]}...")

        # 2. Dynamic Instantiation (Safe approach via registry path)
        try:
            # We assume agent classes are available in the registry
            # For now, we'll use a simple name-to-class mapping or dynamic import
            # CamelCase to snake_case for module name
            module_name = re.sub(r"(?<!^)(?=[A-Z])", "_", target_agent).lower()
            if module_name.endswith("_agent"):
                module_name = module_name.replace("_agent", "")

            import importlib

            # Try with and without _agent suffix in filename
            try:
                module = importlib.import_module(f"cohezion.agents.{module_name}")
            except ImportError:
                module = importlib.import_module(f"cohezion.agents.{module_name}_agent")
            class_ = getattr(module, target_agent)
            peer = class_(config=self.config)

            # 3. Execution
            await tk.log_event(
                agent_name=self.__class__.__name__,
                event_type="DELEGATION_START",
                details={"target": target_agent, "query": query},
            )

            result = await peer.process(query)

            await tk.log_event(
                agent_name=self.__class__.__name__,
                event_type="DELEGATION_COMPLETE",
                details={"target": target_agent},
            )

            return result

        except Exception as e:
            logger.error(f"Delegation to {target_agent} failed: {e}")
            await tk.log_event(
                agent_name=self.__class__.__name__,
                event_type="DELEGATION_ERROR",
                details={"target": target_agent, "error": str(e)},
            )
            return None

    async def offload_to_local(self, query: str, system_prompt: str | None = None) -> AgentResponse:
        """
        Offload a menial task to a local SLM with a context harness.
        """
        recommendation = self._offload_mgr.get_offload_recommendation(query)

        if not recommendation["offload"]:
            logger.info(f"Task unsuitable for offload: {query[:50]}")
            return await self.process(query)  # Fallback to main process

        target_model = recommendation["target"]
        logger.info(f"🚀 Offloading menial task to {target_model}: {query[:50]}")

        # Apply Context Harness
        harness = ContextHarness(target_model=target_model)
        payload = harness.harness_prompt(query, system_prompt)

        # Execute with Ollama directly
        return await self._call_ollama(
            prompt=payload["prompt"],
            system_prompt=payload["system"],
            model=target_model,
            ignore_cache=True,  # Usually offloads are unique/maintenance
        )

    async def self_evaluate(
        self, response_text: str, query: str = "", metadata: dict | None = None
    ) -> tuple[float, float, dict]:
        """
        Evaluate a response against the SELF_EVALUATION_PRIME rubric and alignment auditor.

        Returns:
            (phi_score, confidence, alignment_audit): Metrics (0.0 - 1.0) and audit dict
        """
        eval_model = "phi3:mini"

        # 1. Quality Evaluation
        prompt = f"""Evaluate the agent response below.
1. Technical Accuracy (0.0-1.0)
2. Confidence & Certainty (0.0-1.0)

RESPONSE:
{response_text}

Provide output in JSON format: {{"phi_score": 0.85, "confidence": 0.90}}
"""
        import json

        phi, conf = 0.8, 0.8
        try:
            payload = {
                "model": eval_model,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.0},
            }
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()
            data = response.json().get("response", "{}")
            if isinstance(data, str):
                data = json.loads(data)
            phi = float(data.get("phi_score", 0.8))
            conf = float(data.get("confidence", 0.8))
        except (httpx.HTTPError, json.JSONDecodeError, ValueError, KeyError) as e:
            logger.debug(f"Self-evaluation call failed, using defaults: {e}")

        # 2. Alignment Audit (Phase 22)
        audit_res = {
            "alignment_score": 1.0,
            "violations": [],
            "justification": "Audit skipped.",
        }
        if self.__class__.__name__ != "AlignmentAgent":
            try:
                from cohezion.agents.alignment_agent import AlignmentAgent

                auditor = AlignmentAgent(config=self.config)
                audit_res = await auditor.audit(query, response_text, metadata or {})
                await auditor.close()
            except Exception as e:
                logger.warning(f"Alignment audit failed: {e}")

        return phi, conf, audit_res

    @abstractmethod
    async def process(self, *args: Any, **kwargs: Any) -> Any:
        """Process input and return output. Implemented by subclasses."""

    def get_metrics(self) -> dict[str, Any]:
        """Return current metrics."""
        from cohezion.core.time_keeper import get_time_keeper

        return {
            **self._metrics,
            "model": self.model_name,
            "cache_hit_rate": (self._metrics["cache_hits"] / max(1, self._metrics["total_calls"])),
            "avg_latency_ms": (
                self._metrics["total_latency_ms"] / max(1, self._metrics["total_calls"])
            ),
            "timestamp": get_time_keeper().now_iso,
        }

    def _apply_local_routing(self, model_name: str) -> None:
        """Apply local routing policy if agent has maintenance capabilities."""
        config_path = Path("config/maintenance_config.json")
        if not config_path.exists():
            self.model_name = model_name
            return

        try:
            import json

            policy = json.loads(config_path.read_text())

            # Check if agent has maintenance capabilities
            agent_caps = self.registry.get_capabilities(self.__class__.__name__)
            is_maintenance = any(
                cap in policy.get("maintenance_capabilities", []) for cap in agent_caps
            )

            if is_maintenance and policy.get("policy") == "local_first":
                # Route to local model
                self.model_name = policy.get("default_local_model", "qwen3-coder:32b")
                logger.info(
                    f"🛡️ Local Routing: Agent {self.__class__.__name__} routed to {self.model_name}"
                )
            else:
                self.model_name = model_name
        except Exception as e:
            logger.warning(f"Local routing failed for {self.__class__.__name__}: {e}")
            self.model_name = model_name

    async def _synchronize_mrp(self) -> None:
        """
        Execute the Memory Recovery Protocol (MRP).

        1. Read Knowledge Graph (Learnings, Retrospectives)
        2. Query SurrealDB for latest Mission Pulse
        3. Hydrate state vector
        4. Start background pulse task
        """
        logger.info(f"Agent {self.__class__.__name__} initiating MRP Wake-Up...")

        try:
            # Step 1: Query SurrealDB for the latest SESSION_SNAPSHOT or MISSION_PULSE
            latest_pulse = await self._db.query(
                "SELECT * FROM mission_pulse ORDER BY timestamp DESC LIMIT 1"
            )

            # Check if query returned valid results
            if not latest_pulse or len(latest_pulse) == 0:
                latest_pulse = None

            if latest_pulse:
                pulse_data = latest_pulse[0]
                logger.info(
                    f"MRP: Reached consensus with latest pulse from {pulse_data.get('timestamp')}"
                )

            # Phase 6: Experience Replay (Semantic Memory Recovery)
            experience = await self._universe.get_experience_replay(self.__class__.__name__)
            if experience:
                logger.info(f"✨ MRP: Experience Replay recovered for {self.__class__.__name__}")
                # Store in internal memory for prompt injection
                self._metrics["mrp_hydrated"] = True
                self._mrp_experience = experience

            # Start the background pulse task
            _task = asyncio.create_task(self._mrp_pulse_loop())
            self._background_tasks.add(_task)
            _task.add_done_callback(self._background_tasks.discard)

        except Exception as e:
            logger.error(f"MRP Synchronization failed: {e}")

    async def _mrp_pulse_loop(self) -> None:
        """Background task to periodically send MISSION_PULSE to SurrealDB."""
        while True:
            await asyncio.sleep(self.config.mrp_pulse_interval_minutes * 60)
            try:
                from datetime import datetime

                pulse_payload = {
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat(),
                    "metrics": self.get_metrics(),
                }
                await self._db.store_node("mission_pulse", pulse_payload)
                logger.debug("MRP: MISSION_PULSE emitted.")
            except Exception as e:
                logger.error(f"MRP Pulse failed: {e}")

    async def _execute_with_universe_tracking(self, query: str, process_func: callable) -> Any:
        """Execute agent process with universe journey tracking and reward system.

        This method wraps the actual processing to provide:
        - 12D/512D manifold tracking via Universe Simulation Engine
        - XP awarding and achievement unlocking via Reward System
        - Knowledge extraction for future learning
        """
        agent_name = self.__class__.__name__

        try:
            # 1. Start Universe Journey
            self._current_journey = await self._universe.start_journey(
                agent_name=agent_name, intent=query
            )

            # 2. Execute actual processing
            result = await process_func(query)

            # 3. Extract phi_score from result
            phi_score = getattr(result, "phi_score", 0.5) if result else 0.5

            # 4. Evolve trajectory with LLM call result
            await self._universe.evolve_trajectory(
                journey=self._current_journey,
                action="llm_call_completed",
                result=str(result)[:200] if result else "No result",
                phi_score=phi_score,
            )

            # 5. Award XP based on quality
            base_xp = 25
            quality_bonus = int((phi_score - 0.5) * 100)  # 0-50 bonus
            total_xp = max(0, base_xp + quality_bonus)

            self._rewards.award_xp(
                agent_id=agent_name,
                amount=total_xp,
                reason=f"Task completed with phi={phi_score:.2f}",
                context={"query": query[:100], "phi": phi_score},
            )

            # 6. Check and unlock achievements
            if phi_score >= 0.8:
                self._rewards.unlock_achievement(agent_id=agent_name, badge_id="phi_80")
            if phi_score >= 0.95:
                self._rewards.unlock_achievement(agent_id=agent_name, badge_id="phi_95")

            # 7. Precipitate reality - manifest results
            await self._universe.precipitate_reality(
                journey=self._current_journey,
                outputs={"response": str(result) if result else {}},
                phi_score=phi_score,
            )

            return result

        except Exception as e:
            # Log failure to universe
            if self._current_journey:
                await self._universe.evolve_trajectory(
                    journey=self._current_journey,
                    action="error",
                    result=str(e)[:200],
                    phi_score=0.0,
                )
            raise
