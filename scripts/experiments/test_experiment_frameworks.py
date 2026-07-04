#!/usr/bin/env python3
"""
Test experiment frameworks without requiring bash/infrastructure.

Validates the structure and logic of exp_UUUU2, exp_VVVV2, exp_WWWW2
frameworks before they're executed.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# Import experiment modules
sys.path.insert(0, str(Path(__file__).parent))

try:
    import exp_UUUU2_sycophancy_calibration as exp_uuuu2
    import exp_VVVV2_domain_code_expansion as exp_vvvv2
    import exp_WWWW2_eval_text_diversity as exp_wwww2
except ImportError as e:
    print(f"Error importing experiment modules: {e}")
    sys.exit(1)


# ============================================================================
# Validation Functions
# ============================================================================


def validate_experiment_structure(module: object, exp_id: str) -> bool:
    """Validate that an experiment module has required structure."""

    required_attributes = [
        "EXPERIMENT_ID",
        "EXPERIMENT_TITLE",
        "ROUND",
        "run_experiment",
        "log_result",
    ]

    missing = [attr for attr in required_attributes if not hasattr(module, attr)]

    if missing:
        print(f"  ✗ {exp_id}: Missing required attributes: {missing}")
        return False

    print(f"  ✓ {exp_id}: Structure valid")
    return True


def validate_experiment_execution(module: object, exp_id: str) -> bool:
    """Test that experiment can be run without errors."""

    try:
        result = module.run_experiment()

        # Validate result object
        if result is None:
            print(f"  ✗ {exp_id}: run_experiment() returned None")
            return False

        required_fields = ["experiment_id", "status", "to_dict"]

        missing_fields = [
            f for f in required_fields if not hasattr(result, f)
        ]

        if missing_fields:
            print(f"  ✗ {exp_id}: Result missing fields: {missing_fields}")
            return False

        # Try to convert to dict
        result_dict = result.to_dict()

        if not isinstance(result_dict, dict):
            print(f"  ✗ {exp_id}: to_dict() didn't return a dict")
            return False

        print(f"  ✓ {exp_id}: Execution successful, result is valid")
        return True

    except Exception as e:
        print(f"  ✗ {exp_id}: Execution failed with error: {e}")
        return False


def validate_result_logging(module: object, exp_id: str) -> bool:
    """Test that results can be logged without errors."""

    try:
        result = module.run_experiment()
        test_output_path = Path("/tmp") / f"{exp_id}_test_result.json"

        module.log_result(result, output_path=test_output_path)

        # Verify file was created
        if not test_output_path.exists():
            print(f"  ✗ {exp_id}: Result file not created")
            return False

        # Verify file contains valid JSON
        with open(test_output_path) as f:
            logged_data = json.load(f)

        if "experiment_id" not in logged_data:
            print(f"  ✗ {exp_id}: Logged data missing experiment_id")
            return False

        # Cleanup
        test_output_path.unlink()

        print(f"  ✓ {exp_id}: Result logging successful")
        return True

    except Exception as e:
        print(f"  ✗ {exp_id}: Logging failed with error: {e}")
        return False


def validate_metrics_computation(module: object, exp_id: str) -> bool:
    """Test that metrics are computed correctly."""

    try:
        result = module.run_experiment()
        result_dict = result.to_dict()

        # Check for essential metrics based on experiment type
        if exp_id == "exp_UUUU2":
            # Should have separations with ratio
            if "mean_ratio" not in result_dict:
                print(f"  ✗ {exp_id}: Missing mean_ratio metric")
                return False
            print(f"  ✓ {exp_id}: Metrics computed (mean_ratio={result_dict['mean_ratio']:.2f}x)")

        elif exp_id == "exp_VVVV2":
            # Should have recommendation
            if "recommendation" not in result_dict:
                print(f"  ✗ {exp_id}: Missing recommendation")
                return False
            print(f"  ✓ {exp_id}: Metrics computed (recommendation={result_dict['recommendation']})")

        elif exp_id == "exp_WWWW2":
            # Should have variance comparison
            if "treatment_better_generalization" not in result_dict:
                print(f"  ✗ {exp_id}: Missing generalization comparison")
                return False
            print(f"  ✓ {exp_id}: Metrics computed (generalization_improvement={result_dict['treatment_better_generalization']})")

        return True

    except Exception as e:
        print(f"  ✗ {exp_id}: Metrics computation failed: {e}")
        return False


# ============================================================================
# Test Suite
# ============================================================================


def run_all_tests() -> dict[str, bool]:
    """Run all validation tests."""

    print("=" * 70)
    print("EXPERIMENT FRAMEWORK VALIDATION")
    print("=" * 70)

    experiments = [
        ("exp_UUUU2", exp_uuuu2),
        ("exp_VVVV2", exp_vvvv2),
        ("exp_WWWW2", exp_wwww2),
    ]

    results = {}

    for exp_id, module in experiments:
        print(f"\n{exp_id}: {module.EXPERIMENT_TITLE}")
        print("-" * 70)

        # Test 1: Structure
        struct_ok = validate_experiment_structure(module, exp_id)
        results[f"{exp_id}_structure"] = struct_ok

        # Test 2: Execution
        exec_ok = validate_experiment_execution(module, exp_id)
        results[f"{exp_id}_execution"] = exec_ok

        # Test 3: Logging
        log_ok = validate_result_logging(module, exp_id)
        results[f"{exp_id}_logging"] = log_ok

        # Test 4: Metrics
        metrics_ok = validate_metrics_computation(module, exp_id)
        results[f"{exp_id}_metrics"] = metrics_ok

    return results


# ============================================================================
# Summary Report
# ============================================================================


def print_summary(results: dict[str, bool]) -> None:
    """Print test summary."""

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    experiments = [
        ("exp_UUUU2", ["structure", "execution", "logging", "metrics"]),
        ("exp_VVVV2", ["structure", "execution", "logging", "metrics"]),
        ("exp_WWWW2", ["structure", "execution", "logging", "metrics"]),
    ]

    all_pass = True

    for exp_id, tests in experiments:
        exp_results = [results.get(f"{exp_id}_{test}", False) for test in tests]
        status = "✓ PASS" if all(exp_results) else "✗ FAIL"
        all_pass = all_pass and all(exp_results)

        print(f"\n{exp_id}: {status}")
        for test in tests:
            test_result = results.get(f"{exp_id}_{test}", False)
            symbol = "✓" if test_result else "✗"
            print(f"  {symbol} {test}")

    print("\n" + "=" * 70)
    if all_pass:
        print("✓ ALL TESTS PASSED - Experiments ready for execution")
    else:
        print("✗ SOME TESTS FAILED - Review above for details")
    print("=" * 70)

    return all_pass


# ============================================================================
# Main
# ============================================================================


def main():
    """Run validation tests."""
    results = run_all_tests()
    all_pass = print_summary(results)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
