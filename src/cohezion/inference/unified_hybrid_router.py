"""Unified Hybrid Router for Cohezion.

Implements 3-tier model routing (Tier 1 Local -> Tier 2 Ollama Cloud -> Tier 3 Premium API)
gated by Expected Value of Intervention (EVI > 0.75).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Tuple

from cohezion.inference.delegation_logger import DelegationEvent, DelegationLogger


logger = logging.getLogger(__name__)

# Default cost units per tier escalation
TIER_COSTS = {
    (1, 2): 0.25,  # Escalation Tier 1 -> Tier 2 (Ollama Cloud)
    (2, 3): 1.00,  # Escalation Tier 2 -> Tier 3 (Premium API)
    (1, 3): 1.25,  # Escalation Tier 1 -> Tier 3
}

# Roster mappings
TIER_1_ROSTER = {
    "reasoning": "deepseek-r1-0528-8b-FLM",
    "coding": "Qwen3-Coder-30B",
    "coding_small": "qwen3-4b-FLM",
    "vision": "qwen3vl-it-4b-FLM",
    "research": "qwen3.6-moe-35b-a3b-FLM",
    "fast_qa": "llama3.2-1b-FLM",
    "embedding": "embed-gemma-300m-FLM",
}

TIER_2_ROSTER = {
    "reasoning": "deepseek-v4-pro:cloud",
    "coding": "qwen3.5:397b-cloud",
    "research": "glm-5.2:cloud",
    "general": "deepseek-v4-pro:cloud",
}

TIER_3_ROSTER = {
    "architecture": "gemini-3-pro",
    "coding": "claude-3-5-sonnet",
    "general": "gemini-3-pro",
}


@dataclass
class RoutingResult:
    """Result of hybrid router decision."""

    selected_tier: int
    model_name: str
    evi_score: float
    escalated: bool
    reason: str


class UnifiedHybridRouter:
    """3-Tier Hybrid Router with EVI Gating (EVI > 0.75)."""

    EVI_THRESHOLD: float = 0.75

    def __init__(self, logger_instance: Optional[DelegationLogger] = None) -> None:
        self.logger = logger_instance or DelegationLogger()

    def compute_evi(
        self,
        quality_gap: float,
        task_importance: float,
        source_tier: int,
        target_tier: int,
    ) -> float:
        """Compute Expected Value of Intervention (EVI).
        
        EVI = (quality_gap * task_importance) / escalation_cost
        """
        cost = TIER_COSTS.get((source_tier, target_tier), 1.0)
        return (quality_gap * task_importance) / max(cost, 1e-4)

    def route(
        self,
        task_type: str,
        task_importance: float = 0.5,
        estimated_tier1_quality: float = 0.8,
        target_quality_required: float = 0.9,
        tier1_saturated: bool = False,
        context_tokens: int = 4096,
        force_tier: Optional[int] = None,
    ) -> RoutingResult:
        """Determine model and execution tier.

        Parameters:
        -----------
        task_type: str
            Category of task ('coding', 'reasoning', 'research', 'vision', 'fast_qa', 'architecture')
        task_importance: float
            Priority weight (0.0 to 1.0)
        estimated_tier1_quality: float
            Expected quality from local model (0.0 to 1.0)
        target_quality_required: float
            Required quality threshold (0.0 to 1.0)
        tier1_saturated: bool
            Whether Tier 1 NPU/iGPU VRAM > 90%
        context_tokens: int
            Input context size in tokens
        force_tier: Optional[int]
            Explicit override tier (1, 2, or 3)
        """
        if force_tier in (1, 2, 3):
            model = self._select_model_for_tier(force_tier, task_type)
            res = RoutingResult(
                selected_tier=force_tier,
                model_name=model,
                evi_score=1.0,
                escalated=False,
                reason=f"Explicit force_tier={force_tier} specified",
            )
            return res

        quality_gap = max(0.0, target_quality_required - estimated_tier1_quality)

        # Baseline: Start at Tier 1 if not saturated and context fits Tier 1
        current_tier = 1
        selected_model = self._select_model_for_tier(1, task_type)

        # Check Tier 1 capability constraints
        tier1_capable = (not tier1_saturated) and (context_tokens <= 32768)

        if not tier1_capable or quality_gap > 0.1:
            # Evaluate escalation to Tier 2
            evi_1_to_2 = self.compute_evi(quality_gap, task_importance, 1, 2)
            
            if not tier1_capable or evi_1_to_2 > self.EVI_THRESHOLD:
                # Escalate to Tier 2
                current_tier = 2
                selected_model = self._select_model_for_tier(2, task_type)
                
                # Check if Tier 2 is sufficient or if Tier 3 escalation is warranted
                if context_tokens > 100000 or (task_type == "architecture" and task_importance > 0.85):
                    evi_2_to_3 = self.compute_evi(quality_gap, task_importance, 2, 3)
                    if evi_2_to_3 > self.EVI_THRESHOLD:
                        current_tier = 3
                        selected_model = self._select_model_for_tier(3, task_type)
                        reason = f"Tier 3 escalation (EVI={evi_2_to_3:.2f} > 0.75, high context/importance)"
                    else:
                        reason = f"Tier 2 escalation (EVI={evi_1_to_2:.2f} > 0.75)"
                else:
                    reason = f"Tier 2 escalation (EVI={evi_1_to_2:.2f} > 0.75)"
            else:
                reason = f"Tier 1 selected (EVI 1->2 = {evi_1_to_2:.2f} <= 0.75)"
        else:
            reason = "Tier 1 selected (quality gap minimal, capacity OK)"

        escalated = current_tier > 1
        result = RoutingResult(
            selected_tier=current_tier,
            model_name=selected_model,
            evi_score=self.compute_evi(quality_gap, task_importance, 1, current_tier) if current_tier > 1 else 0.0,
            escalated=escalated,
            reason=reason,
        )

        # Log delegation event
        event = DelegationEvent(
            task_name=task_type,
            task_importance=task_importance,
            quality_gap=quality_gap,
            escalation_cost=TIER_COSTS.get((1, current_tier), 0.0),
            evi_score=result.evi_score,
            source_tier=1,
            target_tier=current_tier,
            escalated=escalated,
            model_selected=result.model_name,
            reason=result.reason,
        )
        self.logger.log_delegation(event)

        return result

    def _select_model_for_tier(self, tier: int, task_type: str) -> str:
        """Map task type to specific model in tier roster."""
        if tier == 1:
            return TIER_1_ROSTER.get(task_type, TIER_1_ROSTER["coding"])
        elif tier == 2:
            return TIER_2_ROSTER.get(task_type, TIER_2_ROSTER["general"])
        elif tier == 3:
            return TIER_3_ROSTER.get(task_type, TIER_3_ROSTER["general"])
        return "qwen3-4b-FLM"
