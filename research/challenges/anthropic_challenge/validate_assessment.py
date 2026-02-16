#!/usr/bin/env python3
"""
Assessment Integrity Validator

Validates that the Anthropic Performance Take-Home assessment solution
is legitimate by checking for known cheat patterns before running
submission tests.

Usage:
    python validate_assessment.py          # Full validation
    python validate_assessment.py --fix    # Fix known issues and re-validate

Known cheat patterns (from upstream README):
  1. N_CORES changed from 1 to >1 (multicore exploit)
  2. tests/ folder modified
  3. problem.py constraints altered (SLOT_LIMITS, SCRATCH_SIZE, VLEN)
"""

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

CHALLENGE_DIR = Path(__file__).parent
UPSTREAM_CONSTRAINTS = {
    "N_CORES": 1,
    "VLEN": 8,
    "SCRATCH_SIZE": 1536,
}

# Performance thresholds from upstream README
THRESHOLDS = {
    "baseline": 147734,
    "starter_code": 18532,
    "opus4_many_hours": 2164,
    "opus45_casual": 1790,
    "opus45_2hr": 1579,
    "sonnet45_many_hours": 1548,
    "opus45_11hr": 1487,
    "opus45_improved_harness": 1363,
}

FILES_WITH_N_CORES = [
    "problem.py",
    "frozen_problem.py",
    "tests/frozen_problem.py",
]


class ValidationResult:
    def __init__(self):
        self.checks: list[tuple[str, bool, str]] = []  # (name, passed, detail)

    def add(self, name: str, passed: bool, detail: str = ""):
        self.checks.append((name, passed, detail))

    @property
    def all_passed(self) -> bool:
        return all(passed for _, passed, _ in self.checks)

    def report(self) -> str:
        lines = ["\n=== Assessment Integrity Report ===\n"]
        for name, passed, detail in self.checks:
            status = "PASS" if passed else "FAIL"
            line = f"  [{status}] {name}"
            if detail:
                line += f" -- {detail}"
            lines.append(line)

        lines.append("")
        if self.all_passed:
            lines.append("Result: All integrity checks passed. Solution is valid.")
        else:
            failed = [name for name, passed, _ in self.checks if not passed]
            lines.append(f"Result: {len(failed)} integrity check(s) FAILED.")
            lines.append("Fix issues before submitting. Run with --fix to auto-repair.")
        return "\n".join(lines)


def check_n_cores(result: ValidationResult) -> list[str]:
    """Check that N_CORES = 1 in all relevant files."""
    violations = []
    for rel_path in FILES_WITH_N_CORES:
        filepath = CHALLENGE_DIR / rel_path
        if not filepath.exists():
            result.add(f"N_CORES in {rel_path}", False, "file not found")
            continue
        content = filepath.read_text()
        match = re.search(r"^N_CORES\s*=\s*(\d+)", content, re.MULTILINE)
        if match:
            value = int(match.group(1))
            if value != UPSTREAM_CONSTRAINTS["N_CORES"]:
                result.add(
                    f"N_CORES in {rel_path}",
                    False,
                    f"N_CORES = {value} (must be 1)",
                )
                violations.append(rel_path)
            else:
                result.add(f"N_CORES in {rel_path}", True)
        else:
            result.add(f"N_CORES in {rel_path}", False, "N_CORES not found")
    return violations


def check_slot_limits(result: ValidationResult):
    """Check that SLOT_LIMITS haven't been inflated."""
    expected = {"alu": 12, "valu": 6, "load": 2, "store": 2, "flow": 1, "debug": 64}
    for rel_path in ["problem.py", "frozen_problem.py", "tests/frozen_problem.py"]:
        filepath = CHALLENGE_DIR / rel_path
        if not filepath.exists():
            continue
        content = filepath.read_text()
        passed = True
        for engine, limit in expected.items():
            pattern = rf'"{engine}"\s*:\s*(\d+)'
            match = re.search(pattern, content)
            if match and int(match.group(1)) != limit:
                result.add(
                    f"SLOT_LIMITS[{engine}] in {rel_path}",
                    False,
                    f"got {match.group(1)}, expected {limit}",
                )
                passed = False
        if passed:
            result.add(f"SLOT_LIMITS in {rel_path}", True)


def check_scratch_and_vlen(result: ValidationResult):
    """Check SCRATCH_SIZE and VLEN haven't been changed."""
    for rel_path in ["problem.py", "frozen_problem.py", "tests/frozen_problem.py"]:
        filepath = CHALLENGE_DIR / rel_path
        if not filepath.exists():
            continue
        content = filepath.read_text()
        for param, expected in [("SCRATCH_SIZE", 1536), ("VLEN", 8)]:
            match = re.search(rf"^{param}\s*=\s*(\d+)", content, re.MULTILINE)
            if match:
                value = int(match.group(1))
                result.add(
                    f"{param} in {rel_path}",
                    value == expected,
                    f"got {value}" if value != expected else "",
                )


def check_tests_unmodified(result: ValidationResult):
    """Verify tests/ folder hasn't been modified vs upstream."""
    tests_dir = CHALLENGE_DIR / "tests"
    if not tests_dir.exists():
        result.add("tests/ directory exists", False, "missing")
        return

    # Check that the expected files exist
    expected_files = {"submission_tests.py", "frozen_problem.py", "adversarial.py", "debug_scalar.py"}
    actual_files = {f.name for f in tests_dir.iterdir() if f.is_file()}
    if expected_files <= actual_files:
        result.add("tests/ contains expected files", True)
    else:
        missing = expected_files - actual_files
        result.add("tests/ contains expected files", False, f"missing: {missing}")

    # Check submission_tests.py hasn't been modified (verify key assertions exist)
    sub_tests = (tests_dir / "submission_tests.py").read_text()
    key_patterns = [
        r"class CorrectnessTests",
        r"class SpeedTests",
        r"BASELINE\s*=\s*147734",
        r"cycles\(\)\s*<\s*1487",
    ]
    for pattern in key_patterns:
        match = re.search(pattern, sub_tests, re.IGNORECASE)
        result.add(
            f"submission_tests.py contains '{pattern}'",
            match is not None,
        )


def fix_n_cores(violations: list[str]):
    """Fix N_CORES back to 1 in violated files."""
    for rel_path in violations:
        filepath = CHALLENGE_DIR / rel_path
        content = filepath.read_text()
        fixed = re.sub(
            r"^(N_CORES\s*=\s*)\d+",
            r"\g<1>1",
            content,
            flags=re.MULTILINE,
        )
        filepath.write_text(fixed)
        print(f"  Fixed: {rel_path} -> N_CORES = 1")


def run_submission_tests() -> tuple[bool, int | None]:
    """Run the official submission tests and extract cycle count."""
    print("\n=== Running Submission Tests ===\n")
    try:
        proc = subprocess.run(
            [sys.executable, "tests/submission_tests.py"],
            cwd=str(CHALLENGE_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = proc.stdout + proc.stderr
        print(output)

        # Extract cycle count
        cycle_match = re.search(r"CYCLES:\s*(\d+)", output)
        cycles = int(cycle_match.group(1)) if cycle_match else None

        passed = proc.returncode == 0
        return passed, cycles
    except subprocess.TimeoutExpired:
        print("  TIMEOUT: submission tests took >120s")
        return False, None
    except Exception as e:
        print(f"  ERROR: {e}")
        return False, None


def report_performance(cycles: int | None):
    """Report which thresholds are beaten."""
    if cycles is None:
        print("\nCould not determine cycle count.")
        return

    print(f"\n=== Performance Report ({cycles} cycles) ===\n")
    print(f"  Speedup over baseline: {THRESHOLDS['baseline'] / cycles:.1f}x\n")

    ordered = sorted(THRESHOLDS.items(), key=lambda x: x[1], reverse=True)
    for name, threshold in ordered:
        beaten = cycles < threshold
        status = "BEATEN" if beaten else "      "
        print(f"  [{status}] {name}: {threshold} cycles")

    print()
    if cycles < 1487:
        print("  -> Exceeds Claude Opus 4.5 (11hr) threshold!")
        print("  -> Eligible for performance-recruiting@anthropic.com")
    elif cycles < 1790:
        print("  -> Matches best human 2-hour performance range")
    elif cycles < THRESHOLDS["baseline"]:
        print("  -> Solution shows optimization over baseline")


def main():
    parser = argparse.ArgumentParser(description="Validate assessment integrity")
    parser.add_argument("--fix", action="store_true", help="Auto-fix known issues")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running submission tests")
    args = parser.parse_args()

    result = ValidationResult()

    # 1. Check N_CORES
    print("Checking N_CORES constraint...")
    violations = check_n_cores(result)

    # 2. Check SLOT_LIMITS
    print("Checking SLOT_LIMITS...")
    check_slot_limits(result)

    # 3. Check SCRATCH_SIZE and VLEN
    print("Checking SCRATCH_SIZE and VLEN...")
    check_scratch_and_vlen(result)

    # 4. Check tests/ integrity
    print("Checking tests/ folder integrity...")
    check_tests_unmodified(result)

    # Print integrity report
    print(result.report())

    # Auto-fix if requested
    if args.fix and violations:
        print("\n=== Applying Fixes ===\n")
        fix_n_cores(violations)
        print("\nRe-validating after fix...")
        result2 = ValidationResult()
        check_n_cores(result2)
        print(result2.report())

    # Run submission tests if integrity passes (or after fix)
    if not args.skip_tests:
        if result.all_passed or args.fix:
            tests_passed, cycles = run_submission_tests()
            report_performance(cycles)
            if not tests_passed:
                print("\nSubmission tests FAILED. Solution produces incorrect results.")
                sys.exit(2)
        else:
            print("\nSkipping submission tests due to integrity failures.")
            print("Run with --fix to repair and test.")
            sys.exit(1)


if __name__ == "__main__":
    main()
