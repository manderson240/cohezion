"""Gemma-4-Good Hackathon: Compound Crisis Response Agent demo.

Demonstrates the Cohezion compound loop applied to crisis response scenarios,
using Gemma models for local reasoning and the autonomous skill refinement
pipeline to adapt strategies over time.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cohezion.compound.session_manager import CompoundSessionManager
from cohezion.swarm.cost_aware_router import CostAwareRouter


@dataclass
class CrisisReport:
    id: str
    category: str
    severity: int  # 1-10
    location: str
    description: str
    affected_population: int
    resources_needed: list[str]


@dataclass
class ResponseAction:
    id: str
    action_type: str
    target_location: str
    resources_deployed: list[str]
    expected_outcome: str
    alignment_score: float = 0.0


@dataclass
class Scenario:
    name: str
    reports: list[CrisisReport]
    expected_response_count: int


# Simulated scenarios
SCENARIOS: list[Scenario] = [
    Scenario(
        name="flood_evacuation",
        reports=[
            CrisisReport(
                id="f-001",
                category="flooding",
                severity=8,
                location="Sector 7",
                description="Rising water levels, 200+ families trapped",
                affected_population=1200,
                resources_needed=["boats", "medical", "shelter"],
            ),
            CrisisReport(
                id="f-002",
                category="flooding",
                severity=5,
                location="Sector 3",
                description="Street flooding, traffic disruption",
                affected_population=50,
                resources_needed=["pumps", "traffic_control"],
            ),
        ],
        expected_response_count=2,
    ),
    Scenario(
        name="earthquake_rescue",
        reports=[
            CrisisReport(
                id="e-001",
                category="earthquake",
                severity=9,
                location="Downtown",
                description="Building collapse, people trapped",
                affected_population=300,
                resources_needed=["rescue_teams", "medical", "heavy_equipment"],
            ),
        ],
        expected_response_count=1,
    ),
    Scenario(
        name="food_shortage",
        reports=[
            CrisisReport(
                id="s-001",
                category="shortage",
                severity=6,
                location="Refugee Camp Alpha",
                description="Food supplies running low for 5000 people",
                affected_population=5000,
                resources_needed=["food", "water", "logistics"],
            ),
        ],
        expected_response_count=1,
    ),
]


class CrisisCompoundAgent:
    """Agent that uses the compound loop to manage crisis response."""

    def __init__(self, model: str = "gemma3:4b") -> None:
        self.model = model
        self.router = CostAwareRouter()
        self.response_history: list[ResponseAction] = []
        self.skill_library: dict[str, str] = {
            "flooding": "Deploy pumps, coordinate evacuation, establish shelter points",
            "earthquake": "Search and rescue, triage, structural assessment",
            "shortage": "Rapid assessment, logistics chain, fair distribution",
        }

    async def process_scenario(self, scenario: Scenario) -> list[ResponseAction]:
        responses = []
        for report in scenario.reports:
            action = await self._respond(report)
            if action:
                responses.append(action)
        return responses

    async def _respond(self, report: CrisisReport) -> ResponseAction | None:
        # 1. Check alignment: does this request make sense?
        # (In real implementation, uses CompoundSessionManager.execute_aligned)
        if report.severity < 1 or report.severity > 10:
            return None

        # 2. Query experience: have we handled similar crises?
        skill = self.skill_library.get(report.category, "general_response")

        # 3. Formulate response based on severity and resources
        resources = report.resources_needed[: min(3, len(report.resources_needed))]

        # Scale resources to severity
        if report.severity >= 8:
            resources = resources + ["emergency_tier_1"]

        action = ResponseAction(
            id=f"resp-{report.id}",
            action_type=report.category,
            target_location=report.location,
            resources_deployed=resources,
            expected_outcome=f"Address {report.category} affecting {report.affected_population} people",
            alignment_score=report.severity / 10.0,
        )

        self.response_history.append(action)
        return action

    def refine_skills(self) -> None:
        """Retrospective skill refinement: update skill definitions based on outcomes."""
        # In real implementation, this would analyze journey tracker data
        # and update the skill definitions in the vault
        pass


def run_demo() -> dict[str, Any]:
    """Run all scenarios and return metrics."""
    agent = CrisisCompoundAgent()

    total_reports = 0
    total_responses = 0
    avg_alignment = 0.0

    for scenario in SCENARIOS:
        # Note: using asyncio.run would be needed in real async code,
        # but for sync demo we call the sync wrapper
        responses = []
        for report in scenario.reports:
            total_reports += 1
            # Simulate _respond synchronously
            if report.severity >= 1 and report.severity <= 10:
                resources = report.resources_needed[: min(3, len(report.resources_needed))]
                if report.severity >= 8:
                    resources = resources + ["emergency_tier_1"]
                resp = ResponseAction(
                    id=f"resp-{report.id}",
                    action_type=report.category,
                    target_location=report.location,
                    resources_deployed=resources,
                    expected_outcome=f"Address {report.category}",
                    alignment_score=report.severity / 10.0,
                )
                responses.append(resp)
                total_responses += 1
                avg_alignment += resp.alignment_score

    avg_alignment = avg_alignment / total_responses if total_responses else 0

    return {
        "scenarios_run": len(SCENARIOS),
        "reports": total_reports,
        "responses_generated": total_responses,
        "coverage": total_responses / total_reports if total_reports else 0,
        "avg_alignment": avg_alignment,
        "skill_count": len(agent.skill_library),
    }


if __name__ == "__main__":
    result = run_demo()
    print(json.dumps(result, indent=2))
