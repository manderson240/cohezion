"""Plasma Swarm Router for orchestrating EVOs via the Plasma MCP fields."""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from cohezion.reliability import CircuitBreaker, get_circuit
from cohezion.swarm.dynamic_model_router import DynamicModelRouter


logger = logging.getLogger(__name__)


class EvoTopologyRequest(BaseModel):
    """Request to predict an EVO generation topology."""

    fohatic_impulse: float = Field(description="Primary intent sparking the generation")
    swarm_size: int = Field(default=8, description="Target size of the agent swarm cluster")
    plasma_viscosity: float = Field(default=0.5, description="Background field resistance")


class PlasmaSwarmRouter:
    """Multi-agent Swarm routing over Plasma MCP fields using Kordylewski memory.

    Acts as the orchestration layer directing EVOs toward L4/L5 Lagrange points.
    """

    def __init__(self, router: DynamicModelRouter | None = None) -> None:
        self.router: DynamicModelRouter = router or DynamicModelRouter()
        self.circuit: CircuitBreaker = get_circuit(
            "plasma_swarm_router", failure_threshold=2, recovery_timeout=60.0
        )

    async def predict_topology(self, request: EvoTopologyRequest) -> str:
        """Predict EVO generation topologies based on the fohatic_impulse."""
        if not self.circuit.allow_request():
            return "Circuit open: Topology prediction unavailable"

        prompt = (
            "Analyze the following parameters to predict an EVO generation topology "
            "within the 12D semantic space:\n"
            f"- Fohatic Impulse: {request.fohatic_impulse}\n"
            f"- Swarm Size: {request.swarm_size}\n"
            f"- Plasma Viscosity: {request.plasma_viscosity}\n\n"
            "Describe the topological formation "
            "(e.g., Toroidal, Metatron's Cube, "
            "Star Tetrahedron) "
            "that the swarm will naturally assume "
            "at the L4/L5 Lagrange points."
        )

        try:
            # Delegate to local code models (Qwen3-Coder or DeepSeek-R1) via 'coding' task type
            response = await self.router.execute_request(
                {"task_type": "coding", "prompt": prompt, "ide_priority": 1, "urgency": "medium"}
            )
            self.circuit.record_success()
            res = response.get("result")
            if isinstance(res, dict):
                content = res.get("text", "No topology generated.")
            else:
                content = "No topology generated."
            return str(content)
        except Exception as e:
            self.circuit.record_failure()
            logger.error(f"Failed to predict EVO topology: {e}")
            return f"Prediction failed: {e}"
