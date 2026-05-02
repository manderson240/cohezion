import json
import os
import sys


def main():
    """
    Enforces 12D manifold integrity in data artifacts.
    """
    universe_dir = "data/universe/"
    required_dimensions = [
        "x",
        "y",
        "z",
        "time",
        "physics",
        "biology",
        "logic",
        "quantum",
        "field",
        "control",
        "novelty",
        "precipitation",
    ]

    if not os.path.exists(universe_dir):
        # If no artifacts exist, exit with status 0 as requested.
        sys.exit(0)

    for root, _, files in os.walk(universe_dir):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    print(f"CRITICAL: Failed to parse JSON at {file_path}: {e}")
                    sys.exit(1)

                if "physics_state" in data:
                    physics_state = data["physics_state"]

                    if not isinstance(physics_state, dict):
                        print(f"ERROR: 'physics_state' at {file_path} is not a dictionary.")
                        sys.exit(1)

                    # Verify exact dimensions
                    actual_dimensions = list(physics_state.keys())
                    missing = [d for d in required_dimensions if d not in physics_state]
                    extra = [d for d in actual_dimensions if d not in required_dimensions]

                    if missing or extra or len(actual_dimensions) != 12:
                        error_msg = f"ERROR: Manifold integrity violation in {file_path}\n"
                        if missing:
                            error_msg += f"  Missing dimensions: {missing}\n"
                        if extra:
                            error_msg += f"  Unexpected dimensions: {extra}\n"
                        if len(actual_dimensions) != 12:
                            error_msg += (
                                f"  Expected 12 dimensions, found {len(actual_dimensions)}.\n"
                            )
                        print(error_msg)
                        sys.exit(1)

                    # Verify all values are floats/ints (JSON numbers)
                    invalid_fields = []
                    for k, v in physics_state.items():
                        # We accept int as well because json.load might parse 0.0 as 0
                        if not isinstance(v, (float, int)):
                            invalid_fields.append(f"{k} ({type(v).__name__})")

                    if invalid_fields:
                        print(
                            f"ERROR: Type violation in {file_path}\n  Fields must be numeric: {invalid_fields}"
                        )
                        sys.exit(1)

    # If we reached here, all existing artifacts are valid.
    sys.exit(0)


if __name__ == "__main__":
    main()
