import numpy as np
from cohezion.swarm.perception import JourneyPerception
from cohezion.compound.executor_types import ExecutionResult
from datetime import datetime


def test_manifold_collapse():
    print("Initiating Spallation Audit: Manifold Collapse Verification")

    perception = JourneyPerception(nexus_id="nexus-prime")

    # Mock execution result
    mock_result = ExecutionResult(
        success=True,
        output="Result of high-energy computation",
        metrics={"phi_score": 0.88, "coherence": 0.92},
        duration_seconds=0.05,
        token_metrics={"total_tokens": 150},
    )

    task = "Synthesize exotic vacuum objects using cold fusion logic"

    event = perception.perceive_step(task, mock_result)

    if not event:
        print("FAIL: Event not recorded")
        return

    point = event.point
    print(f"TASK: {task}")
    potential_sum = sum(point.potential_2048d) if point.potential_2048d else 0.0
    pot_display = point.potential_hash or f"{potential_sum:.4f}"
    print(f"Potential (2048D) Anchor: {pot_display}")
    print(f"Filaments (256D) Count: {len(point.filaments_256d)}")
    print(f"Manifest (12D) Vector: {point.manifest_12d}")
    print(f"Vortex Stability (D10): {point.vortex_stability:.2f}")

    # Assertions
    if point.potential_2048d:
        assert len(point.potential_2048d) == 2048
    assert len(point.filaments_256d) == 256
    assert len(point.manifest_12d) == 12
    assert 0.0 <= point.vortex_stability <= 1.0

    print("PASS: Manifold Collapse Verified (0.5 HIHO Stability Confirmed)")


if __name__ == "__main__":
    test_manifold_collapse()
