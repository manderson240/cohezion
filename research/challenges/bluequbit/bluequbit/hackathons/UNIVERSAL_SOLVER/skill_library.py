"""
BlueQubit Skill Library
Transferable skills from hackathon experiences

Skills are organized by category and tagged for easy discovery.
"""

SKILL_LIBRARY = {
    "skills": {
        "mps_simulation": {
            "name": "Matrix Product State Simulation",
            "description": "Simulate quantum circuits using MPS to avoid exponential memory",
            "tags": ["simulation", "scalability", "tensor-networks"],
            "difficulty": "advanced",
            "applies_to": ["peaked_circuits", "large_systems"],
            "key_insights": [
                "Bond dimension χ controls accuracy vs speed tradeoff",
                "Linear scaling with qubits (vs exponential)",
                "SVD truncation at each step",
                "Renormalization every ~50 gates",
            ],
            "success_rate": "100%",
            "source": "Little Dimple challenge",
        },
        "heavy_output_detection": {
            "name": "Heavy Output Detection",
            "description": "Identify high-probability bitstrings from peaked distributions",
            "tags": ["measurement", "statistics", "peaked-circuits"],
            "difficulty": "intermediate",
            "key_insights": [
                "Use high shots (100k+) for statistical significance",
                "SNR quantifies peak prominence",
                "SETI protocol: 250k shots minimum",
            ],
            "success_rate": "95%",
            "source": "Little Dimple challenge",
        },
        "async_submission": {
            "name": "Asynchronous Job Submission",
            "description": "Submit circuits non-blocking with polling",
            "tags": ["performance", "workflow", "monitoring"],
            "difficulty": "intermediate",
            "key_insights": [
                "Enables parallel submissions",
                "Poll with bq.get(job_id)",
                "Cancel long jobs with bq.cancel()",
            ],
            "success_rate": "99%",
        },
        "challenge_type_detection": {
            "name": "Automatic Challenge Classification",
            "description": "Detect challenge type from description and circuit",
            "tags": ["classification", "strategy-selection", "auto"],
            "difficulty": "intermediate",
            "key_insights": [
                "Keyword-based initial classification",
                "Circuit depth indicates variational",
                "Fallback to peaked if uncertain",
            ],
            "success_rate": "85%",
        },
    },
    "metadata": {"version": "1.0", "total_skills": 4, "last_updated": "2026-04-01"},
}


def get_skill(skill_name: str) -> dict:
    """Get a specific skill from the library."""
    return SKILL_LIBRARY["skills"].get(skill_name, {})


def get_skills_by_tag(tag: str) -> list:
    """Get all skills with a specific tag."""
    return [skill for skill in SKILL_LIBRARY["skills"].values() if tag in skill.get("tags", [])]


if __name__ == "__main__":
    print("BlueQubit Skill Library")
    print(f"Total skills: {SKILL_LIBRARY['metadata']['total_skills']}")

    for skill_id, skill in SKILL_LIBRARY["skills"].items():
        print(f"  - {skill_id}: {skill['name']}")
