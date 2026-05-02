#!/usr/bin/env python3
"""Run automated repository health checks."""

import argparse
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    """Result of a single health check."""

    name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """Repository health checker."""

    FILE_SIZE_LIMIT = 500  # Lines
    FILE_SIZE_WARNING = 300  # Lines

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.results: list[CheckResult] = []

    def run_check(self, name: str, cmd: list[str]) -> tuple[bool, str]:
        """Run a command and return success status and output."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                check=False,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except FileNotFoundError:
            return False, f"Command not found: {cmd[0]}"

    def check_ruff(self) -> CheckResult:
        """Check code with ruff."""
        passed, output = self.run_check(
            "ruff",
            ["uv", "run", "ruff", "check", "."],
        )
        return CheckResult(
            name="ruff",
            passed=passed,
            message="Ruff linting passed" if passed else "Ruff found issues",
            details={"output": output[:1000] if not passed else ""},
        )

    def check_pytest(self) -> CheckResult:
        """Run pytest."""
        passed, output = self.run_check(
            "pytest",
            ["uv", "run", "pytest", "-q"],
        )
        # Count tests
        import re

        match = re.search(r"(\d+) passed", output)
        test_count = int(match.group(1)) if match else 0

        return CheckResult(
            name="pytest",
            passed=passed,
            message=f"{test_count} tests passed" if passed else "Tests failed",
            details={
                "test_count": test_count,
                "output": output[:1000] if not passed else "",
            },
        )

    def check_file_sizes(self) -> CheckResult:
        """Check Python file sizes."""
        large_files = []
        warning_files = []

        py_files = list(self.repo_root.rglob("*.py"))
        for py_file in py_files:
            # Skip certain directories
            if any(part.startswith(".") for part in py_file.relative_to(self.repo_root).parts):
                continue

            try:
                lines = len(py_file.read_text().split("\n"))
                if lines > self.FILE_SIZE_LIMIT:
                    large_files.append((py_file.relative_to(self.repo_root), lines))
                elif lines > self.FILE_SIZE_WARNING:
                    warning_files.append((py_file.relative_to(self.repo_root), lines))
            except Exception:
                pass

        large_files.sort(key=lambda x: x[1], reverse=True)
        warning_files.sort(key=lambda x: x[1], reverse=True)

        # Convert paths to strings for JSON serialization
        large_files = [(str(p), lines) for p, lines in large_files]
        warning_files = [(str(p), lines) for p, lines in warning_files]

        passed = len(large_files) == 0

        return CheckResult(
            name="file_sizes",
            passed=passed,
            message="File sizes OK" if passed else f"{len(large_files)} files exceed limit",
            details={
                "large_files": large_files[:10],
                "warning_files": warning_files[:10],
                "limit": self.FILE_SIZE_LIMIT,
                "warning": self.FILE_SIZE_WARNING,
            },
        )

    def check_imports(self) -> CheckResult:
        """Check for common import issues."""
        issues = []

        py_files = list(self.repo_root.rglob("*.py"))
        for py_file in py_files:
            if any(part.startswith(".") for part in py_file.relative_to(self.repo_root).parts):
                continue

            try:
                content = py_file.read_text()
                if "import *" in content:
                    issues.append(f"{py_file.relative_to(self.repo_root)}: wildcard import")
            except Exception:
                pass

        return CheckResult(
            name="imports",
            passed=len(issues) == 0,
            message="Imports OK" if not issues else f"{len(issues)} import issues",
            details={"issues": issues},
        )

    def check_git_status(self) -> CheckResult:
        """Check git repository status."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )

            lines = [l for l in result.stdout.split("\n") if l.strip()]
            untracked = [l for l in lines if l.startswith("??")]
            staged = [l for l in lines if not l.startswith("?")]

            return CheckResult(
                name="git_status",
                passed=True,
                message=f"Git status: {len(staged)} staged, {len(untracked)} untracked",
                details={
                    "staged": len(staged),
                    "untracked": len(untracked),
                    "untracked_files": [l[3:] for l in untracked[:5]],
                },
            )
        except Exception as e:
            return CheckResult(
                name="git_status",
                passed=False,
                message=f"Git status check failed: {e}",
            )

    def run_all(self) -> dict:
        """Run all health checks."""
        self.results = [
            self.check_ruff(),
            self.check_pytest(),
            self.check_file_sizes(),
            self.check_imports(),
            self.check_git_status(),
        ]

        failed = [r for r in self.results if not r.passed]

        return {
            "overall": "healthy" if not failed else "unhealthy",
            "passed": len(self.results) - len(failed),
            "failed": len(failed),
            "total": len(self.results),
            "checks": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details,
                }
                for r in self.results
            ],
        }


def main():
    parser = argparse.ArgumentParser(description="Repository health check")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: cwd)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    checker = HealthChecker(args.repo.resolve())
    report = checker.run_all()

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Repository Health Report: {report['overall'].upper()}")
        print(f"  Passed: {report['passed']}/{report['total']}")
        print(f"  Failed: {report['failed']}/{report['total']}")
        print()

        for check in report["checks"]:
            status = "PASS" if check["passed"] else "FAIL"
            print(f"  [{status}] {check['name']}: {check['message']}")
            if not check["passed"] and check.get("details"):
                if "large_files" in check["details"]:
                    for f, lines in check["details"]["large_files"]:
                        print(f"         - {f} ({lines} lines)")
                if "output" in check["details"] and check["details"]["output"]:
                    print(f"         Output: {check['details']['output'][:200]}...")

    return 0 if report["overall"] == "healthy" else 1


if __name__ == "__main__":
    exit(main())
