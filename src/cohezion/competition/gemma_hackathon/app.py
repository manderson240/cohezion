from __future__ import annotations

import random


SEED = 42
random.seed(SEED)

# Inlined compound loop demo (no dependencies, runs in HF Space CPU)

SCENARIOS = [
    {
        "name": "flood_evacuation",
        "reports": [
            {
                "id": "f-001",
                "category": "flooding",
                "severity": 8,
                "location": "Sector 7",
                "description": "Rising water levels, 200+ families trapped",
                "affected_population": 1200,
                "resources_needed": ["boats", "medical", "shelter"],
            },
            {
                "id": "f-002",
                "category": "flooding",
                "severity": 5,
                "location": "Sector 3",
                "description": "Street flooding, traffic disruption",
                "affected_population": 50,
                "resources_needed": ["pumps", "traffic_control"],
            },
        ],
    },
    {
        "name": "earthquake_rescue",
        "reports": [
            {
                "id": "e-001",
                "category": "earthquake",
                "severity": 9,
                "location": "Downtown",
                "description": "Building collapse, people trapped",
                "affected_population": 300,
                "resources_needed": ["rescue_teams", "medical", "heavy_equipment"],
            },
        ],
    },
    {
        "name": "food_shortage",
        "reports": [
            {
                "id": "s-001",
                "category": "shortage",
                "severity": 6,
                "location": "Refugee Camp Alpha",
                "description": "Food supplies running low for 5000 people",
                "affected_population": 5000,
                "resources_needed": ["food", "water", "logistics"],
            },
        ],
    },
    {
        "name": "wildfire_spread",
        "reports": [
            {
                "id": "w-001",
                "category": "wildfire",
                "severity": 10,
                "location": "Northern Forest",
                "description": "Fire spreading toward residential area",
                "affected_population": 8000,
                "resources_needed": ["firefighters", "air_support", "evacuation_buses"],
            },
        ],
    },
    {
        "name": "medical_outbreak",
        "reports": [
            {
                "id": "m-001",
                "category": "disease",
                "severity": 7,
                "location": "Urban Clinic East",
                "description": "Suspected outbreak, 40 cases in 3 days",
                "affected_population": 200,
                "resources_needed": ["quarantine", "testing", "medical_staff"],
            },
        ],
    },
]


def run_agent():
    outcomes = []
    for scenario in SCENARIOS:
        actions = len(scenario["reports"])
        effectiveness = (
            0.3
            + (sum(r["severity"] for r in scenario["reports"]) / actions / 10 * 0.4)
            + min(1.0, actions / 3 * 0.3)
        )
        outcomes.append(
            {
                "name": scenario["name"],
                "actions": actions,
                "effectiveness": round(effectiveness, 2),
            }
        )

    # Simulated episodes
    episodes = []
    for ep in range(1, 9):
        episodes.append(
            {
                "episode": ep,
                "alignment": round(0.60 + ep * 0.02 + random.gauss(0, 0.02), 3),
                "effectiveness": round(0.75 + ep * 0.025 + random.gauss(0, 0.03), 3),
            }
        )

    return {"outcomes": outcomes, "episodes": episodes}
