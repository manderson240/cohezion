"""
Verification script for Adaptive Template Evolution.
Simulates a retrospective cycle and verifies template patching.
"""

import sys
from pathlib import Path


# Mocking the Python path to include src/
sys.path.append(str(Path(__file__).parent.parent / "src"))

from cohezion.evolution.template_evolver import TemplateEvolver


def verify_evolution():
    evolver = TemplateEvolver()
    template_path = Path("/home/mike-anderson/dev/cohezion/templates/skill.md")

    print("--- Initial Template State ---")
    initial_content = template_path.read_text()
    print(f"Version: {re_search_version(initial_content)}")

    simulated_retro = """
    # Retrospective: Mission X
    We discovered that the 12D state vector requires a mandatory 'Brane' field.

    [TEMPLATE IMPROVEMENT]
    ### 12D Brane Requirement
    Standardize the use of the `brane` parameter in all 12D state vector operations to prevent manifold collapse.
    """

    print("\n--- Simulating Retrospective Extraction ---")
    if evolver.analyze_retrospective(simulated_retro):
        print("✅ Template evolution successful.")
    else:
        print("❌ Template evolution failed.")

    print("\n--- Final Template State ---")
    final_content = template_path.read_text()
    print(f"Version: {re_search_version(final_content)}")

    if "12D Brane Requirement" in final_content:
        print("✅ Pattern found in template.")
    else:
        print("❌ Pattern missing from template.")


def re_search_version(content: str) -> str:
    import re

    match = re.search(r"## VERSION\n(v\d+\.\d+)", content)
    return match.group(1) if match else "Unknown"


if __name__ == "__main__":
    verify_evolution()
