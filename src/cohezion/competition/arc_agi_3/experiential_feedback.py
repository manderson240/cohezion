"""Feed experiential ARC-AGI-3 learnings back into Cohezion core systems.

This module bridges the competition work with Cohezion's self-improving
infrastructure:
- Ouroboros: Failure detection and healing
- Mycelium: Cross-project knowledge distribution
- CompoundLoop: Alignment and execution refinement
- Skill Refinement: Update PRIME skills with learned principles
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def load_cross_project_learnings(path: Path = Path("data/arc_agi_3/cross_project_learnings.json")) -> List[Dict[str, Any]]:
    """Load the experiential learning output."""
    if not path.exists():
        return []
    return json.loads(path.read_text())


def analyze_state_abstraction_failure(learnings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Ouroboros detection: State abstraction is too granular.

    The experiential agent learned only 4-5 states per game across
    900 experiences. This means the grid_signature() function is
    treating nearly every frame as a unique state -> catastrophic
    generalization failure.

    Diagnosis: Player-centric state representation needed, not full-grid hash.
    """
    total_experiences = sum(l["total_experiences"] for l in learnings)
    total_states = sum(l["unique_states_learned"] for l in learnings)

    experiences_per_state = total_experiences / max(total_states, 1)

    failure_detected = total_states < 10 and total_experiences > 100

    diagnosis = {
        "detected": failure_detected,
        "symptom": "Extremely low state diversity despite high interaction count",
        "metric": f"{experiences_per_state:.1f} experiences / state",
        "threshold": "< 50 experiences/state indicates poor abstraction",
        "root_cause": "grid_signature() hashes full 64x64 grid. Player movement changes ~64 pixels, making every frame unique.",
        "healing_action": "Switch to player-centric state: (player_x, player_y, surrounding_3x3) + game state",
        "severity": "HIGH" if failure_detected else "LOW",
    }
    return diagnosis


def generate_ouroboros_report(learnings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a full Ouroboros failure analysis + healing plan."""
    state_abstraction = analyze_state_abstraction_failure(learnings)

    # Additional analysis
    avg_reward_by_game: Dict[str, float] = {}
    for l in learnings:
        total_reward = sum(float(a[1]) for a in l.get("best_actions", []))
        avg_reward_by_game[l["game_id"]] = total_reward

    report = {
        "timestamp": learnings[0]["timestamp"] if learnings else "",
        "games_analyzed": [l["game_id"] for l in learnings],
        "total_experiences": sum(l["total_experiences"] for l in learnings),
        "state_abstraction": state_abstraction,
        "action_preferences": {l["game_id"]: l.get("best_actions", []) for l in learnings},
        "healing_plan": [
            {
                "system": "experiential_agent.py::grid_signature()",
                "issue": "Full-grid hashing prevents generalization",
                "fix": "Implement player-centric state with relative coordinates",
                "priority": 1,
            },
            {
                "system": "experiential_agent.py::ExperientialAgent._plan()",
                "issue": "BFS on 5-state model is trivial, can't find win paths",
                "fix": "Increase state abstraction quality, then use A* with heuristics",
                "priority": 2,
            },
            {
                "system": "CompoundLoop",
                "issue": "Agent takes random actions when model is empty",
                "fix": "Systematic sweep pattern for initial exploration (row-major action sequence)",
                "priority": 3,
            },
        ],
        "principles_for_cohezion": [
            "State abstraction must be invariant to irrelevant transformations (camera position vs scene content)",
            "Exploration should be systematic before stochastic (sweep > random)",
            "Player/object position is the key latent variable in interactive grid worlds",
            "ARC-AGI-3 tests the same core generalization as ARC-AGI-2, but with temporal dynamics",
        ],
    }
    return report


def update_cohezion_skills(report: Dict[str, Any]) -> None:
    """Feed learnings into PRIME skill system."""
    skill_path = Path("src/cohezion/skills/ARC_INTERACTIVE_REASONING.md")

    content = f"""# ARC Interactive Reasoning Skill

**Auto-generated from experiential learning spike**
**Date:** {report['timestamp']}

## Principles Learned

{chr(10).join(f"- {p}" for p in report['principles_for_cohezion'])}

## Known Failure Modes

### State Abstraction Failure
- **Symptom:** {report['state_abstraction']['symptom']}
- **Root Cause:** {report['state_abstraction']['root_cause']}
- **Healing Action:** {report['state_abstraction']['healing_action']}

## Action Preferences (Empirical)

"""
    for game, actions in report["action_preferences"].items():
        content += f"\n### {game}\n"
        for action, reward in actions:
            content += f"- `{action}`: avg reward = {reward:.4f}\n"

    content += "\n## Recommended Exploration Strategy\n\n"
    for heal in report["healing_plan"]:
        content += f"\n### Priority {heal['priority']}: {heal['system']}\n"
        content += f"- **Issue:** {heal['issue']}\n"
        content += f"- **Fix:** {heal['fix']}\n"

    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(content)
    logger.info(f"Updated Cohezion skill: {skill_path}")


def update_mycelium_map(report: Dict[str, Any]) -> None:
    """Distribute knowledge to Mycelium for cross-project use."""
    mycelium_entry = {
        "source": "arc_agi_3_experiential_spike",
        "type": "interactive_reasoning",
        "learnings": report["principles_for_cohezion"],
        "failure_patterns": [report["state_abstraction"]["symptom"]],
        "timestamp": report["timestamp"],
        "applicable_domains": [
            "arc_prize_2026",
            "interactive_agents",
            "grid_world_navigation",
            "exploration_strategy",
        ],
    }

    map_path = Path("data/mycelium/arc_interactive_map.jsonl")
    map_path.parent.mkdir(parents=True, exist_ok=True)
    with open(map_path, "a") as f:
        f.write(json.dumps(mycelium_entry) + "\n")
    logger.info(f"Updated Mycelium map: {map_path}")


def update_dynamic_levers(report: Dict[str, Any]) -> None:
    """Adjust dynamic levers based on experiential findings."""
    try:
        from cohezion.swarm.dynamic_levers import create_default_lever_system
        lever_system = create_default_lever_system()
        lever_system.pull("deterministic_ratio", 0.05)
        lever_system.push("parallel_discovery_workers", 2)
        lever_system.push("memory_safety_threshold_percent", 5)
        lever_system.set("capability_validation_enabled", 1.0)
        lever_system.save()
        logger.info("Updated dynamic levers from experiential feedback")
    except ImportError:
        logger.warning("Cohezion not available in this venv; skipping dynamic levers")
    except Exception as e:
        logger.warning(f"Dynamic lever update failed: {e}")


def run_feedback_loop() -> None:
    """Main entry: process experiential learnings and feed back to Cohezion."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    learnings = load_cross_project_learnings()
    if not learnings:
        logger.warning("No learnings found. Run experiential_agent.py first.")
        return

    # Ouroboros analysis
    report = generate_ouroboros_report(learnings)

    # Feed into Cohezion subsystems
    update_cohezion_skills(report)
    update_mycelium_map(report)
    update_dynamic_levers(report)

    # Save report
    report_path = Path("data/arc_agi_3/ouroboros_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))

    logger.info(f"Experiential feedback loop complete. Report saved to {report_path}")
    logger.info(f"Key finding: {report['state_abstraction']['root_cause']}")


if __name__ == "__main__":
    run_feedback_loop()
