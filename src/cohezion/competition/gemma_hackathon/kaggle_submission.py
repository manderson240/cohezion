"""Kaggle-ready standalone script for Compound Crisis Response demo.

Run on Kaggle with Ollama/Gemma integration or as a standalone demo.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class CrisisReport:
    id: str
    category: str
    severity: int
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
    effectiveness: float = 0.0
    lessons: list[str] = field(default_factory=list)


SCENARIOS = [
    {
        "name": "flood_evacuation",
        "reports": [
            {
                "id": "f-001", "category": "flooding", "severity": 8,
                "location": "Sector 7", "description": "Rising water levels, 200+ families trapped",
                "affected_population": 1200, "resources_needed": ["boats", "medical", "shelter"],
            },
            {
                "id": "f-002", "category": "flooding", "severity": 5,
                "location": "Sector 3", "description": "Street flooding, traffic disruption",
                "affected_population": 50, "resources_needed": ["pumps", "traffic_control"],
            },
        ],
    },
    {
        "name": "earthquake_rescue",
        "reports": [
            {
                "id": "e-001", "category": "earthquake", "severity": 9,
                "location": "Downtown", "description": "Building collapse, people trapped",
                "affected_population": 300, "resources_needed": ["rescue_teams", "medical", "heavy_equipment"],
            },
        ],
    },
    {
        "name": "food_shortage",
        "reports": [
            {
                "id": "s-001", "category": "shortage", "severity": 6,
                "location": "Refugee Camp Alpha", "description": "Food supplies running low for 5000 people",
                "affected_population": 5000, "resources_needed": ["food", "water", "logistics"],
            },
        ],
    },
    {
        "name": "wildfire_spread",
        "reports": [
            {
                "id": "w-001", "category": "wildfire", "severity": 10,
                "location": "Northern Forest", "description": "Fire spreading toward residential area, 10km/h wind",
                "affected_population": 8000, "resources_needed": ["firefighters", "air_support", "evacuation_buses"],
            },
        ],
    },
    {
        "name": "medical_outbreak",
        "reports": [
            {
                "id": "m-001", "category": "disease", "severity": 7,
                "location": "Urban Clinic East", "description": "Suspected outbreak, 40 cases in 3 days",
                "affected_population": 200, "resources_needed": ["quarantine", "testing", "medical_staff"],
            },
        ],
    },
]

OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/api")


async def query_ollama(prompt: str, model: str = "gemma4:31b-cloud") -> str:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/generate",
                json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2, "num_predict": 256}},
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
    except Exception:
        return ""


class CrisisCompoundAgent:
    def __init__(self, model: str = "gemma4:31b-cloud"):
        self.model = model
        self.skill_library = {
            "flooding": "Deploy pumps, coordinate evacuation, establish shelter points",
            "earthquake": "Search and rescue, triage, structural assessment",
            "shortage": "Rapid assessment, logistics chain, fair distribution",
            "wildfire": "Evacuate, establish firebreaks, coordinate air/water support",
            "disease": "Contain spread, test/isolate, preserve privacy",
        }
        self.outcome_history: list[ScenarioOutcome] = []

    async def process_scenario(self, scenario: dict[str, Any]) -> ScenarioOutcome:
        actions = []
        for rspec in scenario["reports"]:
            report = CrisisReport(**rspec)
            # Alignment gate
            if not (1 <= report.severity <= 10):
                continue
            # Scale resources
            resources = report.resources_needed[: min(3, len(report.resources_needed))]
            if report.severity >= 8:
                resources.append("emergency_tier_1")
            if report.severity >= 9:
                resources.append("emergency_tier_0")
            # Query Gemma for reasoning
            skill = self.skill_library.get(report.category, "general_response")
            prompt = (
                f"Crisis report: {report.description}\n"
                f"Category: {report.category}, Severity: {report.severity}/10, "
                f"Location: {report.location}, Affected: {report.affected_population}\n"
                f"Skill: {skill}\n\n"
                f"State the single most important immediate action (1 sentence):"
            )
            reasoning = await query_ollama(prompt, self.model)
            action = ResponseAction(
                id=f"resp-{report.id}",
                action_type=report.category,
                target_location=report.location,
                resources_deployed=list(dict.fromkeys(resources)),
                expected_outcome=reasoning or f"Address {report.category}",
                alignment_score=report.severity / 10.0,
                reasoning=reasoning,
            )
            actions.append(action)

        effectiveness = 0.0
        if actions:
            effectiveness = 0.3 + (sum(a.alignment_score for a in actions) / len(actions) * 0.4) + (
                min(1.0, sum(len(a.resources_deployed) for a in actions) / len(actions) / 3) * 0.3
            )
        lessons = [f"{scenario['name']}: effectiveness {effectiveness:.2f}"]
        outcome = ScenarioOutcome(
            scenario_name=scenario["name"],
            actions=actions,
            effectiveness=effectiveness,
            lessons=lessons,
        )
        self.outcome_history.append(outcome)
        return outcome

    def get_metrics(self) -> dict[str, Any]:
        total_actions = sum(len(o.actions) for o in self.outcome_history)
        avg_alignment = sum(
            a.alignment_score
            for o in self.outcome_history
            for a in o.actions
        ) / total_actions if total_actions else 0
        avg_eff = sum(o.effectiveness for o in self.outcome_history) / len(self.outcome_history) if self.outcome_history else 0
        return {
            "scenarios": len(self.outcome_history),
            "actions": total_actions,
            "skills": len(self.skill_library),
            "avg_alignment": round(avg_alignment, 3),
            "avg_effectiveness": round(avg_eff, 3),
        }


async def main() -> dict[str, Any]:
    agent = CrisisCompoundAgent()
    outcomes = []
    for scenario in SCENARIOS:
        outcome = await agent.process_scenario(scenario)
        outcomes.append({
            "name": outcome.scenario_name,
            "actions": len(outcome.actions),
            "effectiveness": round(outcome.effectiveness, 3),
        })
    result = {
        "outcomes": outcomes,
        "metrics": agent.get_metrics(),
        "skills": agent.skill_library,
    }
    return result


if __name__ == "__main__":
    output = asyncio.run(main())
    print(json.dumps(output, indent=2))
    # Save for Kaggle
    with open("compound_crisis_response.json", "w") as f:
        json.dump(output, f, indent=2)
    print("Saved to compound_crisis_response.json")
