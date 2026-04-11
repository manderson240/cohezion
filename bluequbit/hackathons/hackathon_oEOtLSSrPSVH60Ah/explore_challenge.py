"""
BlueQubit Challenge Explorer
Explore ongoing hackathon oEOtLSSrPSVH60Ah
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "code_templates"))

from dotenv import load_dotenv
import bluequbit
import qiskit


def explore_challenge():
    """Explore the ongoing hackathon challenge."""
    project_root = Path(__file__).parent.parent.parent
    load_dotenv(project_root / ".env")

    bq = bluequbit.init()

    print("=" * 70)
    print("BlueQubit Challenge Explorer")
    print("Challenge: oEOtLSSrPSVH60Ah")
    print("=" * 70)

    # Try to get challenge info
    print("\n1. Attempting to get peaked circuit...")
    try:
        for difficulty in [1, 5, 10]:
            try:
                circuit = bq.get_peaked_circuit(difficulty)
                print(f"   ✓ Difficulty {difficulty}: {circuit.num_qubits} qubits")
                return circuit
            except Exception as e:
                print(f"   ℹ Difficulty {difficulty}: {type(e).__name__}")
    except Exception as e:
        print(f"   ✗ get_peaked_circuit not available: {e}")

    # Test search for challenge-related jobs
    print("\n2. Searching for recent jobs...")
    try:
        jobs = bq.search()
        print(f"   ✓ Found {len(jobs)} recent jobs")
        if jobs:
            print(f"   Latest job: {jobs[0].get('job_id', 'N/A')}")
    except Exception as e:
        print(f"   ℹ Search: {e}")

    # Try various challenge endpoints
    print("\n3. Testing challenge access...")
    print("   Challenge appears to require specific access or may be in different phase")

    print("\n" + "=" * 70)
    print("Exploration Complete")
    print("=" * 70)
    print("\nNote: Challenge oEOtLSSrPSVH60Ah may require:")
    print("  - Active participation registration")
    print("  - Specific challenge phase (not yet started)")
    print("  - Different API endpoints")
    print("\nRecommendation: Use this as practice environment")
    print("  - Test SDK methods")
    print("  - Practice circuit submission")
    print("  - Validate heavy output detection")


if __name__ == "__main__":
    explore_challenge()
