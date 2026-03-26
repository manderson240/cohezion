"""Task-type router for three-tier model delegation.

Routes tasks to the optimal provider (Anthropic, Ollama Cloud, Local Ollama)
based on task type, with budget gating and fallback cascading.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from cohezion.swarm.providers.model_provider import GenerationResult, ModelProvider


logger = logging.getLogger(__name__)


class ProviderTier(Enum):
    ANTHROPIC = "anthropic"
    OLLAMA_CLOUD = "ollama-cloud"
    LOCAL = "ollama"


@dataclass
class RouteEntry:
    """A single routing option: provider + model + cost metadata."""

    provider: ProviderTier
    model: str
    cost_per_1k_tokens: float  # USD, 0.0 for local
    quality_score: float  # 0.0-1.0
    max_tokens_default: int = 2048


# Task type → ordered list of routing options (primary first, fallbacks after)
ROUTING_TABLE: dict[str, list[RouteEntry]] = {
    "coding": [
        RouteEntry(ProviderTier.LOCAL, "qwen3-coder:30b", 0.0, 0.85, 2048),
        RouteEntry(ProviderTier.OLLAMA_CLOUD, "qwen3-coder:30b", 0.001, 0.85, 2048),
        RouteEntry(ProviderTier.ANTHROPIC, "claude-sonnet-4-20250514", 0.003, 0.95, 4096),
    ],
    "complex_reasoning": [
        RouteEntry(ProviderTier.ANTHROPIC, "claude-sonnet-4-20250514", 0.003, 0.95, 4096),
        RouteEntry(ProviderTier.ANTHROPIC, "claude-haiku-3.5-20241022", 0.001, 0.80, 4096),
        RouteEntry(ProviderTier.LOCAL, "phi4:latest", 0.0, 0.82, 2048),
    ],
    "creative": [
        RouteEntry(ProviderTier.LOCAL, "deepseek-r1:7b", 0.0, 0.75, 2048),
        RouteEntry(ProviderTier.OLLAMA_CLOUD, "deepseek-r1:7b", 0.001, 0.75, 2048),
        RouteEntry(ProviderTier.ANTHROPIC, "claude-sonnet-4-20250514", 0.003, 0.95, 4096),
    ],
    "embeddings": [
        RouteEntry(ProviderTier.LOCAL, "nomic-embed-text:latest", 0.0, 0.80, 8192),
        RouteEntry(ProviderTier.OLLAMA_CLOUD, "nomic-embed-text:latest", 0.0001, 0.80, 8192),
    ],
    "simple_qa": [
        RouteEntry(ProviderTier.LOCAL, "phi3:mini", 0.0, 0.60, 1024),
        RouteEntry(ProviderTier.ANTHROPIC, "claude-haiku-3.5-20241022", 0.001, 0.80, 2048),
    ],
    "analysis": [
        RouteEntry(ProviderTier.ANTHROPIC, "claude-sonnet-4-20250514", 0.003, 0.95, 4096),
        RouteEntry(ProviderTier.LOCAL, "phi4:latest", 0.0, 0.82, 2048),
        RouteEntry(ProviderTier.LOCAL, "qwen3-coder:30b", 0.0, 0.85, 2048),
    ],
    "synthesis": [
        RouteEntry(ProviderTier.ANTHROPIC, "claude-sonnet-4-20250514", 0.003, 0.95, 4096),
        RouteEntry(ProviderTier.LOCAL, "phi4:latest", 0.0, 0.82, 2048),
    ],
    "summary": [
        RouteEntry(ProviderTier.LOCAL, "phi3:mini", 0.0, 0.60, 1024),
        RouteEntry(ProviderTier.LOCAL, "gemma3:4b", 0.0, 0.65, 1024),
    ],
    "debate": [
        RouteEntry(ProviderTier.ANTHROPIC, "claude-sonnet-4-20250514", 0.003, 0.95, 8192),
        RouteEntry(ProviderTier.LOCAL, "phi4:latest", 0.0, 0.82, 4096),
    ],
}


@dataclass
class RoutingDecision:
    """Observable record of a routing decision."""

    timestamp: float
    task_type: str
    provider: str
    model: str
    success: bool
    latency_ms: float | None = None
    tokens_used: int | None = None
    estimated_cost_usd: float = 0.0
    error: str | None = None


class TaskTypeRouter:
    """Routes tasks to optimal provider based on task type.

    Decision flow per task:
    1. Look up routing table entries for the task type
    2. For each entry (primary → fallbacks):
       a. Check if provider is registered
       b. Budget gate: estimate cost, check enforcer
       c. Execute via provider.generate()
       d. Record cost and log decision
       e. On failure: cascade to next entry
    """

    def __init__(
        self,
        budget_enforcer: Any = None,
        cost_tracker: Any = None,
        routing_table: dict[str, list[RouteEntry]] | None = None,
    ):
        self._providers: dict[ProviderTier, ModelProvider] = {}
        self._budget_enforcer = budget_enforcer
        self._cost_tracker = cost_tracker
        self._routing_table = routing_table or ROUTING_TABLE
        self._routing_log: list[RoutingDecision] = []

    def register_provider(self, tier: ProviderTier, provider: ModelProvider) -> None:
        self._providers[tier] = provider
        logger.info("Registered provider tier: %s", tier.value)

    @property
    def routing_log(self) -> list[RoutingDecision]:
        return list(self._routing_log)

    async def route_and_execute(
        self,
        prompt: str,
        task_type: str,
        max_tokens: int | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> GenerationResult:
        entries = self._routing_table.get(task_type)
        if not entries:
            # Fall back to simple_qa for unknown task types
            entries = self._routing_table.get("simple_qa", [])
            logger.info("Unknown task_type '%s', falling back to simple_qa", task_type)

        errors: list[str] = []
        for entry in entries:
            provider = self._providers.get(entry.provider)
            if provider is None:
                logger.debug("Provider %s not registered, skipping", entry.provider.value)
                continue

            estimated_cost = self._estimate_cost(entry, prompt, max_tokens)
            if not self._check_budget(estimated_cost):
                msg = f"Budget blocked {entry.provider.value}/{entry.model} (${estimated_cost:.6f})"
                logger.info(msg)
                errors.append(msg)
                continue

            try:
                result = await provider.generate(
                    model=entry.model,
                    prompt=prompt,
                    max_tokens=max_tokens or entry.max_tokens_default,
                    temperature=temperature,
                    **kwargs,
                )
                self._record_cost(entry, result)
                self._log_decision(task_type, entry, result, success=True)
                return result

            except Exception as e:
                msg = f"{entry.provider.value}/{entry.model}: {e}"
                logger.warning("Provider failed: %s, cascading", msg)
                errors.append(msg)
                self._log_decision(task_type, entry, None, success=False, error=str(e))

        raise RuntimeError(
            f"All providers exhausted for task_type='{task_type}'. Errors: {'; '.join(errors)}"
        )

    def _estimate_cost(self, entry: RouteEntry, prompt: str, max_tokens: int | None) -> float:
        if entry.cost_per_1k_tokens == 0.0:
            return 0.0
        input_tokens = len(prompt) // 4
        output_tokens = max_tokens or entry.max_tokens_default
        return ((input_tokens + output_tokens) / 1000.0) * entry.cost_per_1k_tokens

    def _check_budget(self, estimated_cost: float) -> bool:
        if estimated_cost == 0.0:
            return True
        if self._budget_enforcer is None:
            return True
        try:
            can_proceed, _reason = self._budget_enforcer.check_budget(estimated_cost)
            return can_proceed
        except Exception:
            logger.debug("Budget check failed, allowing request")
            return True

    def _record_cost(self, entry: RouteEntry, result: GenerationResult) -> None:
        if self._cost_tracker is None or entry.cost_per_1k_tokens == 0.0:
            return
        try:
            self._cost_tracker.track_usage_fast(
                model=f"{entry.provider.value}/{entry.model}",
                tokens=result.tokens_used,
                duration_ms=result.latency_ms,
            )
        except Exception:
            logger.debug("Cost tracking failed, continuing")

    def _log_decision(
        self,
        task_type: str,
        entry: RouteEntry,
        result: GenerationResult | None,
        success: bool,
        error: str | None = None,
    ) -> None:
        decision = RoutingDecision(
            timestamp=time.time(),
            task_type=task_type,
            provider=entry.provider.value,
            model=entry.model,
            success=success,
            latency_ms=result.latency_ms if result else None,
            tokens_used=result.tokens_used if result else None,
            estimated_cost_usd=entry.cost_per_1k_tokens,
            error=error,
        )
        self._routing_log.append(decision)
        if success:
            logger.info(
                "Routed %s → %s/%s (%.0fms, %d tokens)",
                task_type,
                entry.provider.value,
                entry.model,
                result.latency_ms if result else 0,
                result.tokens_used if result else 0,
            )

    def get_routing_stats(self) -> dict[str, Any]:
        """Summary of routing decisions for observability."""
        if not self._routing_log:
            return {"total": 0}
        by_provider: dict[str, int] = {}
        by_task: dict[str, int] = {}
        successes = 0
        for d in self._routing_log:
            if d.success:
                successes += 1
                by_provider[d.provider] = by_provider.get(d.provider, 0) + 1
                by_task[d.task_type] = by_task.get(d.task_type, 0) + 1
        return {
            "total": len(self._routing_log),
            "successes": successes,
            "failures": len(self._routing_log) - successes,
            "by_provider": by_provider,
            "by_task_type": by_task,
        }
