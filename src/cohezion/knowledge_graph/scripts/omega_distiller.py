#!/usr/bin/env python3
"""
OMEGA Distiller v2.0 - Autonomous Skill & Policy Generation.

Parses KEY_LEARNINGS.md and propagates relevant insights into:
1. SKILL_PRIME.md files (Nondeterministic skills)
2. src/cohezion/policies/*.py files (Deterministic policies)
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("omega-distiller")

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent.parent.parent
LEARNINGS_PATH = PROJECT_ROOT / "src/cohezion/knowledge_graph/KEY_LEARNINGS.md"
SKILLS_DIR = PROJECT_ROOT / "src/cohezion/skills"
POLICIES_DIR = PROJECT_ROOT / "src/cohezion/policies"
PROCESSED_LOG = PROJECT_ROOT / ".omega_processed_learnings.json"

# Simple keyword-to-skill mapping
SKILL_MAP = {
    "Model": "MODEL_ROUTING_PRIME.md",
    "Manifold": "MANIFOLD_PHYSICS_OPTIMIZATION_PRIME.md",
    "Kaggle": "KAGGLE_BLACKWELL_RUNNER_PRIME.md",
    "Surreal": "SURREALDB_OPERATIONS_PRIME.md",
    "Skill": "COMPOUND_SELF_IMPROVEMENT_PRIME.md",
    "Async": "LAZY_INFRASTRUCTURE_PRIME.md",
    "MCP": "MCP_OPTIMIZATION_PRIME.md",
    "AIMO": "MATH_REASONING_SWARM_PRIME.md",
    "Fleet": "FLEET_SYNCHRONIZATION_PRIME.md",
    "Integrity": "MANIFOLD_INTEGRITY_PRIME.md",
    "Data Mesh": "DATA_MESH_ARCHITECT_PRIME.md",
}


def load_processed():
    if PROCESSED_LOG.exists():
        with open(PROCESSED_LOG) as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()
    return set()


def save_processed(processed):
    with open(PROCESSED_LOG, "w") as f:
        json.dump(list(processed), f, indent=2)


def generate_policy_stub(learning_id: str, title: str, body: str):
    """Generate a deterministic Python policy stub for a high-coherence insight."""
    safe_title = re.sub(r"[^a-zA-Z0-9]", "_", title).lower()
    policy_path = POLICIES_DIR / f"policy_{learning_id}_{safe_title}.py"

    content = f'''"""
Deterministic Policy distilled from Learning {learning_id}.
Title: {title}
Date: {datetime.now().strftime("%Y-%m-%d")}
"""

def execute_policy(context: dict) -> dict:
    """
    Auto-generated policy logic.
    Original Insight: {body[:200]}...
    """
    # TODO: Implement deterministic logic based on learning
    return {{"success": True, "source": "learning_{learning_id}"}}
'''
    with open(policy_path, "w") as f:
        f.write(content)
    logger.info(f"  ✅ Distilled deterministic policy: {policy_path.name}")


def distill():
    if not LEARNINGS_PATH.exists():
        logger.error(f"Learnings file not found at {LEARNINGS_PATH}")
        return

    content = LEARNINGS_PATH.read_text()
    blocks = re.split(r"### Learning (\d+):", content)

    processed = load_processed()
    new_processed = set(processed)

    for i in range(1, len(blocks), 2):
        learning_id = blocks[i]
        block_content = blocks[i + 1]

        if learning_id in processed:
            continue

        lines = block_content.strip().splitlines()
        if not lines:
            continue

        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()

        logger.info(f"Distilling Learning {learning_id}: {title}")

        # Policy Distillation (Level 2)
        # Check for high-coherence or explicit tags in body
        if "[POLICY]" in body or "[HARNESS]" in body or "coherence: 0.9" in body.lower():
            generate_policy_stub(learning_id, title, body)

        # Skill Refinement (Nondeterministic)
        targets = []
        for keyword, skill_file in SKILL_MAP.items():
            if keyword.lower() in title.lower() or keyword.lower() in body.lower():
                targets.append(skill_file)

        for skill_file in targets:
            skill_path = SKILLS_DIR / skill_file
            if not skill_path.exists():
                continue

            with open(skill_path, "a") as f:
                f.write(f"\n\n## AUTO-REFINEMENT (Learning {learning_id})\n")
                f.write(f"*   **Insight**: {title}\n")
                f.write(f"*   **Details**: {body}\n")
                f.write(f"*   **Date**: {datetime.now().strftime('%Y-%m-%d')}\n")
            logger.info(f"  ✅ Propagated to {skill_file}")

        new_processed.add(learning_id)

    save_processed(new_processed)
    logger.info("✅ OMEGA Distillation cycle complete.")


if __name__ == "__main__":
    distill()
