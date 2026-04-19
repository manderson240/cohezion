"""
Submission Manager

Manages limited submissions (e.g., 5) with maximum confidence.
Pre-validates everything before using submissions.
"""

import json
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ConfidenceLevel(Enum):
    """Confidence levels for submissions."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4


@dataclass
class PreSubmissionValidation:
    """Validation results before submission."""

    passed: bool
    checks: Dict[str, bool]
    warnings: List[str]
    recommendation: str


class SubmissionManager:
    """
    Manages limited submissions carefully.

    Strategy:
    1. Extensive pre-validation (free testing)
    2. Confidence threshold gates
    3. Backup plans for each submission
    4. Progress tracking
    """

    def __init__(self, max_submissions: int = 5):
        """
        Initialize submission manager.

        Args:
            max_submissions: Maximum allowed submissions
        """
        self.max_submissions = max_submissions
        self.used = 0
        self.submissions: List[Dict] = []
        self.validation_history: List[PreSubmissionValidation] = []

        print(f"✓ SubmissionManager initialized")
        print(f"  Max submissions: {max_submissions}")

    def pre_validate(
        self,
        result: Dict,
        min_snr: float = 2.0,
        min_probability: float = 0.05,
        require_convergence: bool = True,
    ) -> PreSubmissionValidation:
        """
        Pre-validate result before submission (FREE).

        Args:
            result: Proposed result
            min_snr: Minimum SNR threshold
            min_probability: Minimum probability
            require_convergence: Require convergence

        Returns:
            PreSubmissionValidation with recommendation
        """
        checks = {}
        warnings = []

        # Check 1: SNR
        snr = result.get("snr", 0)
        if snr >= min_snr:
            checks["snr"] = True
        else:
            checks["snr"] = False
            warnings.append(f"SNR {snr:.2f} < {min_snr}")

        # Check 2: Probability
        prob = result.get("probability", 0)
        if prob >= min_probability:
            checks["probability"] = True
        else:
            checks["probability"] = False
            warnings.append(f"Probability {prob:.4f} < {min_probability}")

        # Check 3: Convergence (if applicable)
        if require_convergence and "converged" in result:
            if result["converged"]:
                checks["convergence"] = True
            else:
                checks["convergence"] = False
                warnings.append("Not converged")
        else:
            checks["convergence"] = True  # Skip if not applicable

        # Check 4: No errors
        if "error" not in result:
            checks["no_errors"] = True
        else:
            checks["no_errors"] = False
            warnings.append(f"Error: {result['error']}")

        # Determine recommendation
        all_passed = all(checks.values())

        if all_passed:
            recommendation = "SUBMIT"
        elif len(warnings) <= 1:
            recommendation = "SUBMIT_WITH_CAUTION"
        else:
            recommendation = "DO_NOT_SUBMIT"

        return PreSubmissionValidation(
            passed=all_passed, checks=checks, warnings=warnings, recommendation=recommendation
        )

    def validate_and_submit(
        self, result: Dict, confidence_threshold: str = "HIGH"
    ) -> Optional[Dict]:
        """
        Validate and submit if confidence is high enough.

        Args:
            result: Result to submit
            confidence_threshold: Minimum confidence level

        Returns:
            Submission record if submitted, None otherwise
        """
        print(f"\n{'=' * 70}")
        print(f"Submission {self.used + 1}/{self.max_submissions}")
        print(f"{'=' * 70}")

        # Check limit
        if self.used >= self.max_submissions:
            print(f"❌ LIMIT REACHED: {self.used}/{self.max_submissions}")
            return None

        # Pre-validate
        validation = self.pre_validate(result)
        self.validation_history.append(validation)

        print(f"Validation:")
        for check, passed in validation.checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")

        if validation.warnings:
            print(f"\nWarnings:")
            for warning in validation.warnings:
                print(f"  ⚠️ {warning}")

        print(f"\nRecommendation: {validation.recommendation}")

        # Check confidence
        confidence = result.get("confidence", "UNKNOWN")
        confidence_levels = ["LOW", "MEDIUM", "HIGH", "VERY HIGH"]

        if confidence not in confidence_levels:
            print(f"❌ Unknown confidence: {confidence}")
            return None

        current_level = confidence_levels.index(confidence)
        required_level = confidence_levels.index(confidence_threshold)

        if current_level < required_level:
            print(f"❌ Confidence {confidence} < {confidence_threshold}")
            return None

        # Submit if validation passed
        if validation.recommendation in ["SUBMIT", "SUBMIT_WITH_CAUTION"]:
            self.used += 1

            submission = {
                "number": self.used,
                "timestamp": time.time(),
                "result": result,
                "validation": {
                    "passed": validation.passed,
                    "checks": validation.checks,
                    "warnings": validation.warnings,
                },
                "confidence": confidence,
            }

            self.submissions.append(submission)

            print(f"\n✅ SUBMITTED #{self.used}")
            print(f"   Confidence: {confidence}")
            print(f"   Result: {json.dumps(result, indent=2)}")

            return submission
        else:
            print(f"\n❌ NOT SUBMITTED")
            print(f"   Fix issues and retry")
            return None

    def get_status(self) -> Dict:
        """Get current submission status."""
        return {
            "used": self.used,
            "remaining": self.max_submissions - self.used,
            "max": self.max_submissions,
            "percentage": (self.used / self.max_submissions) * 100,
            "submissions": self.submissions,
        }

    def get_best_submission(self) -> Optional[Dict]:
        """Get best submission so far."""
        if not self.submissions:
            return None

        # For peaked circuits: highest SNR
        if any("snr" in s["result"] for s in self.submissions):
            return max(self.submissions, key=lambda s: s["result"].get("snr", 0))

        # For QAOA: lowest energy
        if any("optimal_energy" in s["result"] for s in self.submissions):
            return min(
                self.submissions, key=lambda s: s["result"].get("optimal_energy", float("inf"))
            )

        return self.submissions[-1]  # Last submission

    def should_continue(self) -> bool:
        """Check if we should continue submitting."""
        return self.used < self.max_submissions

    def save_state(self, filename: str = "submission_state.json"):
        """Save submission state to file."""
        state = self.get_status()
        with open(filename, "w") as f:
            json.dump(state, f, indent=2)
        print(f"✓ State saved: {filename}")

    def load_state(self, filename: str = "submission_state.json"):
        """Load submission state from file."""
        try:
            with open(filename) as f:
                state = json.load(f)
            self.used = state.get("used", 0)
            self.submissions = state.get("submissions", [])
            print(f"✓ State loaded: {filename}")
            print(f"  Used: {self.used}/{self.max_submissions}")
        except FileNotFoundError:
            print(f"⚠️ No state file found: {filename}")


def demo():
    """Demonstrate submission manager."""
    print("=" * 70)
    print("Submission Manager Demo")
    print("=" * 70)

    manager = SubmissionManager(max_submissions=5)

    # Test case 1: Good result
    print("\nTest 1: High confidence result")
    result1 = {"bitstring": "10101010", "probability": 0.15, "snr": 5.2, "confidence": "HIGH"}

    submission1 = manager.validate_and_submit(result1, confidence_threshold="MEDIUM")

    # Test case 2: Low confidence (should be blocked)
    print("\nTest 2: Low confidence result")
    result2 = {"bitstring": "00000000", "probability": 0.02, "snr": 1.5, "confidence": "LOW"}

    submission2 = manager.validate_and_submit(result2, confidence_threshold="HIGH")

    # Status
    status = manager.get_status()
    print(f"\n{'=' * 70}")
    print("Final Status")
    print(f"{'=' * 70}")
    print(f"Used: {status['used']}/{status['max']}")
    print(f"Remaining: {status['remaining']}")
    print(f"Best submission: {manager.get_best_submission()}")

    return manager


if __name__ == "__main__":
    demo()
