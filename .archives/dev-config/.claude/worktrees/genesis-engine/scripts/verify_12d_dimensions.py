
from cohezion.core.persistence.surreal_client import PhysicsState


def verify_12d():
    state = PhysicsState(
        physics=0.9,
        biology=0.8,
        logic=0.95,
        quantum=0.7,
        field=0.6,
        control=1.0,
        novelty=0.9,
        precipitation=0.95,  # The new 12th dimension
    )

    vec = state.to_array()
    print(f"Vector Length: {len(vec)}")
    print(f"Vector Data: {vec}")

    assert len(vec) == 12, f"Expected 12 dimensions, got {len(vec)}"

    # Check dictionary mapping
    d = state.to_dict()
    print(f"Dictionary Mapping: {d}")
    assert "dim_12_precipitation" in d, "Precipitation field missing from 12D vector map"

    print("\n✅ 12D PhysicsState VERIFIED: Precipitation Brane Active.")


if __name__ == "__main__":
    verify_12d()
