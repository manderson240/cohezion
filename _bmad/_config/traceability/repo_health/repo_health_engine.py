#!/usr/bin/env python3
"""
Automated Repository Health Monitor

Monitors repository health across multiple dimensions:
- Code quality (lint errors, type errors)
- Test coverage (passing tests, coverage %)
- Technical debt (TODOs, FIXMEs, complexity)
- Dependency health (outdated, vulnerabilities)
- Git health (stale branches, large files)
- Documentation health (missing docs, outdated)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


# Add traceability directory to path for both module and script execution
TRACEABILITY_DIR = Path(__file__).parent.parent
if str(TRACEABILITY_DIR) not in sys.path:
    sys.path.insert(0, str(TRACEABILITY_DIR))

from base_engine import EngineConfig


@dataclass
class CodeQualityMetrics:
    """Code quality metrics."""

    lint_errors: int = 0
    lint_warnings: int = 0
    type_errors: int = 0
    format_issues: int = 0
    complexity_avg: float = 0.0
    lines_of_code: int = 0


@dataclass
class TestHealthMetrics:
    """Test health metrics."""

    total_tests: int = 0
    passing_tests: int = 0
    failing_tests: int = 0
    skipped_tests: int = 0
    coverage_percent: float = 0.0
    test_duration_avg: float = 0.0


@dataclass
class TechDebtMetrics:
    """Technical debt metrics."""

    todo_count: int = 0
    fixme_count: int = 0
    hack_count: int = 0
    xxx_count: int = 0
    high_complexity_files: List[str] = field(default_factory=list)
    long_files: List[str] = field(default_factory=list)


@dataclass
class DependencyHealthMetrics:
    """Dependency health metrics."""

    total_deps: int = 0
    outdated_deps: int = 0
    vulnerable_deps: int = 0
    unused_deps: int = 0
    missing_deps: int = 0


@dataclass
class GitHealthMetrics:
    """Git repository health metrics."""

    total_branches: int = 0
    stale_branches: int = 0
    untracked_files: int = 0
    uncommitted_changes: int = 0
    large_files: List[str] = field(default_factory=list)
    merge_conflicts: int = 0


@dataclass
class DocumentationHealthMetrics:
    """Documentation health metrics."""

    total_modules: int = 0
    documented_modules: int = 0
    doc_coverage_percent: float = 0.0
    missing_readmes: List[str] = field(default_factory=list)
    outdated_docs: List[str] = field(default_factory=list)


@dataclass
class RepoHealthReport:
    """Complete repository health report."""

    timestamp: str = ""
    overall_health_score: float = 0.0
    code_quality: CodeQualityMetrics = field(default_factory=CodeQualityMetrics)
    test_health: TestHealthMetrics = field(default_factory=TestHealthMetrics)
    tech_debt: TechDebtMetrics = field(default_factory=TechDebtMetrics)
    dependency_health: DependencyHealthMetrics = field(default_factory=DependencyHealthMetrics)
    git_health: GitHealthMetrics = field(default_factory=GitHealthMetrics)
    documentation_health: DocumentationHealthMetrics = field(
        default_factory=DocumentationHealthMetrics
    )
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class RepoHealthEngine:
    """Repository health monitoring engine."""

    def __init__(self, project_root: Optional[Path] = None, config: Optional[EngineConfig] = None):
        # Support both old API and new DI pattern
        if config:
            self.config = config
            self.project_root = config.project_root
            self.output_dir = config.output_dir
        else:
            self.project_root = project_root or Path("/home/mike-anderson/dev/cohezion")
            self.output_dir = (
                self.project_root / "_bmad" / "_config" / "traceability" / "repo_health"
            )
            self.config = None

        # Setup logging
        import logging

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_command(
        self, cmd: List[str], timeout: Optional[int] = None, capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """Run shell command with error handling."""
        import subprocess

        timeout = timeout or 300
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                cwd=self.project_root,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(cmd[:3])}")
            return -1, "", f"Timeout after {timeout}s"
        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            return -1, "", str(e)

    def run_command(
        self, cmd: List[str], timeout: Optional[int] = None, capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """Run shell command with enhanced error handling."""
        import subprocess

        timeout = timeout or 300
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                cwd=self.project_root,
                timeout=timeout,
            )
            if result.returncode == -1:
                self.logger.warning(f"Command failed: {' '.join(cmd[:3])}")
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(cmd[:3])}")
            return -1, "", f"Timeout after {timeout}s"
        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            return -1, "", str(e)

    def check_code_quality(self) -> CodeQualityMetrics:
        """Check code quality using ruff and mypy."""
        metrics = CodeQualityMetrics()

        # Run ruff check
        returncode, stdout, stderr = self.run_command(
            ["uv", "run", "ruff", "check", "src/cohezion", "--output-format=json"]
        )
        if returncode == 0 or stdout:
            try:
                issues = json.loads(stdout) if stdout else []
                metrics.lint_errors = len([i for i in issues if i.get("level") == "error"])
                metrics.lint_warnings = len([i for i in issues if i.get("level") == "warning"])
            except json.JSONDecodeError:
                # Fallback: parse text output
                metrics.lint_errors = stdout.count("error")
                metrics.lint_warnings = stdout.count("warning")

        # Run mypy
        returncode, stdout, stderr = self.run_command(
            ["uv", "run", "mypy", "src/cohezion", "--no-error-summary"]
        )
        metrics.type_errors = len([line for line in stdout.split("\n") if "error:" in line])

        # Count lines of code (inline - no BaseEngine dependency)
        py_files = list((self.project_root / "src" / "cohezion").glob("**/*.py"))
        metrics.lines_of_code = sum(
            len((f.read_text(encoding="utf-8") if f.exists() else "").split("\n")) for f in py_files
        )

        return metrics

    def check_test_health(
        self, skip_full_run: bool = False, cached_coverage: Optional[float] = None
    ) -> TestHealthMetrics:
        """Check test health."""
        metrics = TestHealthMetrics()

        # Run pytest with --collect-only to count tests (fast)
        returncode, stdout, stderr = self.run_command(
            ["uv", "run", "pytest", "tests/", "--collect-only", "-q"], timeout=60
        )
        match = re.search(r"(\d+) tests? collected", stdout)
        if match:
            metrics.total_tests = int(match.group(1))

        if not skip_full_run:
            # Run actual tests to get pass/fail counts (slow - optional)
            returncode, stdout, stderr = self.run_command(
                ["uv", "run", "pytest", "tests/fast", "-v", "--tb=no"], timeout=300
            )
            metrics.passing_tests = stdout.count(" PASSED")
            metrics.failing_tests = stdout.count(" FAILED")
            metrics.skipped_tests = stdout.count(" SKIPPED")

            # Get coverage (slow - optional)
            returncode, stdout, stderr = self.run_command(
                ["uv", "run", "pytest", "tests/fast", "--cov=src/cohezion", "-q"], timeout=300
            )
            match = re.search(r"TOTAL.*?(\d+)%", stdout)
            if match:
                metrics.coverage_percent = int(match.group(1))
            else:
                metrics.coverage_percent = cached_coverage or 0.0
        else:
            # Use cached coverage if provided, otherwise mark as estimated
            metrics.coverage_percent = cached_coverage if cached_coverage is not None else 0.0
            metrics.passing_tests = metrics.total_tests
            self.logger.warning("Test health check skipped, using cached/estimated coverage")

        return metrics

    def check_tech_debt(self) -> TechDebtMetrics:
        """Check technical debt markers."""
        metrics = TechDebtMetrics()

        py_files = list((self.project_root / "src" / "cohezion").glob("**/*.py"))

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                metrics.todo_count += len(re.findall(r"\bTODO\b", content))
                metrics.fixme_count += len(re.findall(r"\bFIXME\b", content))
                metrics.hack_count += len(re.findall(r"\bHACK\b", content))
                metrics.xxx_count += len(re.findall(r"\bXXX\b", content))

                # Long files (>500 lines)
                lines = len(content.split("\n"))
                if lines > 500:
                    metrics.long_files.append(str(py_file.relative_to(self.project_root)))

            except Exception:
                pass

        return metrics

    def check_dependency_health(self) -> DependencyHealthMetrics:
        """Check dependency health."""
        metrics = DependencyHealthMetrics()

        # Check pyproject.toml for dependencies
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8")
            # Count dependencies
            deps_section = re.search(
                r"\[project\.optional-dependencies\](.*?)(?=^\[|\Z)",
                content,
                re.MULTILINE | re.DOTALL,
            )
            if deps_section:
                metrics.total_deps = len(re.findall(r"^\w+", deps_section.group(1), re.MULTILINE))

        # Check for outdated dependencies
        returncode, stdout, stderr = self.run_command(["uv", "pip", "list", "--outdated"])
        metrics.outdated_deps = len(stdout.split("\n")) - 2  # Subtract header lines

        # Check uv.lock
        lock_file = self.project_root / "uv.lock"
        if lock_file.exists():
            lock_content = lock_file.read_text(encoding="utf-8")
            metrics.total_deps = len(re.findall(r'name\s*=\s*"([^"]+)"', lock_content))

        return metrics

    def check_git_health(self) -> GitHealthMetrics:
        """Check Git repository health."""
        metrics = GitHealthMetrics()

        # Count branches
        returncode, stdout, stderr = self.run_command(["git", "branch", "-a"])
        metrics.total_branches = len(stdout.strip().split("\n"))

        # Check for untracked files
        returncode, stdout, stderr = self.run_command(["git", "status", "--porcelain"])
        untracked = [line for line in stdout.split("\n") if line.startswith("??")]
        metrics.untracked_files = len(untracked)

        # Check for uncommitted changes
        modified = [line for line in stdout.split("\n") if line.startswith(("M", "A", "D"))]
        metrics.uncommitted_changes = len(modified)

        # Find large files (>1MB)
        for pattern in ["**/*"]:
            for file in self.project_root.glob(pattern):
                if file.is_file() and file.stat().st_size > 1024 * 1024:
                    rel_path = str(file.relative_to(self.project_root))
                    if not rel_path.startswith((".git", ".venv", "node_modules")):
                        metrics.large_files.append(rel_path)

        return metrics

    def check_documentation_health(self) -> DocumentationHealthMetrics:
        """Check documentation health."""
        metrics = DocumentationHealthMetrics()

        # Count Python modules
        py_files = list((self.project_root / "src" / "cohezion").glob("**/*.py"))
        metrics.total_modules = len(py_files)

        # Check for docstrings
        documented = 0
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                if '"""' in content or "'''" in content:
                    documented += 1
            except Exception:
                pass

        metrics.documented_modules = documented
        metrics.doc_coverage_percent = (documented / len(py_files) * 100) if py_files else 0

        # Check for missing READMEs in directories
        for dir_path in (self.project_root / "src" / "cohezion").iterdir():
            if dir_path.is_dir():
                readme = dir_path / "README.md"
                if not readme.exists():
                    metrics.missing_readmes.append(str(dir_path.relative_to(self.project_root)))

        return metrics

    def calculate_health_score(self, report: RepoHealthReport) -> float:
        """Calculate overall health score (0-100)."""
        scores = []

        # Code quality score (weight: 30)
        quality_score = max(
            0, 100 - (report.code_quality.lint_errors * 2) - report.code_quality.type_errors
        )
        scores.append(quality_score * 0.3)

        # Test health score (weight: 25)
        test_score = report.test_health.coverage_percent
        if report.test_health.failing_tests > 0:
            test_score *= 0.5
        scores.append(test_score * 0.25)

        # Tech debt score (weight: 20)
        debt_score = max(
            0,
            100 - (report.tech_debt.fixme_count * 5) - (report.tech_debt.todo_count * 2),
        )
        scores.append(debt_score * 0.2)

        # Git health score (weight: 15)
        git_score = max(
            0,
            100
            - (report.git_health.untracked_files * 2)
            - (report.git_health.uncommitted_changes * 3),
        )
        scores.append(git_score * 0.15)

        # Documentation score (weight: 10)
        doc_score = report.documentation_health.doc_coverage_percent
        scores.append(doc_score * 0.1)

        return sum(scores)

    def generate_recommendations(self, report: RepoHealthReport) -> None:
        """Generate recommendations based on health metrics."""
        recommendations = []

        if report.code_quality.lint_errors > 10:
            recommendations.append(
                "Run `uv run ruff check src/cohezion --fix` to auto-fix lint issues"
            )

        if report.code_quality.type_errors > 5:
            recommendations.append("Run `uv run mypy src/cohezion` and fix type errors")

        if report.test_health.coverage_percent < 80:
            recommendations.append(
                f"Increase test coverage from {report.test_health.coverage_percent}% to 80%+"
            )

        if report.test_health.failing_tests > 0:
            recommendations.append(
                f"Fix {report.test_health.failing_tests} failing tests immediately"
            )

        if report.tech_debt.fixme_count > 10:
            recommendations.append(f"Address {report.tech_debt.fixme_count} FIXME markers")

        if report.git_health.untracked_files > 20:
            recommendations.append(
                f"Clean up or commit {report.git_health.untracked_files} untracked files"
            )

        if report.git_health.large_files:
            recommendations.append(
                f"Consider moving {len(report.git_health.large_files)} large files to Git LFS"
            )

        if report.documentation_health.doc_coverage_percent < 50:
            recommendations.append("Add docstrings to undocumented modules")

        report.recommendations = recommendations

    def generate_critical_issues(self, report: RepoHealthReport) -> None:
        """Identify critical issues."""
        critical = []

        if report.test_health.failing_tests > 10:
            critical.append(
                f"CRITICAL: {report.test_health.failing_tests} failing tests blocking CI"
            )

        if report.code_quality.type_errors > 20:
            critical.append(
                f"CRITICAL: {report.code_quality.type_errors} type errors indicating broken code"
            )

        if report.tech_debt.fixme_count > 50:
            critical.append(
                f"CRITICAL: {report.tech_debt.fixme_count} FIXMEs indicating technical debt crisis"
            )

        if report.git_health.merge_conflicts > 0:
            critical.append(
                f"CRITICAL: {report.git_health.merge_conflicts} merge conflicts to resolve"
            )

        report.critical_issues = critical

    def generate_warnings(self, report: RepoHealthReport) -> None:
        """Identify warnings."""
        warnings = []

        if 5 <= report.test_health.failing_tests <= 10:
            warnings.append(f"WARNING: {report.test_health.failing_tests} failing tests")

        if 10 <= report.code_quality.lint_errors <= 20:
            warnings.append(f"WARNING: {report.code_quality.lint_errors} lint errors")

        if report.test_health.coverage_percent < 60:
            warnings.append(f"WARNING: Low test coverage ({report.test_health.coverage_percent}%)")

        if report.tech_debt.todo_count > 30:
            warnings.append(f"WARNING: {report.tech_debt.todo_count} TODOs accumulating")

        report.warnings = warnings

    def run_full_health_check(self) -> RepoHealthReport:
        """Execute full repository health check."""
        print("🏥 Repository Health Engine")
        print("=" * 60)

        report = RepoHealthReport(
            timestamp=datetime.now().isoformat(),
        )

        print("Checking code quality...")
        report.code_quality = self.check_code_quality()
        print(
            f"  Lint: {report.code_quality.lint_errors} errors, {report.code_quality.lint_warnings} warnings"
        )
        print(f"  Type errors: {report.code_quality.type_errors}")

        print("Checking test health...")
        report.test_health = self.check_test_health()
        print(
            f"  Tests: {report.test_health.passing_tests}/{report.test_health.total_tests} passing"
        )
        print(f"  Coverage: {report.test_health.coverage_percent}%")

        print("Checking technical debt...")
        report.tech_debt = self.check_tech_debt()
        print(
            f"  Markers: {report.tech_debt.todo_count} TODO, {report.tech_debt.fixme_count} FIXME"
        )

        print("Checking dependency health...")
        report.dependency_health = self.check_dependency_health()
        print(f"  Dependencies: {report.dependency_health.total_deps} total")

        print("Checking Git health...")
        report.git_health = self.check_git_health()
        print(f"  Branches: {report.git_health.total_branches} total")
        print(f"  Untracked: {report.git_health.untracked_files} files")

        print("Checking documentation health...")
        report.documentation_health = self.check_documentation_health()
        print(f"  Doc coverage: {report.documentation_health.doc_coverage_percent}%")

        # Calculate scores
        report.overall_health_score = self.calculate_health_score(report)
        print(f"\n📊 Overall Health Score: {report.overall_health_score:.1f}/100")

        # Generate issues and recommendations
        self.generate_critical_issues(report)
        self.generate_warnings(report)
        self.generate_recommendations(report)

        if report.critical_issues:
            print(f"\n⚠️  CRITICAL ISSUES ({len(report.critical_issues)}):")
            for issue in report.critical_issues:
                print(f"  - {issue}")

        if report.warnings:
            print(f"\n⚠️  WARNINGS ({len(report.warnings)}):")
            for warning in report.warnings:
                print(f"  - {warning}")

        if report.recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(report.recommendations)}):")
            for rec in report.recommendations:
                print(f"  - {rec}")

        return report

    def write_report(self, report: RepoHealthReport) -> Path:
        """Write health report to file."""
        report_file = self.output_dir / f"health_report_{report.timestamp.replace(':', '_')}.json"

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2)

        # Also write markdown summary
        md_file = self.output_dir / "health_report.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("# Repository Health Report\n\n")
            f.write(f"**Generated**: {report.timestamp}\n")
            f.write(f"**Overall Score**: {report.overall_health_score:.1f}/100\n\n")

            f.write("## Code Quality\n")
            f.write(f"- Lint errors: {report.code_quality.lint_errors}\n")
            f.write(f"- Type errors: {report.code_quality.type_errors}\n")
            f.write(f"- LOC: {report.code_quality.lines_of_code}\n\n")

            f.write("## Test Health\n")
            f.write(
                f"- Passing: {report.test_health.passing_tests}/{report.test_health.total_tests}\n"
            )
            f.write(f"- Coverage: {report.test_health.coverage_percent}%\n\n")

            f.write("## Technical Debt\n")
            f.write(f"- TODO: {report.tech_debt.todo_count}\n")
            f.write(f"- FIXME: {report.tech_debt.fixme_count}\n\n")

            f.write("## Git Health\n")
            f.write(f"- Branches: {report.git_health.total_branches}\n")
            f.write(f"- Untracked: {report.git_health.untracked_files}\n\n")

            if report.critical_issues:
                f.write("## ⚠️ Critical Issues\n")
                for issue in report.critical_issues:
                    f.write(f"- {issue}\n")
                f.write("\n")

            if report.recommendations:
                f.write("## 💡 Recommendations\n")
                for rec in report.recommendations:
                    f.write(f"- {rec}\n")

        return report_file


def main():
    """Main entry point."""
    project_root = Path("/home/mike-anderson/dev/cohezion")
    engine = RepoHealthEngine(project_root)

    report = engine.run_full_health_check()
    report_file = engine.write_report(report)

    print(f"\n📄 Report written to: {report_file}")
    print("\n✅ Repository health check complete!")


if __name__ == "__main__":
    main()
