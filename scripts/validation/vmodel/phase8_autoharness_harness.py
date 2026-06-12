#!/usr/bin/env python3
"""V-Model Phase 8 — AutoHarness Verification Harness.

Deterministic gatekeeper that verifies the 5 invariants from
``docs/vmodel/PHASE8_AUTOHARNESS_PLAN.md`` for a target validation script.

Accepts a file argument and runs lint, type-check, and skill validation on it.
Outputs JSON to stdout.

Usage: python scripts/validation/vmodel/phase8_autoharness_harness.py <target_file>
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _run_script(name: str, args: list[str], timeout: int) -> dict:
    """Run a python script under uv and capture results."""
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            ["uv", "run", "python", *args],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.perf_counter() - t0
        return {
            "check": name,
            "passed": result.returncode == 0,
            "elapsed_s": round(elapsed, 3),
            "exit_code": result.returncode,
            "detail": _extract_detail(result.stdout) if result.returncode == 0 else "FAILED",
        }
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - t0
        return {
            "check": name,
            "passed": False,
            "elapsed_s": round(elapsed, 3),
            "detail": f"Timed out after {timeout}s",
        }
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return {
            "check": name,
            "passed": False,
            "elapsed_s": round(elapsed, 3),
            "detail": str(exc),
        }


def _extract_detail(stdout: str) -> str:
    """Extract a concise detail summary from validate output."""
    lines = stdout.strip().splitlines()
    for line in lines:
        if line.startswith("OK:") or "OK," in line:
            return line.strip()
    return "completed"


def _run_lint(file_path: str) -> dict:
    """Run ruff lint on the target file."""
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            ["uv", "run", "ruff", "check", file_path],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        elapsed = time.perf_counter() - t0
        passed = result.returncode == 0
        return {
            "check": "lint",
            "passed": passed,
            "elapsed_s": round(elapsed, 3),
            "detail": "clean"
            if passed
            else (result.stderr.splitlines()[0][:200] if result.stderr else "lint errors"),
        }
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return {
            "check": "lint",
            "passed": False,
            "elapsed_s": round(elapsed, 3),
            "detail": str(exc),
        }


def _run_typecheck(file_path: str) -> dict:
    """Run mypy on the target file."""
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            ["uv", "run", "mypy", file_path, "--ignore-missing-imports"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )

        elapsed = time.perf_counter() - t0
        passed = result.returncode == 0
        return {
            "check": "typecheck",
            "passed": passed,
            "elapsed_s": round(elapsed, 3),
            "detail": "clean" if passed else (result.stdout[:200].strip() or "type errors"),
        }
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return {
            "check": "typecheck",
            "passed": False,
            "elapsed_s": round(elapsed, 3),
            "detail": str(exc),
        }


def main() -> int:
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {
                    "passed": False,
                    "file": "",
                    "checks": [],
                    "elapsed_s": 0.0,
                    "error": "Missing target file argument",
                },
                indent=2,
            )
        )
        return 1

    target = sys.argv[1]
    t0 = time.perf_counter()
    checks: list[dict] = []

    checks.append(_run_lint(target))
    checks.append(_run_typecheck(target))

    script_path = Path(target)
    if script_path.name == "validate_skills.py":
        checks.append(_run_script("validate_skills", ["scripts/ci/validate_skills.py"], timeout=60))

    checks.append(_run_script("p2_registry", ["scripts/ci/validate_registry.py"], timeout=30))

    elapsed = time.perf_counter() - t0
    passed = all(c.get("passed", False) for c in checks)

    output = {
        "passed": passed,
        "file": target,
        "checks": checks,
        "elapsed_s": round(elapsed, 3),
    }
    print(json.dumps(output, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
