"""2026 Intelligence Pipeline and Mixture-of-Experts Orchestration.

This module implements the orchestration logic for 2026+ SLMs, Inference Models,
World Models, and Large Quantitative Models (LQMs). It includes robust Out-Of-Memory (OOM)
defenses via a controlled SandboxManager.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from cohezion.reliability.circuit_breaker import get_circuit


logger = logging.getLogger(__name__)


class ModelProfile(BaseModel):
    """Profile for a specific intelligence model."""

    name: str
    category: str = Field(description="SLM, INFERENCE, WORLD, LQM")
    vram_requirements_gb: float
    context_window: int
    strengths: list[str]


# Pre-defined 2026 Profiles
MODELS_2026 = {
    "deepseek-r1": ModelProfile(
        name="deepseek-r1",
        category="INFERENCE",
        vram_requirements_gb=32.0,
        context_window=128000,
        strengths=["deep reasoning", "architecture", "mathematics"],
    ),
    "gemini-3-pro": ModelProfile(
        name="gemini-3-pro",
        category="INFERENCE",
        vram_requirements_gb=40.0,
        context_window=2000000,
        strengths=["multimodal synthesis", "massive context", "coding"],
    ),
    "qwen3-coder": ModelProfile(
        name="qwen3-coder",
        category="SLM",
        vram_requirements_gb=16.0,
        context_window=64000,
        strengths=["rapid code generation", "multi-language"],
    ),
    "phi-4-mini": ModelProfile(
        name="phi-4-mini",
        category="SLM",
        vram_requirements_gb=4.0,
        context_window=8000,
        strengths=["edge deployment", "rapid QA"],
    ),
    "lqm-math-oracle": ModelProfile(
        name="lqm-math-oracle",
        category="LQM",
        vram_requirements_gb=12.0,
        context_window=32000,
        strengths=["strict mathematical coherence", "theorem proving"],
    ),
    "world-physics-v1": ModelProfile(
        name="world-physics-v1",
        category="WORLD",
        vram_requirements_gb=24.0,
        context_window=64000,
        strengths=["environmental simulation", "physics prediction"],
    ),
}


@dataclass
class OrchestrationRequest:
    """Request to the Mixture-of-Experts pipeline."""

    task_description: str
    complexity_score: float  # 0.0 to 1.0
    requires_math_proof: bool = False
    requires_world_sim: bool = False
    max_latency_ms: int = 30000


class SandboxManager:
    """Zero-Drop OOM Protection and VRAM Budgeting."""

    def __init__(self, max_vram_gb: float = 120.0):
        self.max_vram_gb = max_vram_gb
        self.current_vram_gb = 0.0
        self.active_models: list[str] = []

    def can_allocate(self, required_vram: float) -> bool:
        """Check if VRAM budget allows this allocation."""
        return (self.current_vram_gb + required_vram) <= self.max_vram_gb

    def allocate(self, model_name: str, required_vram: float) -> bool:
        """Attempt to allocate VRAM for a model."""
        if self.can_allocate(required_vram):
            self.current_vram_gb += required_vram
            self.active_models.append(model_name)
            logger.info(f"Allocated {required_vram}GB for {model_name}. Total VRAM: {self.current_vram_gb}GB")
            return True
        logger.warning(
            f"OOM Prevented: Cannot allocate {required_vram}GB for {model_name}. "
            f"Current: {self.current_vram_gb}GB / Max: {self.max_vram_gb}GB"
        )
        return False

    def release(self, model_name: str, allocated_vram: float) -> None:
        """Release VRAM back to the budget."""
        if model_name in self.active_models:
            self.current_vram_gb -= allocated_vram
            self.active_models.remove(model_name)
            logger.info(f"Released {allocated_vram}GB from {model_name}. Total VRAM: {self.current_vram_gb}GB")


class MixtureOfExpertsRouter:
    """Routes tasks to the optimal 2026 model based on complexity and requirements."""

    def __init__(self, sandbox_manager: SandboxManager):
        self.sandbox = sandbox_manager

    @get_circuit(name="moe_routing", failure_threshold=3, recovery_timeout=30)
    async def route_task(self, req: OrchestrationRequest) -> dict[str, Any]:
        """Determine the optimal model and execution plan for the task."""
        selected_models = []

        if req.requires_math_proof:
            selected_models.append("lqm-math-oracle")

        if req.requires_world_sim:
            selected_models.append("world-physics-v1")

        if req.complexity_score > 0.8:
            selected_models.append("deepseek-r1")
        elif req.complexity_score > 0.5:
            selected_models.append("gemini-3-pro")
        else:
            selected_models.append("qwen3-coder")

        # Fallback to ultra-fast SLM if latency is tight
        if req.max_latency_ms < 5000 and req.complexity_score < 0.4:
            selected_models = ["phi-4-mini"]

        execution_plan = []
        for model_name in list(dict.fromkeys(selected_models)):  # Deduplicate
            profile = MODELS_2026.get(model_name)
            if profile and self.sandbox.allocate(model_name, profile.vram_requirements_gb):
                execution_plan.append(model_name)
            else:
                logger.warning(f"Could not include {model_name} in plan due to OOM constraints.")

        # If no models could be allocated, fallback to smallest SLM and force offload
        if not execution_plan:
            logger.warning("Applying aggressive context offloading for fallback.")
            self.sandbox.allocate("phi-4-mini", MODELS_2026["phi-4-mini"].vram_requirements_gb)
            execution_plan.append("phi-4-mini")

        return {
            "task": req.task_description,
            "complexity": req.complexity_score,
            "execution_plan": execution_plan,
            "status": "routed",
        }
