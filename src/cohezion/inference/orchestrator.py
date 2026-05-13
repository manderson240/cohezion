"""Tiered orchestrator — smarter models orchestrate less-smart models.

Abstracts Claude Code's ``/advisor`` pattern (a secondary, smarter model
silently advises a primary) and applies it across the whole Cohezion fleet:

    Tier 0   — fast/cheap primary    (e.g. Gemma-4-E2B on NPU)
    Tier 1   — midsize reasoner     (e.g. Gemma-4-26B-A4B on iGPU)
    Tier 2   — first cloud fallback  (e.g. Haiku via headless CLI)
    Tier 3+  — reviewer / arbiter    (Sonnet, Opus)

A tier runs only if the tier below it fails its **QualityGate**. Every
escalation is logged; total cost is bounded by ``max_cost_usd``. Each tier
can itself be another ``TieredOrchestrator`` — so agents can have sub-agents
which can have sub-sub-agents.

See ``docs/vmodel/PHASE6_ORCHESTRATOR_PLAN.md`` for invariants (O1–O8).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from cohezion.inference.fleet import RouteResult, route
from cohezion.inference.registry import Task


logger = logging.getLogger(__name__)


@dataclass
class QualityGate:
    """Deterministic pass/fail rule for a tier's output.

    - ``min_chars`` — accept if ``len(result.text) >= min_chars``.
    - ``require_nonempty`` — accept if ``result.text.strip() != ""``.
    - ``TRUST`` — always pass (terminal tier).
    """

    min_chars: int | None = None
    require_nonempty: bool = True

    def check(self, result: RouteResult) -> tuple[bool, str]:
        if result.error:
            return False, f"error={result.error}"
        if self.require_nonempty and not result.text.strip():
            return False, "empty response"
        if self.min_chars is not None and len(result.text) < self.min_chars:
            return False, f"too short ({len(result.text)} < {self.min_chars})"
        return True, "ok"


# Sentinel — always passes. Use for the terminal tier.
QualityGate.TRUST = QualityGate(min_chars=None, require_nonempty=False)  # type: ignore[attr-defined]


@dataclass
class TierAttempt:
    """Log entry for one tier invocation."""

    tier_index: int
    model_or_sub: str
    passed: bool
    reason: str
    cost_usd: float
    latency_ms: float
    ttft_ms: float | None


@dataclass
class OrchestrationResult:
    """Outcome of ``TieredOrchestrator.run()``.

    Always returned — even on exhausted failure, ``error`` is populated but
    the caller gets a structured object to inspect, per invariant O7.
    """

    text: str
    primary_model: str
    final_model: str
    escalation_count: int
    tier_path: list[TierAttempt] = field(default_factory=list)
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    ttft_ms: float | None = None
    error: str | None = None


@runtime_checkable
class Runnable(Protocol):
    """A tier target — either a model_id string or a nested orchestrator."""

    async def run(self, prompt: str, **kwargs) -> OrchestrationResult: ...


TierEntry = tuple[str | Runnable, QualityGate]


class TieredOrchestrator:
    """Smarter models orchestrate less-smart models.

    Tiers are ordered by priority: index 0 runs first, higher indices only
    run if the previous tier fails its gate. Invariants O1–O8 enforced.
    """

    def __init__(
        self,
        tiers: list[TierEntry],
        *,
        max_cost_usd: float | None = None,
        task: Task | str | None = None,
        max_tokens: int = 600,
        stream: bool = True,
        pre_dispatch_classifier: object | None = None,
    ) -> None:
        if not tiers:
            raise ValueError("TieredOrchestrator requires at least one tier")
        self.tiers = tiers
        self.max_cost_usd = max_cost_usd
        self.task = task
        self.max_tokens = max_tokens
        self.stream = stream
        # Optional callable: (prompt: str) -> RouteDecision
        # Sets start_tier_index and per-tier gate override based on output_type.
        self._pre_dispatch_classifier = pre_dispatch_classifier

    async def _invoke_tier(
        self,
        target: str | Runnable,
        prompt: str,
        remaining_budget: float | None,
    ) -> tuple[RouteResult | OrchestrationResult, float, float | None]:
        """Dispatch a single tier target; return (result, cost, ttft_ms)."""
        if isinstance(target, str):
            r = await route(
                prompt,
                task=self.task,
                prefer=target,
                budget_usd=remaining_budget,
                stream=self.stream,
                max_tokens=self.max_tokens,
            )
            return r, r.cost_usd, r.ttft_ms
        # Nested orchestrator (O4: composable recursion). O3b: the parent's
        # remaining budget overrides the nested orchestrator's own
        # ``max_cost_usd`` ceiling so a sub-orchestrator cannot overspend
        # its caller's envelope.
        sub = await target.run(prompt, budget_usd=remaining_budget)
        return sub, sub.cost_usd, sub.ttft_ms

    async def run(self, prompt: str, *, budget_usd: float | None = None) -> OrchestrationResult:
        """Execute tier 0, escalate while gates fail, honor budget.

        ``budget_usd`` is the caller's (usually the parent orchestrator's)
        remaining budget. When set, it caps spending *in addition to*
        ``self.max_cost_usd`` — the effective ceiling is the stricter of the
        two. This is how nested orchestrators inherit the parent's envelope
        without plumbing a shared mutable counter (O3b).
        """
        # Effective ceiling: min(self.max_cost_usd, budget_usd), ignoring Nones.
        if self.max_cost_usd is None:
            effective_max_cost: float | None = budget_usd
        elif budget_usd is None:
            effective_max_cost = self.max_cost_usd
        else:
            effective_max_cost = min(self.max_cost_usd, budget_usd)

        start = time.perf_counter()
        path: list[TierAttempt] = []
        accumulated_cost = 0.0
        last_text = ""
        last_model = ""

        # Pre-dispatch classification: determines start tier + per-tier gate override
        _start_tier = 0
        _gate_override: dict[int, QualityGate] = {}
        if self._pre_dispatch_classifier is not None:
            try:
                decision = self._pre_dispatch_classifier(prompt)
                if decision.node == "gpu":
                    _start_tier = 1  # skip tier 0 (NPU) entirely
                    # Also override tier 1's gate: classifier knows the expected output length,
                    # so a 300-char function shouldn't escalate to CPU due to gate=2000.
                    _gate_override[1] = QualityGate(min_chars=decision.quality_gate_chars)
                else:
                    # Override tier-0 gate based on expected output length
                    _gate_override[0] = QualityGate(min_chars=decision.quality_gate_chars)
                    # Also cap the iGPU fallback gate to prevent CPU over-escalation.
                    # Default triune_orchestrator iGPU gate is 2000 chars, causing ~85%
                    # CPU escalation for NPU-fallback tasks (empirically: median iGPU
                    # response for short/factual tasks is ~400 chars, far below 2000).
                    # Cap at 750: sufficient for a substantive answer, avoids CPU waste.
                    _igpu_fallback_gate = min(max(decision.quality_gate_chars * 15, 200), 750)
                    _gate_override[1] = QualityGate(min_chars=_igpu_fallback_gate)
                # EXP-EVO-BUDGET: per-task cost ceiling (HierRouter, arXiv:2511.09873).
                # Tightens effective_max_cost for cheap tasks so they never escalate
                # to expensive tiers (e.g., paid cloud models) even if quality gate passes.
                # For local-only deployments (all costs=$0), this gate never fires —
                # it activates only when cloud tiers with cost_usd > 0 are present.
                _TASK_BUDGET_USD: dict[str, float] = {
                    "short_categorical": 0.0001,  # 1¢ / 10k calls — stay local
                    "short_answer": 0.0005,  # 5¢ / 10k calls — prefer local
                    "medium_generation": 0.005,  # 5¢ / 1k calls
                    "long_generation": 0.01,  # 1¢ / call
                    "code": 0.01,
                    "math_reasoning": 0.01,
                }
                task_budget = _TASK_BUDGET_USD.get(decision.output_type)
                if task_budget is not None:
                    if effective_max_cost is None or task_budget < effective_max_cost:
                        effective_max_cost = task_budget
                logger.debug(
                    "pre_dispatch: %s → tier%d gate=%d budget=$%.4f (%s, conf=%.2f)",
                    decision.output_type,
                    _start_tier,
                    decision.quality_gate_chars,
                    effective_max_cost or 0.0,
                    decision.reason,
                    decision.confidence,
                )
            except Exception as exc:
                logger.warning("pre_dispatch_classifier failed, using defaults: %s", exc)

        for idx, (target, gate) in enumerate(self.tiers):
            if idx < _start_tier:
                continue
            gate = _gate_override.get(idx, gate)
            model_name = target if isinstance(target, str) else type(target).__name__

            # O3: budget gate — short-circuit before invoking if cost already
            # STRICTLY EXCEEDS the cap (with float epsilon per review edge-case
            # #11). `max_cost_usd=0.0` means "local-only, no paid cloud" —
            # local tiers at $0 still run; cloud tiers at >$0 are skipped.
            _BUDGET_EPS = 1e-9
            if (
                effective_max_cost is not None
                and accumulated_cost > effective_max_cost + _BUDGET_EPS
                and idx > 0
            ):
                path.append(
                    TierAttempt(
                        tier_index=idx,
                        model_or_sub=model_name,
                        passed=False,
                        reason="budget_exceeded",
                        cost_usd=0.0,
                        latency_ms=0.0,
                        ttft_ms=None,
                    )
                )
                break

            remaining = (
                (effective_max_cost - accumulated_cost) if effective_max_cost is not None else None
            )
            tier_start = time.perf_counter()
            try:
                result, tier_cost, tier_ttft = await self._invoke_tier(target, prompt, remaining)
            except Exception as exc:
                logger.warning("Tier %d (%s) raised: %s", idx, model_name, exc)
                path.append(
                    TierAttempt(
                        tier_index=idx,
                        model_or_sub=model_name,
                        passed=False,
                        reason=f"exception: {exc}",
                        cost_usd=0.0,
                        latency_ms=(time.perf_counter() - tier_start) * 1000,
                        ttft_ms=None,
                    )
                )
                continue

            tier_latency = (time.perf_counter() - tier_start) * 1000
            accumulated_cost += tier_cost

            # Coerce OrchestrationResult to a RouteResult-shaped view for the gate.
            if isinstance(result, OrchestrationResult):
                view = RouteResult(
                    text=result.text,
                    model=result.final_model,
                    lane="nested",
                    latency_ms=result.latency_ms,
                    ttft_ms=result.ttft_ms,
                    cost_usd=result.cost_usd,
                    error=result.error,
                )
            else:
                view = result

            passed, reason = gate.check(view)
            path.append(
                TierAttempt(
                    tier_index=idx,
                    model_or_sub=model_name,
                    passed=passed,
                    reason=reason,
                    cost_usd=tier_cost,
                    latency_ms=tier_latency,
                    ttft_ms=tier_ttft,
                )
            )

            # --- JOURNEY TELEMETRY INSTRUMENTATION ---
            try:
                from datetime import datetime

                from cohezion.core.telemetry_bus import get_telemetry_bus
                from cohezion.data_mesh.journey_telemetry import (
                    FlumeJourneyEvent,
                    HardwareTier,
                    QuadratureFabrics,
                    RZeroMetrics,
                    SwarmExpert,
                )

                # Determine hardware tier based on model name or port (heuristic)
                h_tier = HardwareTier.CPU
                if "FLM" in model_name or "Gemma-4-E2B" in model_name:
                    h_tier = HardwareTier.NPU
                elif "Gemma-4-26B" in model_name or "Gemma-4-E4B" in model_name:
                    h_tier = HardwareTier.IGPU
                elif "claude" in model_name:
                    h_tier = HardwareTier.CLOUD

                bus = get_telemetry_bus()
                event = FlumeJourneyEvent(
                    event_id=f"tier_{int(datetime.now().timestamp())}_{idx}",
                    journey_id=f"orch_{int(start)}",
                    z_vector=[0.0] * 256,
                    state_12d=[0.0] * 12,
                    coherence=1.0 if passed else 0.5,
                    fabrics=QuadratureFabrics(
                        space=0.8, field=0.2, control=0.9, precipitation=1.0 if passed else 0.0
                    ),
                    awareness_parameter=0.8,
                    expert_stream=SwarmExpert.ENGINEER,
                    hardware_tier=h_tier,
                    latency_ms=tier_latency,
                    r_zero=RZeroMetrics(
                        success_rate=1.0 if passed else 0.0,
                        iteration_count=idx + 1,
                        difficulty_adjustment=1.0,
                    ),
                    metadata={"reason": reason, "model": model_name},
                )

                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(bus.emit(event))
                except RuntimeError:
                    pass
            except Exception as te:
                logger.debug("Failed to emit orchestration telemetry: %s", te)

            last_text = view.text
            last_model = view.model

            if passed:
                # O1: higher tiers don't run once a lower tier passes.
                return OrchestrationResult(
                    text=view.text,
                    primary_model=self.tiers[0][0]
                    if isinstance(self.tiers[0][0], str)
                    else type(self.tiers[0][0]).__name__,
                    final_model=last_model or model_name,
                    escalation_count=idx,
                    tier_path=path,
                    cost_usd=accumulated_cost,
                    latency_ms=(time.perf_counter() - start) * 1000,
                    ttft_ms=path[0].ttft_ms if path else None,
                    error=None,
                )

        # O7: exhausted — every tier failed. Return structured error, don't raise.
        return OrchestrationResult(
            text=last_text,
            primary_model=self.tiers[0][0]
            if isinstance(self.tiers[0][0], str)
            else type(self.tiers[0][0]).__name__,
            final_model=last_model,
            escalation_count=len([p for p in path if not p.passed]),
            tier_path=path,
            cost_usd=accumulated_cost,
            latency_ms=(time.perf_counter() - start) * 1000,
            ttft_ms=path[0].ttft_ms if path else None,
            error="all tiers exhausted",
        )


# Convenience factory — the "smarter orchestrates less-smart" default hierarchy.
def default_hierarchy(
    *, include_claude: bool = True, max_cost_usd: float = 0.05
) -> TieredOrchestrator:
    """Pre-built 4-tier orchestrator matching the plan's reference stack."""
    tiers: list[TierEntry] = [
        ("Gemma-4-E2B-it-GGUF", QualityGate(min_chars=15)),
        ("Gemma-4-26B-A4B-it-GGUF", QualityGate(min_chars=30)),
    ]
    if include_claude:
        tiers.extend(
            [
                ("claude-haiku-4-5", QualityGate(min_chars=50)),
                ("claude-sonnet-4-6", QualityGate.TRUST),  # type: ignore[attr-defined]
            ]
        )
    return TieredOrchestrator(tiers=tiers, max_cost_usd=max_cost_usd)
