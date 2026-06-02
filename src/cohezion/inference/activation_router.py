"""Prefill-based Activation Router for Swarm Inference.

Routes prompts dynamically between local low-cost engines (NPU, GPU)
and premium cloud fallbacks based on estimated prefill token length,
activation cost, and complexity.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from cohezion.inference.task_classifier import RouteDecision


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PrefillActivationRouter:
    """Dynamic router based on estimated prefill sizes and activation constraints.

    Conforms to the pre_dispatch_classifier protocol expected by TieredOrchestrator.
    """

    base_classifier: Callable[[str], RouteDecision] | None = None
    char_to_token_ratio: float = 4.0
    npu_token_limit: int = 1000  # ~4000 characters
    gpu_token_limit: int = 4000  # ~16000 characters

    def estimate_tokens(self, prompt: str) -> int:
        """Estimate the token count of a prompt using character ratio.

        Parameters
        ----------
        prompt : str
            The input prompt string.

        Returns
        -------
        int
            Estimated token count.
        """
        return int(len(prompt) / self.char_to_token_ratio)

    def route_decision(self, prompt: str) -> RouteDecision:
        """Route the prompt to the optimal hardware tier.

        Parameters
        ----------
        prompt : str
            The input prompt.

        Returns
        -------
        RouteDecision
            Structured decision including target node, type, and gates.
        """
        estimated_tokens = self.estimate_tokens(prompt)

        # 1. Base classification decision
        base_decision = None
        if self.base_classifier is not None:
            try:
                base_decision = self.base_classifier(prompt)
            except Exception as e:
                logger.warning("Base classifier failed in activation router: %s", e)

        # 2. Apply Prefill/Activation constraints
        # Exceeds local GPU capacity -> Route to Cloud (escalates by starting at cloud/gpu tier)
        if estimated_tokens > self.gpu_token_limit:
            return RouteDecision(
                node="gpu",  # GPU/Cloud path
                output_type=base_decision.output_type if base_decision else "long_generation",
                quality_gate_chars=base_decision.quality_gate_chars if base_decision else 0,
                confidence=1.0,
                reason=f"Prefill tokens ({estimated_tokens}) exceeds GPU limit ({self.gpu_token_limit}). Routed to Cloud.",
            )

        # Exceeds NPU capacity -> Route to GPU
        if estimated_tokens > self.npu_token_limit:
            return RouteDecision(
                node="gpu",
                output_type=base_decision.output_type if base_decision else "medium_generation",
                quality_gate_chars=base_decision.quality_gate_chars if base_decision else 0,
                confidence=0.9,
                reason=f"Prefill tokens ({estimated_tokens}) exceeds NPU limit ({self.npu_token_limit}). Routed to GPU.",
            )

        # If base classifier exists, respect its decision (npu/gpu) unless overridden by limits
        if base_decision is not None:
            return RouteDecision(
                node=base_decision.node,
                output_type=base_decision.output_type,
                quality_gate_chars=base_decision.quality_gate_chars,
                confidence=base_decision.confidence,
                reason=f"Respected base classifier. {base_decision.reason}",
            )

        # Fallback default: NPU for very short prompts, GPU otherwise
        default_node: Literal["npu", "gpu"] = "npu" if estimated_tokens < 200 else "gpu"
        return RouteDecision(
            node=default_node,
            output_type="short_answer" if default_node == "npu" else "medium_generation",
            quality_gate_chars=0,
            confidence=0.5,
            reason=f"Fallback routing based on prefill tokens ({estimated_tokens}).",
        )

    def __call__(self, prompt: str) -> RouteDecision:
        """Call interface to match TieredOrchestrator pre_dispatch_classifier protocol."""
        return self.route_decision(prompt)
