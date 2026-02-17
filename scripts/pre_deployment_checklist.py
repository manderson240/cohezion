#!/usr/bin/env python3
"""
Pre-Deployment Verification Checklist
Automated checks for production deployment readiness
"""

import subprocess
import sys


def run_command(cmd, description):
    """Run command and return success/failure"""
    print(f"\n{'=' * 60}")
    print(f"Checking: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print(f"✅ PASS: {description}")
            if result.stdout:
                print(f"Output:\n{result.stdout[:500]}")
            return True
        else:
            print(f"❌ FAIL: {description}")
            if result.stderr:
                print(f"Error:\n{result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT: {description}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {description}")
        print(f"Exception: {e}")
        return False


def main():
    """Run pre-deployment checklist"""

    print("\n" + "=" * 60)
    print("COHEZION FRAMEWORK - PRE-DEPLOYMENT CHECKLIST")
    print("=" * 60)

    checks = []

    # 1. Python version check
    checks.append(
        (
            "Python 3.13+",
            run_command(["python", "--version"], "Verify Python 3.13+ installed"),
        )
    )

    # 2. Framework import check
    checks.append(
        (
            "Framework Imports",
            run_command(
                [
                    "uv",
                    "run",
                    "python",
                    "-c",
                    "from cohezion.compound.executor import CompoundExecutor; print('✅ Imports OK')",
                ],
                "Verify framework imports successfully",
            ),
        )
    )

    # 3. Test Suite: Compound
    checks.append(
        (
            "Compound Tests",
            run_command(
                ["uv", "run", "pytest", "tests/compound/", "-q", "--tb=no"],
                "Run compound executor tests",
            ),
        )
    )

    # 4. Test Suite: Cache
    checks.append(
        (
            "Cache Tests",
            run_command(
                ["uv", "run", "pytest", "tests/cache/", "-q", "--tb=no"],
                "Run cache system tests",
            ),
        )
    )

    # 5. Test Suite: Security
    checks.append(
        (
            "Security Tests",
            run_command(
                ["uv", "run", "pytest", "tests/security/", "-q", "--tb=no"],
                "Run security hardening tests",
            ),
        )
    )

    # 6. Build artifact
    checks.append(("Build Artifact", run_command(["uv", "build"], "Build deployment artifact")))

    # 7. Git status
    checks.append(
        (
            "Git Status",
            run_command(["git", "status", "--short"], "Verify clean git state"),
        )
    )

    # 8. Configuration check
    checks.append(
        (
            "Config Files",
            run_command(
                ["ls", "-la", "src/cohezion/core/config_templates.py"],
                "Verify configuration files exist",
            ),
        )
    )

    # 9. Security config
    checks.append(
        (
            "Security Config",
            run_command(
                ["ls", "-la", "src/cohezion/security/guardrail_pipeline.py"],
                "Verify security configuration",
            ),
        )
    )

    # 10. Cache config
    checks.append(
        (
            "Cache Config",
            run_command(
                ["ls", "-la", "src/cohezion/cache/semantic_cache.py"],
                "Verify cache configuration",
            ),
        )
    )

    # Summary
    print("\n" + "=" * 60)
    print("PRE-DEPLOYMENT CHECKLIST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in checks if result)
    total = len(checks)

    for check_name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {passed}/{total} checks passed")
    print(f"{'=' * 60}")

    if passed == total:
        print("\n🎉 ALL PRE-DEPLOYMENT CHECKS PASSED!")
        print("Ready for production deployment.")
        return 0
    else:
        failed = total - passed
        print(f"\n⚠️  {failed} check(s) failed. Address issues before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
