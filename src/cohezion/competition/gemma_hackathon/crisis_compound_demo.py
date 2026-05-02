"""Gemma-4-Good Hackathon: Compound Crisis Response Agent demo.

Demonstrates the Cohezion compound loop applied to crisis response scenarios,
using Gemma models for local reasoning and the autonomous skill refinement
pipeline to adapt strategies over time.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx


logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434/api"


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
    reasoning: str = ""


@dataclass
class ScenarioOutcome:
    scenario_name: str
    actions: list[ResponseAction]
    effectiveness: float = 0.0  # 0-1
    lessons: list[str] = field(default_factory=list)


@dataclass
class Scenario:
    name: str
    reports: list[CrisisReport]
    expected_response_count: int
    evaluation_criteria: list[str]


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
        evaluation_criteria=["prioritize_high_severity", "match_resources_to_scale"],
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
        evaluation_criteria=["search_and_rescue_first", "coordinate_aftershock_protocol"],
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
        evaluation_criteria=["rapid_assessment", "fair_distribution"],
    ),
    Scenario(
        name="wildfire_spread",
        reports=[
            CrisisReport(
                id="w-001",
                category="wildfire",
                severity=10,
                location="Northern Forest",
                description="Fire spreading toward residential area, 10km/h wind",
                affected_population=8000,
                resources_needed=["firefighters", "air_support", "evacuation_buses"],
            ),
        ],
        expected_response_count=1,
        evaluation_criteria=["evacuate_immediately", "establish_firebreak"],
    ),
    Scenario(
        name="medical_outbreak",
        reports=[
            CrisisReport(
                id="m-001",
                category="disease",
                severity=7,
                location="Urban Clinic East",
                description="Suspected outbreak, 40 cases in 3 days",
                affected_population=200,
                resources_needed=["quarantine", "testing", "medical_staff"],
            ),
        ],
        expected_response_count=1,
        evaluation_criteria=["contain_spread", "preserve_privacy"],
    ),
]


async def query_gemma(prompt: str, model: str = "gemma3:4b") -> str:
    """Query Gemma via local Ollama for reasoning."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 256},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
    except Exception as exc:
        logger.warning("Ollama query failed: %s", exc)
        return ""


class CrisisCompoundAgent:
    """Agent that uses the compound loop to manage crisis response."""

    def __init__(self, model: str = "gemma4:31b-cloud") -> None:
        self.model = model
        self.response_history: list[ResponseAction] = []
        self.skill_library: dict[str, str] = {
            "flooding": "Deploy pumps, coordinate evacuation, establish shelter points",
            "earthquake": "Search and rescue, triage, structural assessment",
            "shortage": "Rapid assessment, logistics chain, fair distribution",
            "wildfire": "Evacuate, establish firebreaks, coordinate air/water support",
            "disease": "Contain spread, test/isolate, preserve privacy",
        }
        self.outcome_history: list[ScenarioOutcome] = []
        self.refinement_log: list[str] = []

    async def process_scenario(self, scenario: Scenario) -> ScenarioOutcome:
        actions = []
        for report in scenario.reports:
            action = await self._respond(report)
            if action:
                actions.append(action)

        # Evaluate effectiveness
        effectiveness = self._evaluate(scenario, actions)
        lessons = self._extract_lessons(scenario, actions, effectiveness)

        outcome = ScenarioOutcome(
            scenario_name=scenario.name,
            actions=actions,
            effectiveness=effectiveness,
            lessons=lessons,
        )
        self.outcome_history.append(outcome)
        return outcome

    async def _respond(self, report: CrisisReport) -> ResponseAction | None:
        # 1. Alignment gate: basic sanity check
        if report.severity < 1 or report.severity > 10:
            return None

        # 2. Skill-guided reasoning with Gemma
        skill = self.skill_library.get(report.category, "general_response")
        reasoning = await self._reason(report, skill)

        # 3. Scale resources to severity
        resources = report.resources_needed[: min(3, len(report.resources_needed))]
        if report.severity >= 8:
            resources = resources + ["emergency_tier_1"]
        if report.severity >= 9:
            resources = resources + ["emergency_tier_0"]

        # 4. Formulate response
        action = ResponseAction(
            id=f"resp-{report.id}",
            action_type=report.category,
            target_location=report.location,
            resources_deployed=list(dict.fromkeys(resources)),
            expected_outcome=reasoning or f"Address {report.category}",
            alignment_score=report.severity / 10.0,
            reasoning=reasoning,
        )
        self.response_history.append(action)
        return action

    async def _reason(self, report: CrisisReport, skill: str) -> str:
        prompt = (
            f"You are a crisis response coordinator. A report arrived:\n"
            f"Category: {report.category}\n"
            f"Severity: {report.severity}/10\n"
            f"Location: {report.location}\n"
            f"Description: {report.description}\n"
            f"Affected: {report.affected_population} people\n"
            f"Resources requested: {', '.join(report.resources_needed)}\n"
            f"Known skill for this category: {skill}\n\n"
            f"Briefly state the single most important action to take (1 sentence):"
        )
        return await query_gemma(prompt, self.model)

    def _evaluate(self, scenario: Scenario, actions: list[ResponseAction]) -> float:
        if not actions:
            return 0.0
        score = 0.0
        # Coverage
        if len(actions) >= scenario.expected_response_count:
            score += 0.3
        # Alignment
        score += sum(a.alignment_score for a in actions) / len(actions) * 0.4
        # Resource adequacy
        score += (
            min(1.0, sum(len(a.resources_deployed) for a in actions) / len(scenario.reports) / 3)
            * 0.3
        )
        return min(1.0, score)

    def _extract_lessons(
        self, scenario: Scenario, actions: list[ResponseAction], effectiveness: float
    ) -> list[str]:
        lessons = []
        if effectiveness < 0.5:
            lessons.append(f"{scenario.name}: low effectiveness, review resource allocation")
        for action in actions:
            if action.alignment_score < 0.6:
                lessons.append(f"{action.id}: alignment too low, needs better reasoning")
        if not lessons:
            lessons.append(f"{scenario.name}: executed well")
        return lessons

    def refine_skills(self) -> dict[str, str]:
        """Retrospective skill refinement based on outcomes."""
        updated = {}
        for category in self.skill_library:
            # Find all outcomes for this category
            related = [
                o for o in self.outcome_history if any(a.action_type == category for a in o.actions)
            ]
            if not related:
                continue
            avg_eff = sum(o.effectiveness for o in related) / len(related)
            if avg_eff < 0.7:
                self.skill_library[category] += (
                    f" (refined: improve response speed, current avg effectiveness {avg_eff:.2f})"
                )
                self.refinement_log.append(f"Refined {category}: effectiveness {avg_eff:.2f}")
                updated[category] = self.skill_library[category]
        return updated

    def get_metrics(self) -> dict[str, Any]:
        total_actions = len(self.response_history)
        avg_alignment = (
            sum(a.alignment_score for a in self.response_history) / total_actions
            if total_actions
            else 0
        )
        avg_effectiveness = (
            sum(o.effectiveness for o in self.outcome_history) / len(self.outcome_history)
            if self.outcome_history
            else 0
        )
        return {
            "scenarios_processed": len(self.outcome_history),
            "total_actions": total_actions,
            "skill_count": len(self.skill_library),
            "avg_alignment": round(avg_alignment, 3),
            "avg_effectiveness": round(avg_effectiveness, 3),
            "refinements": len(self.refinement_log),
        }


async def run_demo() -> dict[str, Any]:
    agent = CrisisCompoundAgent()
    outcomes = []

    for scenario in SCENARIOS:
        outcome = await agent.process_scenario(scenario)
        outcomes.append(
            {
                "name": outcome.scenario_name,
                "actions": len(outcome.actions),
                "effectiveness": round(outcome.effectiveness, 3),
                "lessons": outcome.lessons[:3],
            }
        )

    # Refine after all scenarios
    refinements = agent.refine_skills()

    metrics = agent.get_metrics()
    return {
        "outcomes": outcomes,
        "metrics": metrics,
        "refinements": list(refinements.keys()),
        "skills": agent.skill_library,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(run_demo())
    print(json.dumps(result, indent=2))
