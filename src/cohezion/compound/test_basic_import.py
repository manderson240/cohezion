#!/usr/bin/env python3
"""Basic import test for our new components."""

import sys
from pathlib import Path


# Add the project root to the path (so we can import cohezion.*)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that we can import our new components."""
    try:
        # Test importing our new modules
        from cohezion.compound.tdd_adversarial import (
            get_adversarial_review_system,  # noqa: F401
            get_tdd_adversarial_coordinator,  # noqa: F401
            get_tdd_integration,  # noqa: F401
        )

        print("✓ Successfully imported TDD and Adversarial Review components")

        # Test importing daemon components
        from cohezion.compound.daemon import get_workflow_initializer  # noqa: F401

        print("✓ Successfully imported daemon components")

        # Test that they're in the compound module
        import cohezion.compound  # noqa: F401

        print("✓ Successfully accessed compound module")

        print("✓ All basic import tests passed")
        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
