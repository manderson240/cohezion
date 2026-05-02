"""Scenario Modeling and Tradeoff Analysis for EcoResilience.
Extends the CompoundEngine to evaluate multiple competing scenarios
using InVEST biophysical grounding.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from cohezion.compound.eco_symphony import EcoResilienceCompoundEngine
from cohezion.compound.invest.bridge import InVESTBridge


logger = logging.getLogger(__name__)


class ScenarioOutcome(BaseModel):
    """The quantified result of a specific resilience scenario."""

    scenario_id: str
    strategy: str
    biophysical_value: float
    stability_score: float
    tradeoff_index: float
    is_stable: bool


class ScenarioModeler:
    """
    Orchestrates multiple competing scenarios and analyzes tradeoffs.
    Moves the swarm from a single-answer loop to a multi-scenario a-b-c.
    """

    def __init__(self, engine: EcoResilienceCompoundEngine, invest_bridge: InVESTBridge):
        self.engine = engine
        self.invest_bridge = invest_bridge

    async def evaluate_scenario(self, scenario_id: str, input_text: str) -> ScenarioOutcome:
        """
        Runs a compound synthesis for a specific scenario and
        grounds it with InVEST metrics.
        """
        # 1. Run the reflexive symphony for the scenario
        symphony = await self.engine.compound_synthesize(input_text)

        # 2. Ground the result with InVEST biophysical data
        # In a real scenario, the 'strategy' would be used to query an InVEST model.
        # Here, we simulate the InVEST output based on the strategy content.
        invest_state = await self.invest_bridge.get_invest_metrics(
            region="Sundarbans", model="Coastal Blue Carbon"
        )

        # Adjust the biophysical value based on the strategy's 'reasoning'
        # (e.g., if 'Sabu-Sabu' is present, boost the value)
        multiplier = 1.5 if "Sabu-Sabu" in symphony.final_strategy else 1.0
        final_value = invest_state.biophysical_value * multiplier

        return ScenarioOutcome(
            scenario_id=scenario_id,
            strategy=symphony.final_strategy,
            biophysical_value=final_value,
            stability_score=symphony.stability_score,
            tradeoff_index=invest_state.tradeoff_index,
            is_stable=symphony.manifold_state.stability,
        )

    async def run_tradeoff_analysis(self, scenarios: dict[str, str]) -> list[ScenarioOutcome]:
        """
        Evaluates multiple scenarios and identifies the optimal tradeoff.
        """
        outcomes = []
        for sid, text in scenarios.items():
            logger.info("Evaluating Scenario: %s...", sid)
            outcome = await self.evaluate_scenario(sid, text)
            outcomes.append(outcome)

        # Sort by Stability * Value (The "Symphony Efficiency" metric)
        outcomes.sort(key=lambda x: x.stability_score * x.biophysical_value, reverse=True)
        return outcomes
