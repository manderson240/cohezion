#!/usr/bin/env python3
"""
Refine Skill (Reward Action)
===========================
Allows an agent to append a validated insight to a skill file.
This is the "Reward" for completing a task successfully.
"""

import datetime
import sys
from pathlib import Path


# Add scripts/drivers to path to import pipeline
sys.path.append(str(Path(__file__).parent))
from skill_improvement_pipeline import RZeroSkillPipeline


def refine_skill(skill_path_str: str, insight: str, agent_name: str):
    path = Path(skill_path_str)
    if not path.exists():
        print(f"Error: Skill {path} not found.")
        return False

    content = path.read_text()

    # Check if we already have a REFINEMENTS section
    header = "## SWARM REFINEMENTS"
    entry = f"\n- **{datetime.date.today()} ({agent_name})**: {insight}"

    if header in content:
        # Append to existing section
        parts = content.split(header)
        new_content = parts[0] + header + entry + parts[1]
    else:
        # Append new section at the end
        new_content = content + f"\n\n{header}{entry}\n"

    # Write back
    path.write_text(new_content)
    print(f"✅ Skill {path.name} refined by {agent_name}.")

    # Verify Quality
    pipeline = RZeroSkillPipeline(path.parent)
    eval_result = pipeline.evaluate_skill(path)
    print(f"📊 New Quality Score: {eval_result.quality_score:.1f}/100")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: uv run refine_skill.py <path> <insight> [agent_name]")
        sys.exit(1)

    path = sys.argv[1]
    insight = sys.argv[2]
    agent = sys.argv[3] if len(sys.argv) > 3 else "AnonymousSwarm"

    refine_skill(path, insight, agent)
