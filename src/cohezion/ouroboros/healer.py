"""Ouroboros Healer — synthesizes patches + emits HEALING_EVENT to the bus.

WS1B (2026-06-04) adds the analyze_and_heal() method that:
1. Runs OuroborosFailureAnalyzer on the failure log (deterministic)
2. Optionally calls synthesize_patch() for an LLM-driven proposal (best-effort)
3. Emits a HEALING_EVENT to the precipitation bus with the full result

This closes the previously-broken self-healing loop: a failure in
CompoundExecutor triggers analyze_and_heal(), which emits HEALING_EVENT
that downstream bus subscribers (e.g. SelfImprovementOrchestrator in
WS4) can act on.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig


logger = logging.getLogger(__name__)


class HealerAgent(BaseAgent):
    """
    Agent responsable for synthesizing system patches and architecture
    adjustments based on Ouroboros anomaly reports.
    """

    def __init__(
        self, model_name: str = "qwen3-coder", config: SwarmConfig | None = None, **kwargs
    ):
        super().__init__(model_name, config, **kwargs)

    def analyze_and_heal(
        self, failure_log: str, target: str = "unknown"
    ) -> dict[str, Any]:
        """Analyze a failure log + emit a HEALING_EVENT to the bus.

        The deterministic FailureAnalyzer is the source of truth.
        The LLM patch proposal is best-effort and only enriches the
        payload if the LLM is reachable. Either way, a HEALING_EVENT
        is emitted so downstream subscribers can act.

        Args:
            failure_log: The raw failure log to analyze.
            target: Human-readable label for the failure (e.g. skill
                name, "training", "deployment"). Used as the universe
                id for the HEALING_EVENT so clustering can group
                similar failures.

        Returns:
            Dict with keys: root_cause, suggested_mutation, learning_id,
            is_recoverable, patch_proposal (optional, only if LLM succeeded).
        """
        # 1. Deterministic analysis
        analysis: dict[str, Any] = {
            "root_cause": "Unknown failure",
            "suggested_mutation": "Investigate log context",
            "is_recoverable": True,
        }
        try:
            from cohezion.ouroboros.failure_analyzer import OuroborosFailureAnalyzer

            fa = OuroborosFailureAnalyzer()
            result = fa.analyze(failure_log, target=target)
            analysis = {
                "root_cause": result.root_cause,
                "suggested_mutation": result.suggested_mutation,
                "is_recoverable": result.is_recoverable,
                "learning_id": result.learning_id,
            }
        except Exception as e:
            logger.debug("FailureAnalyzer failed (non-blocking): %s", e)

        # 2. Optional LLM patch proposal (best-effort)
        patch_proposal: str | None = None
        try:
            if hasattr(self, "synthesize_patch"):
                # synthesize_patch is async; we run it synchronously
                # via asyncio.run() if no event loop is running
                import asyncio

                try:
                    asyncio.get_running_loop()
                    # If a loop is running, skip the LLM call (would block)
                    logger.debug("Event loop running, skipping LLM patch synthesis")
                except RuntimeError:
                    # No event loop; safe to run synchronously
                    try:
                        patch_proposal = asyncio.run(
                            self.synthesize_patch(
                                {
                                    "target": target,
                                    "root_cause": analysis["root_cause"],
                                    "suggested_mutation": analysis["suggested_mutation"],
                                    "log_excerpt": failure_log[:500],
                                }
                            )
                        )
                    except Exception as e:
                        logger.debug("synthesize_patch failed (non-blocking): %s", e)
        except Exception as e:
            logger.debug("LLM path failed (non-blocking): %s", e)

        if patch_proposal:
            analysis["patch_proposal"] = patch_proposal

        # 3. Emit HEALING_EVENT to the bus (best-effort)
        try:
            from cohezion.precipitation.bus import get_bus
            from cohezion.precipitation.events import (
                PrecipitationEvent,
                PrecipitationKind,
            )

            safe_target = target.replace(" ", "-").replace("/", "_")
            get_bus().emit(
                PrecipitationEvent(
                    kind=PrecipitationKind.HEALING_EVENT,
                    universe_id=f"ouroboros.heal.{safe_target}",
                    coherence=0.5,
                    agent_id="ouroboros-healer",
                    payload={
                        "target": target,
                        "root_cause": analysis["root_cause"],
                        "suggested_mutation": analysis["suggested_mutation"],
                        "is_recoverable": analysis["is_recoverable"],
                        "learning_id": analysis.get("learning_id", ""),
                        "has_patch": patch_proposal is not None,
                        "log_excerpt": failure_log[:300],
                        "created_at": datetime.now(UTC).isoformat(),
                    },
                )
            )
            logger.info(
                "ouroboros healer: emitted HEALING_EVENT for %s (root_cause=%s)",
                target,
                analysis["root_cause"][:80],
            )
        except Exception as e:
            logger.debug("HEALING_EVENT emission failed (non-blocking): %s", e)

        return analysis

    async def synthesize_patch(self, anomaly_report: dict[str, Any]) -> str:
        """
        Generates a patch proposal based on the provided anomaly report.

        Args:
            anomaly_report: Dictionary containing degradation details.

        Returns:
            str: The synthesized patch proposal.
        """
        prompt = f"""
        ANOMALY REPORT DETECTED:
        {json.dumps(anomaly_report, indent=2)}

        As the Ouroboros Healer, synthesize a specific patch proposal to stabilize
        the Cohezion Triune Manifold. Focus on coherence recovery toward the 0.5
        HIHO stability point.

        Provide your response in the following format:
        PATCH Proposal: <Description of adjustment>
        Rationale: <Explanation of why this stabilizes the system>
        """

        logger.info("HealerAgent synthesizing patch for detected anomalies...")
        patch_proposal = await self._call_ollama(prompt)

        return patch_proposal

    async def process(self, *args: Any, **kwargs: Any) -> Any:
        """
        Required BaseAgent process implementation.
        """
        report = args[0] if args else kwargs.get("report", {})
        return await self.synthesize_patch(report)
