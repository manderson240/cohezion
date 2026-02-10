#!/usr/bin/env python3
"""
Pre-Deployment Checklist - Cohezion Framework

Automated verification script to validate that all systems are ready
for production deployment.

Run: uv run python scripts/pre_deployment_checklist.py
"""

import subprocess
import sys
from pathlib import Path

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


class PreDeploymentChecker:
    """Automated pre-deployment verification"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.checks_results = []

    def check(self, name: str, condition: bool, error_msg: str = "") -> None:
        """Record a check result"""
        if condition:
            self.passed += 1
            status = f"{GREEN}✅ PASS{RESET}"
            self.checks_results.append((name, True))
        else:
            self.failed += 1
            status = f"{RED}❌ FAIL{RESET}"
            self.checks_results.append((name, False))
            if error_msg:
                print(f"   Error: {error_msg}")

        print(f"{status} {name}")

    def warn(self, name: str, message: str) -> None:
        """Record a warning"""
        self.warnings += 1
        status = f"{YELLOW}⚠️  WARN{RESET}"
        self.checks_results.append((name, None))
        print(f"{status} {name}")
        print(f"   Info: {message}")

    def run_command(self, cmd: list, description: str) -> tuple[bool, str]:
        """Run a shell command and return success/output"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, f"Command timed out: {' '.join(cmd)}"
        except Exception as e:
            return False, str(e)

    def check_python_version(self) -> None:
        """Check 1: Python 3.13+ available"""
        print(f"\n{BOLD}1. PYTHON VERSION{RESET}")

        success, output = self.run_command(
            ["python3", "--version"],
            "Check Python version",
        )

        if not success:
            self.check("Python 3.13+ installed", False, "Python not found")
            return

        # Parse version
        try:
            version_str = output.split()[-1]
            major, minor, *_ = version_str.split(".")
            major, minor = int(major), int(minor)

            is_valid = major > 3 or (major == 3 and minor >= 13)
            self.check(
                f"Python 3.13+ installed (found: {version_str})",
                is_valid,
                f"Python 3.13+ required, found {version_str}",
            )
        except Exception as e:
            self.check("Python 3.13+ installed", False, str(e))

    def check_uv_available(self) -> None:
        """Check 2: UV package manager available"""
        print(f"\n{BOLD}2. PACKAGE MANAGER{RESET}")

        success, output = self.run_command(["uv", "--version"], "Check UV version")
        self.check("UV package manager available", success, output if not success else "")

    def check_framework_imports(self) -> None:
        """Check 3: Framework imports successfully"""
        print(f"\n{BOLD}3. FRAMEWORK IMPORTS{RESET}")

        # Try importing core modules
        imports = [
            ("CompoundExecutor", "from cohezion.compound.executor import CompoundExecutor"),
            ("SemanticCache", "from cohezion.cache.semantic_cache import SemanticCache"),
            ("GuardrailPipeline", "from cohezion.security.guardrail_pipeline import GuardrailPipeline"),
            ("TeamOrchestrator", "from cohezion.compound.team_orchestrator import TeamOrchestrator"),
        ]

        all_pass = True
        for name, import_stmt in imports:
            try:
                exec(import_stmt)
                self.check(f"{name} imports", True)
            except ImportError as e:
                self.check(f"{name} imports", False, str(e))
                all_pass = False

        if all_pass:
            print(f"   All core modules import successfully")

    def check_test_suite(self) -> None:
        """Check 4-6: Test suite status"""
        print(f"\n{BOLD}4. TEST SUITE VERIFICATION{RESET}")

        # Run pytest on key test directories
        success, output = self.run_command(
            ["uv", "run", "pytest", "tests/compound/", "-q", "--tb=no"],
            "Run compound tests",
        )

        if success:
            # Try to extract test count
            if "passed" in output:
                self.check("Compound tests passing", True, output.split("\n")[-1])
            else:
                self.check("Compound tests passing", True)
        else:
            self.check("Compound tests passing", False, "Some tests failed")

        # Cache tests
        success_cache, output_cache = self.run_command(
            ["uv", "run", "pytest", "tests/cache/", "-q", "--tb=no"],
            "Run cache tests",
        )

        if success_cache:
            self.check("Cache tests passing", True, output_cache.split("\n")[-1] if output_cache else "")
        else:
            self.check("Cache tests passing", False, "Some tests failed")

        # Security tests
        success_sec, output_sec = self.run_command(
            ["uv", "run", "pytest", "tests/security/", "-q", "--tb=no"],
            "Run security tests",
        )

        if success_sec:
            self.check("Security tests passing", True, output_sec.split("\n")[-1] if output_sec else "")
        else:
            self.check("Security tests passing", False, "Some tests failed")

    def check_build_artifact(self) -> None:
        """Check 7: Build artifact creation"""
        print(f"\n{BOLD}5. BUILD ARTIFACT{RESET}")

        # Check if dist directory exists
        dist_dir = Path("dist")
        if dist_dir.exists():
            tar_files = list(dist_dir.glob("cohezion-*.tar.gz"))
            if tar_files:
                artifact = tar_files[0]
                size_mb = artifact.stat().st_size / (1024 * 1024)
                self.check(f"Build artifact exists", True, f"Size: {size_mb:.1f} MB")
            else:
                self.warn("Build artifact", "No tar.gz found in dist/ - run 'uv build' to create")
        else:
            self.warn("Build artifact", "dist/ directory not found - run 'uv build' to create")

    def check_git_status(self) -> None:
        """Check 8: Git status clean"""
        print(f"\n{BOLD}6. GIT STATUS{RESET}")

        success, output = self.run_command(
            ["git", "status", "--porcelain"],
            "Check git status",
        )

        if success:
            if output.strip():
                self.warn("Git working tree clean", f"Found uncommitted changes:\n{output}")
            else:
                self.check("Git working tree clean", True)
        else:
            self.check("Git status readable", False, "Git command failed")

    def check_configuration(self) -> None:
        """Check 9: Configuration files present"""
        print(f"\n{BOLD}7. CONFIGURATION{RESET}")

        config_files = [
            "src/cohezion/core/config_templates.py",
            ".env.example",
            "pyproject.toml",
        ]

        for config_file in config_files:
            config_path = Path(config_file)
            self.check(f"Config file exists: {config_file}", config_path.exists())

    def check_security_config(self) -> None:
        """Check 10: Security configuration"""
        print(f"\n{BOLD}8. SECURITY CONFIGURATION{RESET}")

        # Check for pre-commit config
        precommit_path = Path(".pre-commit-config.yaml")
        self.check(".pre-commit-config.yaml exists", precommit_path.exists())

        # Check for security tools in requirements
        try:
            with open("pyproject.toml", "r") as f:
                content = f.read()
                has_bandit = "bandit" in content
                has_detect_secrets = "detect-secrets" in content

                self.check("Bandit security scanner configured", has_bandit)
                self.check("Detect-secrets credential scanner configured", has_detect_secrets)
        except Exception:
            self.warn("Security tools", "Could not verify security tool configuration")

    def run_all_checks(self) -> None:
        """Run all pre-deployment checks"""
        print(f"\n{BOLD}{'=' * 70}{RESET}")
        print(f"{BOLD}COHEZION FRAMEWORK - PRE-DEPLOYMENT CHECKLIST{RESET}")
        print(f"{BOLD}{'=' * 70}{RESET}\n")

        self.check_python_version()
        self.check_uv_available()
        self.check_framework_imports()
        self.check_test_suite()
        self.check_build_artifact()
        self.check_git_status()
        self.check_configuration()
        self.check_security_config()

        # Summary
        print(f"\n{BOLD}{'=' * 70}{RESET}")
        print(f"{BOLD}SUMMARY{RESET}")
        print(f"{BOLD}{'=' * 70}{RESET}\n")

        print(f"{GREEN}✅ PASSED: {self.passed}{RESET}")
        if self.warnings:
            print(f"{YELLOW}⚠️  WARNINGS: {self.warnings}{RESET}")
        if self.failed:
            print(f"{RED}❌ FAILED: {self.failed}{RESET}")

        # Determine overall status
        print()
        if self.failed == 0:
            print(f"{GREEN}{BOLD}✅ ALL CHECKS PASSED - READY FOR DEPLOYMENT{RESET}")
            return 0
        else:
            print(f"{RED}{BOLD}❌ SOME CHECKS FAILED - FIX ISSUES BEFORE DEPLOYMENT{RESET}")
            return 1

    def show_details(self) -> None:
        """Show detailed check results"""
        print(f"\n{BOLD}DETAILED RESULTS{RESET}")
        print("-" * 70)
        for name, result in self.checks_results:
            if result is True:
                status = f"{GREEN}✅{RESET}"
            elif result is False:
                status = f"{RED}❌{RESET}"
            else:
                status = f"{YELLOW}⚠️{RESET}"
            print(f"{status} {name}")


def main() -> int:
    """Main entry point"""
    checker = PreDeploymentChecker()
    exit_code = checker.run_all_checks()

    if exit_code == 0:
        print(f"\n{GREEN}{BOLD}Ready to proceed with deployment!{RESET}\n")
        print("Next steps:")
        print("1. Review COMPREHENSIVE_DEPLOYMENT_RUNBOOK.md")
        print("2. Verify infrastructure is prepared (SurrealDB, Ollama, etc.)")
        print("3. Execute canary deployment per runbook Phase 2")
        print("4. Monitor metrics for 7 days per runbook Phase 4")
    else:
        print(f"\n{RED}{BOLD}Fix the above issues before proceeding.{RESET}\n")
        print("See COMPREHENSIVE_DEPLOYMENT_RUNBOOK.md for troubleshooting.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
